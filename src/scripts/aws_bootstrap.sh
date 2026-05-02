#!/usr/bin/env bash
# One-shot AWS bootstrap for the ingestion stack.
#
#   - S3 raw bucket (versioned, encrypted)
#   - ECR repos for backfill + stream images
#   - IAM role + instance profile for the EC2
#   - Security group (egress only, ingress 22 from your IP)
#   - EC2 t3.small with the role attached, docker pre-installed via user-data
#
# Idempotent: all `aws ... create-*` calls are guarded so re-runs are safe.

set -euo pipefail

REGION="${AWS_REGION:-eu-west-3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IAM_DIR="${SCRIPT_DIR}/aws/iam"
USER_DATA="${SCRIPT_DIR}/aws/user-data.sh"

ACCT="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${S3_RAW_BUCKET:-clair-obscur-raw-${ACCT}}"
ROLE="ClairObscurIngestionRole"
PROFILE="ClairObscurIngestionProfile"
SG_NAME="clair-obscur-ingestion-sg"
KEY_NAME="${EC2_KEY_NAME:-clair-obscur-ingestion-key}"
INSTANCE_TYPE="${EC2_INSTANCE_TYPE:-t3.small}"
TAG_NAME="clair-obscur-ingestion"

ECR_BACKFILL="clair-obscur/backfill"
ECR_STREAM="clair-obscur/stream"

log() { printf "\033[1;36m[bootstrap]\033[0m %s\n" "$*"; }

# ---------- 1. S3 ----------
log "S3 bucket: $BUCKET"
if ! aws s3api head-bucket --bucket "$BUCKET" --region "$REGION" 2>/dev/null; then
  aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" \
    --create-bucket-configuration "LocationConstraint=$REGION" >/dev/null
fi
aws s3api put-bucket-versioning --bucket "$BUCKET" \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$BUCKET" \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-public-access-block --bucket "$BUCKET" \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# ---------- 2. ECR ----------
for repo in "$ECR_BACKFILL" "$ECR_STREAM"; do
  log "ECR repo: $repo"
  aws ecr describe-repositories --repository-names "$repo" --region "$REGION" >/dev/null 2>&1 \
    || aws ecr create-repository --repository-name "$repo" --region "$REGION" \
         --image-scanning-configuration scanOnPush=true >/dev/null
done

# ---------- 3. IAM ----------
log "IAM role: $ROLE"
aws iam get-role --role-name "$ROLE" >/dev/null 2>&1 \
  || aws iam create-role --role-name "$ROLE" \
       --assume-role-policy-document "file://${IAM_DIR}/trust-ec2.json" >/dev/null

POLICY_FILE="$(mktemp)"
sed "s|__BUCKET__|${BUCKET}|g" "${IAM_DIR}/policy-ingestion.json.tpl" >"$POLICY_FILE"
aws iam put-role-policy --role-name "$ROLE" \
  --policy-name "ingestion-inline" \
  --policy-document "file://${POLICY_FILE}"
rm -f "$POLICY_FILE"

aws iam get-instance-profile --instance-profile-name "$PROFILE" >/dev/null 2>&1 \
  || aws iam create-instance-profile --instance-profile-name "$PROFILE" >/dev/null

if ! aws iam get-instance-profile --instance-profile-name "$PROFILE" \
     --query "InstanceProfile.Roles[?RoleName=='${ROLE}']" --output text | grep -q "$ROLE"; then
  aws iam add-role-to-instance-profile --instance-profile-name "$PROFILE" --role-name "$ROLE"
fi

# ---------- 4. Security group ----------
log "security group: $SG_NAME"
VPC_ID="$(aws ec2 describe-vpcs --filters Name=is-default,Values=true \
  --query 'Vpcs[0].VpcId' --output text --region "$REGION")"
SG_ID="$(aws ec2 describe-security-groups --filters Name=group-name,Values="$SG_NAME" \
  --query 'SecurityGroups[0].GroupId' --output text --region "$REGION" 2>/dev/null || echo None)"
if [ "$SG_ID" = "None" ] || [ -z "$SG_ID" ]; then
  SG_ID="$(aws ec2 create-security-group --group-name "$SG_NAME" \
    --description "Clair Obscur ingestion" --vpc-id "$VPC_ID" \
    --region "$REGION" --query GroupId --output text)"
fi
MY_IP="$(curl -fsS https://checkip.amazonaws.com)/32"
aws ec2 authorize-security-group-ingress --group-id "$SG_ID" \
  --protocol tcp --port 22 --cidr "$MY_IP" --region "$REGION" 2>/dev/null || true

# ---------- 5. EC2 ----------
log "EC2 instance"
EXISTING_IID="$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=${TAG_NAME}" "Name=instance-state-name,Values=running,pending,stopped,stopping" \
  --query 'Reservations[0].Instances[0].InstanceId' --output text --region "$REGION" 2>/dev/null || echo None)"

if [ "$EXISTING_IID" = "None" ] || [ -z "$EXISTING_IID" ]; then
  AMI_ID="$(aws ssm get-parameter --region "$REGION" \
    --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
    --query Parameter.Value --output text)"

  IID="$(aws ec2 run-instances --region "$REGION" \
    --image-id "$AMI_ID" --instance-type "$INSTANCE_TYPE" \
    --iam-instance-profile "Name=$PROFILE" \
    --security-group-ids "$SG_ID" \
    --key-name "$KEY_NAME" \
    --user-data "file://${USER_DATA}" \
    --block-device-mappings 'DeviceName=/dev/xvda,Ebs={VolumeSize=30,VolumeType=gp3}' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${TAG_NAME}}]" \
    --query 'Instances[0].InstanceId' --output text)"
  log "launched $IID"
else
  IID="$EXISTING_IID"
  log "reusing $IID"
fi

aws ec2 wait instance-running --instance-ids "$IID" --region "$REGION"
PUB_IP="$(aws ec2 describe-instances --instance-ids "$IID" --region "$REGION" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)"

cat <<EOF

-------------------------------clair-obscur-logs-534727954026-eu-west-3-an----------------------------
Bootstrap complete.

  Bucket  : s3://$BUCKET
  Role    : $ROLE  (instance profile: $PROFILE)
  EC2 IID : $IID
  Public  : $PUB_IP
  ECR     : ${ACCT}.dkr.ecr.${REGION}.amazonaws.com/${ECR_BACKFILL}
            ${ACCT}.dkr.ecr.${REGION}.amazonaws.com/${ECR_STREAM}

Next:
  1. Add to your .env:        S3_RAW_BUCKET=$BUCKET
  2. Build + push images:     ./src/scripts/deploy.sh
  3. Run backfill on EC2:     ssh ec2-user@$PUB_IP 'cd /opt/clair-obscur && \
                                docker compose --profile backfill run --rm backfill'
  4. Start stream:            sudo systemctl start clair-obscur-stream
---------------------------------------------------------------
EOF
