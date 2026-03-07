# Technical Status Breakdown

## Application Runtime

- Django modular monolith with Django REST Framework
- server-rendered operational UI plus authenticated JSON APIs
- PostgreSQL persistence with custom user model and shop-scoped authorization

## Functional Domains

### Core and Access Control

- custom `accounts.User` with role-based access
- per-shop access assignments
- active shop middleware and role/queryset mixins
- login throttling and security event logging

### Shop Operations

- shop management for platform admins
- barber, product, sale, and expense CRUD with validation and soft delete
- sale item snapshotting and commission calculation

### Appointments and Customers

- `appointments` app with `Customer` and `Appointment` models
- internal CRUD flows for customer records and appointments
- public booking UI and public booking API endpoint
- public availability UI and public availability API endpoint
- WhatsApp and Telegram share helpers for availability and appointment messaging
- overlap validation for barber schedule conflicts
- demo seed data for upcoming appointments

### Reporting and Oversight

- dashboard metrics for sales, expenses, commissions, and appointment visibility
- daily, weekly, monthly, top barber, commission, expense, net revenue, shop comparison, and product performance reporting
- audit log and security event capture

## Delivery and Infrastructure

- single-VPS production baseline with host `nginx`, Docker Compose, PostgreSQL, and explicit deployment scripts
- backup, restore, rollback, and diagnostics scripts for operator workflows
- GitHub Actions CI for linting, tests, migrations, and container build validation
- explicit migration and `collectstatic` execution before the web service is restarted

## Verification State

- Django unit and API tests cover auth, authorization, barber/product/sale/expense rules, reporting, audit logging, and customer/appointment/public-booking flows
- browser smoke covers login and navigation across customer and appointment screens in addition to the original modules
- I could not execute the full Django test suite in this shell because the local virtualenv does not currently have Django installed
