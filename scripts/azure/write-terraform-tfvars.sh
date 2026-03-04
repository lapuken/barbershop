#!/usr/bin/env bash
set -euo pipefail

output_path="${1:-infra/generated.auto.tfvars}"

require_var() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: ${name}" >&2
    exit 1
  fi
}

render_list() {
  local raw="$1"
  local result=""
  IFS=',' read -r -a items <<<"${raw}"
  for item in "${items[@]}"; do
    local trimmed="${item#"${item%%[![:space:]]*}"}"
    trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"
    [[ -z "${trimmed}" ]] && continue
    result="${result}  \"${trimmed}\",\n"
  done
  printf "%b" "${result}"
}

require_var AZURE_SUBSCRIPTION_ID
require_var AZURE_TENANT_ID
require_var TF_VAR_environment
require_var TF_VAR_location
require_var TF_VAR_name_suffix
require_var TF_VAR_owner
require_var TF_VAR_team
require_var TF_VAR_github_environment
require_var TF_VAR_github_repository
require_var TF_VAR_postgres_sku_name
require_var TF_VAR_container_image
require_var TF_VAR_django_allowed_hosts
require_var TF_VAR_django_csrf_trusted_origins

cat >"${output_path}" <<EOF
subscription_id = "${AZURE_SUBSCRIPTION_ID}"
tenant_id       = "${AZURE_TENANT_ID}"
project_name    = "${TF_VAR_project_name:-smartbarbershops}"
environment     = "${TF_VAR_environment}"
github_environment = "${TF_VAR_github_environment}"
github_repository  = "${TF_VAR_github_repository}"
name_suffix        = "${TF_VAR_name_suffix}"
location           = "${TF_VAR_location}"
owner              = "${TF_VAR_owner}"
team               = "${TF_VAR_team}"
cost_center        = "${TF_VAR_cost_center:-}"
acr_sku            = "${TF_VAR_acr_sku:-Basic}"
log_analytics_retention_days = ${TF_VAR_log_analytics_retention_days:-30}
key_vault_purge_protection_enabled = ${TF_VAR_key_vault_purge_protection_enabled:-true}
postgres_sku_name              = "${TF_VAR_postgres_sku_name}"
postgres_storage_mb            = ${TF_VAR_postgres_storage_mb:-32768}
postgres_backup_retention_days = ${TF_VAR_postgres_backup_retention_days:-7}
postgres_zone                  = "${TF_VAR_postgres_zone:-1}"
postgres_database_name         = "${TF_VAR_postgres_database_name:-smart_barber_shops}"
container_image                = "${TF_VAR_container_image}"
app_release_sha                = "${TF_VAR_app_release_sha:-bootstrap}"
container_app_target_port      = ${TF_VAR_container_app_target_port:-8000}
container_app_min_replicas     = ${TF_VAR_container_app_min_replicas:-1}
container_app_max_replicas     = ${TF_VAR_container_app_max_replicas:-3}
container_app_cpu              = ${TF_VAR_container_app_cpu:-0.5}
container_app_memory           = "${TF_VAR_container_app_memory:-1Gi}"
whatsapp_phone_number_id       = "${TF_VAR_whatsapp_phone_number_id:-}"
app_timezone                   = "${TF_VAR_app_timezone:-America/New_York}"
session_cookie_age             = ${TF_VAR_session_cookie_age:-3600}
login_rate_limit               = ${TF_VAR_login_rate_limit:-5}
login_rate_window_seconds      = ${TF_VAR_login_rate_window_seconds:-900}
secure_hsts_seconds            = ${TF_VAR_secure_hsts_seconds:-31536000}
django_allowed_hosts = [
$(render_list "${TF_VAR_django_allowed_hosts}")]
django_csrf_trusted_origins = [
$(render_list "${TF_VAR_django_csrf_trusted_origins}")]
EOF
