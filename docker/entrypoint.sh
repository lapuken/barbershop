#!/bin/sh
set -e

should_collectstatic() {
  case "${RUN_COLLECTSTATIC:-true}" in
    1|[Tt][Rr][Uu][Ee]|[Yy][Ee][Ss]|[Oo][Nn])
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

if should_collectstatic; then
  python manage.py collectstatic --noinput
fi

exec "$@"
