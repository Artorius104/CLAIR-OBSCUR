"""PyFlink ingestion job: local JSONL files → ClickHouse.

Source:   FileSource (Java-backed) reads DATA_ROOT line by line.
Throttle: ThrottleMap limits to INGEST_RPS rec/s (default 8200 ≈ 30 min).
Sink:     ClickHouseBatchSink batches inserts into logs_raw.

Run via docker-compose (./scripts/run local up) or directly:
    python /app/job/ingestion_job.py
"""

from __future__ import annotations

import logging
import time

from pyflink.common import Configuration, Types, WatermarkStrategy
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.file_system import FileSource, StreamFormat
from pyflink.datastream.functions import MapFunction

from common.config import Config
from job.clickhouse_sink import ClickHouseBatchSink

log = logging.getLogger(__name__)

_LOG_EVERY = 100_000
_TOTAL_DOCS = 14_721_375


class ThrottleMap(MapFunction):
    """Rate-limit emission to target_rps rec/s using a virtual-clock approach."""

    def __init__(self, target_rps: int) -> None:
        self._target_rps = target_rps
        self._count: int = 0
        self._start: float = 0.0

    def open(self, runtime_context) -> None:  # type: ignore[override]
        self._count = 0
        self._start = time.monotonic()
        idx = runtime_context.get_index_of_this_subtask()
        log.info("ThrottleMap[%d] open — target_rps=%d", idx, self._target_rps)

    def map(self, value: str) -> str:  # type: ignore[override]
        self._count += 1

        if self._target_rps > 0 and self._count % 500 == 0:
            target_elapsed = self._count / self._target_rps
            actual_elapsed = time.monotonic() - self._start
            gap = target_elapsed - actual_elapsed
            if gap > 0.005:
                time.sleep(gap)

        if self._count % _LOG_EVERY == 0:
            elapsed = time.monotonic() - self._start
            rps = self._count / max(elapsed, 1)
            eta_min = (_TOTAL_DOCS - self._count) / max(rps, 1) / 60
            log.info(
                "ThrottleMap: %d docs | %.0f rec/s | ETA ~%.0f min",
                self._count, rps, eta_min,
            )

        return value


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [local-ingest] %(message)s")
    cfg = Config.load()

    log.info(
        "Starting local ingestion — data_root=%s  clickhouse=%s/%s  target_rps=%d",
        cfg.data_root, cfg.clickhouse_host, cfg.clickhouse_database, cfg.target_rps,
    )

    env = StreamExecutionEnvironment.get_execution_environment(Configuration())
    env.set_parallelism(cfg.flink_parallelism)

    file_source = (
        FileSource.for_record_stream_format(StreamFormat.text_line_format(), cfg.data_root)
        .build()
    )

    (
        env.from_source(file_source, WatermarkStrategy.no_watermarks(), "local-jsonl-source")
        .map(ThrottleMap(cfg.target_rps), output_type=Types.STRING())
        .name("throttle")
        .add_sink(ClickHouseBatchSink(batch_size=1000))
        .name("clickhouse-sink")
    )

    env.execute("clair-obscur-local-ingestion")


if __name__ == "__main__":
    main()
