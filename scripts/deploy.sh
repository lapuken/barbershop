#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env}"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/docker-compose.yml}"

require_command() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Missing required command: ${cmd}" >&2
    exit 1
  fi
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
  local attempts=40
  local delay_seconds=3
  local i

  for i in $(seq 1 "${attempts}"); do
    if compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
      return
    fi
    sleep "${delay_seconds}"
  done

  echo "Database did not become ready in time." >&2
  exit 1
}

require_command docker

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "Compose file not found: ${COMPOSE_FILE}" >&2
  exit 1
fi

if [[ ! -f "${ROOT_DIR}/Caddyfile" ]]; then
  echo "Caddyfile not found at ${ROOT_DIR}/Caddyfile" >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Environment file not found: ${ENV_FILE}" >&2
  echo "Create it from .env.example before deployment." >&2
  exit 1
fi

set -a
. "${ENV_FILE}"
set +a

required_vars=(
  APP_DOMAIN
  ACME_EMAIL
  DJANGO_SETTINGS_MODULE
  DJANGO_SECRET_KEY
  DJANGO_ALLOWED_HOSTS
  DJANGO_CSRF_TRUSTED_ORIGINS
  POSTGRES_DB
  POSTGRES_USER
  POSTGRES_PASSWORD
  POSTGRES_HOST
)

for name in "${required_vars[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required variable in ${ENV_FILE}: ${name}" >&2
    exit 1
  fi
done

COMPOSE="$(compose_cmd)"

echo "Building web image..."
compose build web

echo "Starting database..."
compose up -d db
wait_for_db

echo "Running Django migrations..."
compose run --rm -e RUN_COLLECTSTATIC=false web python manage.py migrate --noinput

echo "Collecting static files..."
compose run --rm -e RUN_COLLECTSTATIC=false web python manage.py collectstatic --noinput

echo "Starting web and caddy..."
compose up -d web caddy

echo
echo "Current service status:"
compose ps

cat <<EOF

Deployment complete.

Suggested validation commands:
  curl -H "Host: ${APP_DOMAIN}" http://127.0.0.1/healthz/
  curl -I https://${APP_DOMAIN}/healthz/

Useful operations:
  ./scripts/create-initial-admin.sh
  ./scripts/backup-db.sh
  ${COMPOSE} --env-file ${ENV_FILE} -f ${COMPOSE_FILE} logs -f caddy web
EOF
