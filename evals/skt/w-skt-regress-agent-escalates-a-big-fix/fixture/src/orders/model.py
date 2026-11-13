from dataclasses import dataclass


@dataclass
class Order:
    """Row of the `orders` table: id, total (minor units)."""
    id: int
    total: int
