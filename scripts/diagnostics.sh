#!/usr/bin/env bash
set -u

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
TAIL_LINES="${TAIL_LINES:-120}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tail)
      TAIL_LINES="${2:?--tail requires a value}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  . "${ENV_FILE}"
  set +a
fi

export ENV_FILE_PATH="${ENV_FILE}"
APP_DOMAIN="${APP_DOMAIN:-app.machinjiri.net}"
NGINX_ACCESS_LOG="${PROJECT_DIR}/logs/nginx/app.machinjiri.net.access.log"
NGINX_ERROR_LOG="${PROJECT_DIR}/logs/nginx/app.machinjiri.net.error.log"

compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    echo "docker compose"
    return
  fi
  if command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
    return
  fi
  echo ""
}

run_shell_section() {
  local title="$1"
  local cmd="$2"
  printf '\n== %s ==\n' "${title}"
  bash -lc "${cmd}" || true
}

COMPOSE="$(compose_cmd)"

echo "Diagnostics captured at $(date --iso-8601=seconds)"
echo "Repository: ${ROOT_DIR}"
echo "Environment file: ${ENV_FILE}"

run_shell_section "Git Release" "git rev-parse HEAD && git status --short"
run_shell_section "Disk" "df -h"
run_shell_section "Memory" "free -h"
run_shell_section "Docker Containers" "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"

if [[ -n "${COMPOSE}" ]]; then
  run_shell_section "Compose Status" "${COMPOSE} --env-file '${ENV_FILE}' -f '${COMPOSE_FILE}' ps"
  run_shell_section "Compose Logs" "${COMPOSE} --env-file '${ENV_FILE}' -f '${COMPOSE_FILE}' logs --tail=${TAIL_LINES} web db"
fi

run_shell_section "Local Health" "'${ROOT_DIR}/scripts/healthcheck.sh' local"
run_shell_section "Public Health" "'${ROOT_DIR}/scripts/healthcheck.sh' public"
run_shell_section "Open Ports" "ss -tulpn | grep -E ':80|:443|:8000|:5432' || true"

if command -v sudo >/dev/null 2>&1; then
  run_shell_section "Nginx Status" "sudo systemctl status nginx --no-pager --lines=25"
  run_shell_section "Nginx Config Test" "sudo nginx -t"
fi

if [[ -f "${NGINX_ERROR_LOG}" ]]; then
  run_shell_section "Nginx Error Log" "tail -n ${TAIL_LINES} '${NGINX_ERROR_LOG}'"
fi

if [[ -f "${NGINX_ACCESS_LOG}" ]]; then
  run_shell_section "Nginx Access Log" "tail -n ${TAIL_LINES} '${NGINX_ACCESS_LOG}'"
fi
