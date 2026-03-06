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
  for i in $(seq 1 30); do
    if compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
      return
    fi
    sleep 2
  done
  echo "Database did not become ready in time." >&2
  exit 1
}

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Environment file not found: ${ENV_FILE}" >&2
  exit 1
fi

set -a
. "${ENV_FILE}"
set +a
export APP_UID="${APP_UID:-$(id -u)}"
export APP_GID="${APP_GID:-$(id -g)}"
export APP_PORT="${APP_PORT:-8000}"

COMPOSE="$(compose_cmd)"
compose up -d db
wait_for_db

if [[ -n "${DJANGO_SUPERUSER_USERNAME:-}" && -n "${DJANGO_SUPERUSER_EMAIL:-}" && -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]]; then
  echo "Creating initial admin user non-interactively..."
  compose run --rm --no-deps web python manage.py createsuperuser --noinput
else
  cat <<EOF
Environment variables DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, and
DJANGO_SUPERUSER_PASSWORD were not all set.

Launching interactive createsuperuser instead.
EOF
  compose run --rm --no-deps web python manage.py createsuperuser
fi
