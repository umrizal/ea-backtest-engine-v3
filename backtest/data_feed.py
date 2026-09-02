from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import csv
from typing import Iterator, Optional, Iterable


def _dt(v: str) -> datetime:
    v = v.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    return datetime.fromisoformat(v)


def _float(row, *names, default=0.0):
    for n in names:
        if n in row and row[n] not in ("", None):
            return float(row[n])
    return default


@dataclass(frozen=True)
class MarketBar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    spread_points: float = 0.0

    @property
    def mid(self) -> float:
        return self.close


@dataclass(frozen=True)
class Tick:
    time: datetime
    bid: float
    ask: float
    volume: float = 0.0

    @property
    def spread(self) -> float:
        return self.ask - self.bid

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0


class CSVDataFeed:
    """Deterministic CSV feed. Required columns: time/open/high/low/close.
    Optional: volume, spread_points, bid, ask.
    """

    def __init__(self, path: str | Path, symbol: str = "", point: float = 0.01):
        self.path = Path(path)
        self.symbol = symbol
        self.point = point

    def bars(self) -> Iterator[MarketBar]:
        with self.path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield MarketBar(
                    time=_dt(row["time"]),
                    open=_float(row, "open", "Open"),
                    high=_float(row, "high", "High"),
                    low=_float(row, "low", "Low"),
                    close=_float(row, "close", "Close"),
                    volume=_float(row, "volume", "Volume", default=0.0),
                    spread_points=_float(row, "spread_points", "Spread", default=0.0),
                )

    def ticks(self) -> Iterator[Tick]:
        with self.path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                bid = _float(row, "bid", "Bid")
                ask = _float(row, "ask", "Ask")
                if not bid or not ask:
                    mid = _float(row, "price", "Price", "close", "Close")
                    spread = _float(row, "spread", "Spread", default=0.0)
                    bid, ask = mid - spread / 2, mid + spread / 2
                yield Tick(_dt(row["time"]), bid, ask, _float(row, "volume", "Volume"))


class IterableBarFeed:
    def __init__(self, bars: Iterable[MarketBar]):
        self._bars = bars

    def bars(self):
        yield from self._bars
