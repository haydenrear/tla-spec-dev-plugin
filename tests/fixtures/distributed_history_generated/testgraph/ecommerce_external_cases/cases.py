from __future__ import annotations

from .types import StateGraphCase, StateGraphInput


SOURCE_MODULE = "examples.distributed_history.specs.program_model.External"


EMPTY = {
    "accounts": [],
    "carts": {},
    "orders": {},
    "outbox": [],
    "projections": {},
}

ACCOUNT = {
    "accounts": ["acct-1"],
    "carts": {},
    "orders": {},
    "outbox": [],
    "projections": {},
}

ACCOUNT_WITH_CART = {
    "accounts": ["acct-1"],
    "carts": {"acct-1": ["sku-1"]},
    "orders": {},
    "outbox": [],
    "projections": {},
}

ORDER_ACCEPTED = {
    "accounts": ["acct-1"],
    "carts": {"acct-1": ["sku-1"]},
    "orders": {
        "order-1": {
            "account": "acct-1",
            "items": ["sku-1"],
            "status": "accepted",
        }
    },
    "outbox": [{"order_id": "order-1", "event": "OrderAccepted"}],
    "projections": {},
}

ORDER_PROJECTED = {
    "accounts": ["acct-1"],
    "carts": {"acct-1": ["sku-1"]},
    "orders": {
        "order-1": {
            "account": "acct-1",
            "items": ["sku-1"],
            "status": "accepted",
        }
    },
    "outbox": [],
    "projections": {"order-1": "ready_to_ship"},
}


CASES = [
    StateGraphCase(
        name="external_submit_create_account",
        before=EMPTY,
        input=StateGraphInput(
            action="SubmitCreateAccount",
            params={"account": "acct-1"},
            source_node="e0",
            target_node="e1",
        ),
        after=ACCOUNT,
        output={"status": 201, "body": {"account": "acct-1"}},
        labels=("SubmitCreateAccount", "ecommerce_external"),
        tags=("account", "smoke"),
    ),
    StateGraphCase(
        name="external_submit_add_cart_item",
        before=ACCOUNT,
        input=StateGraphInput(
            action="SubmitAddCartItem",
            params={"account": "acct-1", "sku": "sku-1"},
            source_node="e1",
            target_node="e2",
        ),
        after=ACCOUNT_WITH_CART,
        output={"status": 202, "body": {"account": "acct-1", "sku": "sku-1"}},
        labels=("SubmitAddCartItem", "ecommerce_external"),
        tags=("cart", "smoke"),
    ),
    StateGraphCase(
        name="external_submit_checkout",
        before=ACCOUNT_WITH_CART,
        input=StateGraphInput(
            action="SubmitCheckout",
            params={"account": "acct-1", "order": "order-1"},
            source_node="e2",
            target_node="e3",
        ),
        after=ORDER_ACCEPTED,
        output={"status": 202, "body": {"order": "order-1", "status": "accepted"}},
        labels=("SubmitCheckout", "ecommerce_external"),
        tags=("checkout", "outbox", "smoke"),
    ),
    StateGraphCase(
        name="external_run_fulfillment_worker",
        before=ORDER_ACCEPTED,
        input=StateGraphInput(
            action="RunFulfillmentWorker",
            params={"limit": 100},
            source_node="e3",
            target_node="e4",
        ),
        after=ORDER_PROJECTED,
        output={"status": 200, "body": {"processed": 1}},
        labels=("RunFulfillmentWorker", "ecommerce_external"),
        tags=("worker", "projection"),
    ),
]

CASES_BY_NAME = {case.name: case for case in CASES}
