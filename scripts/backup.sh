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
BACKUP_DIR="${BACKUP_DIR:-${DEFAULT_BACKUP_DIR}}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
BACKUP_ARCHIVE="${BACKUP_ARCHIVE:-false}"

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

env_bool() {
  case "${1:-false}" in
    1|true|TRUE|yes|YES|on|ON)
      return 0
      ;;
  esac
  return 1
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
export ENV_FILE_PATH="${ENV_FILE}"
export APP_UID="${APP_UID:-$(id -u)}"
export APP_GID="${APP_GID:-$(id -g)}"
export APP_PORT="${APP_PORT:-8000}"

if [[ -z "${POSTGRES_DB:-}" || -z "${POSTGRES_USER:-}" ]]; then
  echo "POSTGRES_DB and POSTGRES_USER must be set in ${ENV_FILE}." >&2
  exit 1
fi

timestamp="$(date +%Y%m%d-%H%M%S)"
backup_set_dir="${BACKUP_DIR}/${timestamp}"
mkdir -p "${backup_set_dir}"
chmod 700 "${backup_set_dir}"

COMPOSE="$(compose_cmd)"
compose up -d db
wait_for_db

db_backup="${backup_set_dir}/database.dump"
echo "Creating database backup: ${db_backup}"
compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "${db_backup}"
chmod 600 "${db_backup}"

if [[ -d "${ROOT_DIR}/shared/media" ]] && [[ -n "$(find "${ROOT_DIR}/shared/media" -mindepth 1 -print -quit)" ]]; then
  media_backup="${backup_set_dir}/media.tar.gz"
  echo "Archiving media files: ${media_backup}"
  tar -C "${ROOT_DIR}/shared" -czf "${media_backup}" media
  chmod 600 "${media_backup}"
else
  echo "No media files found under ${ROOT_DIR}/shared/media. Skipping media archive."
fi

metadata_file="${backup_set_dir}/metadata.txt"
{
  echo "created_at=$(date --iso-8601=seconds)"
  echo "app_domain=${APP_DOMAIN:-app.machinjiri.net}"
  echo "git_sha=$(git rev-parse HEAD 2>/dev/null || echo unavailable)"
} > "${metadata_file}"
chmod 600 "${metadata_file}"

if env_bool "${BACKUP_ARCHIVE}"; then
  archive_file="${BACKUP_DIR}/smartbarber-${timestamp}.tar.gz"
  echo "Creating archive: ${archive_file}"
  tar -C "${BACKUP_DIR}" -czf "${archive_file}" "${timestamp}"
  chmod 600 "${archive_file}"
fi

if [[ "${BACKUP_RETENTION_DAYS}" =~ ^[0-9]+$ ]] && [[ "${BACKUP_RETENTION_DAYS}" -gt 0 ]]; then
  RETENTION_DAYS="${BACKUP_RETENTION_DAYS}" BACKUP_DIR="${BACKUP_DIR}" "${ROOT_DIR}/scripts/cleanup-backups.sh"
fi

echo "Backup complete: ${backup_set_dir}"
