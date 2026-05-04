-- ClickHouse schema for the local ingestion variant.
-- Mounted to /docker-entrypoint-initdb.d/ in the clickhouse-server container.

CREATE DATABASE IF NOT EXISTS clair_obscur;

CREATE TABLE IF NOT EXISTS clair_obscur.logs_raw (
    id          String,
    timestamp   DateTime64(3),
    ingest_ts   DateTime64(3) DEFAULT now64(3),
    raw         String  CODEC(ZSTD(3))
) ENGINE = ReplacingMergeTree(ingest_ts)
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (timestamp, id);

CREATE TABLE IF NOT EXISTS clair_obscur.stream_cursor (
    component   String,
    cursor_ts   String,
    cursor_id   String,
    updated_at  DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (component);
