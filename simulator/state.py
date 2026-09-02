from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class SimulatorState:
    status: str = "STOPPED"       # STOPPED, PAUSED, PLAYING, FINISHED
    mode: str = "candle"          # candle or tick
    index: int = -1
    total: int = 0
    current_time: Any = None
    current_price: float | None = None
    balance: float = 0.0
    equity: float = 0.0
    floating_profit: float = 0.0
    margin: float = 0.0
    free_margin: float = 0.0
    margin_level: float = 0.0
    drawdown: float = 0.0
    drawdown_pct: float = 0.0
    active_trade_count: int = 0
    completed_trade_count: int = 0
    speed: float = 1.0
    selected_trade: int | None = None

    def to_dict(self):
        return asdict(self)
