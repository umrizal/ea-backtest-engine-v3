from __future__ import annotations
from dataclasses import dataclass
from .order_engine import Order, OrderEngine
from .position_engine import PositionEngine
from .account_engine import AccountEngine


@dataclass
class ExecutionConfig:
    mode: str = "heuristic"
    slippage_points: float = 0.0
    point: float = 0.01
    commission_per_lot: float = 0.0
    swap_per_lot: float = 0.0
    default_spread_points: float = 0.0


@dataclass
class TradeRecord:
    ticket: int
    symbol: str
    direction: str
    volume: float
    entry_time: object
    entry_price: float
    exit_time: object | None = None
    exit_price: float | None = None
    sl: float | None = None
    tp: float | None = None
    commission: float = 0.0
    swap: float = 0.0
    profit: float = 0.0
    reason: str = ""


class ExecutionEngine:
    def __init__(self, cfg: ExecutionConfig, orders: OrderEngine,
                 positions: PositionEngine, account: AccountEngine):
        self.cfg, self.orders, self.positions, self.account = cfg, orders, positions, account
        self.trades: list[TradeRecord] = []

    def _fill_price(self, side, mid, spread):
        raw = mid + (spread / 2 if side == "BUY" else -spread / 2)
        slip = self.cfg.slippage_points * self.cfg.point
        return raw + (slip if side == "BUY" else -slip)

    def execute_market(self, symbol, side, volume, time, mid, spread=0.0,
                       sl=None, tp=None, comment=""):
        price = self._fill_price(side, mid, spread)
        commission = self.cfg.commission_per_lot * volume
        p = self.positions.open(symbol=symbol, side=side, volume=volume,
                                entry_price=price, entry_time=time, sl=sl, tp=tp,
                                comment=comment)
        self.trades.append(TradeRecord(p.ticket, symbol, side, volume, time, price,
                                       sl=sl, tp=tp, commission=commission))
        return p

    def close_position(self, ticket, time, mid, spread=0.0, reason=""):
        p = self.positions.positions[ticket]
        side = "SELL" if p.side == "BUY" else "BUY"
        price = self._fill_price(side, mid, spread)
        commission = self.cfg.commission_per_lot * p.volume
        closed = self.positions.close(ticket, price, time, commission, reason)
        net = closed.profit - closed.commission - closed.swap
        self.account.apply_profit(net)
        for tr in self.trades:
            if tr.ticket == ticket:
                tr.exit_time, tr.exit_price = closed.exit_time, closed.exit_price
                tr.commission += closed.commission
                tr.swap = closed.swap
                tr.profit = closed.profit
                tr.reason = reason
                break
        return closed

    def process_protection(self, bar, time, spread=0.0):
        for ticket, price, reason in self.positions.evaluate_protection(bar, self.cfg.mode):
            p = self.positions.positions[ticket]
            # Protection levels are modeled at requested price, then opposite-side spread is not double-counted.
            closed = self.positions.close(ticket, price, time,
                                          self.cfg.commission_per_lot * p.volume, reason)
            self.account.apply_profit(closed.profit - closed.commission - closed.swap)
            for tr in self.trades:
                if tr.ticket == ticket:
                    tr.exit_time, tr.exit_price = time, price
                    tr.commission += closed.commission
                    tr.profit = closed.profit
                    tr.reason = reason
                    break
