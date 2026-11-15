from .model import Order
from .schema import OrderOut


def get_order(order: Order) -> OrderOut:
    return OrderOut(id=order.id, total=order.total)
