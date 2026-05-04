#!/usr/bin/env bash
# Submit the local PyFlink job (OpenSearch -> ClickHouse) to the jobmanager.
set -euo pipefail
exec /opt/flink/bin/flink run \
  -m jobmanager:8081 \
  -py /app/job/ingestion_job.py \
  -pyFiles /app
