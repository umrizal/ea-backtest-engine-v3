from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Callable, Iterable, Any
from .data_feed import MarketBar
from .market_engine import MarketEngine
from .order_engine import OrderEngine
from .position_engine import PositionEngine
from .account_engine import AccountEngine
from .execution_engine import ExecutionEngine, ExecutionConfig
from .statistics import StatisticsEngine, Statistics


@dataclass
class BacktestConfig:
    symbol: str = "XAUUSD"
    initial_balance: float = 10000.0
    leverage: float = 100.0
    contract_size: float = 1.0
    point: float = 0.01
    execution_mode: str = "heuristic"
    default_spread_points: float = 0.0
    slippage_points: float = 0.0
    commission_per_lot: float = 0.0
    swap_per_lot: float = 0.0
    hedging: bool = True
    seed: int = 42


@dataclass
class BacktestResult:
    config: dict
    trades: list[dict]
    equity_curve: list[dict]
    statistics: dict
    metadata: dict


class BacktestEngine:
    """Deterministic backtest orchestrator.
    Strategy callback receives (bar, context) and may return trade dictionaries:
      {"action":"BUY","volume":0.1,"sl":...,"tp":...,"comment":"..."}
      {"action":"SELL",...}
      {"action":"CLOSE","ticket":123}
    """

    def __init__(self, config: BacktestConfig | None = None):
        self.cfg = config or BacktestConfig()
        self.market = MarketEngine(self.cfg.symbol, self.cfg.point)
        self.orders = OrderEngine()
        self.positions = PositionEngine(self.cfg.contract_size, self.cfg.hedging)
        self.account = AccountEngine(self.cfg.initial_balance, self.cfg.leverage,
                                     self.cfg.contract_size)
        self.execution = ExecutionEngine(
            ExecutionConfig(self.cfg.execution_mode, self.cfg.slippage_points,
                            self.cfg.point, self.cfg.commission_per_lot,
                            self.cfg.swap_per_lot, self.cfg.default_spread_points),
            self.orders, self.positions, self.account
        )
        self.equity_curve: list[dict] = []

    def _context(self):
        snap = self.market.current
        return {
            "symbol": self.cfg.symbol,
            "time": snap.time if snap else None,
            "bid": snap.bid if snap else None,
            "ask": snap.ask if snap else None,
            "price": snap.mid if snap else None,
            "spread": snap.spread if snap else None,
            "positions": self.positions.positions,
            "balance": self.account.balance,
        }

    def _apply_action(self, action, bar):
        if not action:
            return
        if isinstance(action, dict):
            action = [action]
        for a in action:
            typ = str(a.get("action", "")).upper()
            if typ in {"BUY", "SELL"}:
                self.execution.execute_market(
                    self.cfg.symbol, typ, float(a.get("volume", 0.01)),
                    bar.time, bar.close,
                    self.market.current.spread if self.market.current else 0.0,
                    a.get("sl"), a.get("tp"), a.get("comment", "")
                )
            elif typ == "CLOSE":
                ticket = int(a["ticket"])
                if ticket in self.positions.positions and self.positions.positions[ticket].status == "OPEN":
                    self.execution.close_position(ticket, bar.time, bar.close,
                                                  self.market.current.spread if self.market.current else 0.0,
                                                  "strategy_close")

    def run(self, bars: Iterable[MarketBar],
            strategy: Callable[[MarketBar, dict], Any] | None = None) -> BacktestResult:
        for bar in bars:
            self.market.update_bar(bar, self.cfg.default_spread_points)
            # Protection is checked before strategy action to model existing positions first.
            self.execution.process_protection(bar, bar.time,
                                              self.market.current.spread if self.market.current else 0.0)
            if strategy:
                self._apply_action(strategy(bar, self._context()), bar)

            floating = self.positions.floating(bar.close)
            margin = sum(
                self.account.margin_required(bar.close, p.volume)
                for p in self.positions.positions.values() if p.status == "OPEN"
            )
            snap = self.account.snapshot(bar.time, floating, margin)
            self.equity_curve.append(asdict(snap))

        # No forced liquidation: open positions remain open by design.
        stats = StatisticsEngine().calculate(
            self.execution.trades,
            self.account.max_drawdown,
            self.account.max_drawdown_pct
        )
        return BacktestResult(
            config=asdict(self.cfg),
            trades=[asdict(t) for t in self.execution.trades],
            equity_curve=self.equity_curve,
            statistics=asdict(stats),
            metadata={
                "engine": "EA Backtest Engine V3",
                "execution_mode": self.cfg.execution_mode,
                "deterministic": True,
                "seed": self.cfg.seed,
            }
        )
