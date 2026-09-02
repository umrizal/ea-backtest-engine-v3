from __future__ import annotations
from dataclasses import dataclass
from math import sqrt


@dataclass
class Statistics:
    trades: int
    wins: int
    losses: int
    net_profit: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    win_rate_pct: float
    avg_win: float
    avg_loss: float
    expectancy: float
    max_drawdown: float
    max_drawdown_pct: float
    recovery_factor: float
    avg_trade_duration_seconds: float
    max_win_streak: int
    max_loss_streak: int


class StatisticsEngine:
    def calculate(self, trades, max_drawdown=0.0, max_drawdown_pct=0.0):
        profits = [t.profit - t.commission - t.swap for t in trades]
        wins = [x for x in profits if x > 0]
        losses = [x for x in profits if x < 0]
        streak_w = streak_l = max_w = max_l = 0
        durations = []
        for t, p in zip(trades, profits):
            if p > 0:
                streak_w += 1; streak_l = 0
                max_w = max(max_w, streak_w)
            elif p < 0:
                streak_l += 1; streak_w = 0
                max_l = max(max_l, streak_l)
            if t.entry_time and t.exit_time:
                durations.append((t.exit_time - t.entry_time).total_seconds())
        gp, gl = sum(wins), abs(sum(losses))
        net = gp - gl
        n = len(profits)
        return Statistics(
            trades=n, wins=len(wins), losses=len(losses),
            net_profit=net, gross_profit=gp, gross_loss=gl,
            profit_factor=(gp / gl if gl else float("inf")),
            win_rate_pct=(len(wins) / n * 100 if n else 0.0),
            avg_win=(gp / len(wins) if wins else 0.0),
            avg_loss=(gl / len(losses) if losses else 0.0),
            expectancy=(net / n if n else 0.0),
            max_drawdown=max_drawdown, max_drawdown_pct=max_drawdown_pct,
            recovery_factor=(net / max_drawdown if max_drawdown else float("inf")),
            avg_trade_duration_seconds=(sum(durations) / len(durations) if durations else 0.0),
            max_win_streak=max_w, max_loss_streak=max_l
        )
