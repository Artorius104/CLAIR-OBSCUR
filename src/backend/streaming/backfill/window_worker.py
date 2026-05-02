"""One backfill worker — drains a single time window in chronological order.

Output JSONL paths follow `logs-raw/dt=YYYY-MM-DD/hour=HH/part-w<n>-<seq>.jsonl`,
bucketed by the FIRST event timestamp in each chunk. Across windows, partitions
do not overlap, so a recursive S3 listing returns files in chronological order.
"""

from __future__ import annotations

import io
import logging
import time
from datetime import datetime, timezone
from typing import Any

import orjson

from common.config import Config
from common.os_client import make_client
from common.s3 import get_json, put_bytes, put_json, s3_client

log = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _bucket_path(ts: str) -> str:
    # Expect ISO8601, e.g. 2026-04-15T14:36:37.694Z
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    return f"dt={dt.strftime('%Y-%m-%d')}/hour={dt.strftime('%H')}"


def _progress_key(cfg: Config, window_id: int) -> str:
    return f"{cfg.s3_backfill_prefix}/window={window_id}/progress.json"


def _part_key(cfg: Config, ts: str, window_id: int, seq: int) -> str:
    return f"{cfg.s3_raw_prefix}/{_bucket_path(ts)}/part-w{window_id:03d}-{seq:08d}.jsonl"


def run_window(window_id: int, t_start: str, t_end: str, pit_id: str, ts_field: str) -> dict[str, Any]:
    """Drain window [t_start, t_end), emit JSONL chunks. Returns summary stats."""
    cfg = Config.load()
    TS_FIELD = ts_field
    s3 = s3_client(cfg.aws_region)
    client = make_client(cfg)

    progress = get_json(s3, cfg.s3_raw_bucket, _progress_key(cfg, window_id)) or {}
    search_after = progress.get("last_sort")
    seq = int(progress.get("parts_written", 0))
    total_docs = int(progress.get("docs_written", 0))
    max_ts_seen: str | None = progress.get("max_ts")

    log.info(
        "window=%d start=%s end=%s resume=%s seq=%d docs=%d",
        window_id, t_start, t_end, bool(search_after), seq, total_docs,
    )

    buf = io.BytesIO()
    buf_first_ts: str | None = None
    pages_since_progress = 0

    def _flush() -> None:
        nonlocal buf, buf_first_ts, seq, total_docs
        if buf.tell() == 0:
            return
        key = _part_key(cfg, buf_first_ts or t_start, window_id, seq)
        put_bytes(s3, cfg.s3_raw_bucket, key, buf.getvalue())
        log.info("window=%d wrote %s (%.1f MiB)", window_id, key, buf.tell() / 1024 / 1024)
        seq += 1
        buf = io.BytesIO()
        buf_first_ts = None

    body: dict[str, Any] = {
        "size": cfg.backfill_page_size,
        "pit": {"id": pit_id, "keep_alive": "10m"},
        "sort": [{TS_FIELD: "asc"}, {"_id": "asc"}],
        "query": {"range": {TS_FIELD: {"gte": t_start, "lt": t_end}}},
        "track_total_hits": False,
    }

    try:
        while True:
            if search_after:
                body["search_after"] = search_after
            r = client.search(body=body)
            hits = r["hits"]["hits"]
            if not hits:
                break

            for h in hits:
                src = h.get("_source", {})
                ts = src.get(TS_FIELD)
                record = {"id": h["_id"], "ingest_ts": _now_iso(), **src}
                line = orjson.dumps(record) + b"\n"

                if buf_first_ts is None:
                    buf_first_ts = ts or t_start

                # roll the chunk if it would exceed target size, OR if hour boundary changes
                if buf.tell() and (
                    buf.tell() + len(line) > cfg.backfill_chunk_bytes
                    or (ts and _bucket_path(ts) != _bucket_path(buf_first_ts))
                ):
                    _flush()
                    buf_first_ts = ts or t_start

                buf.write(line)
                if ts and (max_ts_seen is None or ts > max_ts_seen):
                    max_ts_seen = ts

            search_after = hits[-1]["sort"]
            total_docs += len(hits)
            pages_since_progress += 1

            if pages_since_progress >= cfg.backfill_progress_every_pages:
                _flush()
                put_json(
                    s3,
                    cfg.s3_raw_bucket,
                    _progress_key(cfg, window_id),
                    {
                        "last_sort": search_after,
                        "parts_written": seq,
                        "docs_written": total_docs,
                        "max_ts": max_ts_seen,
                        "updated_at": _now_iso(),
                    },
                )
                pages_since_progress = 0

        _flush()
        put_json(
            s3,
            cfg.s3_raw_bucket,
            _progress_key(cfg, window_id),
            {
                "last_sort": search_after,
                "parts_written": seq,
                "docs_written": total_docs,
                "max_ts": max_ts_seen,
                "completed_at": _now_iso(),
                "done": True,
            },
        )
    except Exception:
        log.exception("window=%d failed", window_id)
        _flush()
        raise

    return {"window_id": window_id, "docs": total_docs, "parts": seq, "max_ts": max_ts_seen}
