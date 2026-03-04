# Architecture

The authoritative deployment architecture is documented in [docs/architecture.md](/home/khido/projects/barbershop/docs/architecture.md).

At a high level, Smart Barber Shops runs as a containerized Django application on Azure Container Apps, stores images in Azure Container Registry, uses Azure Database for PostgreSQL Flexible Server for persistent data, resolves runtime secrets from Azure Key Vault via managed identity, and uses GitHub Actions with OIDC for infrastructure and release automation.
