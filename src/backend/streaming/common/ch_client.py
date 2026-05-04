"""ClickHouse helpers for the local ingestion variant.

Mirrors the role of `common/s3.py` in the cloud variant: cursor read/write +
log-row inserts. Uses `clickhouse-connect` over HTTP (port 8123).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import clickhouse_connect

from .config import Config

log = logging.getLogger(__name__)


def make_ch_client(cfg: Config):
    return clickhouse_connect.get_client(
        host=cfg.clickhouse_host,
        port=cfg.clickhouse_port,
        username=cfg.clickhouse_user,
        password=cfg.clickhouse_password,
        database=cfg.clickhouse_database,
        connect_timeout=10,
        send_receive_timeout=120,
    )


def get_stream_cursor(client, component: str = "stream") -> dict[str, str] | None:
    r = client.query(
        "SELECT cursor_ts, cursor_id FROM stream_cursor FINAL WHERE component = %(c)s LIMIT 1",
        parameters={"c": component},
    )
    if r.row_count == 0:
        return None
    row = r.first_row
    return {"ts": row[0], "id": row[1]}


def set_stream_cursor(client, ts: str, id_: str, component: str = "stream") -> None:
    client.insert(
        "stream_cursor",
        [(component, ts, id_)],
        column_names=["component", "cursor_ts", "cursor_id"],
    )


def insert_log_rows(client, rows: list[tuple[str, datetime, datetime, str]]) -> None:
    """Insert a batch of (id, timestamp, ingest_ts, raw) tuples."""
    if not rows:
        return
    client.insert(
        "logs_raw",
        rows,
        column_names=["id", "timestamp", "ingest_ts", "raw"],
    )


def seed_min_ts_from_opensearch(os_client, index: str, ts_field: str) -> str:
    """Return the oldest timestamp in the OS index as an ISO8601 Z string."""
    r = os_client.search(
        index=index,
        body={"size": 0, "aggs": {"m": {"min": {"field": ts_field}}}},
    )
    ms = r["aggregations"]["m"]["value"]
    if ms is None:
        raise RuntimeError(
            f"Index {index!r} has no documents with field {ts_field!r}; "
            f"cannot seed initial cursor"
        )
    return (
        datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )
