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
GIT_PULL_BEFORE_DEPLOY="${GIT_PULL_BEFORE_DEPLOY:-false}"
BACKUP_BEFORE_DEPLOY="${BACKUP_BEFORE_DEPLOY:-true}"
RUN_DIAGNOSTICS_ON_FAILURE="${RUN_DIAGNOSTICS_ON_FAILURE:-true}"
RELEASES_DIR="${PROJECT_DIR}/logs/releases"
LATEST_RELEASE_FILE="${RELEASES_DIR}/latest-successful-release.env"
PREVIOUS_RELEASE_FILE="${RELEASES_DIR}/previous-successful-release.env"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --git-pull)
      GIT_PULL_BEFORE_DEPLOY=true
      shift
      ;;
    --skip-git-pull)
      GIT_PULL_BEFORE_DEPLOY=false
      shift
      ;;
    --skip-backup)
      BACKUP_BEFORE_DEPLOY=false
      shift
      ;;
    --no-nginx-reload)
      RELOAD_NGINX=false
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

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

  export ENV_FILE_PATH="${ENV_FILE}"
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

env_bool() {
  case "${1:-false}" in
    1|true|TRUE|yes|YES|on|ON)
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

  if ! env_bool "${SECURE_SSL_REDIRECT:-true}"; then
    echo "SECURE_SSL_REDIRECT must be True for server deployments." >&2
    exit 1
  fi

  if ! env_bool "${SESSION_COOKIE_SECURE:-true}"; then
    echo "SESSION_COOKIE_SECURE must be True for server deployments." >&2
    exit 1
  fi

  if ! env_bool "${CSRF_COOKIE_SECURE:-true}"; then
    echo "CSRF_COOKIE_SECURE must be True for server deployments." >&2
    exit 1
  fi

  if [[ ",${DJANGO_ALLOWED_HOSTS}," != *",${APP_DOMAIN},"* ]]; then
    echo "DJANGO_ALLOWED_HOSTS must include ${APP_DOMAIN}." >&2
    exit 1
  fi

  if [[ ",${DJANGO_ALLOWED_HOSTS}," != *",${ROOT_DOMAIN},"* ]]; then
    echo "DJANGO_ALLOWED_HOSTS must include ${ROOT_DOMAIN}." >&2
    exit 1
  fi

  if [[ ",${DJANGO_CSRF_TRUSTED_ORIGINS}," != *",https://${APP_DOMAIN},"* ]]; then
    echo "DJANGO_CSRF_TRUSTED_ORIGINS must include https://${APP_DOMAIN}." >&2
    exit 1
  fi
}

prepare_directories() {
  install -d -m 0755 "${ROOT_DIR}/shared" "${ROOT_DIR}/shared/static" "${ROOT_DIR}/shared/media"
  install -d -m 0700 "${DEFAULT_BACKUP_DIR}"
  install -d -m 0755 "${RELEASES_DIR}"
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
  local i

  for i in $(seq 1 "${attempts}"); do
    if "${ROOT_DIR}/scripts/healthcheck.sh" local >/dev/null 2>&1; then
      return
    fi
    sleep "${delay_seconds}"
  done

  echo "Web health check failed." >&2
  compose logs --tail=200 web db >&2 || true
  exit 1
}

git_pull_if_requested() {
  local branch_name

  if ! env_bool "${GIT_PULL_BEFORE_DEPLOY}"; then
    return
  fi

  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Skipping git pull because ${ROOT_DIR} is not a git worktree."
    return
  fi

  if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    echo "Refusing to git pull with local modifications present." >&2
    exit 1
  fi

  branch_name="$(git branch --show-current)"
  if [[ -z "${branch_name}" ]]; then
    echo "Refusing to git pull from a detached HEAD. Check out a branch first." >&2
    exit 1
  fi

  echo "Pulling latest code from ${branch_name}..."
  git pull --ff-only
}

backup_if_requested() {
  if ! env_bool "${BACKUP_BEFORE_DEPLOY}"; then
    return
  fi

  echo "Creating pre-deploy backup..."
  "${ROOT_DIR}/scripts/backup.sh"
}

record_successful_release() {
  local release_sha branch_name timestamp

  release_sha="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
  branch_name="$(git branch --show-current 2>/dev/null || true)"
  timestamp="$(date --iso-8601=seconds)"

  if [[ -f "${LATEST_RELEASE_FILE}" ]]; then
    cp "${LATEST_RELEASE_FILE}" "${PREVIOUS_RELEASE_FILE}"
  fi

  cat > "${LATEST_RELEASE_FILE}" <<EOF
sha=${release_sha}
branch=${branch_name:-detached}
timestamp=${timestamp}
EOF
}

run_failure_diagnostics() {
  local exit_code=$?

  if env_bool "${RUN_DIAGNOSTICS_ON_FAILURE}" && [[ -x "${ROOT_DIR}/scripts/diagnostics.sh" ]]; then
    echo
    echo "Deployment failed. Collecting diagnostics..."
    "${ROOT_DIR}/scripts/diagnostics.sh" --tail 80 || true
  fi

  exit "${exit_code}"
}

reload_nginx_if_possible() {
  if ! env_bool "${RELOAD_NGINX}"; then
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
trap run_failure_diagnostics ERR

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "Compose file not found: ${COMPOSE_FILE}" >&2
  exit 1
fi

load_env
validate_env
prepare_directories
git_pull_if_requested
backup_if_requested

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
record_successful_release

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
