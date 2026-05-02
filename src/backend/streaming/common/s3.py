"""Thin S3 helpers used by backfill and stream."""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

log = logging.getLogger(__name__)


def s3_client(region: str):
    return boto3.client("s3", region_name=region)


def put_json(client, bucket: str, key: str, payload: dict[str, Any]) -> None:
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(payload, separators=(",", ":")).encode(),
        ContentType="application/json",
    )


def get_json(client, bucket: str, key: str) -> dict[str, Any] | None:
    try:
        r = client.get_object(Bucket=bucket, Key=key)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return None
        raise
    return json.loads(r["Body"].read())


def put_bytes(client, bucket: str, key: str, body: bytes, content_type: str = "application/x-ndjson") -> None:
    client.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)
