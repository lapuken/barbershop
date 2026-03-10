# User Roles Guide

This guide explains the user roles in Smart Barber Shops, what each role can do, and the limits that apply in the current app.

## How Access Works

- Most staff features require sign-in.
- Access is controlled by both `role` and `shop assignment`.
- `platform_admin` users can work across all shops and do not need a shop assignment.
- All other roles must be assigned to at least one active shop to use shop-scoped pages.
- Most non-admin data is limited to the user’s assigned shops, and many web screens use the current active shop.
- The app uses soft deletion for business records. In practice, "delete" actions archive records instead of permanently removing them.

## Public Access

These features do not require a staff account:

- Public booking page
- Public availability page
- Public booking API
- Public availability API

These are intended for customers, not internal staff workflows.

## Role Summary

| Role | Main purpose | Scope |
| --- | --- | --- |
| Platform Admin | Full platform oversight | All shops |
| Shop Owner | Runs one or more assigned shops | Assigned shops |
| Shop Manager | Manages daily operations | Assigned shops |
| Cashier / Front Desk | Handles bookings, sales, and expense entry | Assigned shops |
| Barber | Read-only operational visibility in the web app | Assigned shops |

## What Every Signed-In User Can Do

Any authenticated user can access these areas, subject to shop scope:

- Dashboard
- Reports
- Audit log
- Settings
- Shop selector

In the web UI, any signed-in user with an active shop can also open list pages for:

- Customers
- Appointments
- Barbers
- Products
- Sales
- Expenses

Important:

- Opening a list page does not mean the user can create, edit, or archive records there.
- The API is stricter than the web UI for some roles, especially the `barber` role.

## Role Details

### Platform Admin

Platform admins have full access across the application.

Can do:

- View and switch across all shops
- Create and update shops
- View, create, edit, and archive barbers
- View, create, edit, and archive products
- View, create, edit, and archive customers
- View, create, edit, and archive appointments
- View, create, edit, and archive sales
- View, create, edit, and archive expenses
- View dashboard, reports, settings, and audit logs across the platform
- Use all authenticated API endpoints across all shops

Cannot do:

- They do not use per-shop access assignments in normal operation

### Shop Owner

Shop owners are full operators inside their assigned shops.

Can do:

- View dashboard, reports, settings, audit logs, and switch between assigned shops
- View customer, appointment, barber, product, sale, and expense lists for the active shop
- Create, edit, and archive barbers
- Create, edit, and archive products
- Create, edit, and archive customers
- Create, edit, and archive appointments
- Create, edit, and archive sales
- Create, edit, and archive expenses
- Use management and sales APIs for assigned shops

Cannot do:

- Create or edit shops
- Access shops that are not assigned to them

### Shop Manager

Shop managers currently have the same application permissions as shop owners.

Can do:

- Everything a shop owner can do inside assigned shops

Cannot do:

- Create or edit shops
- Access shops that are not assigned to them

### Cashier / Front Desk

Cashiers can run day-to-day front-desk operations, but they do not have management rights.

Can do:

- View dashboard, reports, settings, audit logs, and switch between assigned shops
- View customer, appointment, barber, product, sale, and expense lists for the active shop
- Create and edit customers
- Create and edit appointments
- Create and edit sales
- Create and edit expenses
- Use sales-entry APIs for customers, appointments, sales, and expenses in assigned shops

Cannot do:

- Create, edit, or archive barbers
- Create, edit, or archive products
- Archive customers
- Archive appointments
- Archive sales
- Archive expenses
- Create or edit shops
- Access shops that are not assigned to them

### Barber

The barber role is mostly read-only in the current web app.

Can do:

- View dashboard, reports, settings, audit logs, and switch between assigned shops
- Open list pages for customers, appointments, barbers, products, sales, and expenses for the active shop in the web UI

Cannot do:

- Create, edit, or archive shops
- Create, edit, or archive barbers
- Create, edit, or archive products
- Create, edit, or archive customers
- Create, edit, or archive appointments
- Create, edit, or archive sales
- Create, edit, or archive expenses
- Use the operational create/update/delete APIs for barbers, products, customers, appointments, sales, or expenses
- Access shops that are not assigned to them

## Permission Matrix

| Area | Platform Admin | Shop Owner | Shop Manager | Cashier | Barber |
| --- | --- | --- | --- | --- | --- |
| Dashboard, reports, settings, audit | Yes | Yes | Yes | Yes | Yes |
| Switch active shop | Yes | Yes | Yes | Yes | Yes |
| View shop list in main UI | Yes | No | No | No | No |
| Create or edit shops | Yes | No | No | No | No |
| View operational list pages in web UI | Yes | Yes | Yes | Yes | Yes |
| Create or edit barbers | Yes | Yes | Yes | No | No |
| Archive barbers | Yes | Yes | Yes | No | No |
| Create or edit products | Yes | Yes | Yes | No | No |
| Archive products | Yes | Yes | Yes | No | No |
| Create or edit customers | Yes | Yes | Yes | Yes | No |
| Archive customers | Yes | Yes | Yes | No | No |
| Create or edit appointments | Yes | Yes | Yes | Yes | No |
| Archive appointments | Yes | Yes | Yes | No | No |
| Create or edit sales | Yes | Yes | Yes | Yes | No |
| Archive sales | Yes | Yes | Yes | No | No |
| Create or edit expenses | Yes | Yes | Yes | Yes | No |
| Archive expenses | Yes | Yes | Yes | No | No |

## Important Notes

- Shop owners and shop managers currently behave the same in the permission model.
- Barbers can view more in the web UI than they can through the operational APIs.
- User account creation, role assignment, and shop assignment are not handled through a dedicated end-user screen in the main app UI today.
- If a non-admin user has no active shop assignment, shop-scoped pages will not work until access is assigned.

## How To Create Users And Assign Roles

There are two supported ways to create users today:

- Use the go-live initializer for controlled batch creation or first production setup.
- Use Django admin for one-off additions after go-live.

General provisioning rules:

- `platform_admin` users do not get `UserShopAccess` rows.
- Every non-`platform_admin` user must have at least one active `UserShopAccess` row.
- Set a strong temporary password and `must_change_password = true` for normal human users.
- `is_superuser` should only be `true` for `platform_admin`.
- `is_staff` should be `true` for `platform_admin`, `shop_owner`, and `shop_manager`.
- `is_staff` should be `false` for `cashier` and `barber`.

### Provisioning Matrix

| Role | Go-live JSON location | `role` value | `is_staff` | `is_superuser` | Shop access required |
| --- | --- | --- | --- | --- | --- |
| Platform Admin | `platform_admin` | `platform_admin` | Yes | Yes | No |
| Shop Owner | `shops[].users[]` | `shop_owner` | Yes | No | Yes |
| Shop Manager | `shops[].users[]` | `shop_manager` | Yes | No | Yes |
| Cashier / Front Desk | `shops[].users[]` | `cashier` | No | No | Yes |
| Barber | `shops[].users[]` | `barber` | No | No | Yes |

### Platform Admin

Use this role for a system-wide administrator who can work across all shops.

Go-live initializer:

1. Add or update the top-level `platform_admin` object in `golive-init.json`.
2. Set `username`, `email`, `password`, and optional `phone`.
3. Use `must_change_password: true` for a real human admin account.
4. Run `./scripts/initialize-golive.sh /path/to/golive-init.json`.
5. Do not add a `UserShopAccess` entry for this user.

Example:

```json
"platform_admin": {
  "username": "platformadmin",
  "email": "admin@example.com",
  "password": "TemporaryAdminPass123!",
  "phone": "+265-999-000-001",
  "must_change_password": true
}
```

Django admin:

1. Open `/admin/` and create a new `User`.
2. Set `username`, `email`, `role = platform_admin`, and a strong temporary password.
3. Set `is_active = true`, `is_staff = true`, and `is_superuser = true`.
4. Set `must_change_password = true`.
5. Save the user.
6. Do not create a `UserShopAccess` row for this user.

### Shop Owner

Use this role for a branch owner who needs full operational control inside assigned shops.

Go-live initializer:

1. Add the user under the correct shop's `shops[].users[]` list.
2. Set `"role": "shop_owner"`.
3. Set the normal account fields such as `username`, `email`, `password`, and optional `phone`.
4. Leave `shop_access_is_active` as `true` unless you intentionally want inactive access.
5. Run `./scripts/initialize-golive.sh /path/to/golive-init.json`.

Example:

```json
{
  "username": "owner-downtown",
  "email": "owner@example.com",
  "password": "TemporaryOwnerPass123!",
  "role": "shop_owner",
  "phone": "+265-999-000-010",
  "must_change_password": true
}
```

Django admin:

1. Open `/admin/` and create a new `User`.
2. Set `role = shop_owner`.
3. Set `is_active = true`, `is_staff = true`, and `is_superuser = false`.
4. Set a strong temporary password and `must_change_password = true`.
5. Save the user.
6. Create one or more `UserShopAccess` rows for the shops this owner should access.
7. Set each `UserShopAccess.is_active = true`.

### Shop Manager

Use this role for a daily operations manager. In the current app, this role has the same permissions as `shop_owner`.

Go-live initializer:

1. Add the user under the correct shop's `shops[].users[]` list.
2. Set `"role": "shop_manager"`.
3. Fill in `username`, `email`, `password`, and optional `phone`.
4. Keep `shop_access_is_active` set to `true` unless you need disabled access.
5. Run `./scripts/initialize-golive.sh /path/to/golive-init.json`.

Example:

```json
{
  "username": "manager-downtown",
  "email": "manager@example.com",
  "password": "TemporaryManagerPass123!",
  "role": "shop_manager",
  "phone": "+265-999-000-011",
  "must_change_password": true
}
```

Django admin:

1. Open `/admin/` and create a new `User`.
2. Set `role = shop_manager`.
3. Set `is_active = true`, `is_staff = true`, and `is_superuser = false`.
4. Set a strong temporary password and `must_change_password = true`.
5. Save the user.
6. Create one or more active `UserShopAccess` rows for the shops this manager should use.

### Cashier / Front Desk

Use this role for front-desk staff who handle appointments, sales, customers, and expense entry.

Go-live initializer:

1. Add the user under the correct shop's `shops[].users[]` list.
2. Set `"role": "cashier"`.
3. Fill in `username`, `email`, `password`, and optional `phone`.
4. Keep `shop_access_is_active` set to `true` unless you intentionally want inactive access.
5. Run `./scripts/initialize-golive.sh /path/to/golive-init.json`.

Example:

```json
{
  "username": "cashier-downtown",
  "email": "cashier@example.com",
  "password": "TemporaryCashierPass123!",
  "role": "cashier",
  "phone": "+265-999-000-012",
  "must_change_password": true
}
```

Django admin:

1. Open `/admin/` and create a new `User`.
2. Set `role = cashier`.
3. Set `is_active = true`, `is_staff = false`, and `is_superuser = false`.
4. Set a strong temporary password and `must_change_password = true`.
5. Save the user.
6. Create one or more active `UserShopAccess` rows for the shops this cashier should use.

### Barber

Use this role for a barber who needs sign-in access with read-only operational visibility.

Go-live initializer:

1. Add the login account under the correct shop's `shops[].users[]` list.
2. Set `"role": "barber"`.
3. Fill in `username`, `email`, `password`, and optional `phone`.
4. Keep `shop_access_is_active` set to `true` unless you intentionally want inactive access.
5. Run `./scripts/initialize-golive.sh /path/to/golive-init.json`.

Example:

```json
{
  "username": "barber-downtown",
  "email": "barber@example.com",
  "password": "TemporaryBarberPass123!",
  "role": "barber",
  "phone": "+265-999-000-013",
  "must_change_password": true
}
```

Django admin:

1. Open `/admin/` and create a new `User`.
2. Set `role = barber`.
3. Set `is_active = true`, `is_staff = false`, and `is_superuser = false`.
4. Set a strong temporary password and `must_change_password = true`.
5. Save the user.
6. Create one or more active `UserShopAccess` rows for the shops this barber should access.

Important:

- A `barber` login user is separate from the `Barber` business record used in scheduling and operational screens.
- If the person should appear in barber lists, appointment booking, or sale attribution, also create or update the matching `Barber` record for that shop.
