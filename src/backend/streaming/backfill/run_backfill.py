"""Backfill driver: probe index, compute equal-doc time windows, fan out workers,
write the cutover marker on success.

Run: `python -m backfill.run_backfill`
"""

from __future__ import annotations

import json
import logging
import multiprocessing as mp
import sys
import time
from datetime import datetime, timezone
from typing import Any

from common.config import Config
from common.os_client import make_client
from common.s3 import get_json, put_json, s3_client

from .window_worker import run_window

log = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _detect_ts_field(client, index: str, candidates: list[str]) -> str:
    """Return the first candidate field that exists and has a non-null min agg."""
    for field in candidates:
        try:
            r = client.search(
                index=index,
                body={"size": 0, "aggs": {"probe": {"min": {"field": field}}}},
            )
            if r["aggregations"]["probe"]["value"] is not None:
                log.info("auto-detected timestamp field: %s", field)
                return field
        except Exception:
            pass
    # last resort: sample one doc and print its keys to help debug
    sample = client.search(index=index, body={"size": 1})
    hits = sample.get("hits", {}).get("hits", [])
    keys = list(hits[0]["_source"].keys()) if hits else []
    raise RuntimeError(
        f"Could not find a usable timestamp field in {candidates}. "
        f"Sample document keys: {keys}. "
        f"Set OPENSEARCH_TS_FIELD to the correct field name."
    )


def _probe_bounds(client, index: str, ts_field: str) -> tuple[str, str, str, int]:
    """Return (ts_field_actual, min_ts, max_ts, total_docs).

    Auto-detects the timestamp field if the configured one returns null.
    """
    candidates = [ts_field, "@timestamp", "timestamp", "time", "event_time"]
    # deduplicate while preserving order
    seen: set[str] = set()
    ordered = [c for c in candidates if not (c in seen or seen.add(c))]  # type: ignore[func-returns-value]

    actual_field = _detect_ts_field(client, index, ordered)

    r = client.search(
        index=index,
        body={
            "size": 0,
            "track_total_hits": True,
            "aggs": {
                "min_ts": {"min": {"field": actual_field}},
                "max_ts": {"max": {"field": actual_field}},
            },
        },
    )
    total = r["hits"]["total"]["value"]
    min_ms = r["aggregations"]["min_ts"]["value"]
    max_ms = r["aggregations"]["max_ts"]["value"]
    min_iso = datetime.fromtimestamp(min_ms / 1000, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    max_iso = datetime.fromtimestamp(max_ms / 1000, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return actual_field, min_iso, max_iso, total


def _equal_doc_windows(client, cfg: Config, total_docs: int, ts_field: str) -> list[tuple[str, str]]:
    """Use a 1-hour date_histogram to build N windows of ~equal doc counts."""
    target = max(1, total_docs // cfg.backfill_windows)
    r = client.search(
        index=cfg.opensearch_index,
        body={
            "size": 0,
            "aggs": {
                "h": {
                    "date_histogram": {
                        "field": ts_field,
                        "fixed_interval": "1h",
                        "min_doc_count": 1,
                    }
                }
            },
        },
    )
    buckets = r["aggregations"]["h"]["buckets"]
    if not buckets:
        raise RuntimeError("date_histogram returned no buckets")

    boundaries: list[str] = [buckets[0]["key_as_string"]]
    running = 0
    for b in buckets:
        running += b["doc_count"]
        if running >= target and len(boundaries) < cfg.backfill_windows:
            boundaries.append(b["key_as_string"])
            running = 0
    boundaries.append(_iso_plus_hours(buckets[-1]["key_as_string"], 1))
    return list(zip(boundaries[:-1], boundaries[1:]))


def _iso_plus_hours(ts_iso: str, hours: int) -> str:
    from datetime import timedelta

    dt = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
    return (dt + timedelta(hours=hours)).isoformat().replace("+00:00", "Z")


def _notify_sqs(cfg: Config, cutover_ts: str) -> None:
    """Send a wake-up message to SQS so the stream job starts immediately.
    Non-fatal: a failure here must not abort the backfill."""
    if not cfg.stream_sqs_queue_url:
        return
    try:
        import boto3
        sqs = boto3.client("sqs", region_name=cfg.aws_region)
        sqs.send_message(
            QueueUrl=cfg.stream_sqs_queue_url,
            MessageBody=json.dumps({"event": "backfill_complete", "cutover_ts": cutover_ts}),
        )
        log.info("sent backfill_complete wake-up to SQS")
    except Exception:
        log.warning("SQS notify failed (non-fatal)", exc_info=True)


def _open_pit(client, index: str) -> str:
    r = client.create_point_in_time(index=index, params={"keep_alive": "10m"})
    return r["pit_id"]


def _close_pit(client, pit_id: str) -> None:
    try:
        client.delete_point_in_time(body={"pit_id": pit_id})
    except Exception:
        log.warning("failed to close PIT, will expire on its own", exc_info=True)


def _worker_entry(args: tuple[int, str, str, str, str]) -> dict[str, Any]:
    window_id, t_start, t_end, pit_id, ts_field = args
    logging.basicConfig(level=logging.INFO, format=f"%(asctime)s w{window_id:03d} %(message)s")
    return run_window(window_id, t_start, t_end, pit_id, ts_field)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [backfill] %(message)s")
    cfg = Config.load()
    client = make_client(cfg)
    s3 = s3_client(cfg.aws_region)

    cutover_key = f"{cfg.s3_meta_prefix}/cutover.json"
    if get_json(s3, cfg.s3_raw_bucket, cutover_key):
        log.info("cutover.json already present — backfill considered done; exiting")
        return 0

    log.info("probing index %s (ts_field=%s) ...", cfg.opensearch_index, cfg.opensearch_ts_field)
    actual_ts_field, min_ts, max_ts, total = _probe_bounds(client, cfg.opensearch_index, cfg.opensearch_ts_field)
    if actual_ts_field != cfg.opensearch_ts_field:
        log.warning("OPENSEARCH_TS_FIELD was %r — auto-detected field is %r, using that instead",
                    cfg.opensearch_ts_field, actual_ts_field)
    log.info("min=%s max=%s total=%d ts_field=%s", min_ts, max_ts, total, actual_ts_field)

    windows = _equal_doc_windows(client, cfg, total, actual_ts_field)
    log.info("computed %d windows", len(windows))
    for i, (a, b) in enumerate(windows):
        log.info("  w%03d  [%s, %s)", i, a, b)

    pit_id = _open_pit(client, cfg.opensearch_index)
    log.info("opened PIT")
    started = time.time()
    try:
        with mp.Pool(processes=len(windows)) as pool:
            results = pool.map(
                _worker_entry,
                [(i, a, b, pit_id, actual_ts_field) for i, (a, b) in enumerate(windows)],
            )
    finally:
        _close_pit(client, pit_id)

    elapsed = time.time() - started
    docs_total = sum(r["docs"] for r in results)
    parts_total = sum(r["parts"] for r in results)
    max_ts_seen = max((r["max_ts"] for r in results if r["max_ts"]), default=max_ts)
    log.info("backfill done: %d docs in %d parts across %d windows in %.1fs",
             docs_total, parts_total, len(results), elapsed)

    put_json(
        s3,
        cfg.s3_raw_bucket,
        cutover_key,
        {
            "cutover_ts": max_ts_seen,
            "doc_count": docs_total,
            "windows": len(results),
            "parts": parts_total,
            "duration_sec": round(elapsed, 1),
            "completed_at": _now_iso(),
        },
    )
    log.info("wrote s3://%s/%s", cfg.s3_raw_bucket, cutover_key)
    _notify_sqs(cfg, max_ts_seen)
    return 0


if __name__ == "__main__":
    sys.exit(main())
