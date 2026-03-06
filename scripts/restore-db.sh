#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PROJECT_DIR="$(cd "${ROOT_DIR}/.." && pwd)"
if [[ -d "${PROJECT_DIR}/env" || -d "${PROJECT_DIR}/backups" || -d "${PROJECT_DIR}/logs" ]]; then
  DEFAULT_ENV_FILE="${PROJECT_DIR}/env/.env"
else
  DEFAULT_ENV_FILE="${ROOT_DIR}/.env"
fi

ENV_FILE="${ENV_FILE:-${DEFAULT_ENV_FILE}}"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/docker-compose.yml}"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/restore-db.sh <backup_file.dump|backup_file.sql>

Notes:
  - This operation overwrites application data in PostgreSQL.
  - The script prompts for explicit confirmation before restoring.
EOF
}

compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    echo "docker compose"
    return
  fi
  if command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
    return
  fi
  echo "Docker Compose is required but was not found." >&2
  exit 1
}

compose() {
  if [[ "${COMPOSE}" == "docker compose" ]]; then
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
  else
    docker-compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
  fi
}

wait_for_db() {
  local i
  for i in $(seq 1 40); do
    if compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
      return
    fi
    sleep 2
  done
  echo "Database did not become ready in time." >&2
  exit 1
}

if [[ $# -ne 1 ]]; then
  usage
  exit 1
fi

BACKUP_FILE="$1"
if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "Backup file not found: ${BACKUP_FILE}" >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Environment file not found: ${ENV_FILE}" >&2
  exit 1
fi

set -a
. "${ENV_FILE}"
set +a
export ENV_FILE_PATH="${ENV_FILE}"
export APP_UID="${APP_UID:-$(id -u)}"
export APP_GID="${APP_GID:-$(id -g)}"
export APP_PORT="${APP_PORT:-8000}"

echo "WARNING: This restore will overwrite data in database '${POSTGRES_DB:-unset}'."
echo "Backup file: ${BACKUP_FILE}"
read -r -p "Type RESTORE to continue: " confirmation
if [[ "${confirmation}" != "RESTORE" ]]; then
  echo "Restore cancelled."
  exit 1
fi

COMPOSE="$(compose_cmd)"

echo "Stopping application containers to reduce write activity..."
compose stop web >/dev/null 2>&1 || true

echo "Ensuring database is running..."
compose up -d db
wait_for_db

if [[ "${BACKUP_FILE}" == *.sql ]]; then
  echo "Restoring plain SQL dump..."
  cat "${BACKUP_FILE}" | compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
else
  echo "Restoring pg_dump custom-format backup..."
  cat "${BACKUP_FILE}" | compose exec -T db sh -c 'pg_restore --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
fi

echo "Starting web..."
compose up -d web

echo "Restore complete."
