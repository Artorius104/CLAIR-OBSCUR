#!/usr/bin/env bash
# EC2 first-boot bootstrap. Installs docker + compose plugin, drops a systemd
# unit that runs the streaming compose project on boot.
set -euxo pipefail

dnf update -y
dnf install -y docker git
systemctl enable --now docker
usermod -aG docker ec2-user

# docker compose v2 plugin
mkdir -p /usr/local/lib/docker/cli-plugins
COMPOSE_VERSION="v2.29.7"
curl -fsSL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

mkdir -p /opt/clair-obscur
chown ec2-user:ec2-user /opt/clair-obscur

# systemd unit for the stream service (created empty; deploy.sh fills it)
cat >/etc/systemd/system/clair-obscur-stream.service <<'UNIT'
[Unit]
Description=Clair Obscur ingestion stream
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/clair-obscur
ExecStartPre=/usr/local/lib/docker/cli-plugins/docker-compose --profile stream pull
ExecStart=/usr/local/lib/docker/cli-plugins/docker-compose --profile stream up -d
ExecStop=/usr/local/lib/docker/cli-plugins/docker-compose --profile stream down

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
