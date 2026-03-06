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

host_ips() {
  if command -v hostname >/dev/null 2>&1; then
    hostname -I 2>/dev/null | xargs || true
  fi
}

COMPOSE="$(compose_cmd)"

if [[ ! -f ".env" ]]; then
  if [[ -f ".env.local.example" ]]; then
    cp .env.local.example .env
  else
    cp .env.example .env
  fi
fi

set -a
. ./.env
set +a

${COMPOSE} up --build -d db web caddy

for attempt in $(seq 1 40); do
  if ${COMPOSE} exec -T db pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

for attempt in $(seq 1 40); do
  if curl --fail --silent --show-error "http://127.0.0.1/healthz/" >/dev/null 2>&1; then
    break
  fi
  sleep 3
done

${COMPOSE} exec -T web python manage.py migrate --noinput
${COMPOSE} exec -T web python manage.py seed_demo

HOST_IPS="$(host_ips)"

cat <<EOF

Docker bootstrap complete.

Application URLs:
  App root: http://127.0.0.1/
  Login:    http://127.0.0.1/accounts/login/
  Health:   http://127.0.0.1/healthz/

$(if [[ -n "${HOST_IPS}" ]]; then
  printf "Host IP candidates for LAN testing:\n"
  for ip in ${HOST_IPS}; do
    printf "  http://%s/\n" "${ip}"
  done
fi)

Demo credentials:
  platformadmin / ChangeMe12345!
  owner1 / ChangeMe12345!
  manager1 / ChangeMe12345!
  cashier1 / ChangeMe12345!
  owner2 / ChangeMe12345!

Useful commands:
  ./scripts/verify-docker-pilot.sh
  ${COMPOSE} logs -f web
  ${COMPOSE} exec web python manage.py test
  ${COMPOSE} down
EOF
