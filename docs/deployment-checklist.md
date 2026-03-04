# Deployment Checklist

## Initial Azure Bootstrap

- Remote Terraform state storage account and blob container created
- `infra/env/dev` and `infra/env/prod` values reviewed
- First Terraform apply completed by a trusted operator
- If ACR was empty, initial Terraform apply used `deploy_application_resources=false` before the first image push
- Terraform outputs captured
- GitHub environments `dev` and `prod` created
- GitHub environment variables populated
- `prod` environment approval rules configured

## Before Each Release

- CI green
- Migration impact reviewed
- Rollback image tag known
- Key Vault and PostgreSQL status healthy
- No unresolved infrastructure drift

## During Release

- Image built and pushed to ACR
- Migration job updated to the same image tag
- Migration job completed successfully
- Web container updated to the same image tag
- `/healthz/` returned success

## After Release

- Login and dashboard manually verified
- Error logs reviewed
- Audit and security monitoring reviewed for anomalies
- Release record stored with image tag and commit SHA
