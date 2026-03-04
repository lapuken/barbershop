# AGENTS

## Repository Guidance

- Application runtime code lives in the Django apps under `apps/`.
- Azure deployment assets live under `infra/`, `.github/workflows/`, `scripts/azure/`, and `docs/`.
- Keep application startup and migration execution separate. Do not reintroduce automatic migrations into the normal web startup path.
- Treat Terraform state as sensitive because the stack generates and stores secret values in Key Vault.
- Prefer updating Azure deployment behavior through Terraform and the reviewed shell scripts instead of ad hoc CLI commands.

## Deployment Baseline

- Hosting target: Azure Container Apps
- Registry: Azure Container Registry
- Database: Azure Database for PostgreSQL Flexible Server
- Secret source: Azure Key Vault
- GitHub Azure auth: OIDC workload identity federation

## When Changing CI/CD

- Preserve OIDC-based Azure login. Do not introduce client secrets or publish profiles unless explicitly required.
- Keep `dev` and `prod` environment separation intact.
- Ensure migration execution remains an explicit step before the web revision update.

## When Changing Infrastructure

- Maintain least-privilege role assignments for runtime and GitHub identities.
- Document any new Azure service, new secret, or new environment variable in the relevant docs.
- Keep `infra/README.md`, `docs/github-oidc-setup.md`, and `docs/operations-runbook.md` current with workflow changes.
