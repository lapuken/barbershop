# SECURITY

Smart Barber Shops uses a practical VPS and application security baseline aligned to ISO/IEC 27001-style governance intent and informed by ISO/IEC 27002-style control guidance. It is not formally certified.

## Security Baseline

- least-privilege host access through a non-root sudo operator account
- host `nginx` with TLS termination through Let's Encrypt
- Docker Compose isolation between the Django app and PostgreSQL
- explicit deploy flow that runs `check --deploy`, migrations, and `collectstatic` before the web service is restarted
- Django runtime protections in the application layer, including CSRF, security headers, session controls, and audit logging
- backup, rollback, and diagnostics scripts for operator-driven recovery
- GitHub Actions CI for linting, tests, migrations, and image build validation

## Secrets Handling

- production secrets live in an external server-side env file such as `/opt/smartbarber/env/.env`
- secrets are not committed to source control
- the env file should be owned by the deployment user and permissioned `0600`
- rotate secrets by updating the env file and redeploying
- backup archives containing sensitive data should be permission-restricted and copied off-host regularly

## Access Model

- operate through a non-root user such as `barberadmin`
- disable direct root SSH after operator access is verified
- expose only `22/tcp`, `80/tcp`, and `443/tcp`
- keep the Django container bound to `127.0.0.1:8000`
- do not publish PostgreSQL on a host port

## CI/CD Trust Model

- GitHub Actions is used for CI validation only
- production deployment is an operator-initiated server action through the reviewed deployment scripts
- no cloud deployment credentials are required for the repository baseline
- changes should be released only after CI is green and rollback/backup posture is confirmed

## Infrastructure and Network Posture

- public ingress is handled by host `nginx`
- PostgreSQL stays on the internal Docker network
- TLS is enforced for the public application URL
- static and media directories are persisted on the host
- operational logs live on the server and should be reviewed after each release

## Residual Risks

- the application runs on a single VPS, so host failure is still a service risk
- production secrets live on the server filesystem and depend on host hardening discipline
- off-host backup handling is operator-driven unless additional automation is introduced
- the application may still use a broad-privilege database account unless a narrower app-specific role is created
- there is no built-in staging environment or high-availability failover path in the current baseline

## Deferred Controls

- off-host backup automation and restore verification
- centralized log shipping and alerting
- a dedicated staging environment
- dedicated least-privilege application database credentials
- additional reverse-proxy protections such as WAF/CDN or rate limiting beyond the current baseline

## Operational Recommendations

- protect `/opt/smartbarber/env/.env` and `/opt/smartbarber/backups` with strict filesystem permissions
- use SSH keys and disable password authentication where possible
- patch the host OS and container base images regularly
- test backup restore procedures during maintenance windows
- review app, database, and Nginx logs after each release

## Disclosure Note

This repository is designed to align with a practical ISO/IEC 27001-style deployment baseline for an MVP. It does not imply formal certification or a completed ISMS program.
