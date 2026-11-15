from dataclasses import dataclass


@dataclass
class OrderOut:
    id: int
    total: int
