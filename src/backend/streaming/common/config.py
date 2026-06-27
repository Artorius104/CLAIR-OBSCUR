"""Centralised env-var configuration for the ingestion stream."""

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
    # Local data source (both modes)
    data_root: str           # absolute path to dataset_finale/ingestion/ inside container

    # AWS / S3 (cloud mode)
    aws_region: str
    s3_raw_bucket: str
    s3_raw_prefix: str
    s3_meta_prefix: str
    s3_checkpoint_prefix: str

    # ClickHouse (local on-prem mode)
    clickhouse_host: str
    clickhouse_port: int
    clickhouse_user: str
    clickhouse_password: str
    clickhouse_database: str

    # Tuning (both modes)
    chunk_bytes: int
    checkpoint_interval_ms: int
    flink_parallelism: int
    # Target records/s (0 = unlimited).
    # Default 8200 spreads 14.7 M records over ~30 minutes.
    target_rps: int

    @staticmethod
    def load() -> "Config":
        return Config(
            data_root=_req("DATA_ROOT"),
            aws_region=os.environ.get("AWS_REGION", "eu-west-3"),
            s3_raw_bucket=os.environ.get("S3_RAW_BUCKET", ""),
            s3_raw_prefix=os.environ.get("S3_RAW_PREFIX", "logs-raw"),
            s3_meta_prefix=os.environ.get("S3_META_PREFIX", "_meta"),
            s3_checkpoint_prefix=os.environ.get("S3_CHECKPOINT_PREFIX", "_checkpoints/ingestion"),
            clickhouse_host=os.environ.get("CLICKHOUSE_HOST", "clickhouse"),
            clickhouse_port=_int("CLICKHOUSE_PORT", 8123),
            clickhouse_user=os.environ.get("CLICKHOUSE_USER", "default"),
            clickhouse_password=os.environ.get("CLICKHOUSE_PASSWORD", ""),
            clickhouse_database=os.environ.get("CLICKHOUSE_DATABASE", "clair_obscur"),
            chunk_bytes=_int("CHUNK_BYTES", 50 * 1024 * 1024),
            checkpoint_interval_ms=_int("CHECKPOINT_INTERVAL_MS", 60_000),
            flink_parallelism=_int("FLINK_PARALLELISM", 1),
            target_rps=_int("INGEST_RPS", 8200),
        )

    def s3a_uri(self, *parts: str) -> str:
        suffix = "/".join(p.strip("/") for p in parts if p)
        base = f"s3a://{self.s3_raw_bucket}"
        return f"{base}/{suffix}" if suffix else base
