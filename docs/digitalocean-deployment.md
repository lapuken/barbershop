# Legacy Note

The repository no longer uses the older Caddy-based single-droplet path as the primary VPS deployment model.

Use the current documentation instead:

- [DEPLOYMENT.md](../DEPLOYMENT.md)
- [docs/operations-runbook.md](operations-runbook.md)
- [docs/security-hardening.md](security-hardening.md)

The same deployment model works on DigitalOcean, Hetzner, Linode, or any comparable Ubuntu 22.04 VPS:

- host Nginx
- Certbot + Let's Encrypt
- Docker Compose for `web` and `db`
- PostgreSQL Docker volume plus host-backed media files
