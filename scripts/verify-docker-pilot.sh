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

COMPOSE="$(compose_cmd)"
export APP_UID="${APP_UID:-$(id -u)}"
export APP_GID="${APP_GID:-$(id -g)}"
export APP_PORT="${APP_PORT:-8000}"

echo "Checking service status..."
${COMPOSE} ps

echo
echo "Checking application endpoints..."
curl --fail --silent --show-error "http://127.0.0.1:${APP_PORT}/healthz/"
echo
curl --fail --silent --show-error --location "http://127.0.0.1:${APP_PORT}/accounts/login/" >/dev/null
echo "Login page OK"

echo
echo "Running Django regression suite inside the web container..."
${COMPOSE} exec -T web python manage.py test tests.test_smart_barber_shops

cat <<EOF

Pilot verification complete.

Tester URLs:
  App root: http://127.0.0.1:${APP_PORT}/
  Login:    http://127.0.0.1:${APP_PORT}/accounts/login/
  Health:   http://127.0.0.1:${APP_PORT}/healthz/
EOF
