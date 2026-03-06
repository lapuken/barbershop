# Operations Runbook (DigitalOcean Droplet)

This runbook covers day-2 operations for the single-droplet Docker Compose deployment.

## Assumptions

- Stack is running from `/opt/smart-barber` (or equivalent clone path).
- Services are managed by Docker Compose (`caddy`, `web`, `db`).
- Production settings are in `.env`.
- Public hostname is `app.machinjiri.net`.

## First Deployment

```bash
cd /opt/smart-barber
cp .env.example .env
# edit .env with real secrets before deploying
./scripts/deploy.sh
```

Create admin user:

```bash
./scripts/create-initial-admin.sh
```

## Routine Update

If code was already updated (for example via `git pull`):

```bash
./scripts/update-app.sh
```

If you want the script to pull latest commit first:

```bash
./scripts/update-app.sh --git-pull
```

Deployment behavior:

- rebuilds the `web` image
- ensures DB is up
- runs migrations
- runs collectstatic
- restarts `web` and `caddy`
- preserves PostgreSQL volume data
- typically causes a short restart window (low downtime, not zero-downtime)

## Restart Containers

Restart all services:

```bash
docker compose restart
```

Restart only app tier:

```bash
docker compose restart web caddy
```

## View Logs

Tail reverse proxy + app logs:

```bash
docker compose logs -f caddy web
```

Tail database logs:

```bash
docker compose logs -f db
```

## Run Backup

```bash
./scripts/backup-db.sh
```

Backups are written to `./backups/` with timestamps.

Recommended frequency:

- minimum daily backup
- keep at least 7 daily backups + 4 weekly backups
- copy backups off-server (object storage or another host)

## Restore Backup

```bash
./scripts/restore-db.sh backups/smartbarber-YYYYMMDD-HHMMSS.dump
```

Safety behavior:

- prompts for explicit `RESTORE` confirmation
- stops `web` and `caddy` before restore
- restores database
- starts `web` and `caddy` again

Always test restore on a non-production clone before production restores.

## Rotate Django Secret Key or DB Password

1. Edit `.env` and set the new value(s):
   - `DJANGO_SECRET_KEY`
   - `POSTGRES_PASSWORD` (and `DATABASE_URL` if used)
2. If rotating DB password, apply it in PostgreSQL first:

```bash
docker compose exec -T db psql -U "$POSTGRES_USER" -d postgres -c "ALTER USER \"$POSTGRES_USER\" WITH PASSWORD 'new-password';"
```

3. Re-deploy:

```bash
./scripts/deploy.sh
```

## Create Admin User

Interactive:

```bash
./scripts/create-initial-admin.sh
```

Non-interactive:

```bash
export DJANGO_SUPERUSER_USERNAME=admin
export DJANGO_SUPERUSER_EMAIL=admin@example.com
export DJANGO_SUPERUSER_PASSWORD='strong-password'
./scripts/create-initial-admin.sh
```

## Run Migrations Manually

```bash
docker compose run --rm -e RUN_COLLECTSTATIC=false web python manage.py migrate --noinput
```

## Troubleshoot 502 or Startup Failures

1. Check container states:

```bash
docker compose ps
```

2. Inspect logs:

```bash
docker compose logs --tail=200 caddy web db
```

3. Validate DB readiness:

```bash
docker compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

4. Validate Django health endpoint through proxy:

```bash
curl -I https://app.machinjiri.net/healthz/
```

5. Common causes:
   - wrong `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS`
   - invalid DB credentials
   - migrations pending
   - DNS not pointed to droplet (Caddy cannot issue TLS cert)

## TLS Renew / Verification

Caddy manages certificate issuance and renewal automatically.

Check Caddy logs for ACME status:

```bash
docker compose logs --tail=200 caddy
```

Verify served certificate:

```bash
echo | openssl s_client -servername app.machinjiri.net -connect app.machinjiri.net:443 2>/dev/null | openssl x509 -noout -issuer -dates -subject
```

## Recover After Server Reboot

Docker services are configured with `restart: unless-stopped`.
After reboot:

```bash
docker compose ps
docker compose logs --tail=100 caddy web db
```

If services were stopped intentionally before reboot:

```bash
docker compose up -d
```
