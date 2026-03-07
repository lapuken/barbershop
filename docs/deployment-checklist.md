# Deployment Checklist

## Initial Server Bootstrap

- Ubuntu 22.04 VPS provisioned and reachable over SSH
- Docker Engine, Docker Compose, `nginx`, and `certbot` installed
- `/opt/smartbarber/{app,env,backups,logs}` directories created
- repository cloned into `/opt/smartbarber/app`
- external env file created at `/opt/smartbarber/env/.env`
- DNS records pointed at the VPS
- Nginx site installed and TLS certificates issued
- first deploy completed successfully
- initial admin user created

## Before Each Release

- CI green
- migration impact reviewed
- rollback git ref known
- recent backup confirmed or pre-deploy backup enabled
- free disk space checked
- Nginx and Docker services healthy

## During Release

- run `./deploy.sh --git-pull` or `./deploy.sh`
- pre-deploy backup completed if enabled
- web image built successfully
- PostgreSQL started and passed readiness checks
- `python manage.py check --deploy` succeeded
- migrations completed successfully
- static files collected successfully
- web container started successfully
- `/healthz/` returned success locally and publicly

## After Release

- login and dashboard manually verified
- application, database, and Nginx logs reviewed
- release marker recorded under `/opt/smartbarber/logs/releases`
- release notes or operator log updated with commit SHA and timestamp
