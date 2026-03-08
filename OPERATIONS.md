# Smart Barber Shops Operations Guide

## Paths

- App checkout: `/opt/smartbarber/app`
- Environment file: `/opt/smartbarber/env/.env`
- Backups: `/opt/smartbarber/backups`
- Nginx logs: `/opt/smartbarber/logs/nginx`
- Release markers: `/opt/smartbarber/logs/releases`

## Daily Commands

Deploy latest code:

```bash
cd /opt/smartbarber/app
./deploy.sh --git-pull
```

Check health:

```bash
cd /opt/smartbarber/app
./scripts/healthcheck.sh full
docker compose --env-file /opt/smartbarber/env/.env ps
```

Tail app and database logs:

```bash
cd /opt/smartbarber/app
docker compose --env-file /opt/smartbarber/env/.env logs -f web db
```

Tail Nginx logs:

```bash
sudo tail -f /opt/smartbarber/logs/nginx/app.machinjiri.net.access.log /opt/smartbarber/logs/nginx/app.machinjiri.net.error.log
```

Collect diagnostics:

```bash
cd /opt/smartbarber/app
./scripts/diagnostics.sh --tail 150
```

Initialize or update go-live baseline data:

```bash
cd /opt/smartbarber/app
./scripts/initialize-golive.sh /opt/smartbarber/env/golive-init.json
```

For the required JSON fields and table mapping, use [`docs/golive-initialization.md`](docs/golive-initialization.md).

## Restart and Recovery

Restart application services:

```bash
cd /opt/smartbarber/app
docker compose --env-file /opt/smartbarber/env/.env restart web db
sudo nginx -t
sudo systemctl reload nginx
```

Run a manual backup:

```bash
cd /opt/smartbarber/app
./backup.sh
```

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

Restore a full backup set:

```bash
cd /opt/smartbarber/app
./restore.sh /opt/smartbarber/backups/<timestamp>
```

## Health and Diagnostics

Local health:

```bash
cd /opt/smartbarber/app
./scripts/healthcheck.sh local
```

Public HTTPS health:

```bash
cd /opt/smartbarber/app
./scripts/healthcheck.sh public
```

Container health:

```bash
cd /opt/smartbarber/app
docker inspect --format '{{.Name}} {{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' $(docker compose --env-file /opt/smartbarber/env/.env ps -q)
```

Nginx and TLS checks:

```bash
sudo nginx -t
sudo systemctl status nginx --no-pager
sudo certbot renew --dry-run
```

## Scheduled Operations

Install the backup timer:

```bash
sudo cp /opt/smartbarber/app/ops/systemd/smartbarber-backup.service /etc/systemd/system/
sudo cp /opt/smartbarber/app/ops/systemd/smartbarber-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now smartbarber-backup.timer
sudo systemctl list-timers smartbarber-backup.timer
```

Install the Docker prune timer:

```bash
sudo cp /opt/smartbarber/app/ops/systemd/smartbarber-prune.service /etc/systemd/system/
sudo cp /opt/smartbarber/app/ops/systemd/smartbarber-prune.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now smartbarber-prune.timer
sudo systemctl list-timers smartbarber-prune.timer
```

Install log rotation for custom Nginx logs:

```bash
sudo cp /opt/smartbarber/app/ops/logrotate/smartbarber-nginx /etc/logrotate.d/smartbarber-nginx
sudo logrotate -d /etc/logrotate.d/smartbarber-nginx
```

Optional cron alternative:

```bash
crontab -e
```

```cron
15 2 * * * cd /opt/smartbarber/app && /usr/bin/env BACKUP_RETENTION_DAYS=14 ./backup.sh >> /opt/smartbarber/logs/backup-cron.log 2>&1
45 3 * * 0 cd /opt/smartbarber/app && ./scripts/prune-docker.sh >> /opt/smartbarber/logs/docker-prune.log 2>&1
```

## Troubleshooting

App container crash loop:

```bash
cd /opt/smartbarber/app
docker compose --env-file /opt/smartbarber/env/.env ps
docker compose --env-file /opt/smartbarber/env/.env logs --tail=200 web
./scripts/diagnostics.sh --tail 200
```

Nginx bad gateway:

```bash
cd /opt/smartbarber/app
./scripts/healthcheck.sh local
docker compose --env-file /opt/smartbarber/env/.env logs --tail=200 web
sudo tail -n 200 /opt/smartbarber/logs/nginx/app.machinjiri.net.error.log
sudo nginx -t
```

Database connection failure:

```bash
cd /opt/smartbarber/app
docker compose --env-file /opt/smartbarber/env/.env logs --tail=200 db web
docker compose --env-file /opt/smartbarber/env/.env exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Certbot renewal problems:

```bash
sudo certbot renew --dry-run
sudo journalctl -u certbot --no-pager -n 100
sudo nginx -t
```

Port conflicts:

```bash
sudo ss -tulpn | grep -E ':80|:443|:8000|:5432'
```

Disk full:

```bash
df -h
docker system df
cd /opt/smartbarber/app
./scripts/cleanup-backups.sh
./scripts/prune-docker.sh
```
