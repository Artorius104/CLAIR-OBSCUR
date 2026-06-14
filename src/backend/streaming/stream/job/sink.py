"""S3 partitioned sink implemented as a PyFlink FlatMapFunction.

FlatMapFunction is a pure Python UDF — no Java bridge required.
Each invocation buffers the record by timestamp partition and flushes
to S3 when the buffer exceeds `chunk_bytes`. close() flushes the rest.

S3 layout:  <prefix>/dt=YYYY-MM-DD/hour=HH/part-<subtask>-<seq:08d>.jsonl
Checkpoint: <meta_prefix>/ingest_progress.json  (every PROGRESS_EVERY docs)

Usage in the job:
    ds.flat_map(S3SinkFlatMap(...), output_type=Types.STRING()).print()
    # FlatMap emits nothing, so .print() outputs nothing but gives Flink
    # a proper terminal sink to close the topology.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

import orjson
from pyflink.datastream.functions import FlatMapFunction

log = logging.getLogger(__name__)

_FALLBACK_PARTITION = "dt=unknown/hour=00"
_PROGRESS_EVERY = 100_000


def _bucket_path(ts: str) -> str:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    return f"dt={dt.strftime('%Y-%m-%d')}/hour={dt.strftime('%H')}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class S3SinkFlatMap(FlatMapFunction):
    """Buffers JSONL records by timestamp partition, flushes chunks to S3.

    Emits zero downstream elements — used purely for its side-effects.
    """

    def __init__(
        self,
        bucket: str,
        prefix: str,
        region: str,
        chunk_bytes: int,
        meta_prefix: str = "_meta",
    ) -> None:
        self._bucket = bucket
        self._prefix = prefix
        self._region = region
        self._chunk_bytes = chunk_bytes
        self._meta_prefix = meta_prefix
        # Set in open() — not pickled.
        self._s3 = None
        self._subtask: int = 0
        self._seq: int = 0
        self._total_docs: int = 0
        self._since_progress: int = 0
        self._start_time: float = 0.0
        self._buffers: dict[str, list[bytes]] = {}
        self._buf_bytes: dict[str, int] = {}

    # --- lifecycle -----------------------------------------------------------

    def open(self, runtime_context) -> None:  # type: ignore[override]
        import os
        import boto3
        # Pass credentials explicitly so boto3 never attempts profile resolution.
        # AWS_PROFILE="" (passed by docker-compose when unset on host) would
        # otherwise trigger ProfileNotFound before env-var credentials are tried.
        self._s3 = boto3.client(
            "s3",
            region_name=self._region,
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID") or None,
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY") or None,
            aws_session_token=os.environ.get("AWS_SESSION_TOKEN") or None,
        )
        self._subtask = runtime_context.get_index_of_this_subtask()
        self._seq = 0
        self._total_docs = 0
        self._since_progress = 0
        self._start_time = time.monotonic()
        self._buffers = {}
        self._buf_bytes = {}
        log.info(
            "S3SinkFlatMap[%d] open — bucket=%s prefix=%s",
            self._subtask, self._bucket, self._prefix,
        )

    def close(self) -> None:  # type: ignore[override]
        for partition in list(self._buffers.keys()):
            self._flush(partition)
        self._write_progress()
        elapsed = time.monotonic() - self._start_time
        log.info(
            "S3SinkFlatMap[%d] closed — %d docs, %d parts, %.1fs",
            self._subtask, self._total_docs, self._seq, elapsed,
        )

    # --- core ----------------------------------------------------------------

    def flat_map(self, value: str):  # type: ignore[override]
        """Buffer the record; yield nothing (sink-only behaviour)."""
        line = value.encode("utf-8") if isinstance(value, str) else value
        partition = _parse_partition(line)

        self._buffers.setdefault(partition, []).append(line)
        self._buf_bytes[partition] = self._buf_bytes.get(partition, 0) + len(line) + 1
        self._total_docs += 1
        self._since_progress += 1

        if self._buf_bytes[partition] >= self._chunk_bytes:
            self._flush(partition)

        if self._since_progress >= _PROGRESS_EVERY:
            self._write_progress()
            self._since_progress = 0

        return []   # emit nothing downstream

    # --- helpers -------------------------------------------------------------

    def _flush(self, partition: str) -> None:
        lines = self._buffers.pop(partition, [])
        self._buf_bytes.pop(partition, None)
        if not lines:
            return
        body = b"\n".join(lines)
        key = f"{self._prefix}/{partition}/part-{self._subtask:03d}-{self._seq:08d}.jsonl"
        self._s3.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=body,
            ContentType="application/x-ndjson",
        )
        log.info(
            "S3SinkFlatMap[%d] → %s  (%.1f MiB, %d docs)",
            self._subtask, key, len(body) / 1_048_576, len(lines),
        )
        self._seq += 1

    def _write_progress(self) -> None:
        if self._s3 is None or self._total_docs == 0:
            return
        elapsed = time.monotonic() - self._start_time
        payload = json.dumps(
            {
                "total_docs": self._total_docs,
                "parts_written": self._seq,
                "elapsed_sec": round(elapsed, 1),
                "rate_rps": round(self._total_docs / max(elapsed, 1), 1),
                "updated_at": _now_iso(),
            },
            separators=(",", ":"),
        ).encode()
        try:
            self._s3.put_object(
                Bucket=self._bucket,
                Key=f"{self._meta_prefix}/ingest_progress.json",
                Body=payload,
                ContentType="application/json",
            )
        except Exception:
            log.warning("S3SinkFlatMap: failed to write progress", exc_info=True)


def _parse_partition(line: bytes) -> str:
    try:
        obj = orjson.loads(line)
        ts = obj.get("timestamp") or obj.get("@timestamp") or ""
        if ts:
            return _bucket_path(ts)
    except Exception:
        pass
    return _FALLBACK_PARTITION
