#!/usr/bin/env bash
# Build, push, and (re)deploy ingestion images.
#
# Usage:
#   ./src/scripts/deploy.sh                                          # build + push only
#   ./src/scripts/deploy.sh ec2-user@<host>                         # deploy with default key
#   ./src/scripts/deploy.sh ec2-user@<host> keys/my-key.pem         # deploy with explicit key
#
# SSH key resolution order:
#   1. Second argument (explicit key path)
#   2. EC2_SSH_KEY env var
#   3. keys/clair-obscur-ingestion-key.pem next to repo root
set -euo pipefail

REGION="${AWS_REGION:-eu-west-3}"
ACCT="$(aws sts get-caller-identity --query Account --output text)"
ECR_HOST="${ACCT}.dkr.ecr.${REGION}.amazonaws.com"
# REGISTRY includes the namespace so compose's ${REGISTRY}/stream resolves correctly
REGISTRY="${ECR_HOST}/clair-obscur"
TAG="${TAG:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M)}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STREAM_DIR="${ROOT_DIR}/src/backend/streaming"

log() { printf "\033[1;36m[deploy]\033[0m %s\n" "$*"; }

log "ECR login ($ECR_HOST)"
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "$ECR_HOST"

log "build $REGISTRY/backfill:$TAG"
docker build -t "$REGISTRY/backfill:$TAG" \
  -t "$REGISTRY/backfill:latest" \
  -f "$STREAM_DIR/backfill/Dockerfile" "$STREAM_DIR"

log "build $REGISTRY/stream:$TAG"
docker build -t "$REGISTRY/stream:$TAG" \
  -t "$REGISTRY/stream:latest" \
  -f "$STREAM_DIR/stream/Dockerfile" "$STREAM_DIR"

log "push"
docker push "$REGISTRY/backfill:$TAG"
docker push "$REGISTRY/backfill:latest"
docker push "$REGISTRY/stream:$TAG"
docker push "$REGISTRY/stream:latest"

if [ "${1:-}" = "" ]; then
  log "build/push done. Pass an EC2 user@host as \$1 to deploy."
  exit 0
fi

EC2_HOST="$1"

# resolve SSH key
_KEY="${2:-${EC2_SSH_KEY:-}}"
if [ -z "$_KEY" ]; then
  _DEFAULT_KEY="${ROOT_DIR}/keys/clair-obscur-ingestion-key.pem"
  if [ -f "$_DEFAULT_KEY" ]; then
    _KEY="$_DEFAULT_KEY"
  fi
fi
SSH_OPTS=(-o StrictHostKeyChecking=accept-new)
[ -n "$_KEY" ] && SSH_OPTS+=(-i "$_KEY")

log "syncing compose to $EC2_HOST (key=${_KEY:-<agent/default>})"
ssh "${SSH_OPTS[@]}" "$EC2_HOST" "mkdir -p /opt/clair-obscur"
scp "${SSH_OPTS[@]}" "$STREAM_DIR/docker-compose.yml" "$EC2_HOST:/opt/clair-obscur/docker-compose.yml"
scp "${SSH_OPTS[@]}" "$STREAM_DIR/stream/submit.sh"   "$EC2_HOST:/opt/clair-obscur/submit.sh"
scp "${SSH_OPTS[@]}" "$ROOT_DIR/.env"                  "$EC2_HOST:/opt/clair-obscur/.env"

# Append compose-specific vars to the remote .env so any manual docker compose
# command (backfill, etc.) picks up the right registry/tag without extra flags.
ssh "${SSH_OPTS[@]}" "$EC2_HOST" "
  grep -q '^REGISTRY=' /opt/clair-obscur/.env \
    && sed -i 's|^REGISTRY=.*|REGISTRY=$REGISTRY|' /opt/clair-obscur/.env \
    || echo 'REGISTRY=$REGISTRY' >> /opt/clair-obscur/.env
  grep -q '^TAG=' /opt/clair-obscur/.env \
    && sed -i 's|^TAG=.*|TAG=$TAG|' /opt/clair-obscur/.env \
    || echo 'TAG=$TAG' >> /opt/clair-obscur/.env
  grep -q '^ECR_HOST=' /opt/clair-obscur/.env \
    && sed -i 's|^ECR_HOST=.*|ECR_HOST=$ECR_HOST|' /opt/clair-obscur/.env \
    || echo 'ECR_HOST=$ECR_HOST' >> /opt/clair-obscur/.env
"

log "pulling all images on $EC2_HOST"
ssh "${SSH_OPTS[@]}" "$EC2_HOST" "
  set -e
  aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_HOST
  cd /opt/clair-obscur
  docker compose --profile stream pull
  docker compose --profile backfill pull
  sudo systemctl restart clair-obscur-stream || \
    docker compose --profile stream up -d
"
log "done. tag=$TAG"
log ""
log "To run backfill:  ssh ${SSH_OPTS[*]} $EC2_HOST 'cd /opt/clair-obscur && docker compose --profile backfill run --rm backfill'"
