"""S3 FileSink for chronological JSONL output.

Stream files land under `logs-raw/stream/` with rolling 5 min / 50 MB parts.
Each part is internally chronological because the source emits in
`(@timestamp, _id)` order. Hourly bucketing is handled by the backfill phase;
the stream tail is small enough that flat layout + filename timestamp suffix
is sufficient for downstream readers.
"""

from __future__ import annotations

from pyflink.common import Duration
from pyflink.common.serialization import Encoder
from pyflink.datastream.connectors.file_system import (
    FileSink,
    OutputFileConfig,
    RollingPolicy,
)

from common.config import Config


def build_file_sink(cfg: Config) -> FileSink:
    out_path = cfg.s3a_uri(cfg.s3_raw_prefix, "stream")

    return (
        FileSink.for_row_format(out_path, Encoder.simple_string_encoder("UTF-8"))
        .with_rolling_policy(
            RollingPolicy.default_rolling_policy(
                part_size=50 * 1024 * 1024,
                rollover_interval=Duration.of_minutes(5).to_milliseconds(),
                inactivity_interval=Duration.of_minutes(2).to_milliseconds(),
            )
        )
        .with_output_file_config(
            OutputFileConfig.builder()
            .with_part_prefix("part-stream")
            .with_part_suffix(".jsonl")
            .build()
        )
        .build()
    )
