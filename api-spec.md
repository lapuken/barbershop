# API Specification

All API endpoints require authentication unless otherwise noted. Authentication uses Django session cookies with CSRF protection.

## Auth

- `POST /api/auth/login`
  - Request: `{"username": "user", "password": "secret"}`
  - Response: authenticated user summary
- `POST /api/auth/logout`
  - Response: `204 No Content`

## Shops

- `GET /api/shops`
- `GET /api/shops/{id}`
- `POST /api/shops`
- `PATCH /api/shops/{id}`

## Barbers

- `GET /api/barbers`
- `GET /api/barbers/{id}`
- `POST /api/barbers`
- `PATCH /api/barbers/{id}`
- `DELETE /api/barbers/{id}` soft-deletes the barber

## Products

- `GET /api/products`
- `GET /api/products/{id}`
- `POST /api/products`
- `PATCH /api/products/{id}`
- `DELETE /api/products/{id}` soft-deletes the product

## Sales

- `GET /api/sales`
- `GET /api/sales/{id}`
- `POST /api/sales`
- `PATCH /api/sales/{id}`
- `DELETE /api/sales/{id}` soft-deletes the sale for authorized management roles

Sale payload example:

```json
{
  "shop": 1,
  "barber": 2,
  "sale_date": "2026-03-03",
  "notes": "Busy Friday",
  "items": [
    {
      "item_type": "service",
      "item_name_snapshot": "Haircut",
      "unit_price_snapshot": "25.00",
      "quantity": 3
    },
    {
      "item_type": "product",
      "product": 5,
      "item_name_snapshot": "",
      "unit_price_snapshot": "0.00",
      "quantity": 1
    }
  ]
}
```

## Expenses

- `GET /api/expenses`
- `GET /api/expenses/{id}`
- `POST /api/expenses`
- `PATCH /api/expenses/{id}`
- `DELETE /api/expenses/{id}` soft-deletes the expense for authorized management roles

## Reports

- `GET /api/reports/dashboard`
- `GET /api/reports/daily`
- `GET /api/reports/weekly`
- `GET /api/reports/monthly`
- `GET /api/reports/top-barbers`
- `GET /api/reports/commissions`
- `GET /api/reports/expenses`
- `GET /api/reports/net-revenue`

## Audit

- `GET /api/audit`

## Error Patterns

- `400 Bad Request`: validation issues or duplicate business rule conflicts
- `403 Forbidden`: authenticated user lacks required role or shop access
- `404 Not Found`: resource not visible within the caller’s authorized scope
