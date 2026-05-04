"""Local PyFlink streaming job: OpenSearch -> ClickHouse.

Run inside the Flink container as: `flink run -py /app/job/ingestion_job.py`
"""

from __future__ import annotations

import logging

from pyflink.common.typeinfo import Types
from pyflink.datastream import CheckpointingMode, StreamExecutionEnvironment
from pyflink.datastream.checkpoint_storage import FileSystemCheckpointStorage

from common.config import Config

from job.clickhouse_sink import ClickHouseBatchSink
from job.opensearch_source import OpenSearchReplaySource

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [stream] %(message)s")
    cfg = Config.load()

    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(cfg.flink_parallelism)

    env.enable_checkpointing(cfg.checkpoint_interval_ms, CheckpointingMode.AT_LEAST_ONCE)
    env.get_checkpoint_config().set_min_pause_between_checkpoints(5_000)
    env.get_checkpoint_config().set_checkpoint_timeout(120_000)
    env.get_checkpoint_config().set_max_concurrent_checkpoints(1)
    env.get_checkpoint_config().set_checkpoint_storage(
        FileSystemCheckpointStorage("file:///flink-state/checkpoints")
    )

    source = (
        env.add_source(OpenSearchReplaySource(), type_info=Types.STRING())
        .name("opensearch-replay")
    )
    source.add_sink(ClickHouseBatchSink(batch_size=1000)).name("clickhouse-sink")

    env.execute("clair-obscur-ingestion-local")


if __name__ == "__main__":
    main()
