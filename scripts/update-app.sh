#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ "${1:-}" == "--git-pull" ]]; then
  if ! command -v git >/dev/null 2>&1; then
    echo "git is required for --git-pull." >&2
    exit 1
  fi
  echo "Pulling latest code from tracked branch..."
  git pull --ff-only
fi

echo "Running deployment update..."
"${ROOT_DIR}/scripts/deploy.sh"

cat <<EOF

Update flow complete.

Post-update checks:
  docker compose ps
  docker compose logs --tail=100 web
  docker compose logs --tail=100 caddy
EOF
