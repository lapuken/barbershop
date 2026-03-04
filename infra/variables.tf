variable "subscription_id" {
  description = "Azure subscription ID that hosts the environment."
  type        = string
}

variable "tenant_id" {
  description = "Microsoft Entra tenant ID."
  type        = string
}

variable "project_name" {
  description = "Logical application name used in resource naming."
  type        = string
  default     = "smartbarbershops"
}

variable "environment" {
  description = "Deployment environment name, such as dev or prod."
  type        = string
}

variable "github_environment" {
  description = "GitHub Environment name used for OIDC subject matching."
  type        = string
}

variable "github_repository" {
  description = "GitHub repository in owner/name format."
  type        = string
}

variable "name_suffix" {
  description = "Short lowercase suffix added to globally unique Azure resource names."
  type        = string
}

variable "location" {
  description = "Azure region."
  type        = string
}

variable "owner" {
  description = "Primary owner tag value."
  type        = string
}

variable "team" {
  description = "Owning team tag value."
  type        = string
}

variable "cost_center" {
  description = "Optional cost center tag."
  type        = string
  default     = ""
}

variable "additional_tags" {
  description = "Additional tags applied to all supported resources."
  type        = map(string)
  default     = {}
}

variable "acr_sku" {
  description = "Azure Container Registry SKU."
  type        = string
  default     = "Basic"
}

variable "log_analytics_retention_days" {
  description = "Log Analytics retention period."
  type        = number
  default     = 30
}

variable "key_vault_sku_name" {
  description = "Azure Key Vault SKU."
  type        = string
  default     = "standard"
}

variable "key_vault_purge_protection_enabled" {
  description = "Enable purge protection for Key Vault."
  type        = bool
  default     = true
}

variable "key_vault_soft_delete_retention_days" {
  description = "Soft delete retention for Key Vault."
  type        = number
  default     = 30
}

variable "postgres_version" {
  description = "Azure Database for PostgreSQL Flexible Server version."
  type        = string
  default     = "16"
}

variable "postgres_admin_username" {
  description = "PostgreSQL administrator username."
  type        = string
  default     = "smartbarberadmin"
}

variable "postgres_database_name" {
  description = "Application database name."
  type        = string
  default     = "smart_barber_shops"
}

variable "postgres_sku_name" {
  description = "PostgreSQL Flexible Server SKU."
  type        = string
}

variable "postgres_storage_mb" {
  description = "PostgreSQL allocated storage in MB."
  type        = number
  default     = 32768
}

variable "postgres_backup_retention_days" {
  description = "Backup retention period for PostgreSQL Flexible Server."
  type        = number
  default     = 7
}

variable "postgres_zone" {
  description = "Availability zone for PostgreSQL Flexible Server."
  type        = string
  default     = "1"
}

variable "postgres_conn_max_age" {
  description = "Django database connection reuse period."
  type        = number
  default     = 60
}

variable "postgres_firewall_allow_azure_services" {
  description = "Allow Azure services to reach PostgreSQL Flexible Server through the public endpoint."
  type        = bool
  default     = true
}

variable "postgres_public_network_access_enabled" {
  description = "Enable the PostgreSQL public endpoint. Set false only when private network connectivity is in place."
  type        = bool
  default     = true
}

variable "postgres_additional_firewall_rules" {
  description = "Additional PostgreSQL firewall rules keyed by rule name."
  type = map(object({
    start_ip_address = string
    end_ip_address   = string
  }))
  default = {}
}

variable "container_image" {
  description = "Full container image reference to deploy to the Container App."
  type        = string
}

variable "deploy_application_resources" {
  description = "When false, skip creating the web Container App and migration job during initial infrastructure bootstrap."
  type        = bool
  default     = true
}

variable "app_release_sha" {
  description = "Release identifier exposed to the runtime and health endpoint."
  type        = string
  default     = "bootstrap"
}

variable "container_app_target_port" {
  description = "Application port exposed by Gunicorn inside the container."
  type        = number
  default     = 8000
}

variable "container_app_allow_insecure_connections" {
  description = "Allow HTTP ingress to the Container App. Keep false for normal deployments."
  type        = bool
  default     = false
}

variable "container_app_external_enabled" {
  description = "Expose the Container App publicly. Set false for internal-only ingress when your network design supports it."
  type        = bool
  default     = true
}

variable "container_app_min_replicas" {
  description = "Minimum replica count."
  type        = number
  default     = 1
}

variable "container_app_max_replicas" {
  description = "Maximum replica count."
  type        = number
  default     = 3
}

variable "container_app_cpu" {
  description = "CPU cores allocated to the container."
  type        = number
  default     = 0.5
}

variable "container_app_memory" {
  description = "Container memory allocation."
  type        = string
  default     = "1Gi"
}

variable "container_app_revision_mode" {
  description = "Container Apps revision mode."
  type        = string
  default     = "Single"
}

variable "django_settings_module" {
  description = "Django settings module for the deployed runtime."
  type        = string
  default     = "config.settings.prod"
}

variable "django_allowed_hosts" {
  description = "Allowed hosts for Django."
  type        = list(string)
}

variable "django_csrf_trusted_origins" {
  description = "Trusted origins for Django CSRF validation."
  type        = list(string)
}

variable "django_log_level" {
  description = "Django application log level."
  type        = string
  default     = "INFO"
}

variable "app_timezone" {
  description = "Application default timezone."
  type        = string
  default     = "America/New_York"
}

variable "session_cookie_age" {
  description = "Session timeout in seconds."
  type        = number
  default     = 3600
}

variable "whatsapp_phone_number_id" {
  description = "Meta WhatsApp Cloud API phone number ID used for outbound confirmations."
  type        = string
  default     = ""
}

variable "whatsapp_api_base_url" {
  description = "Base URL for the WhatsApp Cloud API."
  type        = string
  default     = "https://graph.facebook.com"
}

variable "whatsapp_api_version" {
  description = "Graph API version used for WhatsApp messaging requests."
  type        = string
  default     = "v21.0"
}

variable "telegram_api_base_url" {
  description = "Base URL for Telegram Bot API requests."
  type        = string
  default     = "https://api.telegram.org"
}

variable "appointment_notification_timeout_seconds" {
  description = "HTTP timeout for outbound appointment confirmation requests."
  type        = number
  default     = 10
}

variable "login_rate_limit" {
  description = "Login retry threshold."
  type        = number
  default     = 5
}

variable "login_rate_window_seconds" {
  description = "Login retry window in seconds."
  type        = number
  default     = 900
}

variable "secure_hsts_seconds" {
  description = "HSTS max-age for the production runtime."
  type        = number
  default     = 31536000
}
