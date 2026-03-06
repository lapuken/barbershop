#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PROJECT_DIR="$(cd "${ROOT_DIR}/.." && pwd)"
if [[ -d "${PROJECT_DIR}/env" || -d "${PROJECT_DIR}/backups" || -d "${PROJECT_DIR}/logs" ]]; then
  DEFAULT_ENV_FILE="${PROJECT_DIR}/env/.env"
  DEFAULT_BACKUP_DIR="${PROJECT_DIR}/backups"
else
  DEFAULT_ENV_FILE="${ROOT_DIR}/.env"
  DEFAULT_BACKUP_DIR="${ROOT_DIR}/backups"
fi

ENV_FILE="${ENV_FILE:-${DEFAULT_ENV_FILE}}"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/docker-compose.yml}"
RELOAD_NGINX="${RELOAD_NGINX:-true}"

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

load_env() {
  if [[ ! -f "${ENV_FILE}" ]]; then
    echo "Environment file not found: ${ENV_FILE}" >&2
    echo "Create it from .env.example before deployment." >&2
    exit 1
  fi

  set -a
  . "${ENV_FILE}"
  set +a

  export APP_UID="${APP_UID:-$(id -u)}"
  export APP_GID="${APP_GID:-$(id -g)}"
  export APP_PORT="${APP_PORT:-8000}"
}

placeholder_value() {
  case "${1:-}" in
    "" | replace_me | change-me-in-production | unsafe-dev-key-change-me | replace-with-openssl-rand-base64-48 | replace-with-strong-db-password)
      return 0
      ;;
  esac
  return 1
}

validate_env() {
  local debug_value
  local required_vars=(
    APP_DOMAIN
    ROOT_DOMAIN
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

  if [[ "${DJANGO_SETTINGS_MODULE}" != "config.settings.prod" ]]; then
    echo "DJANGO_SETTINGS_MODULE must be config.settings.prod for server deployments." >&2
    exit 1
  fi

  debug_value="${DJANGO_DEBUG:-false}"
  debug_value="${debug_value,,}"
  if [[ "${debug_value}" == "true" || "${debug_value}" == "1" ]]; then
    echo "DJANGO_DEBUG must be False for server deployments." >&2
    exit 1
  fi

  if placeholder_value "${DJANGO_SECRET_KEY:-}"; then
    echo "DJANGO_SECRET_KEY is still using a placeholder value." >&2
    exit 1
  fi

  if placeholder_value "${POSTGRES_PASSWORD:-}"; then
    echo "POSTGRES_PASSWORD is still using a placeholder value." >&2
    exit 1
  fi
}

prepare_directories() {
  install -d -m 0755 "${ROOT_DIR}/shared" "${ROOT_DIR}/shared/static" "${ROOT_DIR}/shared/media"
  install -d -m 0700 "${DEFAULT_BACKUP_DIR}"
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

wait_for_web() {
  local attempts=30
  local delay_seconds=3
  local health_url="http://127.0.0.1:${APP_PORT}/healthz/"
  local i

  for i in $(seq 1 "${attempts}"); do
    if curl --fail --silent --show-error "${health_url}" >/dev/null 2>&1; then
      return
    fi
    sleep "${delay_seconds}"
  done

  echo "Web health check failed: ${health_url}" >&2
  compose logs --tail=200 web db >&2 || true
  exit 1
}

reload_nginx_if_possible() {
  if [[ "${RELOAD_NGINX}" != "true" ]]; then
    return
  fi

  if ! command -v sudo >/dev/null 2>&1 || ! command -v nginx >/dev/null 2>&1; then
    return
  fi

  if sudo -n nginx -t >/dev/null 2>&1; then
    sudo -n systemctl reload nginx >/dev/null 2>&1 || true
    return
  fi

  echo "Nginx reload skipped. Run: sudo nginx -t && sudo systemctl reload nginx"
}

require_command docker
require_command curl

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "Compose file not found: ${COMPOSE_FILE}" >&2
  exit 1
fi

load_env
validate_env
prepare_directories

COMPOSE="$(compose_cmd)"

echo "Building web image..."
compose build web

echo "Starting database..."
compose up -d db
wait_for_db

echo "Running Django deployment checks..."
compose run --rm --no-deps -e RUN_COLLECTSTATIC=false web python manage.py check --deploy

echo "Running Django migrations..."
compose run --rm --no-deps -e RUN_COLLECTSTATIC=false web python manage.py migrate --noinput

echo "Collecting static files..."
compose run --rm --no-deps -e RUN_COLLECTSTATIC=false web python manage.py collectstatic --noinput

echo "Starting web..."
compose up -d web
wait_for_web
reload_nginx_if_possible

echo
echo "Current service status:"
compose ps

cat <<EOF

Deployment complete.

Suggested validation commands:
  curl http://127.0.0.1:${APP_PORT}/healthz/
  curl -I https://${APP_DOMAIN}/healthz/

Useful operations:
  ./deploy.sh
  ./backup.sh
  ./scripts/create-initial-admin.sh
  ${COMPOSE} --env-file ${ENV_FILE} -f ${COMPOSE_FILE} logs -f web db
EOF
