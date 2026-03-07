# VPS Deployment Architecture

## Topology

Smart Barber Shops runs as a modular monolith on a single Ubuntu VPS.

Core components:

- host `nginx` for public ingress and TLS termination
- Docker Compose service `web` for the Django application
- Docker Compose service `db` for PostgreSQL
- `shared/static` for collected static assets
- `shared/media` for uploaded files and backup-adjacent persistence
- host-level backup, rollback, and diagnostics scripts

## Resource Relationships

1. Public HTTPS traffic reaches host `nginx`.
2. `nginx` proxies the application to `127.0.0.1:8000`.
3. The `web` container talks to PostgreSQL over the internal Docker network.
4. Static files are collected into `shared/static` for direct serving.
5. Media files persist in `shared/media`.
6. Deployments, backups, and recovery actions are driven through reviewed shell scripts.

## Network and Security Posture

- Only `22/tcp`, `80/tcp`, and `443/tcp` should be exposed on the host.
- The Django app binds only to loopback on the host through Docker port publishing.
- PostgreSQL is not published on a host port.
- TLS is terminated by host `nginx` using Let's Encrypt certificates.
- Production settings enforce secure cookies, SSL redirects, and trusted hosts/origins through the external env file.

## Runtime Configuration Flow

1. Server configuration is stored in `/opt/smartbarber/env/.env`.
2. Docker Compose loads that env file into the `web` and `db` services.
3. The deployment script validates required settings before making runtime changes.
4. The app exposes `/healthz/` for local and public verification.
5. Notification credentials are provided through the external env file, not source control.

## Release Sequence

1. Optionally pull the latest git changes with `./deploy.sh --git-pull`.
2. Optionally create a pre-deploy backup.
3. Build the web image with Docker Compose.
4. Start PostgreSQL and wait for readiness.
5. Run `python manage.py check --deploy`.
6. Run `python manage.py migrate --noinput`.
7. Run `python manage.py collectstatic --noinput`.
8. Start the web container and wait for `/healthz/`.
9. Reload `nginx` if available and record the successful release marker.

## Rollback Sequence

1. Use `./rollback.sh` to return to the previous successful release or a specific git ref.
2. If required, restore the latest database backup with `./restore.sh` or `./scripts/restore-db.sh`.
3. Re-run health checks and inspect logs before reopening access to users.

## DNS and Certificates

Recommended production naming:

- `machinjiri.net`
- `app.machinjiri.net`

The expected flow is:

1. Point the DNS records to the VPS.
2. Install the bootstrap Nginx site.
3. Issue certificates with `certbot`.
4. Switch to the final HTTPS Nginx site.
5. Confirm renewal with `sudo certbot renew --dry-run`.

## Future Hardening Paths

- Off-host backup automation and restore drills
- Centralized log shipping and alerting
- A dedicated staging environment
- Separate application database credentials from the database superuser
- Additional reverse-proxy controls such as rate limiting or WAF/CDN in front of the VPS
