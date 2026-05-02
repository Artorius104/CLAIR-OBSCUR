# Streaming — OpenSearch → S3 Ingestion

Two components, one shared `common/`:

| Component  | What                                                          | Run as                              |
|------------|----------------------------------------------------------------|--------------------------------------|
| `backfill` | One-shot drain of the existing index (~21 M docs). Time-windowed parallel readers, chronological JSONL output, resumable per window. Writes `_meta/cutover.json` on success. | `docker compose --profile backfill run --rm backfill` |
| `stream`   | PyFlink 1.19 job tailing OpenSearch via `search_after`. Exactly-once S3 FileSink, checkpoints to `s3a://`, restart strategy with exponential backoff. | `docker compose --profile stream up -d` |

## S3 layout

```
s3://<bucket>/
  logs-raw/
    dt=YYYY-MM-DD/hour=HH/part-w<NNN>-<seq>.jsonl    # backfill (chronological)
    stream/part-stream-*.jsonl                       # streaming tail
  _backfill/window=<n>/progress.json                 # per-window cursor (resume)
  _meta/cutover.json                                 # backfill → stream handoff
  _meta/stream_cursor.json                           # stream cursor
  _checkpoints/ingestion/                            # Flink checkpoints
```

Every JSONL line:

```json
{ "id": "<OS _id>", "ingest_ts": "...Z", ...original log fields... }
```

## Local quickstart

1. Fill `.env` at the repo root (see `.env.example`).
2. Backfill (smoke):
   ```bash
   cd src/backend/streaming
   BACKFILL_WINDOWS=2 BACKFILL_PAGE_SIZE=1000 \
     docker compose --profile backfill run --rm backfill
   ```
3. Stream:
   ```bash
   docker compose --profile stream up
   # Flink UI on http://localhost:8081
   ```

## Cloud deploy

```bash
# 1. Bootstrap AWS (S3, ECR, IAM, EC2). Idempotent.
./src/scripts/aws_bootstrap.sh

# 2. Build + push images, sync compose to EC2 and restart the systemd unit.
./src/scripts/deploy.sh ec2-user@<public-ip>

# 3. Run backfill on EC2 (one-shot)
ssh ec2-user@<public-ip> 'cd /opt/clair-obscur && docker compose --profile backfill run --rm backfill'

# 4. Stream is started automatically by the systemd unit `clair-obscur-stream`.
```

## Why this shape

- **Time-windowed slicing (not hash slices)** keeps backfill output chronologically ordered both within and across files — easier downstream storage / analysis.
- **`id` (= OS `_id`) on every record** is the universal dedup key.
- **EC2 instance profile** for AWS auth — survives the 8-hour SSO credential rotation with no manual action (boto3 / Hadoop S3A pull rotating creds from IMDS).
- **Backfill ≠ stream**: Flink's source-poll loop isn't built for saturating bandwidth on 21 M docs; a parallel Python pool is much faster for a one-shot drain. Stream stays simple.

## Verification quickstart

```bash
# 1. backfill counts match index size
aws s3 ls s3://$BUCKET/logs-raw/ --recursive | wc -l        # parts written
curl -u $OPENSEARCH_USER:$OPENSEARCH_PASSWORD \
  $OPENSEARCH_URL/$OPENSEARCH_INDEX/_count                  # total docs

# 2. no duplicate ids in a sampled file
aws s3 cp s3://$BUCKET/logs-raw/dt=2026-04-15/hour=14/part-w000-00000000.jsonl - \
  | jq -r '.id' | sort | uniq -d

# 3. cutover present
aws s3 cp s3://$BUCKET/_meta/cutover.json -
```
