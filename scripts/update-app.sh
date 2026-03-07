#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ "${1:-}" == "--git-pull" ]]; then
  shift
  set -- --git-pull "$@"
fi

echo "Running deployment update..."
"${ROOT_DIR}/scripts/deploy.sh" "$@"

cat <<EOF

Update flow complete.

Post-update checks:
  docker compose ps
  docker compose logs --tail=100 web
  docker compose logs --tail=100 db
  sudo nginx -t && sudo systemctl reload nginx
EOF
