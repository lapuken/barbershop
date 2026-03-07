#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PROJECT_DIR="$(cd "${ROOT_DIR}/.." && pwd)"
if [[ -d "${PROJECT_DIR}/backups" ]]; then
  DEFAULT_BACKUP_DIR="${PROJECT_DIR}/backups"
else
  DEFAULT_BACKUP_DIR="${ROOT_DIR}/backups"
fi

BACKUP_DIR="${BACKUP_DIR:-${DEFAULT_BACKUP_DIR}}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
DRY_RUN="${DRY_RUN:-false}"

env_bool() {
  case "${1:-false}" in
    1|true|TRUE|yes|YES|on|ON)
      return 0
      ;;
  esac
  return 1
}

if [[ ! -d "${BACKUP_DIR}" ]]; then
  echo "Backup directory not found: ${BACKUP_DIR}" >&2
  exit 0
fi

if [[ ! "${RETENTION_DAYS}" =~ ^[0-9]+$ ]]; then
  echo "RETENTION_DAYS must be an integer." >&2
  exit 1
fi

echo "Pruning backups older than ${RETENTION_DAYS} day(s) from ${BACKUP_DIR}"

while IFS= read -r path; do
  [[ -z "${path}" ]] && continue
  if env_bool "${DRY_RUN}"; then
    echo "Would remove ${path}"
  else
    rm -rf "${path}"
    echo "Removed ${path}"
  fi
done < <(find "${BACKUP_DIR}" -mindepth 1 -maxdepth 1 \( -type d -o -name '*.tar.gz' \) -mtime +"${RETENTION_DAYS}" -print)
