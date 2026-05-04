# CLAIR OBSCUR — NDR Platform (Network Detection & Response)

Real-time cybersecurity log analysis platform: ingest raw logs from OpenSearch, detect attacks with ML + LLM, surface alerts in a TypeScript dashboard — deployed on AWS.

## Architecture

```
Amazon OpenSearch (~21M logs, live injections)
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Ingestion  (src/backend/streaming/)                    │
│                                                         │
│  Phase A — Backfill (one-shot, parallel)                │
│    Python multiprocessing · PIT + time-window           │
│    slicing · chronological JSONL · resumable            │
│                        │                                │
│                        ▼  cutover.json + SQS message    │
│  Phase B — Stream (continuous, PyFlink 1.19)            │
│    search_after tail · exactly-once FileSink            │
│    60s checkpoints to s3a://                            │
│    SQS long-poll wake-up (< 20s latency)                │
│                        ▲                                │
│                        │ SQS wake-up                    │
│  Lambda Watcher (every 1 min via CloudWatch Events)     │
│    GET /logs-raw/_count · compare with last count       │
│    new docs → SQS message → stream polls immediately    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
         S3  s3://clair-obscur-raw-<acct>/
               logs-raw/dt=YYYY-MM-DD/hour=HH/*.jsonl
                       │
         ┌─────────────┼──────────────┐
         ▼             ▼              ▼
    Detection      Analytics       Agents
    (regex + ML)   (API)           (LLM / Bedrock)
         │             │              │
         └─────────────┴──────────────┘
                       │
                       ▼
              Frontend (Next.js)
```

### Event-driven stream wake-up

OpenSearch has no native push mechanism. Detection latency is kept under 2 minutes via:

1. **Lambda watcher** (`src/backend/streaming/watcher/`) — runs every minute, queries `_count` on the index, sends an SQS message when the count increases.
2. **Backfill → SQS** — on completion the backfill sends a `backfill_complete` message so the stream starts immediately without waiting for the next Lambda tick.
3. **Stream SQS long-poll** — instead of `time.sleep(POLL_INTERVAL_SEC)`, the source function long-polls SQS (`WaitTimeSeconds=20`). Returns in < 20 s on a signal; falls back to `POLL_INTERVAL_SEC` (default 300 s) if the queue stays silent.

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Ingestion — backfill | Python multiprocessing, opensearch-py, boto3, orjson |
| Ingestion — stream | PyFlink 1.19, S3 FileSink, RocksDB state |
| Ingestion — event detection | AWS Lambda (Python 3.12, no extra deps), Amazon SQS |
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
│   │   ├── common/             # Shared config, OS client, S3 helpers
│   │   ├── backfill/           # One-shot bulk drain (Dockerfile inside)
│   │   ├── stream/             # PyFlink tail job (Dockerfile inside)
│   │   ├── watcher/            # Lambda: doc-count watcher → SQS
│   │   └── docker-compose.yml
│   └── init/                   # DB init scripts
├── api/                        # FastAPI detection + analytics API
├── agents/                     # LLM detection agents
├── frontend/                   # Next.js dashboard
└── scripts/
    ├── aws_bootstrap.sh        # One-shot AWS infra setup
    ├── deploy.sh               # Build → ECR → EC2 deploy
    └── aws/
        ├── user-data.sh        # EC2 first-boot docker setup
        └── iam/                # IAM role + policy templates
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
- A populated `.env` file at the repo root:
  ```bash
  cp .env.example .env
  # fill OPENSEARCH_URL, OPENSEARCH_USER, OPENSEARCH_PASSWORD
  # fill S3_RAW_BUCKET, STREAM_SQS_QUEUE_URL
  ```

### Local mode (on-prem)

OpenSearch → PyFlink → ClickHouse, all on this laptop. The Flink job replays the entire history from the oldest log forward, then transitions to live tail.

```bash
./run local up                  # builds image, starts CH + jobmanager + taskmanager + submitter
./run local logs taskmanager    # watch records flow
./run local sql                 # open clickhouse-client REPL
:) SELECT count(), uniqExact(id) FROM clair_obscur.logs_raw FINAL;
:) SELECT min(timestamp), max(timestamp) FROM clair_obscur.logs_raw;
./run local down                # stop everything; CH data persists in volume
```

Flink web UI: http://localhost:8081
ClickHouse HTTP: http://localhost:8123

### Cloud mode (AWS)

Prerequisites: AWS CLI configured (`aws sso login`) + an EC2 SSH key pair named `clair-obscur-ingestion-key`.

```bash
./run cloud bootstrap                       # one-shot AWS setup
./run cloud deploy ec2-user@<public-ip>     # build → ECR → EC2 (stream starts automatically)
./run cloud backfill <public-ip>            # ssh + run one-shot backfill on EC2
# on completion: writes cutover.json, sends SQS wake-up → stream tails from cutover_ts
```

#### One-time SQS + Lambda setup (after bootstrap)

```bash
# 1. Create SQS queue (skip if already exists)
aws sqs create-queue --queue-name clair-obscur-stream-trigger --region eu-west-3
# → set STREAM_SQS_QUEUE_URL in .env

# 2. Deploy Lambda watcher (no extra deps — stdlib + boto3 only)
cd src/backend/streaming/watcher
zip watcher.zip lambda_handler.py
aws lambda create-function \
  --function-name clair-obscur-stream-watcher \
  --runtime python3.12 \
  --zip-file fileb://watcher.zip \
  --handler lambda_handler.handler \
  --role arn:aws:iam::<acct>:role/clair-obscur-lambda-watcher-role \
  --timeout 30 --region eu-west-3 \
  --environment 'Variables={
    OPENSEARCH_URL=<url>,OPENSEARCH_INDEX=logs-raw,
    OPENSEARCH_USER=<user>,OPENSEARCH_PASSWORD=<pass>,
    S3_RAW_BUCKET=<bucket>,S3_META_PREFIX=_meta,
    STREAM_SQS_QUEUE_URL=<queue-url>}'

# 3. CloudWatch Events rule: trigger Lambda every minute
aws events put-rule \
  --name clair-obscur-watcher-schedule \
  --schedule-expression "rate(1 minute)" --state ENABLED --region eu-west-3
aws events put-targets \
  --rule clair-obscur-watcher-schedule \
  --targets "Id=1,Arn=arn:aws:lambda:eu-west-3:<acct>:function:clair-obscur-stream-watcher" \
  --region eu-west-3
aws lambda add-permission \
  --function-name clair-obscur-stream-watcher \
  --statement-id clair-obscur-watcher-schedule \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:eu-west-3:<acct>:rule/clair-obscur-watcher-schedule \
  --region eu-west-3
```

#### Required IAM permissions

| Role | Permissions needed |
|---|---|
| `clair-obscur-ingestion-role` (EC2) | S3 raw bucket full access, `sqs:SendMessage` + `sqs:ReceiveMessage` + `sqs:DeleteMessage` on trigger queue |
| `clair-obscur-lambda-watcher-role` (Lambda) | `s3:GetObject` + `s3:PutObject` on `_meta/*`, `sqs:SendMessage` on trigger queue, CloudWatch Logs |

## S3 Data Layout

```
s3://clair-obscur-raw-<acct>/
  logs-raw/
    dt=YYYY-MM-DD/hour=HH/part-w<NNN>-<seq>.jsonl   # backfill (partitioned by log timestamp)
    stream/part-stream-*.jsonl                       # live tail (flat, rolled every 5 min/50 MiB)
  _backfill/window=<n>/progress.json                 # per-window resume cursors
  _meta/cutover.json                                 # backfill done marker + cutover_ts
  _meta/stream_cursor.json                           # stream position (ts + _id)
  _meta/watcher_state.json                           # Lambda last-known doc count
  _checkpoints/ingestion/                            # Flink RocksDB checkpoints
```

Every JSONL line includes an `id` field (OpenSearch `_id`) and `ingest_ts`.

## Monitoring

```bash
# Is the backfill container still running?
ssh -i keys/clair-obscur-ingestion-key.pem ec2-user@<ip> \
  'docker ps --filter name=backfill --format "{{.Names}}\t{{.Status}}"'

# Live backfill logs
ssh -i keys/clair-obscur-ingestion-key.pem ec2-user@<ip> \
  'docker logs -f $(docker ps -qf name=backfill)'

# Files + total size in S3
aws s3 ls s3://<bucket>/logs-raw/ --recursive \
  | awk '{size+=$3; count++} END {printf "%d files, %.1f GiB\n", count, size/1024/1024/1024}'

# Per-window progress (16 windows)
for w in $(seq 0 15); do
  result=$(aws s3 cp "s3://<bucket>/_backfill/window=${w}/progress.json" - 2>/dev/null)
  [ -n "$result" ] && echo -n "w$w: " && echo "$result" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('docs_written',0):,} docs  done={d.get('done',False)}\")"
done

# Total docs ingested so far
for w in $(seq 0 15); do
  aws s3 cp "s3://<bucket>/_backfill/window=${w}/progress.json" - 2>/dev/null
done | python3 -c "
import sys,json; total=0
for line in sys.stdin:
  try: total += json.loads(line).get('docs_written',0)
  except: pass
print(f'Total: {total:,} / 21,429,338 ({total/21429338*100:.1f}%)')"

# Backfill complete?
aws s3 cp s3://<bucket>/_meta/cutover.json - 2>/dev/null || echo "not done yet"

# SQS queue depth (messages waiting for stream)
aws sqs get-queue-attributes \
  --queue-url <STREAM_SQS_QUEUE_URL> \
  --attribute-names ApproximateNumberOfMessages --region eu-west-3

# Lambda watcher last run result
aws logs filter-log-events \
  --log-group-name /aws/lambda/clair-obscur-stream-watcher \
  --start-time $(($(date +%s) - 300))000 \
  --region eu-west-3 \
  --query 'events[*].message' --output text
```

## Updating the pipeline

```bash
# edit code locally, then:
./run cloud deploy ec2-user@<ip>
# images are tagged with the git short hash, pushed to ECR,
# and the stream service is restarted automatically

# update Lambda watcher after code changes:
cd src/backend/streaming/watcher
zip watcher.zip lambda_handler.py
aws lambda update-function-code \
  --function-name clair-obscur-stream-watcher \
  --zip-file fileb://watcher.zip --region eu-west-3
```

## Troubleshooting

| Problem | Fix |
|---|---|
| SSH timeout after network change | `aws ec2 authorize-security-group-ingress --group-id <sg-id> --protocol tcp --port 22 --cidr 0.0.0.0/0 --region eu-west-3` |
| EC2 frozen / unresponsive | OOM — stop stream before backfill; use t3.medium minimum |
| Backfill `timestamp field null` | Set `OPENSEARCH_TS_FIELD=timestamp` in `.env`; field is auto-detected on restart |
| ECR pull denied on EC2 | `REGISTRY` missing from `.env` — re-run `deploy.sh` to inject it |
| Backfill crashed mid-run | Safe to restart — per-window cursors in S3 resume from last checkpoint |
| Stream job not appearing in Flink UI | Check submitter logs: `docker logs clair-obscur-submitter-1` |
| Stream not waking up on new docs | Check SQS queue depth and Lambda CloudWatch logs; verify `STREAM_SQS_QUEUE_URL` is set in `.env` on EC2 |
| Lambda watcher `AccessDenied` on S3 | `clair-obscur-lambda-watcher-role` needs `s3:GetObject`+`s3:PutObject` on `_meta/*` |
| Lambda watcher `AccessDenied` on SQS | `clair-obscur-lambda-watcher-role` needs `sqs:SendMessage` on the trigger queue ARN |
