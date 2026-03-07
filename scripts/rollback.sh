#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PROJECT_DIR="$(cd "${ROOT_DIR}/.." && pwd)"
RELEASES_DIR="${PROJECT_DIR}/logs/releases"
PREVIOUS_RELEASE_FILE="${RELEASES_DIR}/previous-successful-release.env"
TARGET_REF="${1:-}"
BACKUP_BEFORE_ROLLBACK="${BACKUP_BEFORE_ROLLBACK:-true}"

env_bool() {
  case "${1:-false}" in
    1|true|TRUE|yes|YES|on|ON)
      return 0
      ;;
  esac
  return 1
}

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Rollback requires a git checkout." >&2
  exit 1
fi

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "Refusing to roll back with local modifications present." >&2
  exit 1
fi

if [[ -z "${TARGET_REF}" ]] && [[ -f "${PREVIOUS_RELEASE_FILE}" ]]; then
  # shellcheck disable=SC1090
  . "${PREVIOUS_RELEASE_FILE}"
  TARGET_REF="${sha:-}"
fi

if [[ -z "${TARGET_REF}" ]]; then
  TARGET_REF="HEAD~1"
fi

CURRENT_REF="$(git rev-parse HEAD)"
echo "Current release: ${CURRENT_REF}"
echo "Rollback target: ${TARGET_REF}"

if env_bool "${BACKUP_BEFORE_ROLLBACK}"; then
  echo "Creating safety backup before rollback..."
  "${ROOT_DIR}/scripts/backup.sh"
fi

git checkout "${TARGET_REF}"

if ! BACKUP_BEFORE_DEPLOY=false GIT_PULL_BEFORE_DEPLOY=false "${ROOT_DIR}/scripts/deploy.sh" --skip-git-pull --skip-backup; then
  echo "Rollback deployment failed. Previous checkout was ${CURRENT_REF}." >&2
  exit 1
fi

echo "Rollback complete. Running release is now $(git rev-parse HEAD)."

CURRENT_BRANCH="$(git branch --show-current || true)"
if [[ -z "${CURRENT_BRANCH}" ]]; then
  cat <<EOF

The repository is now in a detached HEAD state at ${TARGET_REF}.
Before your next deploy with --git-pull, switch back to your normal branch.
Example:
  git switch main
EOF
fi
