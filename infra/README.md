# Terraform Infrastructure

This folder provisions the Azure deployment baseline for Smart Barber Shops.

## Structure

- `main.tf`, `locals.tf`, `variables.tf`, `outputs.tf`: root composition
- `modules/`: reusable Azure building blocks
- `env/dev`, `env/prod`: environment-specific backend and variable examples

## Provisioned Resources

- Resource group
- Log Analytics workspace
- Azure Container Registry
- Azure Container Apps Environment
- Azure Container App for the web workload
- Azure Database for PostgreSQL Flexible Server
- Azure Key Vault
- User-assigned managed identities for runtime, GitHub Terraform, and GitHub deployment
- RBAC assignments for ACR, Key Vault, Container Apps, and resource-group operations

## Commands

Dev example:

```bash
cp infra/env/dev/terraform.tfvars.example infra/env/dev/terraform.tfvars
terraform -chdir=infra init -backend-config=env/dev/backend.hcl
terraform -chdir=infra plan -var-file=env/dev/terraform.tfvars
terraform -chdir=infra apply -var-file=env/dev/terraform.tfvars
```

Prod example:

```bash
cp infra/env/prod/terraform.tfvars.example infra/env/prod/terraform.tfvars
terraform -chdir=infra init -backend-config=env/prod/backend.hcl
terraform -chdir=infra plan -var-file=env/prod/terraform.tfvars
terraform -chdir=infra apply -var-file=env/prod/terraform.tfvars
```

## Remote State Guidance

- Use the AzureRM backend with a dedicated storage account and blob container.
- Enable storage account soft delete and access controls for the state container.
- Use separate backend keys for `dev` and `prod`.
- Protect state because Terraform stores generated secret values such as the PostgreSQL admin password and Django secret key.

## Variable Notes

- `name_suffix` keeps globally unique Azure names stable across applies.
- `container_image` should be set to the immutable image tag produced by CI/CD.
- `deploy_application_resources=false` is useful for the first bootstrap when ACR exists but the first application image has not been pushed yet.
- `django_allowed_hosts` and `django_csrf_trusted_origins` must match the deployed ingress hostname or custom domain.
- `whatsapp_phone_number_id` is the non-secret sender identifier required for WhatsApp booking confirmations.
- `postgres_firewall_allow_azure_services` defaults to `true` for a practical MVP. Move to private networking later if your threat model requires it.
- `container_app_external_enabled=false` allows an internal-only Container App when your environment networking supports that posture.
- `postgres_public_network_access_enabled=false` disables the PostgreSQL public endpoint; only use it once private connectivity is designed and available.

## Messaging Secret Placeholders

Terraform creates placeholder Key Vault secrets for these outbound booking confirmation providers:

- `telegram_bot_token`
- `whatsapp_access_token`

Replace those placeholder values after the first apply with [set-keyvault-secret.sh](/home/khido/projects/barbershop/scripts/azure/set-keyvault-secret.sh) or an equivalent reviewed operator flow. The Terraform resources ignore later manual value changes so future applies do not overwrite the live provider tokens.

## Destroy

For non-production:

```bash
terraform -chdir=infra destroy -var-file=env/dev/terraform.tfvars
```

Do not run destroy against production without an explicit recovery and backup plan.
