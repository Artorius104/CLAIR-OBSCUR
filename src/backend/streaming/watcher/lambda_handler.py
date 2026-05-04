"""Lambda watcher: detect new OpenSearch documents and send an SQS wake-up.

Triggered by a CloudWatch Events rule (rate(1 minute)).
Compares the current doc count against the last known count stored in S3
at `{S3_META_PREFIX}/watcher_state.json`. Sends an SQS message when the
count has increased so the stream job wakes up immediately instead of
waiting for its fallback poll interval.

Zero external dependencies — only stdlib + boto3 (built-in Lambda runtime).

Deploy:
    zip watcher.zip lambda_handler.py
    aws lambda create-function \\
      --function-name clair-obscur-stream-watcher \\
      --runtime python3.12 \\
      --zip-file fileb://watcher.zip \\
      --handler lambda_handler.handler \\
      --role arn:aws:iam::<acct>:role/clair-obscur-lambda-role \\
      --timeout 30 --region eu-west-3 \\
      --environment Variables="{
          OPENSEARCH_URL=<url>,OPENSEARCH_INDEX=logs-raw,
          OPENSEARCH_USER=<user>,OPENSEARCH_PASSWORD=<pass>,
          S3_RAW_BUCKET=<bucket>,STREAM_SQS_QUEUE_URL=<queue-url>,
          AWS_REGION=eu-west-3}"

Required IAM permissions for the Lambda role:
    sqs:SendMessage          on the SQS queue
    s3:GetObject + s3:PutObject  on {bucket}/{S3_META_PREFIX}/watcher_state.json
"""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.request
from datetime import datetime, timezone
from typing import Any

import boto3

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def _count_docs(url: str, index: str, user: str, password: str) -> int:
    """Return the current number of documents in the OpenSearch index."""
    creds = base64.b64encode(f"{user}:{password}".encode()).decode()
    req = urllib.request.Request(
        f"{url.rstrip('/')}/{index}/_count",
        headers={"Authorization": f"Basic {creds}"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return int(json.loads(resp.read())["count"])


def _load_state(s3, bucket: str, key: str) -> dict[str, Any]:
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        return json.loads(obj["Body"].read())
    except Exception:
        return {}


def _save_state(s3, bucket: str, key: str, state: dict[str, Any]) -> None:
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(state, separators=(",", ":")).encode(),
        ContentType="application/json",
    )


def handler(event: dict, context: Any) -> dict[str, Any]:
    url      = os.environ["OPENSEARCH_URL"]
    index    = os.environ.get("OPENSEARCH_INDEX", "logs-raw")
    user     = os.environ["OPENSEARCH_USER"]
    password = os.environ["OPENSEARCH_PASSWORD"]
    bucket   = os.environ["S3_RAW_BUCKET"]
    queue    = os.environ["STREAM_SQS_QUEUE_URL"]
    region   = os.environ.get("AWS_REGION", "eu-west-3")
    state_key = os.environ.get("S3_META_PREFIX", "_meta") + "/watcher_state.json"

    current = _count_docs(url, index, user, password)

    s3 = boto3.client("s3", region_name=region)
    state = _load_state(s3, bucket, state_key)
    last = int(state.get("doc_count", 0))

    if current > last:
        added = current - last
        boto3.client("sqs", region_name=region).send_message(
            QueueUrl=queue,
            MessageBody=json.dumps({
                "event": "new_docs_detected",
                "count": current,
                "prev": last,
                "added": added,
                "ts": datetime.now(timezone.utc).isoformat(),
            }),
        )
        _save_state(s3, bucket, state_key, {
            "doc_count": current,
            "last_checked": datetime.now(timezone.utc).isoformat(),
        })
        log.info("new docs: %d → %d (+%d), SQS message sent", last, current, added)
        return {"new_docs": True, "count": current, "added": added}

    log.info("no new docs (count=%d)", current)
    return {"new_docs": False, "count": current}
