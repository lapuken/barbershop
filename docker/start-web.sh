#!/bin/sh
set -e

PORT="${PORT:-8000}"
WORKERS="${GUNICORN_WORKERS:-3}"
TIMEOUT="${GUNICORN_TIMEOUT:-60}"
EXTRA_ARGS="${GUNICORN_EXTRA_ARGS:-}"

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WORKERS}" \
  --timeout "${TIMEOUT}" \
  ${EXTRA_ARGS}
