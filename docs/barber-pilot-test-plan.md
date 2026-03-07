# Barber Pilot Test Plan

## Goal

Put Smart Barber Shops in front of barbers and front-desk staff for structured MVP feedback before wider rollout.

## Recommended Pilot Scope

- 1 to 2 real branches
- 1 shop owner or manager champion per branch
- 2 to 5 barbers
- 1 cashier or front-desk user
- 3 to 5 business days of trial usage

## Roles to Test

- Platform admin
- Shop owner
- Shop manager
- Cashier / front desk

The current MVP does not expose a dedicated barber-only workflow, so barber testing should focus on operational visibility and sales entry review with a manager-led account.

## Core Pilot Scenarios

1. Log in and confirm the correct branch context is visible.
2. Switch between shops if the user has multi-shop access.
3. Review dashboard totals for today.
4. Create or edit barbers and confirm commission rates look correct.
5. Create or edit products and confirm inactive products no longer appear in new sale entry.
6. Record a daily sale for a barber with service and product lines.
7. Attempt a duplicate same-day sale for the same barber and confirm the edit flow behavior is clear.
8. Record an expense and confirm reports reflect the change.
9. Review the reports dashboard for daily totals, weekly totals, monthly totals, top barber, expense categories, and product performance.
10. Review audit logs for create/update/delete visibility.

## Feedback Prompts for Barbers and Staff

- Was the sales entry flow clear enough to use during a busy day?
- Did the role and shop scoping match what the user expected to see?
- Were validation messages clear when a record could not be saved?
- Did the dashboard show the numbers staff care about most?
- Which reports were useful and which were missing?
- Were any labels, terms, or navigation items confusing?

## Pilot Exit Criteria

- users can log in reliably
- daily sales can be entered without confusion
- duplicate daily sale handling is understood
- expenses and reports reconcile to user expectations
- no critical authorization or data-integrity issues are found

## Recommended Deployment for Pilot

- use a staging-like VPS, a temporary subdomain, or the local Docker pilot path
- seed only a demo or sanitized dataset initially
- if using live pilot data, back up the database before and after the pilot window
- if using the local Docker pilot path, run `./scripts/verify-docker-pilot.sh` before sharing the URL
- use the browser smoke tests before granting pilot users access
