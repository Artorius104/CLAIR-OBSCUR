"""PyFlink ingestion job: local JSONL files → S3 partitioned JSONL.

Source:  FileSource (Java-backed) reads DATA_ROOT line by line.
Throttle: ThrottleMap(MapFunction) limits to INGEST_RPS rec/s.
Sink:    S3SinkFlatMap(FlatMapFunction) writes to S3, emits nothing.
         .print() is the Flink terminal sink — prints nothing in practice.
Checkpoint: s3://<bucket>/_meta/ingest_progress.json every 100k docs (via boto3).

Run:
    python /app/job/ingestion_job.py
"""

from __future__ import annotations

import logging

from pyflink.common import Configuration, Types, WatermarkStrategy
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.file_system import FileSource, StreamFormat

from common.config import Config
from job.local_source import ThrottleMap
from job.sink import S3SinkFlatMap

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [ingestion] %(message)s")
    cfg = Config.load()

    log.info(
        "Starting ingestion — data_root=%s  bucket=%s  target_rps=%d",
        cfg.data_root, cfg.s3_raw_bucket, cfg.target_rps,
    )

    flink_conf = Configuration()
    flink_conf.set_string(
        "fs.s3a.aws.credentials.provider",
        "com.amazonaws.auth.DefaultAWSCredentialsProviderChain",
    )
    flink_conf.set_string("fs.s3a.endpoint.region", cfg.aws_region)

    env = StreamExecutionEnvironment.get_execution_environment(flink_conf)
    env.set_parallelism(cfg.flink_parallelism)
    # Flink in-memory checkpoint (default) — the meaningful checkpoint is the
    # external progress file written by S3SinkFlatMap every 100k docs via boto3.

    # Java-backed bounded source — reads every line in every file under data_root.
    file_source = (
        FileSource.for_record_stream_format(StreamFormat.text_line_format(), cfg.data_root)
        .build()
    )

    (
        env.from_source(file_source, WatermarkStrategy.no_watermarks(), "local-jsonl-source")
        # Throttle to target_rps (default 4100 rec/s ≈ 1 h for 14.7 M docs).
        .map(ThrottleMap(cfg.target_rps), output_type=Types.STRING())
        .name("throttle")
        # Write to S3 as a side-effect; FlatMap emits nothing downstream.
        .flat_map(
            S3SinkFlatMap(
                bucket=cfg.s3_raw_bucket,
                prefix=cfg.s3_raw_prefix,
                region=cfg.aws_region,
                chunk_bytes=cfg.chunk_bytes,
                meta_prefix=cfg.s3_meta_prefix,
            ),
            output_type=Types.STRING(),
        )
        .name("s3-sink")
        # print() gives Flink a proper terminal sink — emits nothing since
        # S3SinkFlatMap yields no elements.
        .print()
    )

    env.execute("clair-obscur-ingestion")


if __name__ == "__main__":
    main()
