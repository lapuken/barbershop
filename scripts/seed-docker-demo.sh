#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if docker compose version >/dev/null 2>&1; then
  docker compose exec -T web python manage.py seed_demo
elif command -v docker-compose >/dev/null 2>&1; then
  docker-compose exec -T web python manage.py seed_demo
else
  echo "Docker Compose is required but was not found." >&2
  exit 1
fi
