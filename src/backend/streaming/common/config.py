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

    aws_region: str
    s3_raw_bucket: str
    s3_raw_prefix: str
    s3_meta_prefix: str
    s3_backfill_prefix: str
    s3_checkpoint_prefix: str

    backfill_windows: int
    backfill_page_size: int
    backfill_chunk_bytes: int
    backfill_progress_every_pages: int

    poll_interval_sec: int
    checkpoint_interval_ms: int
    flink_parallelism: int

    @staticmethod
    def load() -> "Config":
        return Config(
            opensearch_url=_req("OPENSEARCH_URL"),
            opensearch_index=os.environ.get("OPENSEARCH_INDEX", "logs-raw"),
            opensearch_user=_req("OPENSEARCH_USER"),
            opensearch_password=_req("OPENSEARCH_PASSWORD"),
            opensearch_ts_field=os.environ.get("OPENSEARCH_TS_FIELD", "timestamp"),
            aws_region=os.environ.get("AWS_REGION", "eu-west-3"),
            s3_raw_bucket=_req("S3_RAW_BUCKET"),
            s3_raw_prefix=os.environ.get("S3_RAW_PREFIX", "logs-raw"),
            s3_meta_prefix=os.environ.get("S3_META_PREFIX", "_meta"),
            s3_backfill_prefix=os.environ.get("S3_BACKFILL_PREFIX", "_backfill"),
            s3_checkpoint_prefix=os.environ.get("S3_CHECKPOINT_PREFIX", "_checkpoints/ingestion"),
            backfill_windows=_int("BACKFILL_WINDOWS", 4),
            backfill_page_size=_int("BACKFILL_PAGE_SIZE", 1000),
            backfill_chunk_bytes=_int("BACKFILL_CHUNK_BYTES", 50 * 1024 * 1024),
            backfill_progress_every_pages=_int("BACKFILL_PROGRESS_EVERY_PAGES", 5),
            poll_interval_sec=_int("POLL_INTERVAL_SEC", 30),
            checkpoint_interval_ms=_int("CHECKPOINT_INTERVAL_MS", 60_000),
            flink_parallelism=_int("FLINK_PARALLELISM", 1),
        )

    def s3_uri(self, *parts: str) -> str:
        suffix = "/".join(p.strip("/") for p in parts if p)
        return f"s3://{self.s3_raw_bucket}/{suffix}" if suffix else f"s3://{self.s3_raw_bucket}"

    def s3a_uri(self, *parts: str) -> str:
        return self.s3_uri(*parts).replace("s3://", "s3a://", 1)
