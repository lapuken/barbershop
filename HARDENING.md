# Smart Barber Shops Hardening Guide

## Host Baseline

Operate through the non-root sudo user:

```bash
whoami
id
sudo -l
```

Disable direct root SSH after `barberadmin` access is confirmed:

```bash
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.$(date +%Y%m%d-%H%M%S)
sudo sed -i 's/^#\\?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/^#\\?PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sshd -t
sudo systemctl reload ssh
```

Expected firewall exposure:

```bash
sudo ufw status verbose
sudo ss -tulpn | grep -E ':22|:80|:443|:8000|:5432'
```

Expected result:

- `22/tcp`, `80/tcp`, `443/tcp` exposed
- Django bound only to `127.0.0.1:8000`
- PostgreSQL not exposed on a host port

## Application Security

Check production security settings:

```bash
cd /opt/smartbarber/app
docker compose --env-file /opt/smartbarber/env/.env run --rm --no-deps -e RUN_COLLECTSTATIC=false web python manage.py check --deploy
```

Protect the environment file and backups:

```bash
sudo chown barberadmin:barberadmin /opt/smartbarber/env/.env
sudo chmod 600 /opt/smartbarber/env/.env
sudo chown -R barberadmin:barberadmin /opt/smartbarber/backups
sudo chmod -R go-rwx /opt/smartbarber/backups
```

Protect the shared app directories:

```bash
sudo chown -R barberadmin:barberadmin /opt/smartbarber/app/shared
sudo chmod -R u+rwX,go-rwx /opt/smartbarber/app/shared/media
sudo chmod -R u+rwX,go+rX /opt/smartbarber/app/shared/static
```

Protect Nginx logs:

```bash
sudo chown -R www-data:adm /opt/smartbarber/logs/nginx
sudo chmod 775 /opt/smartbarber/logs /opt/smartbarber/logs/nginx
```

## Secrets Handling

Generate new secrets:

```bash
openssl rand -base64 48
```

Do not commit secrets:

```bash
cd /opt/smartbarber/app
test ! -f /opt/smartbarber/app/.env && echo "Using external env file only"
git status --short
```

Rotate secrets by editing `/opt/smartbarber/env/.env`, then redeploy:

```bash
nano /opt/smartbarber/env/.env
cd /opt/smartbarber/app
./deploy.sh
```

For GitHub-driven production deploys, use GitHub environment-scoped storage instead of repository-wide secrets:

- environment: `production`
- variables: `PRODUCTION_DEPLOY_HOST`, `PRODUCTION_DEPLOY_PORT`, `PRODUCTION_DEPLOY_USER`
- secrets: `PRODUCTION_DEPLOY_SSH_KEY`, `PRODUCTION_DEPLOY_KNOWN_HOSTS`

Use a dedicated SSH key for GitHub Actions only. Do not reuse a personal operator key.

When rotating the GitHub deploy key:

1. Generate a new SSH key pair.
2. Replace the old public key in `~barberadmin/.ssh/authorized_keys`.
3. Replace `PRODUCTION_DEPLOY_SSH_KEY` in the GitHub `production` environment.
4. Re-check `PRODUCTION_DEPLOY_KNOWN_HOSTS` if the server host key changed.

## Backups and Hygiene

Create and verify backups regularly:

```bash
cd /opt/smartbarber/app
./backup.sh
ls -lah /opt/smartbarber/backups
```

Keep at least one recent off-server copy:

Run this from your workstation:

```bash
scp -r barberadmin@66.42.115.59:/opt/smartbarber/backups/<timestamp> .
```

Test restores on the VPS only during a maintenance window:

```bash
cd /opt/smartbarber/app
./restore.sh /opt/smartbarber/backups/<timestamp>
```

## Patching

Apply OS updates:

```bash
sudo apt update
sudo apt upgrade -y
sudo reboot
```

Refresh app containers after code or base image updates:

```bash
cd /opt/smartbarber/app
./deploy.sh --git-pull
```

For the GitHub Actions path, protect production deploys by:

- limiting automatic deploys to `main`
- requiring `CI` to pass before merge
- optionally requiring reviewers on the GitHub `production` environment
- keeping the server checkout on a clean `main` branch so automation cannot deploy from an unexpected ref

Check TLS renewal:

```bash
sudo certbot renew --dry-run
```
