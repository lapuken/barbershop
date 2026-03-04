#!/bin/sh
set -e

if [ "${RUN_COLLECTSTATIC:-true}" = "true" ]; then
  python manage.py collectstatic --noinput
fi

exec "$@"
