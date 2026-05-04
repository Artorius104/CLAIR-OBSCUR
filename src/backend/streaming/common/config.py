"""Centralised env-var configuration for backfill and stream components."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _req(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Missing required env var: {name}")
    return val


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


@dataclass(frozen=True)
class Config:
    opensearch_url: str
    opensearch_index: str
    opensearch_user: str
    opensearch_password: str
    opensearch_ts_field: str

    # AWS / S3 — required for cloud variant only; left empty for local
    aws_region: str
    s3_raw_bucket: str
    s3_raw_prefix: str
    s3_meta_prefix: str
    s3_backfill_prefix: str
    s3_checkpoint_prefix: str

    # ClickHouse — required for local variant only; left empty for cloud
    clickhouse_host: str
    clickhouse_port: int
    clickhouse_user: str
    clickhouse_password: str
    clickhouse_database: str

    backfill_windows: int
    backfill_page_size: int
    backfill_chunk_bytes: int
    backfill_progress_every_pages: int

    poll_interval_sec: int
    checkpoint_interval_ms: int
    flink_parallelism: int
    stream_sqs_queue_url: str

    @staticmethod
    def load() -> "Config":
        return Config(
            opensearch_url=_req("OPENSEARCH_URL"),
            opensearch_index=os.environ.get("OPENSEARCH_INDEX", "logs-raw"),
            opensearch_user=_req("OPENSEARCH_USER"),
            opensearch_password=_req("OPENSEARCH_PASSWORD"),
            opensearch_ts_field=os.environ.get("OPENSEARCH_TS_FIELD", "timestamp"),
            aws_region=os.environ.get("AWS_REGION", "eu-west-3"),
            s3_raw_bucket=os.environ.get("S3_RAW_BUCKET", ""),
            s3_raw_prefix=os.environ.get("S3_RAW_PREFIX", "logs-raw"),
            s3_meta_prefix=os.environ.get("S3_META_PREFIX", "_meta"),
            s3_backfill_prefix=os.environ.get("S3_BACKFILL_PREFIX", "_backfill"),
            s3_checkpoint_prefix=os.environ.get("S3_CHECKPOINT_PREFIX", "_checkpoints/ingestion"),
            clickhouse_host=os.environ.get("CLICKHOUSE_HOST", "clickhouse"),
            clickhouse_port=_int("CLICKHOUSE_PORT", 8123),
            clickhouse_user=os.environ.get("CLICKHOUSE_USER", "default"),
            clickhouse_password=os.environ.get("CLICKHOUSE_PASSWORD", ""),
            clickhouse_database=os.environ.get("CLICKHOUSE_DATABASE", "clair_obscur"),
            backfill_windows=_int("BACKFILL_WINDOWS", 4),
            backfill_page_size=_int("BACKFILL_PAGE_SIZE", 1000),
            backfill_chunk_bytes=_int("BACKFILL_CHUNK_BYTES", 50 * 1024 * 1024),
            backfill_progress_every_pages=_int("BACKFILL_PROGRESS_EVERY_PAGES", 5),
            poll_interval_sec=_int("POLL_INTERVAL_SEC", 300),
            checkpoint_interval_ms=_int("CHECKPOINT_INTERVAL_MS", 60_000),
            flink_parallelism=_int("FLINK_PARALLELISM", 1),
            stream_sqs_queue_url=os.environ.get("STREAM_SQS_QUEUE_URL", ""),
        )

    def require_s3_bucket(self) -> str:
        if not self.s3_raw_bucket:
            raise RuntimeError("S3_RAW_BUCKET is required for the cloud variant")
        return self.s3_raw_bucket

    def s3_uri(self, *parts: str) -> str:
        suffix = "/".join(p.strip("/") for p in parts if p)
        return f"s3://{self.s3_raw_bucket}/{suffix}" if suffix else f"s3://{self.s3_raw_bucket}"

    def s3a_uri(self, *parts: str) -> str:
        return self.s3_uri(*parts).replace("s3://", "s3a://", 1)
