#!/usr/bin/env bash
set -euo pipefail

key_vault_name="$1"
secret_name="$2"
secret_value="$3"

az keyvault secret set \
  --vault-name "${key_vault_name}" \
  --name "${secret_name}" \
  --value "${secret_value}" \
  --output none

echo "Updated secret ${secret_name} in Key Vault ${key_vault_name}."
