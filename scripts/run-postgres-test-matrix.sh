#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

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

ENV_SOURCE_FILE="${ENV_SOURCE_FILE:-.env.local.example}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-smart-barber-matrix-postgres}"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT_DIR}/docker-compose.yml}"
REBUILD_WEB="${REBUILD_WEB:-true}"
KEEP_STACK="${KEEP_STACK:-false}"
HOST_REPORT_DIR="${HOST_REPORT_DIR:-${ROOT_DIR}/docs/postgres-matrix}"

if [[ ! -f "${ENV_SOURCE_FILE}" ]]; then
  echo "Environment file '${ENV_SOURCE_FILE}' was not found." >&2
  exit 1
fi

mkdir -p "${HOST_REPORT_DIR}"

set -a
. "${ENV_SOURCE_FILE}"
set +a

COMPOSE="$(compose_cmd)"

compose() {
  if [[ "${COMPOSE}" == "docker compose" ]]; then
    ENV_FILE_PATH="${ENV_SOURCE_FILE}" docker compose --env-file "${ENV_SOURCE_FILE}" -p "${COMPOSE_PROJECT_NAME}" -f "${COMPOSE_FILE}" "$@"
  else
    ENV_FILE_PATH="${ENV_SOURCE_FILE}" docker-compose --env-file "${ENV_SOURCE_FILE}" -p "${COMPOSE_PROJECT_NAME}" -f "${COMPOSE_FILE}" "$@"
  fi
}

cleanup() {
  if [[ "${KEEP_STACK}" != "true" ]]; then
    compose down -v --remove-orphans >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

if [[ "${REBUILD_WEB}" == "true" ]]; then
  compose build web
fi

compose up -d db

for attempt in $(seq 1 40); do
  if compose exec -T db pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

compose run --rm --no-deps \
  -v "${HOST_REPORT_DIR}:/report-output" \
  -e DJANGO_SETTINGS_MODULE=config.settings.test \
  -e RUN_COLLECTSTATIC=false \
  web \
  python scripts/generate_app_test_matrix_report.py \
    --verbosity 1 \
    --markdown-output /report-output/app-test-matrix-report.postgres.md \
    --pdf-output /report-output/app-test-matrix-report.postgres.pdf

if [[ "${KEEP_STACK}" == "true" ]]; then
  cat <<EOF

Postgres-backed matrix completed and the Compose project is still running.
Project: ${COMPOSE_PROJECT_NAME}
Environment file: ${ENV_SOURCE_FILE}
Report directory: ${HOST_REPORT_DIR}

Useful commands:
  ENV_FILE_PATH=${ENV_SOURCE_FILE} ${COMPOSE} -p ${COMPOSE_PROJECT_NAME} -f ${COMPOSE_FILE} ps
  ENV_FILE_PATH=${ENV_SOURCE_FILE} ${COMPOSE} -p ${COMPOSE_PROJECT_NAME} -f ${COMPOSE_FILE} logs db
  ENV_FILE_PATH=${ENV_SOURCE_FILE} ${COMPOSE} -p ${COMPOSE_PROJECT_NAME} -f ${COMPOSE_FILE} down -v
EOF
fi
