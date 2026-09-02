from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List
from .data_feed import MarketBar, Tick


@dataclass
class MarketSnapshot:
    symbol: str
    time: object
    bid: float
    ask: float
    mid: float
    spread: float
    bar: MarketBar | None = None


class MarketEngine:
    def __init__(self, symbol: str, point: float = 0.01):
        self.symbol = symbol
        self.point = point
        self.current: MarketSnapshot | None = None

    def update_bar(self, bar: MarketBar, default_spread_points: float = 0.0):
        spread_points = bar.spread_points or default_spread_points
        spread = spread_points * self.point
        self.current = MarketSnapshot(
            self.symbol, bar.time,
            bar.close - spread / 2, bar.close + spread / 2,
            bar.close, spread, bar
        )
        return self.current

    def update_tick(self, tick: Tick):
        self.current = MarketSnapshot(
            self.symbol, tick.time, tick.bid, tick.ask, tick.mid, tick.spread, None
        )
        return self.current

    @staticmethod
    def intrabar_paths(bar: MarketBar):
        return {
            "open_high_low_close": [bar.open, bar.high, bar.low, bar.close],
            "open_low_high_close": [bar.open, bar.low, bar.high, bar.close],
        }
