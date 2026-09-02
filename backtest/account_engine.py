from __future__ import annotations
from dataclasses import dataclass


@dataclass
class AccountSnapshot:
    time: object
    balance: float
    equity: float
    floating_profit: float
    margin: float
    free_margin: float
    margin_level: float
    drawdown: float
    drawdown_pct: float


class AccountEngine:
    def __init__(self, initial_balance: float = 10000.0, leverage: float = 100.0,
                 contract_size: float = 1.0, stop_out_pct: float = 0.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.leverage = leverage
        self.contract_size = contract_size
        self.stop_out_pct = stop_out_pct
        self.peak_equity = initial_balance
        self.max_drawdown = 0.0
        self.max_drawdown_pct = 0.0

    def apply_profit(self, value: float):
        self.balance += value

    def margin_required(self, price: float, volume: float) -> float:
        if self.leverage <= 0:
            return 0.0
        return price * volume * self.contract_size / self.leverage

    def snapshot(self, time, floating_profit: float, margin: float = 0.0):
        equity = self.balance + floating_profit
        self.peak_equity = max(self.peak_equity, equity)
        dd = max(0.0, self.peak_equity - equity)
        dd_pct = dd / self.peak_equity * 100 if self.peak_equity else 0.0
        self.max_drawdown = max(self.max_drawdown, dd)
        self.max_drawdown_pct = max(self.max_drawdown_pct, dd_pct)
        free = equity - margin
        level = equity / margin * 100 if margin > 0 else float("inf")
        return AccountSnapshot(time, self.balance, equity, floating_profit,
                               margin, free, level, dd, dd_pct)
