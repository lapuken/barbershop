# Smart Barber Shops

Smart Barber Shops is a Django-based multi-branch barber shop operations platform. This repository now includes a production-oriented Azure deployment baseline built around Azure Container Apps, Azure Container Registry, Azure Database for PostgreSQL Flexible Server, Azure Key Vault, Terraform, and GitHub Actions using OpenID Connect.

## Architecture Overview

- Application runtime: Django + Django REST Framework in a Docker container
- Hosting: Azure Container Apps
- Image registry: Azure Container Registry
- Database: Azure Database for PostgreSQL Flexible Server
- Secret storage: Azure Key Vault
- Identity: user-assigned managed identities for runtime, GitHub Terraform, and GitHub deployment
- Monitoring: Log Analytics connected to the Container Apps environment
- Infrastructure as Code: Terraform
- CI/CD: GitHub Actions with workload identity federation

Detailed deployment architecture is documented in [docs/architecture.md](/home/khido/projects/barbershop/docs/architecture.md).

Current delivery snapshots:

- [Stakeholder status summary](/home/khido/projects/barbershop/docs/stakeholder-status-summary.md)
- [Technical status breakdown](/home/khido/projects/barbershop/docs/technical-status-breakdown.md)
- [Implementation roadmap](/home/khido/projects/barbershop/docs/implementation-roadmap.md)

## Azure Services Used

- Azure Resource Group
- Azure Container Registry
- Azure Container Apps Environment
- Azure Container App for the web workload
- Azure Container Apps Job for Django migrations
- Azure Database for PostgreSQL Flexible Server
- Azure Key Vault
- Azure Log Analytics Workspace
- Microsoft Entra workload identity federation for GitHub Actions

## Prerequisites

Local:

- Python 3.12
- Docker
- Terraform 1.6+
- Azure CLI
- Access to the target Azure subscription and tenant

GitHub:

- GitHub repository environments named `dev` and `prod`
- Environment variables populated from Terraform outputs and environment-specific configuration
- Optional protection rules for the `prod` environment

Azure:

- A subscription admin or platform admin for the initial bootstrap
- Remote state storage account and blob container for Terraform state

## Fastest Local App Test

If you want to stand the app up locally and log in quickly, use the bootstrap script:

```bash
./scripts/bootstrap-local.sh
source .venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

That script will:

- copy `.env.example` to `.env` if needed
- create `.venv`
- install Python dependencies
- start the PostgreSQL Docker service
- run migrations
- seed demo data

### Demo Credentials

- Platform admin username: `platformadmin`
- Platform admin password: `ChangeMe12345!`
- Shop owner username: `owner1`
- Shop owner password: `ChangeMe12345!`
- Shop manager username: `manager1`
- Shop manager password: `ChangeMe12345!`
- Cashier username: `cashier1`
- Cashier password: `ChangeMe12345!`
- Second shop owner username: `owner2`
- Second shop owner password: `ChangeMe12345!`

### Local URLs

Once `python manage.py runserver 0.0.0.0:8000` is running:

- App root: `http://127.0.0.1:8000/`
- Login: `http://127.0.0.1:8000/accounts/login/`

### What the Demo Seed Includes

- 2 barber shop branches
- 5 demo user accounts
- multiple active barbers
- multiple products across shops
- recent sales over multiple days
- recent expenses
- repeat customers and upcoming appointments
- WhatsApp and Telegram-ready booking and availability sharing
- automatic booking confirmations through WhatsApp or Telegram when delivery credentials are configured

That means the dashboard, reports, audit feed, shop selector, appointment schedule, and messaging/share flows have usable data immediately after bootstrap.

## Docker-Only Pilot Run

If you want to run the app without a local Python setup, use the Docker bootstrap:

```bash
./scripts/bootstrap-docker.sh
```

That path will:

- copy `.env.example` to `.env` if needed
- build the app image
- start PostgreSQL, the Django web container, and Nginx
- wait for the app health endpoint
- seed the richer demo dataset inside the web container

Docker pilot URLs:

- App root: `http://127.0.0.1/`
- Login: `http://127.0.0.1/accounts/login/`
- Health: `http://127.0.0.1/healthz/`

After bootstrap, run the pilot verifier before sharing the URL:

```bash
./scripts/verify-docker-pilot.sh
```

Useful Docker commands:

```bash
./scripts/verify-docker-pilot.sh
docker compose logs -f web
docker compose exec web python manage.py test
docker compose exec web python manage.py seed_demo
docker compose down
```

## Repository Layout

- [infra](/home/khido/projects/barbershop/infra): Terraform root module, reusable modules, and environment examples
- [docs](/home/khido/projects/barbershop/docs): architecture, OIDC setup, runbooks, and deployment checklist
- [.github/workflows](/home/khido/projects/barbershop/.github/workflows): CI/CD and Terraform workflows
- [scripts/azure](/home/khido/projects/barbershop/scripts/azure): Azure automation scripts used by workflows and operators

## Azure Bootstrap Steps

1. Create an Azure Storage Account backend for Terraform state.
2. Copy `infra/env/dev/backend.hcl.example` and `infra/env/prod/backend.hcl.example` to real backend files or provide equivalent values in CI/CD.
3. Copy the environment tfvars examples and replace placeholder values.
4. Run Terraform locally once with a trusted bootstrap identity to create:
   - runtime managed identity
   - GitHub OIDC identities
   - ACR
   - Key Vault
   - PostgreSQL
   - Container Apps environment
   - web app and migration job
5. Capture Terraform outputs for:
   - `github_infra_client_id`
   - `github_deploy_client_id`
   - `acr_name`
   - `acr_login_server`
   - `resource_group_name`
   - `container_app_name`
   - `migration_job_name`
   - `key_vault_name`

If this is the first time the environment is being created and no application image exists yet, run the first Terraform apply with `deploy_application_resources=false`, push the first image to ACR, and then re-run Terraform with `deploy_application_resources=true`.

After the first apply, set the placeholder Key Vault secrets for outbound booking confirmations if you want automatic customer delivery:

- `telegram_bot_token`
- `whatsapp_access_token`

Also set `whatsapp_phone_number_id` in the environment tfvars or GitHub environment variables if WhatsApp delivery should be enabled.

## GitHub Setup Steps

1. Create GitHub environments `dev` and `prod`.
2. Configure environment variables described in [docs/github-oidc-setup.md](/home/khido/projects/barbershop/docs/github-oidc-setup.md).
3. Add environment approvals for `prod`.
4. Run `Terraform Apply` for `dev` once the environment variables are in place.
5. Use `Deploy Dev` to ship the first real application image.

## Terraform Commands

```bash
terraform -chdir=infra fmt -recursive
terraform -chdir=infra init -backend-config=env/dev/backend.hcl
terraform -chdir=infra plan -var-file=env/dev/terraform.tfvars
terraform -chdir=infra apply -var-file=env/dev/terraform.tfvars
```

See [infra/README.md](/home/khido/projects/barbershop/infra/README.md) for the full environment flow.

## Deployment Workflows

- `CI`: lint, tests, and container build validation
- `Terraform Plan`: review environment-specific infrastructure changes
- `Terraform Apply`: provision or update Azure infrastructure
- `Build And Push`: manual image build/push to ACR
- `Deploy Dev`: build, push, run migration job, update the web app, and verify `/healthz/`
- `Deploy Prod`: manual production release using the same sequence with GitHub environment protection

## Local Verification Commands

Application checks:

```bash
source .venv/bin/activate
python manage.py test
ruff check .
black --check .
```

Container path:

```bash
docker compose up --build
```

Browser smoke path:

```bash
source .venv/bin/activate
pip install -r requirements-smoke.txt
python -m playwright install chromium
APP_BASE_URL=http://127.0.0.1:8000 ./scripts/run-browser-smoke.sh
```

Optional write-mode smoke test:

```bash
SMOKE_WRITE_TESTS=true APP_BASE_URL=http://127.0.0.1:8000 ./scripts/run-browser-smoke.sh
```

If you use the Docker-only pilot path, point the smoke test at Nginx instead:

```bash
APP_BASE_URL=http://127.0.0.1 ./scripts/run-browser-smoke.sh
```

## Runtime Configuration

The Azure deployment expects the following categories of configuration:

- non-secret runtime settings passed directly to Container Apps:
  - `DJANGO_SETTINGS_MODULE`
  - `DJANGO_ALLOWED_HOSTS`
  - `DJANGO_CSRF_TRUSTED_ORIGINS`
  - `POSTGRES_HOST`
  - `POSTGRES_DB`
  - `POSTGRES_USER`
  - `POSTGRES_SSLMODE=require`
  - session/security settings
- secrets resolved from Key Vault at runtime through the container app managed identity:
  - `DJANGO_SECRET_KEY`
  - `POSTGRES_PASSWORD`

The local development file remains [`.env.example`](/home/khido/projects/barbershop/.env.example).

## Migration and Static Files Strategy

- Static files are collected by the container entrypoint on startup.
- Migrations are not run on normal web container startup.
- A dedicated Azure Container Apps Job runs `python manage.py migrate --noinput` before the web app image is updated.
- If the migration job fails, the deployment workflow stops before the web revision is updated.

## Rollback Notes

- If a deployment fails before the web app update, rerun the migration job only after fixing the issue.
- If the web app update fails after migrations succeeded, redeploy the previous known-good image tag.
- If a migration is backward-incompatible, application rollback may require a database restore rather than an image rollback alone.
- Preserve previous image tags in ACR for rollback.

## Troubleshooting

- Migration failures: review Container Apps Job execution logs in Azure and the GitHub Actions logs.
- Container app health failures: query `/healthz/` and inspect Container Apps revision logs in Log Analytics.
- OIDC login failures: verify federated credential subject and GitHub environment names match exactly.
- Secret resolution failures: confirm Key Vault secret names, secret versions, and runtime identity role assignments.
- PostgreSQL connectivity failures: confirm the Flexible Server firewall posture and SSL mode.
- Browser smoke failures: confirm the app is running, demo credentials exist, and `python -m playwright install chromium` has been executed in the active environment.

## Additional Documentation

- [infra/README.md](/home/khido/projects/barbershop/infra/README.md)
- [docs/architecture.md](/home/khido/projects/barbershop/docs/architecture.md)
- [docs/operations-runbook.md](/home/khido/projects/barbershop/docs/operations-runbook.md)
- [docs/github-oidc-setup.md](/home/khido/projects/barbershop/docs/github-oidc-setup.md)
- [docs/deployment-checklist.md](/home/khido/projects/barbershop/docs/deployment-checklist.md)
- [docs/barber-pilot-test-plan.md](/home/khido/projects/barbershop/docs/barber-pilot-test-plan.md)
- [SECURITY.md](/home/khido/projects/barbershop/SECURITY.md)
