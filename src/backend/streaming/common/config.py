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
    # Local data source
    data_root: str           # absolute path to dataset_finale/ingestion/ inside container

    # AWS / S3
    aws_region: str
    s3_raw_bucket: str
    s3_raw_prefix: str
    s3_meta_prefix: str
    s3_checkpoint_prefix: str

    # Tuning
    chunk_bytes: int
    checkpoint_interval_ms: int
    flink_parallelism: int
    # Target records/s for the source (0 = unlimited).
    # Default 4100 spreads 14.7 M records over ~1 hour.
    target_rps: int

    @staticmethod
    def load() -> "Config":
        return Config(
            data_root=_req("DATA_ROOT"),
            aws_region=os.environ.get("AWS_REGION", "eu-west-3"),
            s3_raw_bucket=_req("S3_RAW_BUCKET"),
            s3_raw_prefix=os.environ.get("S3_RAW_PREFIX", "logs-raw"),
            s3_meta_prefix=os.environ.get("S3_META_PREFIX", "_meta"),
            s3_checkpoint_prefix=os.environ.get("S3_CHECKPOINT_PREFIX", "_checkpoints/ingestion"),
            chunk_bytes=_int("CHUNK_BYTES", 50 * 1024 * 1024),
            checkpoint_interval_ms=_int("CHECKPOINT_INTERVAL_MS", 60_000),
            flink_parallelism=_int("FLINK_PARALLELISM", 1),
            target_rps=_int("INGEST_RPS", 4100),
        )

    def s3a_uri(self, *parts: str) -> str:
        suffix = "/".join(p.strip("/") for p in parts if p)
        base = f"s3a://{self.s3_raw_bucket}"
        return f"{base}/{suffix}" if suffix else base
