locals {
  project_slug       = replace(lower(var.project_name), "/[^a-z0-9]/", "")
  environment_slug   = replace(lower(var.environment), "/[^a-z0-9]/", "")
  name_suffix_slug   = replace(lower(var.name_suffix), "/[^a-z0-9]/", "")
  base_name          = "${local.project_slug}-${local.environment_slug}-${local.name_suffix_slug}"
  compact_name       = "${local.project_slug}${local.environment_slug}${local.name_suffix_slug}"
  resource_group     = "${local.base_name}-rg"
  log_analytics_name = "${local.base_name}-law"
  container_env_name = "${local.base_name}-cae"
  container_app_name = "${local.base_name}-web"
  migration_job_name = "${local.base_name}-migrate"
  acr_name           = substr("${local.compact_name}acr", 0, 50)
  key_vault_name     = substr("${local.compact_name}kv", 0, 24)
  postgres_name      = substr("${local.project_slug}-${local.environment_slug}-${local.name_suffix_slug}-psql", 0, 63)
  runtime_mi_name    = "${local.base_name}-runtime-mi"
  gha_infra_mi_name  = "${local.base_name}-gha-infra-mi"
  gha_deploy_mi_name = "${local.base_name}-gha-deploy-mi"

  common_tags = merge(
    {
      application = var.project_name
      environment = var.environment
      managed_by  = "terraform"
      owner       = var.owner
      repo        = var.github_repository
      team        = var.team
    },
    var.cost_center == "" ? {} : { cost_center = var.cost_center },
    var.additional_tags,
  )

  github_subject = "repo:${var.github_repository}:environment:${var.github_environment}"

  django_allowed_hosts        = join(",", var.django_allowed_hosts)
  django_csrf_trusted_origins = join(",", var.django_csrf_trusted_origins)
  key_vault_secret_names = {
    django_secret_key       = "${local.base_name}-django-secret-key"
    postgres_admin_password = "${local.base_name}-postgres-admin-password"
    telegram_bot_token      = "${local.base_name}-telegram-bot-token"
    whatsapp_access_token   = "${local.base_name}-whatsapp-access-token"
  }

  container_environment_variables = {
    APPOINTMENT_NOTIFICATION_TIMEOUT_SECONDS = tostring(var.appointment_notification_timeout_seconds)
    APP_RELEASE_SHA                          = var.app_release_sha
    APP_TIME_ZONE                            = var.app_timezone
    CSRF_COOKIE_SECURE                       = "True"
    DJANGO_ALLOWED_HOSTS                     = local.django_allowed_hosts
    DJANGO_CSRF_TRUSTED_ORIGINS              = local.django_csrf_trusted_origins
    DJANGO_DEBUG                             = "False"
    DJANGO_LOG_LEVEL                         = var.django_log_level
    DJANGO_SETTINGS_MODULE                   = var.django_settings_module
    LOGIN_RATE_LIMIT                         = tostring(var.login_rate_limit)
    LOGIN_RATE_WINDOW_SECONDS                = tostring(var.login_rate_window_seconds)
    MFA_READY                                = "False"
    PORT                                     = tostring(var.container_app_target_port)
    POSTGRES_CONN_MAX_AGE                    = tostring(var.postgres_conn_max_age)
    POSTGRES_DB                              = var.postgres_database_name
    POSTGRES_HOST                            = module.postgres.fqdn
    POSTGRES_PORT                            = "5432"
    POSTGRES_SSLMODE                         = "require"
    POSTGRES_USER                            = var.postgres_admin_username
    RUN_COLLECTSTATIC                        = "True"
    SECURE_HSTS_INCLUDE_SUBDOMAINS           = "True"
    SECURE_HSTS_PRELOAD                      = "True"
    SECURE_HSTS_SECONDS                      = tostring(var.secure_hsts_seconds)
    SECURE_SSL_REDIRECT                      = "True"
    SESSION_COOKIE_AGE                       = tostring(var.session_cookie_age)
    SESSION_COOKIE_SECURE                    = "True"
    TELEGRAM_API_BASE_URL                    = var.telegram_api_base_url
    WHATSAPP_API_BASE_URL                    = var.whatsapp_api_base_url
    WHATSAPP_API_VERSION                     = var.whatsapp_api_version
    WHATSAPP_PHONE_NUMBER_ID                 = var.whatsapp_phone_number_id
  }

  migration_environment_variables = merge(
    local.container_environment_variables,
    {
      RUN_COLLECTSTATIC = "False"
    },
  )

  container_secret_environment_variables = {
    DJANGO_SECRET_KEY     = "django-secret-key"
    POSTGRES_PASSWORD     = "postgres-password"
    TELEGRAM_BOT_TOKEN    = "telegram-bot-token"
    WHATSAPP_ACCESS_TOKEN = "whatsapp-access-token"
  }

  postgres_firewall_rules = merge(
    var.postgres_firewall_allow_azure_services ? {
      allow_azure_services = {
        start_ip_address = "0.0.0.0"
        end_ip_address   = "0.0.0.0"
      }
    } : {},
    var.postgres_additional_firewall_rules,
  )
}
