from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
import itertools


_pos_ids = itertools.count(1)


@dataclass
class Position:
    symbol: str
    side: str
    volume: float
    entry_price: float
    entry_time: datetime
    sl: float | None = None
    tp: float | None = None
    ticket: int = field(default_factory=lambda: next(_pos_ids))
    exit_price: float | None = None
    exit_time: datetime | None = None
    profit: float = 0.0
    commission: float = 0.0
    swap: float = 0.0
    status: str = "OPEN"
    comment: str = ""

    def floating_profit(self, price: float, contract_size: float = 1.0) -> float:
        sign = 1 if self.side.upper() == "BUY" else -1
        return (price - self.entry_price) * sign * self.volume * contract_size


class PositionEngine:
    def __init__(self, contract_size: float = 1.0, hedging: bool = True):
        self.contract_size = contract_size
        self.hedging = hedging
        self.positions: dict[int, Position] = {}
        self.closed: list[Position] = []

    def open(self, **kwargs) -> Position:
        p = Position(**kwargs)
        self.positions[p.ticket] = p
        return p

    def floating(self, price: float) -> float:
        return sum(p.floating_profit(price, self.contract_size)
                   for p in self.positions.values() if p.status == "OPEN")

    def close(self, ticket: int, price: float, time, commission: float = 0.0, reason: str = ""):
        p = self.positions[ticket]
        if p.status != "OPEN":
            return p
        p.exit_price = price
        p.exit_time = time
        p.profit = p.floating_profit(price, self.contract_size)
        p.commission = commission
        p.status = "CLOSED"
        p.comment = reason
        self.closed.append(p)
        return p

    def evaluate_protection(self, bar, execution_mode="heuristic"):
        """Return [(ticket, exit_price, reason)] for SL/TP hits.
        For ambiguous OHLC candles, conservative prioritizes the adverse level.
        """
        events = []
        for p in list(self.positions.values()):
            if p.status != "OPEN":
                continue
            hits = []
            if p.side == "BUY":
                if p.sl is not None and bar.low <= p.sl: hits.append((p.sl, "SL"))
                if p.tp is not None and bar.high >= p.tp: hits.append((p.tp, "TP"))
            else:
                if p.sl is not None and bar.high >= p.sl: hits.append((p.sl, "SL"))
                if p.tp is not None and bar.low <= p.tp: hits.append((p.tp, "TP"))
            if hits:
                if len(hits) == 1:
                    events.append((p.ticket, hits[0][0], hits[0][1]))
                elif execution_mode == "optimistic":
                    events.append((p.ticket, hits[-1][0], hits[-1][1]))
                else:
                    events.append((p.ticket, hits[0][0], hits[0][1]))
        return events
