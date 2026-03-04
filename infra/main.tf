resource "random_password" "postgres_admin_password" {
  length           = 32
  special          = true
  override_special = "_-"
}

resource "random_password" "django_secret_key" {
  length           = 64
  special          = true
  override_special = "_-"
}

module "resource_group" {
  source = "./modules/resource-group"

  name     = local.resource_group
  location = var.location
  tags     = local.common_tags
}

module "monitoring" {
  source = "./modules/monitoring"

  name                = local.log_analytics_name
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location
  retention_in_days   = var.log_analytics_retention_days
  tags                = local.common_tags
}

module "acr" {
  source = "./modules/acr"

  name                = local.acr_name
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location
  sku                 = var.acr_sku
  tags                = local.common_tags
}

module "runtime_identity" {
  source = "./modules/identity"

  name                = local.runtime_mi_name
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location
  tags                = local.common_tags
}

module "github_infra_identity" {
  source = "./modules/identity"

  name                        = local.gha_infra_mi_name
  resource_group_name         = module.resource_group.name
  location                    = module.resource_group.location
  create_federated_credential = true
  federated_credential_name   = "${local.environment_slug}-infra"
  federated_subject           = local.github_subject
  tags                        = local.common_tags
}

module "github_deploy_identity" {
  source = "./modules/identity"

  name                        = local.gha_deploy_mi_name
  resource_group_name         = module.resource_group.name
  location                    = module.resource_group.location
  create_federated_credential = true
  federated_credential_name   = "${local.environment_slug}-deploy"
  federated_subject           = local.github_subject
  tags                        = local.common_tags
}

module "key_vault" {
  source = "./modules/key-vault"

  name                       = local.key_vault_name
  resource_group_name        = module.resource_group.name
  location                   = module.resource_group.location
  tenant_id                  = var.tenant_id
  sku_name                   = var.key_vault_sku_name
  purge_protection_enabled   = var.key_vault_purge_protection_enabled
  soft_delete_retention_days = var.key_vault_soft_delete_retention_days
  enable_rbac_authorization  = true
  tags                       = local.common_tags
}

resource "azurerm_key_vault_secret" "django_secret_key" {
  name         = local.key_vault_secret_names.django_secret_key
  value        = random_password.django_secret_key.result
  key_vault_id = module.key_vault.id
  content_type = "django-secret-key"
  tags         = local.common_tags
}

resource "azurerm_key_vault_secret" "postgres_admin_password" {
  name         = local.key_vault_secret_names.postgres_admin_password
  value        = random_password.postgres_admin_password.result
  key_vault_id = module.key_vault.id
  content_type = "postgres-admin-password"
  tags         = local.common_tags
}

resource "azurerm_key_vault_secret" "telegram_bot_token" {
  name         = local.key_vault_secret_names.telegram_bot_token
  value        = "configure-me"
  key_vault_id = module.key_vault.id
  content_type = "telegram-bot-token"
  tags         = local.common_tags

  lifecycle {
    ignore_changes = [value]
  }
}

resource "azurerm_key_vault_secret" "whatsapp_access_token" {
  name         = local.key_vault_secret_names.whatsapp_access_token
  value        = "configure-me"
  key_vault_id = module.key_vault.id
  content_type = "whatsapp-access-token"
  tags         = local.common_tags

  lifecycle {
    ignore_changes = [value]
  }
}

module "postgres" {
  source = "./modules/postgres-flex"

  name                          = local.postgres_name
  resource_group_name           = module.resource_group.name
  location                      = module.resource_group.location
  postgres_version              = var.postgres_version
  administrator_login           = var.postgres_admin_username
  administrator_password        = random_password.postgres_admin_password.result
  database_name                 = var.postgres_database_name
  sku_name                      = var.postgres_sku_name
  storage_mb                    = var.postgres_storage_mb
  backup_retention_days         = var.postgres_backup_retention_days
  zone                          = var.postgres_zone
  public_network_access_enabled = var.postgres_public_network_access_enabled
  firewall_rules                = local.postgres_firewall_rules
  tags                          = local.common_tags
}

module "container_app_environment" {
  source = "./modules/container-app-env"

  name                       = local.container_env_name
  resource_group_name        = module.resource_group.name
  location                   = module.resource_group.location
  log_analytics_workspace_id = module.monitoring.id
  tags                       = local.common_tags
}

module "container_app" {
  count  = var.deploy_application_resources ? 1 : 0
  source = "./modules/container-app"

  name                         = local.container_app_name
  resource_group_name          = module.resource_group.name
  container_app_environment_id = module.container_app_environment.id
  revision_mode                = var.container_app_revision_mode
  tags                         = local.common_tags
  user_assigned_identity_ids   = [module.runtime_identity.id]
  registry_server              = module.acr.login_server
  registry_identity_id         = module.runtime_identity.id
  image                        = var.container_image
  target_port                  = var.container_app_target_port
  allow_insecure_connections   = var.container_app_allow_insecure_connections
  external_enabled             = var.container_app_external_enabled
  min_replicas                 = var.container_app_min_replicas
  max_replicas                 = var.container_app_max_replicas
  cpu                          = var.container_app_cpu
  memory                       = var.container_app_memory
  environment_variables        = local.container_environment_variables
  secret_environment_variables = local.container_secret_environment_variables
  key_vault_secrets = {
    django-secret-key = {
      identity            = module.runtime_identity.id
      key_vault_secret_id = azurerm_key_vault_secret.django_secret_key.versionless_id
    }
    postgres-password = {
      identity            = module.runtime_identity.id
      key_vault_secret_id = azurerm_key_vault_secret.postgres_admin_password.versionless_id
    }
    telegram-bot-token = {
      identity            = module.runtime_identity.id
      key_vault_secret_id = azurerm_key_vault_secret.telegram_bot_token.versionless_id
    }
    whatsapp-access-token = {
      identity            = module.runtime_identity.id
      key_vault_secret_id = azurerm_key_vault_secret.whatsapp_access_token.versionless_id
    }
  }
  command = []
  args    = []
}

module "migration_job" {
  count  = var.deploy_application_resources ? 1 : 0
  source = "./modules/container-app-job"

  name                         = local.migration_job_name
  location                     = module.resource_group.location
  resource_group_name          = module.resource_group.name
  container_app_environment_id = module.container_app_environment.id
  tags                         = local.common_tags
  user_assigned_identity_ids   = [module.runtime_identity.id]
  registry_server              = module.acr.login_server
  registry_identity_id         = module.runtime_identity.id
  image                        = var.container_image
  cpu                          = var.container_app_cpu
  memory                       = var.container_app_memory
  environment_variables        = local.migration_environment_variables
  secret_environment_variables = local.container_secret_environment_variables
  key_vault_secrets = {
    django-secret-key = {
      identity            = module.runtime_identity.id
      key_vault_secret_id = azurerm_key_vault_secret.django_secret_key.versionless_id
    }
    postgres-password = {
      identity            = module.runtime_identity.id
      key_vault_secret_id = azurerm_key_vault_secret.postgres_admin_password.versionless_id
    }
    telegram-bot-token = {
      identity            = module.runtime_identity.id
      key_vault_secret_id = azurerm_key_vault_secret.telegram_bot_token.versionless_id
    }
    whatsapp-access-token = {
      identity            = module.runtime_identity.id
      key_vault_secret_id = azurerm_key_vault_secret.whatsapp_access_token.versionless_id
    }
  }
  command = ["/app/docker/start-migrate.sh"]
  args    = []
}

resource "azurerm_role_assignment" "runtime_acr_pull" {
  scope                            = module.acr.id
  role_definition_name             = "AcrPull"
  principal_id                     = module.runtime_identity.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "runtime_key_vault_secrets_user" {
  scope                            = module.key_vault.id
  role_definition_name             = "Key Vault Secrets User"
  principal_id                     = module.runtime_identity.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "github_infra_contributor" {
  scope                            = module.resource_group.id
  role_definition_name             = "Contributor"
  principal_id                     = module.github_infra_identity.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "github_infra_user_access_administrator" {
  scope                            = module.resource_group.id
  role_definition_name             = "User Access Administrator"
  principal_id                     = module.github_infra_identity.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "github_infra_key_vault_secrets_officer" {
  scope                            = module.key_vault.id
  role_definition_name             = "Key Vault Secrets Officer"
  principal_id                     = module.github_infra_identity.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "github_deploy_container_apps_contributor" {
  scope                            = module.resource_group.id
  role_definition_name             = "Container Apps Contributor"
  principal_id                     = module.github_deploy_identity.principal_id
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "github_deploy_acr_push" {
  scope                            = module.acr.id
  role_definition_name             = "AcrPush"
  principal_id                     = module.github_deploy_identity.principal_id
  skip_service_principal_aad_check = true
}
