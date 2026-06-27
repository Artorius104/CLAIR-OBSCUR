# CLAIR OBSCUR — NDR Platform (Network Detection & Response)

Real-time cybersecurity log analysis platform: ingest raw logs from OpenSearch, detect attacks with ML + LLM, surface alerts in a TypeScript dashboard — deployed on AWS.

## Architecture

```
data/dataset_finale/ingestion/   (93 JSONL files, 14.7 M records)
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Ingestion  (src/backend/streaming/)                    │
│                                                         │
│  FileSource (Java-backed, files read in numeric order)  │
│    ThrottleMap — 8 200 rec/s ≈ 30 min for full dataset  │
│                        │                                │
│          ┌─────────────┴─────────────┐                  │
│          ▼                           ▼                  │
│   Cloud mode (docker-compose.yml)  Local mode           │
│   S3SinkFlatMap                    ClickHouseBatchSink  │
│   · buffers by dt/hour partition   · batches 1 000 rows │
│   · flushes at 50 MiB chunks       · ReplacingMergeTree │
│   · progress checkpoint every      · idempotent on id   │
│     100 k docs → S3 _meta/         · partitioned by day │
└──────────┬────────────────────────────────────┬─────────┘
           ▼                                    ▼
  S3  s3://clair-obscur-raw-<acct>/      ClickHouse
    logs-raw/dt=YYYY-MM-DD/hour=HH/      clair_obscur.logs_raw
      part-000-NNNNNNNN.jsonl
           │
  ┌────────┼──────────┐
  ▼        ▼          ▼
Detection  Analytics  Agents
(regex+ML) (API)      (LLM / Bedrock)
  │        │          │
  └────────┴──────────┘
           │
           ▼
    Frontend (Next.js)
```

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Ingestion — source | PyFlink 1.19 FileSource, 93 JSONL files (14.7 M records) |
| Ingestion — cloud sink | S3 partitioned JSONL, boto3, orjson |
| Ingestion — local sink | ClickHouse ReplacingMergeTree, clickhouse-connect |
| API | FastAPI |
| AI agents | Amazon Bedrock (Claude Opus 4.6) |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Container registry | Amazon ECR |
| Compute | Amazon EC2 t3.medium |
| Storage | Amazon S3 |
| Region | eu-west-3 (Paris) |

## Repository Structure

```
src/
├── backend/
│   ├── streaming/              # Ingestion pipeline
│   │   ├── common/             # Shared config, ClickHouse client
│   │   ├── stream/             # Cloud mode: PyFlink → S3 (Dockerfile inside)
│   │   ├── local/              # Local mode: PyFlink → ClickHouse (Dockerfile inside)
│   │   ├── docker-compose.yml          # Cloud ingestion
│   │   └── docker-compose.local.yml    # Local ingestion
│   └── init/                   # DB init scripts
├── api/                        # FastAPI detection + analytics API
├── agents/                     # LLM detection agents
├── frontend/                   # Next.js dashboard
└── scripts/
    └── run                     # Dual-mode launcher (local / cloud)
```

## Quick Start

A single launcher `./run` at the repo root dispatches to either variant.

```bash
./run                           # print usage
./run local up                  # on-prem: ClickHouse + PyFlink (this laptop)
./run cloud bootstrap           # AWS: provision S3 + EC2 + ECR + IAM
```

### Common prerequisites

- Docker + Docker Compose
- Dataset: `data/dataset_finale/ingestion/` must exist (93 JSONL files, 14.7 M records)
- A populated `.env` file at the repo root:
  ```bash
  cp .env.example .env
  # Cloud only: fill AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_RAW_BUCKET
  # Local only: defaults in .env.example work as-is (no credentials needed)
  ```

### Local mode (on-prem)

JSONL files → PyFlink → ClickHouse, everything on this machine. Throttled at 8 200 rec/s ≈ 30 minutes for the full dataset.

```bash
./scripts/run local up                  # builds image, starts ClickHouse + Flink cluster + submitter
./scripts/run local logs taskmanager    # watch records flow in real time
./scripts/run local sql                 # open clickhouse-client REPL
:) SELECT count(), uniqExact(id) FROM clair_obscur.logs_raw FINAL;
:) SELECT min(timestamp), max(timestamp) FROM clair_obscur.logs_raw;
./scripts/run local down                # stop everything; ClickHouse data persists in volume
```

Flink web UI: http://localhost:8081  
ClickHouse HTTP: http://localhost:8123

### Cloud mode (AWS)

Prerequisites: AWS CLI configured (`aws sso login` or access keys in `.env`).

```bash
./scripts/run cloud ingest              # creates S3 bucket + IAM policy, then starts ingestion (~30 min)
./scripts/run cloud status             # live progress: docs written, rate, ETA
./scripts/run cloud logs               # tail the running stream-worker container
./scripts/run cloud ingest-stop        # stop the ingestion container
```

#### Required IAM permissions

| Identity | Permissions needed |
|---|---|
| IAM user / role running `cloud ingest` | `s3:PutObject` + `s3:GetObject` on `<bucket>/*`, `s3:ListBucket` + `s3:GetBucketLocation` on `<bucket>` |

## S3 Data Layout

```
s3://clair-obscur-raw-<acct>/
  logs-raw/
    dt=YYYY-MM-DD/hour=HH/part-<subtask>-<seq>.jsonl   # partitioned by log timestamp
  _meta/
    ingest_progress.json                               # progress checkpoint (every 100 k docs)
```

Every JSONL line preserves the original fields (`id`, `timestamp`, `ingest_ts`, …) from the source dataset.

## Monitoring

```bash
# Live progress (cloud) — docs written, rate, ETA
./scripts/run cloud status

# Tail live logs (cloud)
./scripts/run cloud logs

# Files + total size in S3 (cloud)
aws s3 ls s3://<bucket>/logs-raw/ --recursive \
  | awk '{size+=$3; count++} END {printf "%d files, %.1f GiB\n", count, size/1024/1024/1024}'

# Raw progress checkpoint (cloud)
aws s3 cp s3://<bucket>/_meta/ingest_progress.json - | python3 -m json.tool

# Live Flink logs (local)
./scripts/run local logs taskmanager

# Row count in ClickHouse (local)
./scripts/run local sql
:) SELECT count(), uniqExact(id) FROM clair_obscur.logs_raw FINAL;
:) SELECT min(timestamp), max(timestamp) FROM clair_obscur.logs_raw;
```

## Updating the pipeline

```bash
# After editing source code — rebuild and restart:
./scripts/run cloud ingest-stop && ./scripts/run cloud ingest   # cloud
./scripts/run local down && ./scripts/run local up              # local
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `HOST_DATA_ROOT` not set | Exported automatically by `./scripts/run`; if running compose manually, set `export HOST_DATA_ROOT=$PWD/data/dataset_finale/ingestion` |
| `Missing required env var: DATA_ROOT` | `.env` is missing or `DATA_ROOT=/data/ingestion` not set — run `cp .env.example .env` |
| S3 write access denied (cloud) | Run `./scripts/run cloud ingest` — it auto-creates the bucket and attaches the IAM policy |
| Flink job not appearing in UI | Check submitter logs: `docker compose -f src/backend/streaming/docker-compose.local.yml logs submitter` |
| ClickHouse rows not appearing | Query with `FINAL` to force merge: `SELECT count() FROM clair_obscur.logs_raw FINAL` |
| Ingestion slower than expected | Check `INGEST_RPS` in `.env` (default 8 200 ≈ 30 min); set to `0` for full speed |
