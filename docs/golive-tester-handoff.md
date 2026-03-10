# Go-Live Tester Handoff Sheet

Use this one-page sheet to collect the minimum production seed data before the operator runs `./scripts/initialize-golive.sh`.

Detailed field definitions and the full production runbook live in [`docs/golive-initialization.md`](./golive-initialization.md).

## Handoff Summary

| Item | Value |
| --- | --- |
| Target go-live date | `YYYY-MM-DD` |
| Prepared by tester | `name / role` |
| Reviewed by operator | `name / role` |
| Password delivery method | `secure channel` |

## Required Seed Inputs

| Seed area | JSON section | Minimum required | Tester must provide |
| --- | --- | --- | --- |
| Platform admin login | `platform_admin` | 1 account | `username`, `email`, temporary `password`, optional `phone` |
| Shop or branch record | `shops[]` | 1 row per active shop | `branch_code`, `name`, `address`, `phone`, optional `whatsapp_number`, `telegram_handle`, `currency`, `timezone` |
| Shop staff login | `shops[].users[]` | At least 1 active `shop_owner`, `shop_manager`, or `cashier` per active shop | `username`, `email`, temporary `password`, `role`, optional `phone` |
| Barber profile | `shops[].barbers[]` | At least 1 active barber per active shop | `full_name`, optional `employee_code`, `phone`, `commission_rate` |
| Product catalog | `shops[].products[]` | Optional | `sku`, `name`, `category`, `sale_price`, optional `cost_price` |

## Tester Sign-Off Checklist

- All usernames and `branch_code` values are final production values.
- Every active shop has at least one active operator with role `shop_owner`, `shop_manager`, or `cashier`.
- Every active shop has at least one active barber profile.
- All temporary passwords are strong and will be shared through a separate secure channel.
- Every seeded human account will be forced to change password at first login.
- Emails, phone numbers, and shop names are real production values, not demo placeholders.

## Delivery Notes

- Start from [`ops/golive-init.example.json`](../ops/golive-init.example.json).
- The completed JSON file must stay outside Git, for example `/opt/smartbarber/env/golive-init.json`.
- Normal reruns must not use `--reset-passwords` unless the operator is intentionally overwriting existing passwords.
