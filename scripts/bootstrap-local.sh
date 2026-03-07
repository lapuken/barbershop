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

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

COMPOSE="$(compose_cmd)"
${COMPOSE} up -d db

for attempt in $(seq 1 30); do
  if ${COMPOSE} exec -T db pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.dev}"
python manage.py migrate --noinput
python manage.py seed_demo

cat <<EOF

Local bootstrap complete.

Next commands:
  source .venv/bin/activate
  python manage.py runserver 0.0.0.0:8000

Application URLs after startup:
  App root: http://127.0.0.1:8000/
  Login:    http://127.0.0.1:8000/accounts/login/

Demo credentials:
  username: platformadmin
  password: ChangeMe12345!

Optional browser smoke test:
  pip install -r requirements-smoke.txt
  python -m playwright install chromium
  APP_BASE_URL=http://127.0.0.1:8000 ./scripts/run-browser-smoke.sh
EOF
