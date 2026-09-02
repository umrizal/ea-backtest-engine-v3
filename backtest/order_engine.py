from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
import itertools


_ids = itertools.count(1)


@dataclass
class Order:
    symbol: str
    side: str
    volume: float
    order_type: str = "market"
    price: float | None = None
    sl: float | None = None
    tp: float | None = None
    created_at: datetime | None = None
    ticket: int = field(default_factory=lambda: next(_ids))
    status: str = "PENDING"
    comment: str = ""


class OrderEngine:
    VALID_TYPES = {"market", "limit", "stop", "stop_limit"}

    def __init__(self):
        self.orders: Dict[int, Order] = {}

    def submit(self, order: Order) -> Order:
        if order.order_type not in self.VALID_TYPES:
            raise ValueError(f"Unsupported order type: {order.order_type}")
        if order.volume <= 0:
            raise ValueError("Order volume must be > 0")
        self.orders[order.ticket] = order
        return order

    def cancel(self, ticket: int) -> bool:
        o = self.orders.get(ticket)
        if not o or o.status != "PENDING":
            return False
        o.status = "CANCELLED"
        return True

    def pending(self):
        return [o for o in self.orders.values() if o.status == "PENDING"]

    def mark_filled(self, ticket: int):
        self.orders[ticket].status = "FILLED"

    def mark_rejected(self, ticket: int, reason: str = ""):
        self.orders[ticket].status = "REJECTED"
        self.orders[ticket].comment = reason
