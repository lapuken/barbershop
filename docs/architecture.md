# Azure Deployment Architecture

## Topology

Smart Barber Shops uses a modular monolith application runtime deployed as a single web container on Azure Container Apps.

Core Azure resources per environment:

- Resource Group
- Azure Container Registry
- Azure Container Apps Environment
- Azure Container App `web`
- Azure Container Apps Job `migrate`
- Azure Database for PostgreSQL Flexible Server
- Azure Key Vault
- Azure Log Analytics Workspace
- User-assigned managed identities for:
  - application runtime
  - GitHub Terraform automation
  - GitHub deployment automation

## Resource Relationships

1. GitHub Actions authenticates to Azure using OIDC and an environment-specific user-assigned managed identity.
2. Terraform provisions Azure infrastructure and writes generated secrets into Key Vault.
3. The runtime managed identity receives `AcrPull` and `Key Vault Secrets User`.
4. The web container and migration job pull images from ACR and resolve Key Vault secrets at runtime.
5. The application connects to PostgreSQL Flexible Server over TLS with `sslmode=require`.
6. Container Apps emits platform/runtime logs into Log Analytics.

## Network and Security Posture

- Web ingress is public through Container Apps external ingress by default, but Terraform can now disable external ingress for internal-only deployments.
- TLS termination is handled by Azure Container Apps ingress.
- Django trusts `X-Forwarded-Proto` so secure redirects and cookie behavior work correctly behind Azure ingress.
- PostgreSQL Flexible Server is provisioned with public network access enabled for the MVP and a firewall rule that allows Azure services by default, but Terraform can now disable the public endpoint for private-network-ready environments.
- Key Vault uses RBAC authorization instead of access policies.
- Secrets are not stored in GitHub for Azure authentication.

## Identity Flows

### Runtime

- Container App and migration job use the runtime managed identity.
- The runtime identity pulls images from ACR.
- The runtime identity resolves `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD` from Key Vault.

### Infrastructure Automation

- The GitHub Terraform workflow uses the infra managed identity.
- That identity applies Terraform, writes Key Vault secrets, and manages RBAC assignments in the environment resource group.

### Release Automation

- The GitHub deploy workflow uses the deploy managed identity.
- That identity builds and pushes images to ACR, updates the migration job image, runs the migration job, and updates the web container image.

## Runtime Configuration Flow

1. Terraform provisions infrastructure and generates the Key Vault secret IDs referenced by Container Apps.
2. The Container App template receives non-secret settings directly as environment variables.
3. Secret environment variables reference named Container App secrets backed by Key Vault.
4. At runtime, Azure resolves the secret values using the managed identity.
5. The app exposes `/healthz/` for deployment verification.

## Release Sequence

1. Build Docker image from the repository.
2. Push immutable tag `${GITHUB_SHA}` to ACR.
3. Update the migration job image to the same immutable tag.
4. Run the migration job and wait for success.
5. Update the web container image to the same immutable tag.
6. Verify `https://<container-app-fqdn>/healthz/`.

## Rollback Sequence

1. Select the previous known-good image tag in ACR.
2. Re-run the deploy workflow with that tag or manually update the migration job and web app images.
3. If the failed release included a backward-incompatible migration, perform database restore or operator-led rollback steps instead of image-only rollback.

## Custom Domains and Certificates

Custom domains are not fully automated in Terraform in this baseline. Recommended next-step flow:

1. Validate the Container App ingress and final hostname.
2. Create DNS CNAME or apex records per Azure Container Apps guidance.
3. Bind the custom domain and managed certificate in Azure.
4. Update `django_allowed_hosts` and `django_csrf_trusted_origins`.

## Future Hardening Paths

- Private endpoints and private DNS for PostgreSQL and Key Vault
- Azure Front Door or Application Gateway with WAF
- Separate application database user and tighter DB grants
- Secret rotation automation
- Artifact signing and image provenance enforcement
