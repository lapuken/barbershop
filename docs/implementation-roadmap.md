# Implementation Roadmap

## Near-Term

1. Run the full Django test suite and browser smoke suite in a prepared environment, then fix any integration defects found in the booking flows.
2. Add reschedule and cancellation flows for public bookings so customers are not limited to one-way request submission.
3. Add appointment-derived operational reporting such as utilization, no-show rate, and conversion from requested to confirmed.

## Mid-Term

1. Introduce notifications for booking confirmation and reminders via email or SMS.
2. Add calendar-oriented schedule views and barber availability management.
3. Harden the VPS operating model with off-host backups, centralized monitoring, and a staging environment.

## Deferred

1. POS and payment integration.
2. Customer self-service accounts and booking history.
3. More advanced revenue forecasting and staffing optimization.
