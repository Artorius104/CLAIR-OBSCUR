"""Custom Flink Python SinkFunction batching writes into ClickHouse.

Buffers up to `batch_size` records, then issues a single
`INSERT INTO logs_raw (id, timestamp, ingest_ts, raw)` via clickhouse-connect.
Idempotency is provided downstream by ReplacingMergeTree(ingest_ts).
"""

from __future__ import annotations

import logging
from datetime import datetime

import orjson
from pyflink.datastream.functions import SinkFunction

from common.ch_client import insert_log_rows, make_ch_client
from common.config import Config

log = logging.getLogger(__name__)


def _parse_iso(s: str) -> datetime:
    # Accept both "...Z" and "+00:00" suffixes
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class ClickHouseBatchSink(SinkFunction):
    def __init__(self, batch_size: int = 1000) -> None:
        self._batch_size = batch_size
        self._buffer: list[tuple[str, datetime, datetime, str]] = []
        self._client = None

    def open(self, _runtime_context):  # type: ignore[override]
        cfg = Config.load()
        self._client = make_ch_client(cfg)
        log.info(
            "ClickHouseBatchSink ready (host=%s db=%s batch=%d)",
            cfg.clickhouse_host, cfg.clickhouse_database, self._batch_size,
        )

    def invoke(self, value, _context):  # type: ignore[override]
        rec = orjson.loads(value)
        ts_str = rec.get("timestamp")
        if ts_str is None:
            log.warning("record missing timestamp field; dropping")
            return
        self._buffer.append(
            (rec["id"], _parse_iso(ts_str), _parse_iso(rec["ingest_ts"]), value)
        )
        if len(self._buffer) >= self._batch_size:
            self._flush()

    def close(self):  # type: ignore[override]
        self._flush()
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass

    def _flush(self) -> None:
        if not self._buffer:
            return
        try:
            insert_log_rows(self._client, self._buffer)
            log.info("inserted %d rows into logs_raw", len(self._buffer))
        finally:
            self._buffer.clear()
