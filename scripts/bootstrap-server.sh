#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root (for example: sudo ./scripts/bootstrap-server.sh)." >&2
  exit 1
fi

APP_DIR="${APP_DIR:-/opt/smart-barber}"
APP_USER="${APP_USER:-${SUDO_USER:-root}}"
CONFIGURE_UFW="${CONFIGURE_UFW:-false}"
ADMIN_SSH_IP="${ADMIN_SSH_IP:-}"

echo "Updating Ubuntu packages..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

echo "Installing base packages..."
apt-get install -y ca-certificates curl git gnupg lsb-release jq ufw

echo "Installing Docker Engine and Docker Compose plugin..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /tmp/docker.gpg
gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg /tmp/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
rm -f /tmp/docker.gpg

. /etc/os-release
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

echo "Preparing application directories..."
install -d -m 0755 "${APP_DIR}"
install -d -m 0755 "${APP_DIR}/backups"

if id "${APP_USER}" >/dev/null 2>&1; then
  chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
  usermod -aG docker "${APP_USER}" || true
fi

if [[ "${CONFIGURE_UFW}" == "true" ]]; then
  echo "Configuring UFW baseline rules..."
  ufw default deny incoming
  ufw default allow outgoing
  if [[ -n "${ADMIN_SSH_IP}" ]]; then
    ufw allow from "${ADMIN_SSH_IP}" to any port 22 proto tcp
  else
    ufw allow OpenSSH
  fi
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw --force enable
fi

cat <<EOF

Server bootstrap complete.

Application directory:
  ${APP_DIR}

Next steps:
1. Upload or clone the repository into ${APP_DIR}
2. Create ${APP_DIR}/.env from .env.example with production secrets
3. Run:
     cd ${APP_DIR}
     ./scripts/deploy.sh

Firewall guidance (if CONFIGURE_UFW was false):
  sudo ufw allow OpenSSH
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
  sudo ufw enable

If APP_USER was updated for Docker group membership, start a new shell session before running docker commands.
EOF
