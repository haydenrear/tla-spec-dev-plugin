# Validation report 20261112-090000 — ordersContract: FAILED

| node | status |
| --- | --- |
| orders.service.start | passed |
| orders.api.contract | failed |

## orders.api.contract

assertion `response_carries_currency`: FAILED
GET /orders/17 returned {"id": 17, "total": 1250} — field `currency` is absent.
Contract v2 (docs/contract-v2.md) requires `currency` on every order.

See node-logs/orders.api.contract.log
