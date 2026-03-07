# AGENTS

## Repository Guidance

- Application runtime code lives in the Django apps under `apps/`.
- Deployment and server operations assets live under the repository root, `scripts/`, `nginx/`, `ops/`, and `docs/`.
- Keep application startup and migration execution separate. Do not reintroduce automatic migrations into the normal web startup path.
- Prefer updating deployment behavior through the reviewed shell scripts and checked-in server configuration rather than ad hoc operator commands.

## Deployment Baseline

- Hosting target: Ubuntu 22.04 VPS
- Web entrypoint: host `nginx`
- TLS: `certbot` + Let's Encrypt
- Runtime: Docker Compose
- Database: PostgreSQL container
- Secrets source: external server-side `.env` file

## When Changing CI/CD

- Keep CI focused on validation unless the user explicitly asks for deployment automation changes.
- Do not introduce long-lived deployment secrets into GitHub unless explicitly required.
- Ensure migration execution remains an explicit deployment step before the web service is restarted.

## When Changing Infrastructure

- Maintain the least-privilege host posture documented in `HARDENING.md`.
- Document any new system package, DNS requirement, backup behavior, or environment variable in the relevant docs.
- Keep `DEPLOYMENT.md`, `OPERATIONS.md`, `HARDENING.md`, and `docs/operations-runbook.md` current with workflow changes.
