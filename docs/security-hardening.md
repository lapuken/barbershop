# Security Hardening Baseline (Single Droplet)

This is a production-minded baseline for a small-business deployment on one server.
It improves security posture, but it is not equivalent to a multi-zone enterprise architecture.

## 1. Network Exposure

Current design:

- Public: `80/tcp`, `443/tcp` (Caddy only)
- Private containers: `web`, `db` on internal Docker network
- No direct public PostgreSQL port mapping
- No direct public Django/Gunicorn port mapping

## 2. SSH and Host Access

Recommended controls:

- SSH keys only (disable password authentication)
- disable root SSH login or use restricted root access
- allow `22/tcp` only from trusted admin IPs
- use separate non-root operator account for daily actions

Suggested SSH hardening (`/etc/ssh/sshd_config`):

- `PasswordAuthentication no`
- `PermitRootLogin prohibit-password` (or `no` if using sudo user)
- `PubkeyAuthentication yes`

Then reload:

```bash
sudo systemctl reload ssh
```

## 3. Firewall Baseline

At cloud firewall and/or UFW layer:

- allow `22/tcp` from admin IP ranges
- allow `80/tcp` from anywhere
- allow `443/tcp` from anywhere
- deny other inbound ports

## 4. Secret Handling

- Keep all secrets in server-side `.env`.
- Never commit `.env` to git.
- Commit only `.env.example`.
- Restrict `.env` file permissions:

```bash
chmod 600 .env
```

Minimum sensitive values:

- `DJANGO_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `DATABASE_URL` (if present)
- messaging tokens (WhatsApp/Telegram)

## 5. Django Runtime Hardening

For production in `.env`:

- `DJANGO_SETTINGS_MODULE=config.settings.prod`
- `DJANGO_DEBUG=False`
- `SECURE_SSL_REDIRECT=True`
- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- `DJANGO_ALLOWED_HOSTS=app.machinjiri.net`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://app.machinjiri.net`

Proxy TLS headers are already configured via Django settings and Caddy reverse proxy behavior.

## 6. Data Protection and Backups

- PostgreSQL data persists in Docker named volume (`postgres_data`).
- Volume persistence is not a backup strategy.
- Use `./scripts/backup-db.sh` on schedule.
- Keep backup copies off-server (DigitalOcean Spaces, S3-compatible storage, or separate host).
- Regularly test restore with `./scripts/restore-db.sh` in a non-production environment.

## 7. Patch and Update Strategy

- OS updates: at least monthly (or faster for critical CVEs)
- Docker image rebuild + app redeploy: each release
- Re-run deployment script after env/security changes

Recommended cadence:

- weekly dependency review
- monthly base image refresh
- monthly server package patching

## 8. Optional Additional Controls

- Fail2ban for SSH brute-force reduction
- unattended security upgrades (`unattended-upgrades`)
- central log shipping
- remote backup encryption + retention policies

## 9. Residual Risks of Single-Droplet Architecture

- single point of failure (host outage affects app and DB together)
- limited horizontal scaling
- maintenance windows can impact availability
- no managed database isolation

For higher resilience, move to split tiers (managed DB + separate app nodes + load balancer).
