from __future__ import annotations

from .types import StateGraphCase, StateGraphInput


SOURCE_MODULE = "examples.distributed_history.specs.program_model.Internal"


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
        name="internal_create_account",
        before=EMPTY,
        input=StateGraphInput(
            action="CreateAccount",
            params={"account": "acct-1"},
            source_node="s0",
            target_node="s1",
        ),
        after=ACCOUNT,
        output={"status": 201, "body": {"account": "acct-1"}},
        labels=("CreateAccount", "ecommerce_internal"),
        tags=("account",),
    ),
    StateGraphCase(
        name="internal_add_cart_item",
        before=ACCOUNT,
        input=StateGraphInput(
            action="AddCartItem",
            params={"account": "acct-1", "sku": "sku-1"},
            source_node="s1",
            target_node="s2",
        ),
        after=ACCOUNT_WITH_CART,
        output={"status": 202, "body": {"account": "acct-1", "sku": "sku-1"}},
        labels=("AddCartItem", "ecommerce_internal"),
        tags=("cart",),
    ),
    StateGraphCase(
        name="internal_checkout_creates_outbox",
        before=ACCOUNT_WITH_CART,
        input=StateGraphInput(
            action="Checkout",
            params={"account": "acct-1", "order": "order-1"},
            source_node="s2",
            target_node="s3",
        ),
        after=ORDER_ACCEPTED,
        output={"status": 202, "body": {"order": "order-1", "status": "accepted"}},
        labels=("Checkout", "ecommerce_internal"),
        tags=("checkout", "outbox"),
    ),
    StateGraphCase(
        name="internal_project_order",
        before=ORDER_ACCEPTED,
        input=StateGraphInput(
            action="ProjectOrder",
            params={"order": "order-1"},
            source_node="s3",
            target_node="s4",
        ),
        after=ORDER_PROJECTED,
        output={"status": 200, "body": {"processed": 1}},
        labels=("ProjectOrder", "ecommerce_internal"),
        tags=("projection",),
    ),
]

CASES_BY_NAME = {case.name: case for case in CASES}
