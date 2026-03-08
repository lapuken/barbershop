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

## Idempotency Rules

- Shops are matched by `branch_code`.
- Shop users are matched by `username`.
- Shop access rows are matched by `(user, shop)`.
- Barbers are matched by `employee_code` when present, otherwise `(shop, full_name)`.
- Products are matched by `(shop, sku)`.
- Existing passwords are left unchanged unless `--reset-passwords` is supplied.
