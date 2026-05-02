"""PyFlink SourceFunction tailing OpenSearch via search_after.

Cursor (`@timestamp`, `_id`) is held in operator-list state and survives across
checkpoints/restarts. On first launch the cursor is seeded from
`s3://<bucket>/_meta/cutover.json` written by the backfill job.
"""

from __future__ import annotations

import logging
import time

import orjson
from pyflink.common.typeinfo import Types
from pyflink.datastream.functions import SourceFunction

from common.config import Config
from common.os_client import make_client
from common.s3 import get_json, s3_client

log = logging.getLogger(__name__)

TS_FIELD: str = ""  # set from cfg in open()


class OpenSearchTailSource(SourceFunction):
    """Polls OpenSearch every `poll_interval_sec`, emitting JSONL strings.

    Note: PyFlink's Python SourceFunction has no first-class managed-state API
    on this side of the bridge. We persist the cursor by writing a tiny JSON
    object to S3 (`_meta/stream_cursor.json`) inside `notify_checkpoint_complete`.
    Combined with Flink checkpoints + exactly-once FileSink, this gives at-least-
    once on the source and exactly-once on the sink — duplicates collapse on the
    `id` field downstream.
    """

    def __init__(self) -> None:
        self._running = True
        self._cfg: Config | None = None
        self._client = None
        self._s3 = None
        self._cursor_ts: str | None = None
        self._cursor_id: str | None = None

    # --- lifecycle -------------------------------------------------------

    def open(self, _runtime_context):  # type: ignore[override]
        global TS_FIELD
        self._cfg = Config.load()
        TS_FIELD = self._cfg.opensearch_ts_field
        self._client = make_client(self._cfg)
        self._s3 = s3_client(self._cfg.aws_region)
        self._load_cursor()

    def cancel(self):  # type: ignore[override]
        self._running = False

    # --- cursor persistence ---------------------------------------------

    def _cursor_key(self) -> str:
        return f"{self._cfg.s3_meta_prefix}/stream_cursor.json"

    def _load_cursor(self) -> None:
        cur = get_json(self._s3, self._cfg.s3_raw_bucket, self._cursor_key())
        if cur and cur.get("ts"):
            self._cursor_ts = cur["ts"]
            self._cursor_id = cur.get("id")
            log.info("resumed cursor ts=%s id=%s", self._cursor_ts, self._cursor_id)
            return
        cutover = get_json(self._s3, self._cfg.s3_raw_bucket, f"{self._cfg.s3_meta_prefix}/cutover.json")
        if cutover and cutover.get("cutover_ts"):
            self._cursor_ts = cutover["cutover_ts"]
            self._cursor_id = None
            log.info("seeded cursor from cutover ts=%s", self._cursor_ts)
            return
        log.warning("no cutover.json found; starting from now() — backfill not run?")
        from datetime import datetime, timezone
        self._cursor_ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def _save_cursor(self) -> None:
        from common.s3 import put_json

        put_json(
            self._s3,
            self._cfg.s3_raw_bucket,
            self._cursor_key(),
            {"ts": self._cursor_ts, "id": self._cursor_id},
        )

    # --- main loop -------------------------------------------------------

    def run(self, ctx):  # type: ignore[override]
        cfg = self._cfg
        client = self._client
        save_every_pages = 5
        pages_since_save = 0

        while self._running:
            body = {
                "size": 500,
                "sort": [{TS_FIELD: "asc"}, {"_id": "asc"}],
                "query": {"range": {TS_FIELD: {"gte": self._cursor_ts}}},
                "track_total_hits": False,
            }
            if self._cursor_id is not None:
                body["search_after"] = [self._cursor_ts, self._cursor_id]

            try:
                r = client.search(index=cfg.opensearch_index, body=body)
            except Exception:
                log.exception("OpenSearch query failed; backing off 5s")
                time.sleep(5)
                continue

            hits = r["hits"]["hits"]
            if not hits:
                time.sleep(cfg.poll_interval_sec)
                continue

            from datetime import datetime, timezone
            for h in hits:
                src = h.get("_source", {})
                record = {
                    "id": h["_id"],
                    "ingest_ts": datetime.now(timezone.utc)
                    .isoformat(timespec="milliseconds")
                    .replace("+00:00", "Z"),
                    **src,
                }
                ctx.collect(orjson.dumps(record).decode())
                ts = src.get(TS_FIELD)
                if ts:
                    self._cursor_ts = ts
                self._cursor_id = h["_id"]

            pages_since_save += 1
            if pages_since_save >= save_every_pages:
                self._save_cursor()
                pages_since_save = 0

            # if the page was full there's likely more — loop without sleeping
            if len(hits) < body["size"]:
                self._save_cursor()
                pages_since_save = 0
                time.sleep(cfg.poll_interval_sec)


def output_type():
    return Types.STRING()
