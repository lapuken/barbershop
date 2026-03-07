#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="$(cd "${ROOT_DIR}/.." && pwd)"
MODE="${1:-local}"

if [[ -d "${PROJECT_DIR}/env" ]] && [[ -f "${PROJECT_DIR}/env/.env" ]]; then
  DEFAULT_ENV_FILE="${PROJECT_DIR}/env/.env"
else
  DEFAULT_ENV_FILE="${ROOT_DIR}/.env"
fi

ENV_FILE="${ENV_FILE:-${DEFAULT_ENV_FILE}}"
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  . "${ENV_FILE}"
  set +a
fi

APP_DOMAIN="${APP_DOMAIN:-app.machinjiri.net}"
APP_PORT="${APP_PORT:-8000}"
PORT="${PORT:-8000}"

case "${MODE}" in
  container)
    python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:${PORT}/healthz/', timeout=5).read()"
    ;;
  local)
    curl --fail --silent --show-error "http://127.0.0.1:${APP_PORT}/healthz/" >/dev/null
    ;;
  public)
    curl --fail --silent --show-error "https://${APP_DOMAIN}/healthz/" >/dev/null
    ;;
  full)
    "${BASH_SOURCE[0]}" local
    "${BASH_SOURCE[0]}" public
    ;;
  *)
    echo "Usage: $0 [container|local|public|full]" >&2
    exit 1
    ;;
esac
