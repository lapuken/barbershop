# Operations Runbook (Ubuntu VPS)

## Paths

- App checkout: `/opt/smartbarber/app`
- Env file: `/opt/smartbarber/env/.env`
- Backups: `/opt/smartbarber/backups`
- Nginx logs: `/opt/smartbarber/logs/nginx`

## Deploy

```bash
cd /opt/smartbarber/app
git pull --ff-only
./deploy.sh
docker compose --env-file /opt/smartbarber/env/.env ps
curl -I https://app.machinjiri.net/healthz/
```

## Restart

```bash
cd /opt/smartbarber/app
docker compose --env-file /opt/smartbarber/env/.env restart web db
sudo systemctl reload nginx
```

## Logs

```bash
cd /opt/smartbarber/app
docker compose --env-file /opt/smartbarber/env/.env logs -f web db
sudo tail -f /opt/smartbarber/logs/nginx/app.machinjiri.net.access.log /opt/smartbarber/logs/nginx/app.machinjiri.net.error.log
```

## Backups

```bash
cd /opt/smartbarber/app
./backup.sh
./scripts/backup-db.sh
ls -lah /opt/smartbarber/backups
```

## Restore

```bash
cd /opt/smartbarber/app
./scripts/restore-db.sh /opt/smartbarber/backups/<timestamp>/database.dump
```

```bash
sudo rm -rf /opt/smartbarber/app/shared/media
sudo mkdir -p /opt/smartbarber/app/shared
sudo tar -xzf /opt/smartbarber/backups/<timestamp>/media.tar.gz -C /opt/smartbarber/app/shared
sudo chown -R barberadmin:barberadmin /opt/smartbarber/app/shared/media
sudo systemctl reload nginx
```

## Health

```bash
cd /opt/smartbarber/app
docker compose --env-file /opt/smartbarber/env/.env ps
curl http://127.0.0.1:8000/healthz/
curl -I https://app.machinjiri.net/healthz/
sudo nginx -t
sudo systemctl status nginx --no-pager
sudo certbot renew --dry-run
```
