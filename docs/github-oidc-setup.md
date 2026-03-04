# GitHub OIDC Setup

## Goal

Allow GitHub Actions to authenticate to Azure without storing long-lived client secrets.

This repository expects one GitHub environment per deployment environment:

- `dev`
- `prod`

Each environment is mapped to two Azure user-assigned managed identities:

- infrastructure identity
- deployment identity

## Bootstrap Options

You can bootstrap the identities in two ways:

1. Recommended: run Terraform once locally with a trusted Azure operator identity.
2. Alternative: create the identities and federated credentials manually, then let Terraform adopt or recreate the pattern later.

The Terraform stack already provisions:

- runtime identity
- GitHub infra identity with federated credential
- GitHub deploy identity with federated credential

## Federated Credential Subject

The Terraform configuration uses this subject pattern:

```text
repo:<github-owner>/<github-repo>:environment:<github-environment>
```

Examples:

- `repo:your-org/smart-barber-shops:environment:dev`
- `repo:your-org/smart-barber-shops:environment:prod`

The GitHub environment name must exactly match the `github_environment` Terraform variable.

## GitHub Environment Variables

Set these per environment in GitHub:

- `AZURE_SUBSCRIPTION_ID`
- `AZURE_TENANT_ID`
- `AZURE_INFRA_CLIENT_ID`
- `AZURE_DEPLOY_CLIENT_ID`
- `AZURE_ACR_NAME`
- `AZURE_ACR_LOGIN_SERVER`
- `AZURE_RESOURCE_GROUP`
- `AZURE_CONTAINER_APP_NAME`
- `AZURE_MIGRATION_JOB_NAME`
- `TFSTATE_RESOURCE_GROUP`
- `TFSTATE_STORAGE_ACCOUNT`
- `TFSTATE_CONTAINER`
- `TF_LOCATION`
- `TF_NAME_SUFFIX`
- `TF_OWNER`
- `TF_TEAM`
- `TF_COST_CENTER`
- `TF_ACR_SKU`
- `TF_LOG_RETENTION_DAYS`
- `TF_KEYVAULT_PURGE_PROTECTION`
- `TF_POSTGRES_SKU_NAME`
- `TF_POSTGRES_STORAGE_MB`
- `TF_POSTGRES_BACKUP_RETENTION_DAYS`
- `TF_POSTGRES_ZONE`
- `TF_POSTGRES_DATABASE_NAME`
- `TF_CONTAINER_APP_TARGET_PORT`
- `TF_CONTAINER_APP_MIN_REPLICAS`
- `TF_CONTAINER_APP_MAX_REPLICAS`
- `TF_CONTAINER_APP_CPU`
- `TF_CONTAINER_APP_MEMORY`
- `TF_WHATSAPP_PHONE_NUMBER_ID`
- `TF_DJANGO_ALLOWED_HOSTS`
- `TF_DJANGO_CSRF_TRUSTED_ORIGINS`

Most of the Azure resource-name variables come directly from Terraform outputs after the first successful apply.

## Required Azure Role Assignments

### Runtime identity

- `AcrPull` on the ACR
- `Key Vault Secrets User` on the Key Vault

### GitHub infra identity

- `Contributor` on the environment resource group
- `User Access Administrator` on the environment resource group
- `Key Vault Secrets Officer` on the Key Vault

### GitHub deploy identity

- `Container Apps Contributor` on the environment resource group
- `AcrPush` on the ACR

## Manual Azure CLI Bootstrap Example

If you need to create a federated credential manually before Terraform:

```bash
az identity federated-credential create \
  --name dev-deploy \
  --identity-name <identity-name> \
  --resource-group <resource-group> \
  --issuer https://token.actions.githubusercontent.com \
  --subject repo:<github-owner>/<github-repo>:environment:dev \
  --audiences api://AzureADTokenExchange
```

## GitHub Environment Protection Guidance

- Require reviewers on `prod`
- Restrict who can deploy to `prod`
- Keep `dev` more open for normal engineering flow
- Enable branch protection on `main`

## Validation Steps

1. Trigger `Build And Push` for `dev`.
2. Confirm `azure/login` succeeds without any client secret.
3. Trigger `Terraform Apply` for `dev`.
4. Trigger `Deploy Dev`.
5. Confirm the migration job and web deployment both succeed.
