# Go-Live Initialization

Migrations create the schema. The go-live initializer creates the minimum business records the app needs for first production use.

Use the JSON-driven loader:

```bash
./scripts/initialize-golive.sh /opt/smartbarber/env/golive-init.json
```

Keep the JSON file outside Git because it contains real user passwords. Start from [`ops/golive-init.example.json`](../ops/golive-init.example.json).

## Seeded Tables

| Database table | Go-live requirement | Required fields on first initialization | Optional fields | Notes |
| --- | --- | --- | --- | --- |
| `accounts_user` (`platform_admin`) | Required | `username`, `email`, `password` | `phone`, `must_change_password`, `is_active` | The initializer creates or updates one active platform admin with role `platform_admin`, `is_staff=true`, and `is_superuser=true`. |
| `shops_shop` | At least 1 active shop | `branch_code`, `name`, `address`, `phone` | `whatsapp_number`, `telegram_handle`, `currency`, `timezone`, `is_active` | `branch_code` is the stable lookup key for reruns. |
| `accounts_user` (`shops[].users[]`) | At least 1 active operator per active shop | `username`, `email`, `password`, `role` | `phone`, `must_change_password`, `is_active`, `shop_access_is_active` | Valid roles here are `shop_owner`, `shop_manager`, `cashier`, or `barber`. Each active shop must end up with at least one active `shop_owner`, `shop_manager`, or `cashier`. |
| `accounts_usershopaccess` | Required for every non-platform-admin shop user | Implied by each `shops[].users[]` entry | `shop_access_is_active` | Created automatically by the initializer when a shop user is attached to a shop. |
| `barbers_barber` | At least 1 active barber per active shop | `full_name` | `employee_code`, `phone`, `commission_rate`, `is_active` | Required so the sales and appointment flows can operate on day one. |
| `products_product` | Optional | `sku`, `name`, `category`, `sale_price` | `cost_price`, `is_active` | Only required if the branch will sell stocked products immediately at go-live. |

## Schema-Only Tables

These tables are created by migrations but do not need seed rows for go-live:

| Database table | How rows are created |
| --- | --- |
| `appointments_customer` | Created when real customers are entered. |
| `appointments_appointment` | Created when appointments are booked. |
| `appointments_appointmentnotification` | Created automatically when confirmation delivery runs. |
| `sales_sale` | Created when daily sales are recorded. |
| `sales_saleitem` | Created together with each sale. |
| `expenses_expense` | Created when expenses are logged. |
| `audit_auditlog` | Created by normal application activity. |
| `audit_securityevent` | Created by authentication and security events. |

## JSON Field Map

| JSON path | Underlying table(s) | Required fields | Optional fields |
| --- | --- | --- | --- |
| `platform_admin` | `accounts_user` | `username`, `email`, `password` | `phone`, `must_change_password`, `is_active` |
| `shops[]` | `shops_shop` | `branch_code`, `name`, `address`, `phone` | `whatsapp_number`, `telegram_handle`, `currency`, `timezone`, `is_active` |
| `shops[].users[]` | `accounts_user`, `accounts_usershopaccess` | `username`, `email`, `password`, `role` | `phone`, `must_change_password`, `is_active`, `shop_access_is_active` |
| `shops[].barbers[]` | `barbers_barber` | `full_name` | `employee_code`, `phone`, `commission_rate`, `is_active` |
| `shops[].products[]` | `products_product` | `sku`, `name`, `category`, `sale_price` | `cost_price`, `is_active` |

## Initial Seeding Required From Tester

Use this checklist when the tester or go-live coordinator is collecting the real production values that must go into `golive-init.json`.

| Tester must provide | JSON section | Minimum count | Required fields | Optional fields | Notes |
| --- | --- | --- | --- | --- | --- |
| Platform admin login | `platform_admin` | 1 | `username`, `email`, `password` | `phone` | This is the system-wide admin account. Use a real email and a strong temporary password. |
| Shop or branch record | `shops[]` | 1 per active shop | `branch_code`, `name`, `address`, `phone` | `whatsapp_number`, `telegram_handle`, `currency`, `timezone` | Keep `branch_code` stable because reruns match by it. |
| Shop staff login | `shops[].users[]` | At least 1 active `shop_owner`, `shop_manager`, or `cashier` per active shop | `username`, `email`, `password`, `role` | `phone` | Add extra users only if they need access on day one. |
| Barber profile | `shops[].barbers[]` | At least 1 active barber per active shop | `full_name` | `employee_code`, `phone`, `commission_rate` | Required for appointment and sales flows to work on day one. |
| Product catalog | `shops[].products[]` | Optional | `sku`, `name`, `category`, `sale_price` | `cost_price` | Only collect this if the shop will sell stocked products immediately at go-live. |

Before the file is approved, the tester should also confirm that all usernames, branch codes, phone numbers, and email addresses are final production values and that every seeded human account will be forced to change the temporary password at first login.

## Operator Workflow

```bash
cp /opt/smartbarber/app/ops/golive-init.example.json /opt/smartbarber/env/golive-init.json
nano /opt/smartbarber/env/golive-init.json
cd /opt/smartbarber/app
./scripts/initialize-golive.sh /opt/smartbarber/env/golive-init.json
```

If you intentionally need to force the file's passwords onto existing users, rerun with:

```bash
./scripts/initialize-golive.sh /opt/smartbarber/env/golive-init.json --reset-passwords
```

## Production Runbook

Use this runbook when you are creating the first real users for a production branch or replacing a controlled batch of temporary passwords.

### 1. Prepare the server-side JSON file

Create the file on the production host and keep it outside Git:

```bash
sudo install -d -m 750 /opt/smartbarber/env
sudo cp /opt/smartbarber/app/ops/golive-init.example.json /opt/smartbarber/env/golive-init.json
sudo chmod 600 /opt/smartbarber/env/golive-init.json
sudo nano /opt/smartbarber/env/golive-init.json
```

Use this structure and replace every placeholder value before you run anything:

```json
{
  "platform_admin": {
    "username": "platformadmin",
    "email": "admin@machinjiri.net",
    "password": "TemporaryAdminPass123!",
    "phone": "+265-999-000-001",
    "must_change_password": true
  },
  "shops": [
    {
      "branch_code": "BLZ-001",
      "name": "Machinjiri Barber Lounge",
      "address": "101 Example Road, Blantyre",
      "phone": "+265-999-000-010",
      "whatsapp_number": "265999000010",
      "telegram_handle": "machinjiri_barber_lounge",
      "currency": "MWK",
      "timezone": "Africa/Blantyre",
      "users": [
        {
          "username": "owner-machinjiri",
          "email": "owner@machinjiri.net",
          "password": "TemporaryOwnerPass123!",
          "role": "shop_owner",
          "phone": "+265-999-000-011",
          "must_change_password": true
        },
        {
          "username": "cashier-machinjiri",
          "email": "cashier@machinjiri.net",
          "password": "TemporaryCashierPass123!",
          "role": "cashier",
          "phone": "+265-999-000-012",
          "must_change_password": true
        }
      ],
      "barbers": [
        {
          "full_name": "Alex Banda",
          "employee_code": "BR-001",
          "phone": "+265-999-000-021",
          "commission_rate": "45.00"
        }
      ],
      "products": []
    }
  ]
}
```

Minimum operator rules:

- Use strong temporary passwords with at least 12 characters.
- Set `must_change_password: true` for every human account.
- Keep usernames stable because reruns match existing users by `username`.
- Remove example emails, phone numbers, and passwords before saving the file.

### 2. Run the initializer on the production host

Run the reviewed initializer from the app checkout:

```bash
cd /opt/smartbarber/app
./scripts/initialize-golive.sh /opt/smartbarber/env/golive-init.json
```

Expected result:

- Missing users, shops, shop access rows, barbers, and products are created.
- Existing users are updated by `username`.
- Existing passwords stay unchanged unless you explicitly pass `--reset-passwords`.

### 3. Verify the result

Check the host, then verify with an actual login:

```bash
cd /opt/smartbarber/app
./scripts/healthcheck.sh local
docker compose --env-file /opt/smartbarber/env/.env ps
docker compose --env-file /opt/smartbarber/env/.env logs --tail=100 web
```

Then confirm all of the following in the browser:

- The new username can sign in with the temporary password.
- The app immediately redirects that user to `/accounts/password-change/`.
- After the password change, the user can reach the dashboard and shop selector normally.

### 4. Use `--reset-passwords` only when you mean it

Only rerun with `--reset-passwords` when you intentionally want the JSON file to overwrite the passwords of already-existing users:

```bash
cd /opt/smartbarber/app
./scripts/initialize-golive.sh /opt/smartbarber/env/golive-init.json --reset-passwords
```

Do not use this for normal reruns. It is a deliberate password reset operation.

### 5. Day-2 user management after go-live

Use the go-live initializer for the first real production load or a controlled batch update. For one-off user additions later, use Django admin:

- Create the `User` record with the correct role.
- Set a temporary strong password.
- Set `must_change_password = true`.
- Create the corresponding `UserShopAccess` row for every non-platform-admin user.

## Password Rotation Guidance

- Treat every password in the go-live JSON as temporary and deliver it to the user through a separate secure channel.
- Set `must_change_password: true` for every seeded human account so the app redirects that user to `/accounts/password-change/` immediately after login.
- Do not rerun the initializer with `--reset-passwords` unless you intentionally want to overwrite an existing user's password with the value in the JSON file.
- If a user cannot sign in with the temporary password, verify that the initializer was actually run with the intended JSON and that the username exists in the live database before resetting anything.
- If a user forgets the rotated password later, use the normal password reset workflow from the login page.

## Idempotency Rules

- Shops are matched by `branch_code`.
- Shop users are matched by `username`.
- Shop access rows are matched by `(user, shop)`.
- Barbers are matched by `employee_code` when present, otherwise `(shop, full_name)`.
- Products are matched by `(shop, sku)`.
- Existing passwords are left unchanged unless `--reset-passwords` is supplied.
