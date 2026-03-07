#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/restore.sh <backup_directory>

Example:
  ./scripts/restore.sh /opt/smartbarber/backups/20260306-030000
EOF
}

if [[ $# -ne 1 ]]; then
  usage
  exit 1
fi

BACKUP_SET_DIR="$1"
DB_DUMP="${BACKUP_SET_DIR}/database.dump"
MEDIA_ARCHIVE="${BACKUP_SET_DIR}/media.tar.gz"

if [[ ! -d "${BACKUP_SET_DIR}" ]]; then
  echo "Backup directory not found: ${BACKUP_SET_DIR}" >&2
  exit 1
fi

if [[ ! -f "${DB_DUMP}" ]]; then
  echo "Database dump not found: ${DB_DUMP}" >&2
  exit 1
fi

"${ROOT_DIR}/scripts/restore-db.sh" "${DB_DUMP}"

if [[ -f "${MEDIA_ARCHIVE}" ]]; then
  echo "Restoring media archive..."
  rm -rf "${ROOT_DIR}/shared/media"
  mkdir -p "${ROOT_DIR}/shared"
  tar -xzf "${MEDIA_ARCHIVE}" -C "${ROOT_DIR}/shared"
  echo "Media restore complete."
else
  echo "No media archive found in ${BACKUP_SET_DIR}. Skipping media restore."
fi
