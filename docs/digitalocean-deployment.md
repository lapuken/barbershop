# DigitalOcean Deployment Guide (Single Droplet)

This guide deploys Smart Barber Shops on one Ubuntu droplet using Docker Compose.

## Deployment Model

- Droplet OS: Ubuntu LTS
- Containers:
  - `caddy` (TLS termination + reverse proxy)
  - `web` (Django + Gunicorn)
  - `db` (PostgreSQL)
- Public hostname: `app.machinjiri.net`
- Root domain: `machinjiri.net` (can remain unchanged for other uses)

Traffic flow:

Internet -> Caddy -> Django/Gunicorn -> PostgreSQL

## Recommended Droplet Size

Smallest practical baseline for a production-like MVP:

- **Basic Droplet**
- **2 GB RAM / 1 vCPU** (recommended starting point)
- 50 GB SSD
- Region close to your users

You can start smaller for tests, but 1 GB RAM is often tight for Django + PostgreSQL + Caddy on one host.

## 1. Create the Droplet

1. In DigitalOcean, create a new Droplet with Ubuntu LTS.
2. Add your SSH public key during creation.
3. Disable password auth at creation time if possible (SSH keys only).
4. Assign a static IP (Reserved IP) if you want stable failover behavior.

## 2. DNS Setup

Before deployment, point DNS for the app hostname to the droplet IP.

- Domain: `machinjiri.net`
- App record: `app.machinjiri.net` -> droplet public IPv4

See [domain-dns-setup.md](/home/khido/projects/barbershop/docs/domain-dns-setup.md).

## 3. DigitalOcean Firewall

Create a cloud firewall and attach it to the droplet:

- Inbound allow:
  - `22/tcp` from your admin IP (preferred) or trusted office/VPN ranges
  - `80/tcp` from anywhere
  - `443/tcp` from anywhere
- Inbound deny: everything else
- Outbound allow: all (or minimum required egress if your policy requires it)

## 4. Server Bootstrap

SSH into the droplet:

```bash
ssh root@<DROPLET_IP>
```

Clone repository and bootstrap:

```bash
git clone https://github.com/lapuken/barbershop.git /opt/smart-barber
cd /opt/smart-barber
./scripts/bootstrap-server.sh
```

If you want the script to also configure UFW:

```bash
CONFIGURE_UFW=true ADMIN_SSH_IP=<YOUR_PUBLIC_IP>/32 ./scripts/bootstrap-server.sh
```

## 5. Configure Environment File

Create the production env file:

```bash
cd /opt/smart-barber
cp .env.example .env
```

Edit `.env` and set strong secrets:

- `DJANGO_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `DATABASE_URL` (if used)
- `ACME_EMAIL`
- `DJANGO_ALLOWED_HOSTS=app.machinjiri.net`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://app.machinjiri.net`

Do not commit `.env`.

## 6. Deploy

```bash
cd /opt/smart-barber
./scripts/deploy.sh
```

Then create an admin account:

```bash
./scripts/create-initial-admin.sh
```

## 7. Verify Deployment

Container status:

```bash
docker compose ps
```

Health checks:

```bash
curl -I https://app.machinjiri.net/healthz/
curl -I https://app.machinjiri.net/accounts/login/
```

If TLS issuance fails initially, wait for DNS propagation and review Caddy logs:

```bash
docker compose logs -f caddy
```

## 8. Routine Operations

- App updates: `./scripts/update-app.sh --git-pull`
- DB backups: `./scripts/backup-db.sh`
- Restore: `./scripts/restore-db.sh <dump-file>`
- Runbook: [operations-runbook.md](/home/khido/projects/barbershop/docs/operations-runbook.md)
- Security baseline: [security-hardening.md](/home/khido/projects/barbershop/docs/security-hardening.md)
