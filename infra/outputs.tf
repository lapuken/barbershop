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
