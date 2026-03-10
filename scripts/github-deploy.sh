#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

TARGET_BRANCH="${1:-main}"
EXPECTED_SHA="${2:-}"

require_clean_worktree() {
  if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    echo "Refusing GitHub-driven deploy with local modifications present." >&2
    exit 1
  fi
}

require_branch_checkout() {
  local current_branch

  current_branch="$(git branch --show-current)"
  if [[ -z "${current_branch}" ]]; then
    echo "Refusing GitHub-driven deploy from a detached HEAD." >&2
    exit 1
  fi

  if [[ "${current_branch}" != "${TARGET_BRANCH}" ]]; then
    echo "Refusing GitHub-driven deploy from ${current_branch}; expected ${TARGET_BRANCH}." >&2
    exit 1
  fi
}

fetch_target_branch() {
  echo "Fetching origin/${TARGET_BRANCH}..."
  git fetch --prune origin "${TARGET_BRANCH}"
}

verify_expected_sha() {
  local remote_sha

  remote_sha="$(git rev-parse "origin/${TARGET_BRANCH}")"
  if [[ -n "${EXPECTED_SHA}" && "${remote_sha}" != "${EXPECTED_SHA}" ]]; then
    echo "Refusing deploy because origin/${TARGET_BRANCH} is ${remote_sha}, expected ${EXPECTED_SHA}." >&2
    exit 1
  fi
}

fast_forward_checkout() {
  echo "Fast-forwarding ${TARGET_BRANCH} to origin/${TARGET_BRANCH}..."
  git merge --ff-only "origin/${TARGET_BRANCH}"
}

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "GitHub-driven deploy requires a git worktree." >&2
  exit 1
fi

require_clean_worktree
require_branch_checkout
fetch_target_branch
verify_expected_sha
fast_forward_checkout

echo "Running reviewed deployment script..."
"${ROOT_DIR}/deploy.sh" --skip-git-pull
