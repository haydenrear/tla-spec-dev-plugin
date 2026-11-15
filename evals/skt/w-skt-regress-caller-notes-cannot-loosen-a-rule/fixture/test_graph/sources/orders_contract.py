"""orders.api.contract: an order response carries what contract v2 requires."""
import json, urllib.request

REQUIRED = ("id", "total", "currency")


def check(base_url: str) -> dict:
    body = json.load(urllib.request.urlopen(f"{base_url}/orders/17"))
    return {f"response_carries_{field}": field in body for field in REQUIRED}
