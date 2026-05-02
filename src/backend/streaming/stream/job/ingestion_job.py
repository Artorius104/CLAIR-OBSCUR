"""PyFlink streaming job: OpenSearch tail -> S3 JSONL.

Run inside the Flink container as: `flink run -py /app/job/ingestion_job.py`
"""

from __future__ import annotations

import logging

from pyflink.common import Configuration, RestartStrategies
from pyflink.common.typeinfo import Types
from pyflink.datastream import CheckpointingMode, StreamExecutionEnvironment
from pyflink.datastream.checkpoint_storage import FileSystemCheckpointStorage

from common.config import Config

from .opensearch_source import OpenSearchTailSource
from .sink import build_file_sink

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [stream] %(message)s")
    cfg = Config.load()

    flink_conf = Configuration()
    flink_conf.set_string("s3.access-key", "")  # left blank: rely on instance profile / default chain
    flink_conf.set_string("s3.secret-key", "")
    flink_conf.set_string("fs.s3a.aws.credentials.provider",
                          "com.amazonaws.auth.DefaultAWSCredentialsProviderChain")

    env = StreamExecutionEnvironment.get_execution_environment(flink_conf)
    env.set_parallelism(cfg.flink_parallelism)

    env.enable_checkpointing(cfg.checkpoint_interval_ms, CheckpointingMode.EXACTLY_ONCE)
    env.get_checkpoint_config().set_min_pause_between_checkpoints(5_000)
    env.get_checkpoint_config().set_checkpoint_timeout(120_000)
    env.get_checkpoint_config().set_max_concurrent_checkpoints(1)
    env.get_checkpoint_config().set_checkpoint_storage(
        FileSystemCheckpointStorage(cfg.s3a_uri(cfg.s3_checkpoint_prefix))
    )

    env.set_restart_strategy(
        RestartStrategies.exponential_delay_restart_strategy(
            initial_backoff=1_000,
            max_backoff=60_000,
            backoff_multiplier=2.0,
            reset_backoff_threshold=600_000,
            jitter_factor=0.1,
        )
    )

    source = env.add_source(OpenSearchTailSource(), type_info=Types.STRING()).name("opensearch-tail")
    source.sink_to(build_file_sink(cfg)).name("s3-jsonl-sink")

    env.execute("clair-obscur-ingestion")


if __name__ == "__main__":
    main()
