# Technical Status Breakdown

## Application Runtime

- Django modular monolith with Django REST Framework
- Server-rendered operational UI plus authenticated JSON APIs
- PostgreSQL persistence with custom user model and shop-scoped authorization

## Functional Domains

### Core and Access Control

- Custom `accounts.User` with role-based access
- Per-shop access assignments
- Active shop middleware and role/queryset mixins
- Login throttling and security event logging

### Shop Operations

- Shop management for platform admins
- Barber, product, sale, and expense CRUD with validation and soft delete
- Sale item snapshotting and commission calculation

### Appointments and Customers

- New `appointments` app with `Customer` and `Appointment` models
- Internal CRUD flows for customer records and appointments
- Public booking UI and public booking API endpoint
- Public availability UI and public availability API endpoint
- WhatsApp and Telegram share helpers for availability and appointment messaging
- Overlap validation for barber schedule conflicts
- Demo seed data for upcoming appointments

### Reporting and Oversight

- Dashboard metrics for sales, expenses, commissions, and now appointment visibility
- Daily, weekly, monthly, top barber, commission, expense, net revenue, shop comparison, and product performance reporting
- Audit log and security event capture

## Delivery and Infrastructure

- Terraform-managed Azure baseline for Container Apps, ACR, PostgreSQL Flexible Server, Key Vault, monitoring, and identities
- GitHub Actions OIDC for Terraform and deploy automation
- Explicit migration job execution before web revision rollout
- New Terraform toggles for Container App external ingress and PostgreSQL public-network exposure

## Verification State

- Django unit/API tests cover auth, authorization, barber/product/sale/expense rules, reporting, audit logging, and now customer/appointment/public-booking flows
- Browser smoke covers login and navigation across customer and appointment screens in addition to the original modules
- I could not execute the full Django test suite in this shell because the local virtualenv does not currently have Django installed
