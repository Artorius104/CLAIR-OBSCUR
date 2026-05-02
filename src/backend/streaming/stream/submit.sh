#!/usr/bin/env bash
# Submit the PyFlink job to the local cluster (jobmanager service).
set -euo pipefail
exec /opt/flink/bin/flink run \
  -m jobmanager:8081 \
  -py /app/job/ingestion_job.py \
  -pyFiles /app
