# Security Hardening Baseline (Single VPS)

## Network

```bash
sudo ufw status verbose
sudo ss -tulpn | grep -E ':22|:80|:443|:8000'
```

Expected exposure:

- `22/tcp` for SSH
- `80/tcp` and `443/tcp` for Nginx
- `127.0.0.1:8000` for the Django container only
- no PostgreSQL host port

## Secrets

```bash
sudo chown barberadmin:barberadmin /opt/smartbarber/env/.env
chmod 600 /opt/smartbarber/env/.env
```

## Shared Files

```bash
sudo chown -R barberadmin:barberadmin /opt/smartbarber/app/shared /opt/smartbarber/backups
sudo chmod -R u+rwX,go+rX /opt/smartbarber/app/shared
```

## Nginx Logs

```bash
sudo chown -R www-data:adm /opt/smartbarber/logs/nginx
sudo chmod 775 /opt/smartbarber/logs /opt/smartbarber/logs/nginx
```

## TLS

```bash
sudo certbot renew --dry-run
```

## Backups

```bash
cd /opt/smartbarber/app
./backup.sh
ls -lah /opt/smartbarber/backups
```
