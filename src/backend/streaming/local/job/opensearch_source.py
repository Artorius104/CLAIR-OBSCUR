"""PyFlink SourceFunction replaying OpenSearch chronologically into ClickHouse.

Cursor (`timestamp`, `_id`) is persisted to `clair_obscur.stream_cursor` in
ClickHouse. On first ever run (cursor table empty), the cursor is seeded from
`min(timestamp)` aggregation on the OpenSearch index — so the job processes
every doc from oldest to newest, then transitions to live tail.

Adapted from `stream/job/opensearch_source.py`. Only the cursor persistence
layer (load/save) differs.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import orjson
from pyflink.datastream.functions import SourceFunction

from common.ch_client import (
    get_stream_cursor,
    make_ch_client,
    seed_min_ts_from_opensearch,
    set_stream_cursor,
)
from common.config import Config
from common.os_client import make_client

log = logging.getLogger(__name__)


class OpenSearchReplaySource(SourceFunction):
    """Polls OpenSearch in `(timestamp, _id)` order, emits JSONL strings.

    PyFlink's Python `SourceFunction` is at-least-once. Combined with the
    ClickHouse `ReplacingMergeTree(ingest_ts)` sink, restarts may emit a few
    duplicate rows — but `SELECT ... FINAL` always returns each `id` once.
    """

    def __init__(self) -> None:
        super().__init__()
        self._running = True
        self._cfg: Config | None = None
        self._os = None
        self._ch = None
        self._ts_field: str = ""
        self._cursor_ts: str | None = None
        self._cursor_id: str | None = None

    def open(self, _runtime_context):  # type: ignore[override]
        self._cfg = Config.load()
        self._ts_field = self._cfg.opensearch_ts_field
        self._os = make_client(self._cfg)
        self._ch = make_ch_client(self._cfg)
        self._load_cursor()

    def cancel(self):  # type: ignore[override]
        self._running = False

    def _load_cursor(self) -> None:
        cur = get_stream_cursor(self._ch)
        if cur and cur.get("ts"):
            self._cursor_ts = cur["ts"]
            self._cursor_id = cur.get("id") or None
            log.info(
                "resumed from CH cursor ts=%s id=%s",
                self._cursor_ts, self._cursor_id,
            )
            return
        self._cursor_ts = seed_min_ts_from_opensearch(
            self._os, self._cfg.opensearch_index, self._ts_field
        )
        self._cursor_id = None
        log.info("first run — seeded from OS min(%s)=%s", self._ts_field, self._cursor_ts)

    def _save_cursor(self) -> None:
        if self._cursor_ts is None:
            return
        set_stream_cursor(self._ch, self._cursor_ts, self._cursor_id or "")

    def run(self, ctx):  # type: ignore[override]
        cfg = self._cfg
        ts_field = self._ts_field
        save_every_pages = 5
        pages_since_save = 0

        while self._running:
            body = {
                "size": 500,
                "sort": [{ts_field: "asc"}, {"_id": "asc"}],
                "query": {"range": {ts_field: {"gte": self._cursor_ts}}},
                "track_total_hits": False,
            }
            if self._cursor_id:
                body["search_after"] = [self._cursor_ts, self._cursor_id]

            try:
                r = self._os.search(index=cfg.opensearch_index, body=body)
            except Exception:
                log.exception("OpenSearch query failed; backing off 5s")
                time.sleep(5)
                continue

            hits = r["hits"]["hits"]
            if not hits:
                time.sleep(cfg.poll_interval_sec)
                continue

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
                ts = src.get(ts_field)
                if ts:
                    self._cursor_ts = ts
                self._cursor_id = h["_id"]

            pages_since_save += 1
            if pages_since_save >= save_every_pages:
                self._save_cursor()
                pages_since_save = 0

            if len(hits) < body["size"]:
                self._save_cursor()
                pages_since_save = 0
                time.sleep(cfg.poll_interval_sec)
