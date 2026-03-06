output "resource_group_name" {
  description = "Azure resource group name."
  value       = module.resource_group.name
}

output "container_app_name" {
  description = "Azure Container App name."
  value       = var.deploy_application_resources ? module.container_app[0].name : null
}

output "migration_job_name" {
  description = "Azure Container Apps Job name used for Django migrations."
  value       = var.deploy_application_resources ? module.migration_job[0].name : null
}

output "container_app_url" {
  description = "Azure Container App FQDN URL."
  value       = var.deploy_application_resources ? module.container_app[0].latest_revision_fqdn : null
}

output "container_app_environment_name" {
  description = "Azure Container Apps environment name."
  value       = module.container_app_environment.name
}

output "acr_name" {
  description = "Azure Container Registry name."
  value       = module.acr.name
}

output "acr_login_server" {
  description = "Azure Container Registry login server."
  value       = module.acr.login_server
}

output "key_vault_name" {
  description = "Azure Key Vault name."
  value       = module.key_vault.name
}

output "key_vault_uri" {
  description = "Azure Key Vault URI."
  value       = module.key_vault.vault_uri
}

output "postgres_server_name" {
  description = "Azure PostgreSQL Flexible Server name."
  value       = module.postgres.server_name
}

output "postgres_fqdn" {
  description = "Azure PostgreSQL Flexible Server FQDN."
  value       = module.postgres.fqdn
}

output "postgres_database_name" {
  description = "Application database name."
  value       = module.postgres.database_name
}

output "github_infra_client_id" {
  description = "Client ID for the GitHub OIDC Terraform identity."
  value       = module.github_infra_identity.client_id
}

output "github_deploy_client_id" {
  description = "Client ID for the GitHub OIDC deployment identity."
  value       = module.github_deploy_identity.client_id
}

output "runtime_identity_client_id" {
  description = "Client ID for the runtime managed identity."
  value       = module.runtime_identity.client_id
}

output "secret_names" {
  description = "Key Vault secret names expected by the runtime."
  value       = local.key_vault_secret_names
}

output "github_environment_variables" {
  description = "GitHub environment variables expected by CI/CD workflows."
  value = {
    AZURE_SUBSCRIPTION_ID             = var.subscription_id
    AZURE_TENANT_ID                   = var.tenant_id
    AZURE_INFRA_CLIENT_ID             = module.github_infra_identity.client_id
    AZURE_DEPLOY_CLIENT_ID            = module.github_deploy_identity.client_id
    AZURE_ACR_NAME                    = module.acr.name
    AZURE_ACR_LOGIN_SERVER            = module.acr.login_server
    AZURE_RESOURCE_GROUP              = module.resource_group.name
    AZURE_CONTAINER_APP_NAME          = var.deploy_application_resources ? module.container_app[0].name : ""
    AZURE_MIGRATION_JOB_NAME          = var.deploy_application_resources ? module.migration_job[0].name : ""
    TF_LOCATION                       = var.location
    TF_NAME_SUFFIX                    = var.name_suffix
    TF_OWNER                          = var.owner
    TF_TEAM                           = var.team
    TF_COST_CENTER                    = var.cost_center
    TF_ACR_SKU                        = var.acr_sku
    TF_LOG_RETENTION_DAYS             = tostring(var.log_analytics_retention_days)
    TF_KEYVAULT_PURGE_PROTECTION      = tostring(var.key_vault_purge_protection_enabled)
    TF_POSTGRES_SKU_NAME              = var.postgres_sku_name
    TF_POSTGRES_STORAGE_MB            = tostring(var.postgres_storage_mb)
    TF_POSTGRES_BACKUP_RETENTION_DAYS = tostring(var.postgres_backup_retention_days)
    TF_POSTGRES_ZONE                  = var.postgres_zone
    TF_POSTGRES_DATABASE_NAME         = var.postgres_database_name
    TF_CONTAINER_APP_TARGET_PORT      = tostring(var.container_app_target_port)
    TF_CONTAINER_APP_MIN_REPLICAS     = tostring(var.container_app_min_replicas)
    TF_CONTAINER_APP_MAX_REPLICAS     = tostring(var.container_app_max_replicas)
    TF_CONTAINER_APP_CPU              = tostring(var.container_app_cpu)
    TF_CONTAINER_APP_MEMORY           = var.container_app_memory
    TF_WHATSAPP_PHONE_NUMBER_ID       = var.whatsapp_phone_number_id
    TF_DJANGO_ALLOWED_HOSTS           = local.django_allowed_hosts
    TF_DJANGO_CSRF_TRUSTED_ORIGINS    = local.django_csrf_trusted_origins
  }
}
