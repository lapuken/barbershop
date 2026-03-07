# Smart Barber Shops VPS Deployment Runbook

## Deployment Model

- Host OS: Ubuntu 22.04
- Reverse proxy: host `nginx`
- TLS: Let's Encrypt with `certbot`
- Application runtime: Docker Compose
- Services: `web` and `db`
- Public app URL: `https://app.machinjiri.net`
- Apex redirect: `https://machinjiri.net` -> `https://app.machinjiri.net`

The `web` container exposes only `127.0.0.1:8000` on the VPS. PostgreSQL stays on the Docker network only.

## Server Prerequisites

```bash
ssh barberadmin@66.42.115.59
sudo apt update
sudo apt install -y git certbot python3-certbot-nginx
docker version
docker compose version
sudo systemctl status nginx --no-pager
sudo ufw status verbose
df -h
free -h
```

## Production Layout

```bash
sudo install -d -o barberadmin -g barberadmin -m 0755 /opt/smartbarber
sudo install -d -o barberadmin -g barberadmin -m 0755 /opt/smartbarber/app
sudo install -d -o barberadmin -g barberadmin -m 0755 /opt/smartbarber/env
sudo install -d -o barberadmin -g barberadmin -m 0755 /opt/smartbarber/backups
sudo install -d -o barberadmin -g barberadmin -m 0755 /opt/smartbarber/logs
sudo install -d -o www-data -g adm -m 0775 /opt/smartbarber/logs/nginx
sudo install -d -o barberadmin -g barberadmin -m 0755 /var/www/certbot
```

## Clone the Repository

```bash
git clone https://github.com/lapuken/barbershop.git /opt/smartbarber/app
sudo chown -R barberadmin:barberadmin /opt/smartbarber/app
cd /opt/smartbarber/app
git branch --show-current
```

## Configure Environment

```bash
cp /opt/smartbarber/app/.env.example /opt/smartbarber/env/.env
chmod 600 /opt/smartbarber/env/.env
id -u barberadmin
id -g barberadmin
openssl rand -base64 48
nano /opt/smartbarber/env/.env
```

Required values to replace:

- `LETSENCRYPT_EMAIL`
- `DJANGO_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `APP_UID`
- `APP_GID`
- optional `DJANGO_SUPERUSER_USERNAME`
- optional `DJANGO_SUPERUSER_EMAIL`
- optional `DJANGO_SUPERUSER_PASSWORD`

Important deployment defaults already included in `.env.example`:

- `DJANGO_SETTINGS_MODULE=config.settings.prod`
- `DJANGO_DEBUG=False`
- `SECURE_SSL_REDIRECT=True`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- `BACKUP_BEFORE_DEPLOY=true`
- `BACKUP_RETENTION_DAYS=14`
- `RUN_DIAGNOSTICS_ON_FAILURE=true`

## First Deploy

Run the deployment script. It validates the env file, optionally creates a pre-deploy backup, builds the image, starts PostgreSQL, runs `check --deploy`, runs migrations, collects static files, starts the web container, verifies health, and exits nonzero on failure.

```bash
cd /opt/smartbarber/app
./deploy.sh
docker compose --env-file /opt/smartbarber/env/.env ps
```

## Nginx and TLS

Install the bootstrap site first:

```bash
sudo cp /opt/smartbarber/app/nginx/app.machinjiri.net.bootstrap.conf /etc/nginx/sites-available/smartbarber
sudo ln -sfn /etc/nginx/sites-available/smartbarber /etc/nginx/sites-enabled/smartbarber
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

Issue certificates:

```bash
sudo certbot certonly --webroot --cert-name app.machinjiri.net -w /var/www/certbot -d app.machinjiri.net -d machinjiri.net -m YOUR_EMAIL@example.com --agree-tos --no-eff-email
```

Install the final HTTPS site:

```bash
sudo cp /opt/smartbarber/app/nginx/app.machinjiri.net.conf /etc/nginx/sites-available/smartbarber
sudo nginx -t
sudo systemctl reload nginx
```

Verify renewal:

```bash
sudo certbot renew --dry-run
```

## Initial Admin User

```bash
cd /opt/smartbarber/app
./scripts/create-initial-admin.sh
```

If `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PASSWORD` are set in `/opt/smartbarber/env/.env`, the script runs non-interactively. Otherwise it falls back to interactive `createsuperuser`.

## Validation

```bash
cd /opt/smartbarber/app
./scripts/healthcheck.sh local
./scripts/healthcheck.sh public
docker compose --env-file /opt/smartbarber/env/.env ps
docker compose --env-file /opt/smartbarber/env/.env logs --tail=100 web db
sudo nginx -t
```

## Repeat Deploy

```bash
cd /opt/smartbarber/app
./deploy.sh --git-pull
./scripts/healthcheck.sh full
```

Skip the automatic pre-deploy backup only if you have a confirmed recent backup:

```bash
cd /opt/smartbarber/app
./deploy.sh --git-pull --skip-backup
```

## Rollback

Roll back to the previous successful release:

```bash
cd /opt/smartbarber/app
./rollback.sh
```

Roll back to a specific git ref:

```bash
cd /opt/smartbarber/app
./rollback.sh <git-ref>
```

## Backups and Restore

Create a timestamped backup set:

```bash
cd /opt/smartbarber/app
./backup.sh
ls -lah /opt/smartbarber/backups
```

Restore a full backup set:

```bash
cd /opt/smartbarber/app
./restore.sh /opt/smartbarber/backups/<timestamp>
```

Restore only the database:

```bash
cd /opt/smartbarber/app
./scripts/restore-db.sh /opt/smartbarber/backups/<timestamp>/database.dump
```

## Scheduled Maintenance

Install the daily backup timer:

```bash
sudo cp /opt/smartbarber/app/ops/systemd/smartbarber-backup.service /etc/systemd/system/
sudo cp /opt/smartbarber/app/ops/systemd/smartbarber-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now smartbarber-backup.timer
```

Install the weekly Docker prune timer:

```bash
sudo cp /opt/smartbarber/app/ops/systemd/smartbarber-prune.service /etc/systemd/system/
sudo cp /opt/smartbarber/app/ops/systemd/smartbarber-prune.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now smartbarber-prune.timer
```

Install log rotation for custom Nginx logs:

```bash
sudo cp /opt/smartbarber/app/ops/logrotate/smartbarber-nginx /etc/logrotate.d/smartbarber-nginx
sudo logrotate -d /etc/logrotate.d/smartbarber-nginx
```

## Diagnostics and Troubleshooting

Collect a full on-host snapshot:

```bash
cd /opt/smartbarber/app
./scripts/diagnostics.sh --tail 150
```

Common checks:

```bash
cd /opt/smartbarber/app
docker compose --env-file /opt/smartbarber/env/.env logs --tail=200 web db
sudo tail -n 200 /opt/smartbarber/logs/nginx/app.machinjiri.net.error.log
sudo ss -tulpn | grep -E ':80|:443|:8000|:5432'
df -h
docker system df
```

For the ongoing operator workflow, use:

- [`OPERATIONS.md`](OPERATIONS.md)
- [`HARDENING.md`](HARDENING.md)
