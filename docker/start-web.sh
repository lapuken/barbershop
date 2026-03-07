#!/bin/sh
set -e

PORT="${PORT:-8000}"
WORKERS="${GUNICORN_WORKERS:-2}"
TIMEOUT="${GUNICORN_TIMEOUT:-60}"

set -- \
  gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WORKERS}" \
  --timeout "${TIMEOUT}" \
  --access-logfile - \
  --error-logfile -

if [ -n "${GUNICORN_EXTRA_ARGS:-}" ]; then
  # shellcheck disable=SC2086
  set -- "$@" ${GUNICORN_EXTRA_ARGS}
fi

exec "$@"
