# Operations Runbook

## Deploy a New Version

1. Confirm `CI` is green on the target commit.
2. For `dev`, run or allow `Deploy Dev`.
3. For `prod`, trigger `Deploy Prod` and complete any GitHub environment approvals.
4. Verify:
   - migration job succeeded
   - Container App revision updated
   - `/healthz/` returns `200`
   - login and dashboard load correctly

## Rotate a Secret

### Django secret key, PostgreSQL password, or messaging provider tokens

1. Use [set-keyvault-secret.sh](/home/khido/projects/barbershop/scripts/azure/set-keyvault-secret.sh) or the Azure portal/CLI to write the new secret value into Key Vault.
2. If rotating the PostgreSQL admin password, update the password on the PostgreSQL server first.
3. For customer booking confirmations, the relevant Key Vault secret names are exposed through Terraform outputs:
   - `telegram_bot_token`
   - `whatsapp_access_token`
4. Restart the Container App revision so the new secret version is resolved:

```bash
az containerapp revision restart \
  --resource-group <resource-group> \
  --name <container-app-name> \
  --revision <revision-name>
```

5. Re-run the migration job if the password is used there as well.

## Enable WhatsApp or Telegram Booking Confirmations

1. Apply Terraform so the Container App has the new secret references and runtime variables.
2. Set the Key Vault placeholder secrets to their real provider values:

```bash
./scripts/azure/set-keyvault-secret.sh <key-vault-name> <telegram-bot-token-secret-name> <telegram-bot-token>
./scripts/azure/set-keyvault-secret.sh <key-vault-name> <whatsapp-access-token-secret-name> <whatsapp-access-token>
```

3. Set `whatsapp_phone_number_id` in Terraform or the `TF_WHATSAPP_PHONE_NUMBER_ID` GitHub environment variable if WhatsApp delivery should be active.
4. Restart the Container App revision so the updated secret versions are loaded.
5. Create or confirm a test appointment and verify an `AppointmentNotification` record is written in Django admin.

## Run Migrations Manually

```bash
./scripts/azure/run-migration-job.sh <resource-group> <migration-job-name> <image-reference>
```

Use the same image tag you intend to deploy to the web application.

## Roll Back the Application

1. Identify the previous known-good ACR image tag.
2. Update the migration job image only if you need the older code path for later database tasks.
3. Update the web app image:

```bash
az containerapp update \
  --resource-group <resource-group> \
  --name <container-app-name> \
  --image <acr-login-server>/smartbarber/web:<previous-tag>
```

4. Verify `/healthz/`.

If the failed release contained incompatible schema changes, do not rely on image rollback alone.

## Scale the App

Infrastructure-managed path:

1. Update `TF_VAR_container_app_min_replicas` and `TF_VAR_container_app_max_replicas`.
2. Run `Terraform Apply`.

Emergency runtime path:

```bash
az containerapp update \
  --resource-group <resource-group> \
  --name <container-app-name> \
  --min-replicas 2 \
  --max-replicas 6
```

Record the emergency change and reconcile it back into Terraform.

## Move to a More Private Network Posture

Infrastructure-managed path:

1. Set `container_app_external_enabled=false` if the web workload should be internal-only.
2. Set `postgres_public_network_access_enabled=false` once private connectivity to PostgreSQL exists.
3. Run `Terraform Apply`.

Do not disable public ingress or PostgreSQL public networking until the replacement network path has been validated end to end.

## Troubleshoot a Failed Deployment

1. Check the GitHub Actions job logs.
2. Inspect the migration job execution:

```bash
az containerapp job execution list \
  --resource-group <resource-group> \
  --name <migration-job-name> \
  --output table
```

3. Inspect the web app revision state:

```bash
az containerapp revision list \
  --resource-group <resource-group> \
  --name <container-app-name> \
  --output table
```

4. Query the health endpoint and review logs in Log Analytics.
5. If secret resolution failed, verify:
   - Key Vault secret exists
   - runtime identity still has `Key Vault Secrets User`
   - the Container App secret references still point to the correct secret IDs

## Troubleshoot PostgreSQL Connectivity

1. Confirm the server FQDN and database name match the Container App environment variables.
2. Confirm `POSTGRES_SSLMODE=require`.
3. Confirm the Azure services firewall rule or your approved source IP rule is present.
4. Validate password state in Key Vault and on the PostgreSQL server.

## Recovery Considerations

- Ensure PostgreSQL backups and retention settings meet business needs before production use.
- Treat Terraform state as a recovery-critical system asset.
- Keep at least one previous application image tag available in ACR.
