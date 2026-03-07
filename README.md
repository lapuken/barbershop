# Smart Barber Shops

Smart Barber Shops is a Django-based multi-branch barber shop operations platform.

## Production Deployment

This repository includes a production deployment path for a single Ubuntu 22.04 VPS using:

- host `nginx` for reverse proxy and TLS termination
- `certbot` + Let's Encrypt for certificates
- Docker Compose for the Django web app and PostgreSQL
- a host-mounted `shared/static` directory for direct static serving
- a host-mounted `shared/media` directory for persistent uploads and backups

Target hostname for this path:

- `app.machinjiri.net`

Optional redirect target:

- `machinjiri.net` -> `https://app.machinjiri.net`

Key deployment assets:

- [DEPLOYMENT.md](DEPLOYMENT.md)
- [OPERATIONS.md](OPERATIONS.md)
- [HARDENING.md](HARDENING.md)
- [docker-compose.yml](docker-compose.yml)
- [deploy.sh](deploy.sh)
- [backup.sh](backup.sh)
- [rollback.sh](rollback.sh)
- [restore.sh](restore.sh)
- [nginx/app.machinjiri.net.bootstrap.conf](nginx/app.machinjiri.net.bootstrap.conf)
- [nginx/app.machinjiri.net.conf](nginx/app.machinjiri.net.conf)
- [docs/architecture.md](docs/architecture.md)
- [docs/deployment-checklist.md](docs/deployment-checklist.md)
- [docs/operations-runbook.md](docs/operations-runbook.md)
- [docs/security-hardening.md](docs/security-hardening.md)

System assumptions for the single-VPS path:

- one VPS hosts Nginx, the Django app container, and the PostgreSQL container
- only `80/tcp` and `443/tcp` are exposed publicly
- the app container binds only to `127.0.0.1:8000`
- `.env` exists only on the server and is never committed
- PostgreSQL persists in a named Docker volume
- uploaded files live under `shared/media/` and should be included in backups

## Architecture Overview

- Application runtime: Django + Django REST Framework in a Docker container
- Web ingress: host `nginx` terminating TLS and proxying to `127.0.0.1:8000`
- Database: PostgreSQL in Docker Compose on the internal Docker network
- Static files: collected into `shared/static`
- Media files: persisted in `shared/media`
- Deployment: reviewed shell scripts with explicit backup, migration, and health-check steps
- CI: GitHub Actions runs linting, tests, migrations, and container build validation

Current delivery snapshots:

- [Stakeholder status summary](docs/stakeholder-status-summary.md)
- [Technical status breakdown](docs/technical-status-breakdown.md)
- [Implementation roadmap](docs/implementation-roadmap.md)
- [User roles guide](USER_ROLES.md)

## Prerequisites

Local development:

- Python 3.12
- Docker

Server deployment:

- Ubuntu 22.04
- Docker Engine with Docker Compose
- Nginx
- Certbot
- SSH access to the target server

## Fastest Local App Test

If you want to stand the app up locally and log in quickly, use the bootstrap script:

```bash
./scripts/bootstrap-local.sh
source .venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

That script will:

- copy `.env.local.example` to `.env` if needed
- create `.venv`
- install Python dependencies
- start the PostgreSQL Docker service
- run migrations
- seed demo data

### Demo Credentials

- Platform admin username: `platformadmin`
- Platform admin password: `ChangeMe12345!`
- Shop owner username: `owner1`
- Shop owner password: `ChangeMe12345!`
- Shop manager username: `manager1`
- Shop manager password: `ChangeMe12345!`
- Cashier username: `cashier1`
- Cashier password: `ChangeMe12345!`
- Second shop owner username: `owner2`
- Second shop owner password: `ChangeMe12345!`

### Local URLs

Once `python manage.py runserver 0.0.0.0:8000` is running:

- App root: `http://127.0.0.1:8000/`
- Login: `http://127.0.0.1:8000/accounts/login/`

### What the Demo Seed Includes

- 2 barber shop branches
- 5 demo user accounts
- multiple active barbers
- multiple products across shops
- recent sales over multiple days
- recent expenses
- repeat customers and upcoming appointments
- WhatsApp and Telegram-ready booking and availability sharing
- automatic booking confirmations through WhatsApp or Telegram when delivery credentials are configured

That means the dashboard, reports, audit feed, shop selector, appointment schedule, and messaging/share flows have usable data immediately after bootstrap.

## Docker-Only Pilot Run

If you want to run the app without a local Python setup, use the Docker bootstrap:

```bash
./scripts/bootstrap-docker.sh
```

That path will:

- copy `.env.local.example` to `.env` if needed
- build the app image
- start PostgreSQL and the Django web container
- wait for the app health endpoint
- seed the richer demo dataset inside the web container

Docker pilot URLs:

- App root: `http://127.0.0.1:8000/`
- Login: `http://127.0.0.1:8000/accounts/login/`
- Health: `http://127.0.0.1:8000/healthz/`

After bootstrap, run the pilot verifier before sharing the URL:

```bash
./scripts/verify-docker-pilot.sh
```

Useful Docker commands:

```bash
./scripts/verify-docker-pilot.sh
docker compose logs -f web
docker compose exec web python manage.py test
docker compose exec web python manage.py seed_demo
docker compose down
```

## Repository Layout

- [apps](apps): Django applications
- [config](config): Django settings and project configuration
- [docs](docs): deployment, architecture, pilot, and runbook docs
- [.github/workflows](.github/workflows): CI workflow definitions
- [nginx](nginx): reviewed Nginx site configuration
- [ops](ops): systemd and logrotate assets
- [scripts](scripts): local, deployment, backup, and diagnostic automation

## Release Workflow

For a first server deployment, follow [DEPLOYMENT.md](DEPLOYMENT.md) end to end.

For normal production updates on the VPS:

```bash
cd /opt/smartbarber/app
./deploy.sh --git-pull
./scripts/healthcheck.sh full
```

The deployment script validates the environment, optionally creates a pre-deploy backup, builds the web image, starts PostgreSQL, runs `check --deploy`, runs migrations, collects static files, starts the web container, verifies health, and records the release marker.

## Local Verification Commands

Application checks:

```bash
source .venv/bin/activate
python manage.py test
ruff check .
black --check .
```

Container path:

```bash
docker compose up --build
```

Browser smoke path:

```bash
source .venv/bin/activate
pip install -r requirements-smoke.txt
python -m playwright install chromium
APP_BASE_URL=http://127.0.0.1:8000 ./scripts/run-browser-smoke.sh
```

Optional write-mode smoke test:

```bash
SMOKE_WRITE_TESTS=true APP_BASE_URL=http://127.0.0.1:8000 ./scripts/run-browser-smoke.sh
```

## Runtime Configuration

Production defaults live in [`.env.example`](.env.example). Local development defaults live in [`.env.local.example`](.env.local.example).

Production configuration is loaded from an external env file, typically `/opt/smartbarber/env/.env`, and includes:

- Django runtime settings such as `DJANGO_SETTINGS_MODULE`, `DJANGO_ALLOWED_HOSTS`, and `DJANGO_CSRF_TRUSTED_ORIGINS`
- PostgreSQL connection settings such as `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_HOST`
- deployment controls such as `BACKUP_BEFORE_DEPLOY`, `BACKUP_RETENTION_DAYS`, and `RUN_DIAGNOSTICS_ON_FAILURE`
- notification credentials such as `WHATSAPP_ACCESS_TOKEN` and `TELEGRAM_BOT_TOKEN`

## Migration and Static Files Strategy

- Migrations are not run on normal web container startup.
- Production deployments run migrations explicitly from `scripts/deploy.sh` before the web container is restarted.
- Production deployments run `collectstatic` explicitly from `scripts/deploy.sh`.
- If the migration step fails, the deploy script exits nonzero before the web service is updated.

## Rollback Notes

- Use [rollback.sh](rollback.sh) to return to the previous successful release marker or a specific git ref.
- If a release fails after a backward-incompatible migration, a database restore may be required in addition to a code rollback.
- Keep recent backup sets and test restores regularly.

## Troubleshooting

- App health failures: run `./scripts/healthcheck.sh full` and inspect `docker compose logs --tail=200 web db`
- Deploy failures: rerun with diagnostics enabled and inspect `./scripts/diagnostics.sh --tail 150`
- Nginx problems: run `sudo nginx -t` and inspect `/opt/smartbarber/logs/nginx/*.log`
- Backup and restore issues: use [OPERATIONS.md](OPERATIONS.md) and [HARDENING.md](HARDENING.md)

## Additional Documentation

- [docs/architecture.md](docs/architecture.md)
- [docs/deployment-checklist.md](docs/deployment-checklist.md)
- [docs/domain-dns-setup.md](docs/domain-dns-setup.md)
- [docs/operations-runbook.md](docs/operations-runbook.md)
- [docs/barber-pilot-test-plan.md](docs/barber-pilot-test-plan.md)
- [SECURITY.md](SECURITY.md)
