# Acceptance Tests

## Quick Local Execution

1. Bootstrap the local environment:

```bash
./scripts/bootstrap-local.sh
source .venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

2. Sign in with demo credentials:
   - `platformadmin / ChangeMe12345!`
   - `owner1 / ChangeMe12345!`
   - `manager1 / ChangeMe12345!`
   - `cashier1 / ChangeMe12345!`

3. Use these local URLs after `runserver` starts:
   - `http://127.0.0.1:8000/`
   - `http://127.0.0.1:8000/accounts/login/`

4. Run the automated checks:

```bash
python manage.py test
ruff check .
black --check .
```

5. Run the browser smoke suite against the running app:

```bash
pip install -r requirements-smoke.txt
python -m playwright install chromium
APP_BASE_URL=http://127.0.0.1:8000 ./scripts/run-browser-smoke.sh
```

If the app was started with `./scripts/bootstrap-docker.sh`, use:

```bash
APP_BASE_URL=http://127.0.0.1:8000 ./scripts/run-browser-smoke.sh
```

For the Docker pilot path, run this verifier before sharing the URL:

```bash
./scripts/verify-docker-pilot.sh
```

## Major Requirement Verification

1. Authentication and authorization
   - Log in with a valid active user and confirm dashboard access.
   - Attempt invalid credentials repeatedly and confirm throttling message appears.
   - Attempt cross-shop record access and confirm `403` or scoped invisibility.

2. Barber management
   - Create a barber with a valid commission rate.
   - Attempt duplicate barber creation in the same shop and confirm rejection.
   - Attempt commission values outside `0-100` and confirm validation.

3. Product management
   - Create a product with a unique SKU in the selected shop.
   - Attempt duplicate SKU creation in the same shop and confirm rejection.
   - Mark a product inactive and confirm it cannot be used on new sales.

4. Customer management
   - Create a customer with at least one contact method.
   - Attempt customer creation without phone, email, or Telegram chat ID and confirm rejection.
   - Confirm customer records stay scoped to the selected shop.

5. Appointment workflow
   - Create an appointment for a valid customer and barber in the selected shop.
   - Attempt an overlapping appointment for the same barber and confirm rejection.
   - Submit a public booking request and confirm it lands as a `requested` appointment.
   - Confirm a requested appointment and verify an `AppointmentNotification` record is written.
   - With WhatsApp credentials configured, confirm a customer with a phone number receives a WhatsApp booking confirmation.
   - With Telegram credentials configured, confirm a customer with a Telegram chat ID receives a Telegram booking confirmation.
   - Open the public availability page and confirm open slots are shown by barber.
   - Use WhatsApp and Telegram share actions from customer or appointment screens and confirm the generated messages include booking or availability details.

6. Sales workflow
   - Create a daily sale with service and product items.
   - Confirm line totals, total sales, and commission values are calculated automatically.
   - Attempt a second sale for the same barber/shop/date and confirm redirect or validation failure.
   - Change source product pricing and confirm historical sale item snapshots remain unchanged.

7. Expense workflow
   - Create an expense with a positive amount.
   - Attempt a zero or negative amount and confirm rejection.
   - Confirm net revenue reports decrease when expenses are added.

8. Reporting
   - Compare daily, weekly, and monthly totals against underlying records.
   - Confirm top barber and commission summaries reflect actual sale values.
   - Confirm shop comparison and product performance summaries reconcile to sale data.
   - Confirm the dashboard shows upcoming appointments and appointment counts.

9. Audit logging
   - Create, update, and soft-delete key entities and confirm corresponding audit log entries exist.
   - Confirm normal users cannot edit audit records from UI or API.

10. Platform operations
   - Run migrations successfully.
   - Start with Docker Compose and confirm the UI loads.
   - Run Ruff, Black, and the Django test suite successfully.

## Browser Smoke Coverage

The browser-driven smoke suite in [test_ui_smoke.py](tests/browser/test_ui_smoke.py#L1) covers:

- login through the real browser UI
- navigation to customers and appointments
- dashboard load
- navigation to barbers, products, sales, expenses, reports, audit, and settings
- optional write-mode creation of a barber and product when `SMOKE_WRITE_TESTS=true`

## Expected Demo Outcomes

After `seed_demo` runs successfully:

- the dashboard should show non-zero sales, expenses, commissions, and net revenue
- the dashboard should show upcoming appointments
- reports should include top barbers, expense categories, and product performance
- the shop selector should show at least two branches for the platform admin

## Pilot Recommendation

For barber testing, use the checklist in [barber-pilot-test-plan.md](docs/barber-pilot-test-plan.md#L1) and run at least one browser smoke pass before sharing the URL with pilot users.
