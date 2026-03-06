# Smart Barber Shops VPS Deployment Runbook

## Phase 1 — Verify Server Prerequisites

```bash
ssh barberadmin@66.42.115.59
docker version
docker compose version
sudo systemctl status nginx --no-pager
sudo ufw status verbose
df -h
free -h
```

## Phase 2 — Create Production Directory Structure

```bash
sudo install -d -o barberadmin -g barberadmin -m 0755 /opt/smartbarber
sudo install -d -o barberadmin -g barberadmin -m 0755 /opt/smartbarber/app
sudo install -d -o barberadmin -g barberadmin -m 0755 /opt/smartbarber/env
sudo install -d -o barberadmin -g barberadmin -m 0755 /opt/smartbarber/backups
sudo install -d -o barberadmin -g barberadmin -m 0755 /opt/smartbarber/logs
sudo install -d -o www-data -g adm -m 0775 /opt/smartbarber/logs/nginx
sudo install -d -o barberadmin -g barberadmin -m 0755 /var/www/certbot
```

## Phase 3 — Clone the Repository

```bash
git clone https://github.com/lapuken/barbershop.git /opt/smartbarber/app
sudo chown -R barberadmin:barberadmin /opt/smartbarber/app
cd /opt/smartbarber/app
git branch --show-current
```

## Phase 4 — Configure Environment Variables

```bash
cat > /opt/smartbarber/env/.env <<'EOF'
APP_ENV=production
APP_DOMAIN=app.machinjiri.net
SECRET_KEY=REPLACE_WITH_LONG_RANDOM_SECRET
DATABASE_URL=
REDIS_URL=
ALLOWED_HOSTS=app.machinjiri.net,machinjiri.net,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://app.machinjiri.net,https://machinjiri.net
ROOT_DOMAIN=machinjiri.net
LETSENCRYPT_EMAIL=YOUR_EMAIL@example.com
APP_PORT=8000
APP_UID=1000
APP_GID=1000
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=REPLACE_WITH_LONG_RANDOM_SECRET
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=app.machinjiri.net,machinjiri.net,127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=https://app.machinjiri.net,https://machinjiri.net
DJANGO_LOG_LEVEL=INFO
APP_TIME_ZONE=Africa/Blantyre
POSTGRES_DB=smartbarber
POSTGRES_USER=smartbarber
POSTGRES_PASSWORD=REPLACE_WITH_STRONG_DB_PASSWORD
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_SSLMODE=disable
POSTGRES_CONN_MAX_AGE=60
SESSION_COOKIE_AGE=3600
LOGIN_RATE_LIMIT=5
LOGIN_RATE_WINDOW_SECONDS=900
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
MFA_READY=False
APP_RELEASE_SHA=manual
RUN_COLLECTSTATIC=False
GUNICORN_WORKERS=2
GUNICORN_TIMEOUT=60
PORT=8000
TZ=Africa/Blantyre
DJANGO_SUPERUSER_USERNAME=
DJANGO_SUPERUSER_EMAIL=
DJANGO_SUPERUSER_PASSWORD=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_API_BASE_URL=https://graph.facebook.com
WHATSAPP_API_VERSION=v21.0
TELEGRAM_BOT_TOKEN=
TELEGRAM_API_BASE_URL=https://api.telegram.org
APPOINTMENT_NOTIFICATION_TIMEOUT_SECONDS=10
EOF
chmod 600 /opt/smartbarber/env/.env
nano /opt/smartbarber/env/.env
id -u barberadmin
id -g barberadmin
openssl rand -base64 48
```

## Phase 5 — Build and Start Containers

```bash
cd /opt/smartbarber/app
docker compose --env-file /opt/smartbarber/env/.env build
./deploy.sh
docker compose --env-file /opt/smartbarber/env/.env ps
docker compose --env-file /opt/smartbarber/env/.env logs --tail=200 web db
```

## Phase 6 — Configure Nginx Reverse Proxy

Bootstrap config:

```bash
sudo cp /opt/smartbarber/app/nginx/app.machinjiri.net.bootstrap.conf /etc/nginx/sites-available/smartbarber
sudo ln -sfn /etc/nginx/sites-available/smartbarber /etc/nginx/sites-enabled/smartbarber
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

Final HTTPS config after certificates:

```bash
sudo cp /opt/smartbarber/app/nginx/app.machinjiri.net.conf /etc/nginx/sites-available/smartbarber
sudo nginx -t
sudo systemctl reload nginx
```

## Phase 7 — Install SSL Certificates

```bash
sudo certbot --nginx -d machinjiri.net -d app.machinjiri.net
```

Choose this when prompted:

```text
2: Redirect - Make all requests redirect to secure HTTPS access
```

If you want the repo-managed Nginx config to remain the source of truth, use this instead:

```bash
sudo certbot certonly --webroot --cert-name app.machinjiri.net -w /var/www/certbot -d app.machinjiri.net -d machinjiri.net -m YOUR_EMAIL@example.com --agree-tos --no-eff-email
sudo cp /opt/smartbarber/app/nginx/app.machinjiri.net.conf /etc/nginx/sites-available/smartbarber
sudo nginx -t
sudo systemctl reload nginx
```

## Phase 8 — Database Migrations and Startup

```bash
cd /opt/smartbarber/app
docker compose --env-file /opt/smartbarber/env/.env run --rm --no-deps -e RUN_COLLECTSTATIC=false web python manage.py migrate --noinput
docker compose --env-file /opt/smartbarber/env/.env run --rm --no-deps -e RUN_COLLECTSTATIC=false web python manage.py collectstatic --noinput
docker compose --env-file /opt/smartbarber/env/.env up -d web
./scripts/create-initial-admin.sh
curl http://127.0.0.1:8000/healthz/
curl -I https://app.machinjiri.net/healthz/
```

## Phase 9 — Operations and Monitoring

Restart services:

```bash
cd /opt/smartbarber/app
docker compose --env-file /opt/smartbarber/env/.env restart web db
sudo systemctl reload nginx
```

View logs:

```bash
cd /opt/smartbarber/app
docker compose --env-file /opt/smartbarber/env/.env logs -f web db
sudo tail -f /opt/smartbarber/logs/nginx/app.machinjiri.net.access.log /opt/smartbarber/logs/nginx/app.machinjiri.net.error.log
```

Check health:

```bash
cd /opt/smartbarber/app
docker compose --env-file /opt/smartbarber/env/.env ps
curl http://127.0.0.1:8000/healthz/
curl -I https://app.machinjiri.net/healthz/
sudo nginx -t
sudo systemctl status nginx --no-pager
sudo certbot renew --dry-run
```

## Phase 10 — Backup Strategy

Create backups:

```bash
cd /opt/smartbarber/app
./backup.sh
./scripts/backup-db.sh
ls -lah /opt/smartbarber/backups
```

Restore database:

```bash
cd /opt/smartbarber/app
./scripts/restore-db.sh /opt/smartbarber/backups/<timestamp>/database.dump
```

Restore media files:

```bash
sudo rm -rf /opt/smartbarber/app/shared/media
sudo mkdir -p /opt/smartbarber/app/shared
sudo tar -xzf /opt/smartbarber/backups/<timestamp>/media.tar.gz -C /opt/smartbarber/app/shared
sudo chown -R barberadmin:barberadmin /opt/smartbarber/app/shared/media
sudo systemctl reload nginx
```

## Repeat Deploy

```bash
cd /opt/smartbarber/app
git pull --ff-only
./deploy.sh
docker compose --env-file /opt/smartbarber/env/.env ps
curl -I https://app.machinjiri.net/healthz/
```
