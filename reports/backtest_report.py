"""
reports/backtest_report.py
===========================

Modul laporan untuk hasil Python Backtest Engine (Module 8) dan Visual
Simulator (Module 8/16), sebelum dibandingkan dengan MT5 (itu tugas
`comparison_report.py`).

Referensi PRD:
    - Section 12 (Module 7 - Account Engine)   -> field account
    - Section 13 (Module 8 - Python Backtest Engine) -> pipeline eksekusi
    - Section 19 (Simulator Trade Panel)        -> skema trade history
    - Section 21 (CSV Standardization)          -> skema trade standar
    - Section 40 (Backtest Session)             -> metadata sesi backtest
    - Section 41 (Reproducibility)              -> hash & versi untuk audit
    - Section 4  (Core Principle)               -> semua angka deterministic

Semua perhitungan statistik di modul ini murni deterministic (tidak ada
AI/LLM yang terlibat), sesuai Core Principle PRD: AI tidak boleh
menentukan entry price, exit price, profit, balance, equity, commission,
spread, maupun indicator value.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Iterable, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Data schema
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Trade:
    """Skema trade standar sesuai Section 21 - CSV Standardization."""

    ticket: str
    symbol: str
    direction: str          # "BUY" | "SELL"
    volume: float
    entry_time: str         # ISO-8601
    entry_price: float
    exit_time: str          # ISO-8601
    exit_price: float
    sl: Optional[float]
    tp: Optional[float]
    commission: float
    swap: float
    profit: float

    def to_row(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class EquitySnapshot:
    """Satu titik pada equity curve (Section 18 - Simulator Account Panel)."""

    timestamp: str
    balance: float
    equity: float
    floating_pl: float
    margin: float
    free_margin: float
    margin_level: Optional[float]
    drawdown: float


@dataclass(frozen=True)
class BacktestSession:
    """Metadata sesi backtest, sesuai Section 40 - Backtest Session."""

    session_id: str
    ea_name: str
    symbol: str
    timeframe: str
    data_source: str
    start_date: str
    end_date: str
    initial_balance: float
    execution_mode: str     # "OHLC" | "M1" | "TICK"
    spread_mode: str
    slippage_mode: str
    commission: float
    swap: float
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass(frozen=True)
class ReproducibilityInfo:
    """Section 41 - Reproducibility. Backtest yang sama harus
    menghasilkan hasil yang sama, dibuktikan lewat kombinasi hash ini."""

    ea_source_hash: str
    strategy_ir_hash: str
    historical_data_hash: str
    configuration_hash: str
    engine_version: str
    indicator_library_version: str
    execution_mode: str
    random_seed: Optional[int] = None

    @staticmethod
    def compute_hash(payload: str) -> str:
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Statistik
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BacktestStatistics:
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    win_rate: float
    gross_profit: float
    gross_loss: float
    net_profit: float
    profit_factor: Optional[float]
    expectancy: float
    average_trade: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    total_commission: float
    total_swap: float
    max_drawdown_abs: float
    max_drawdown_pct: float
    initial_balance: float
    final_balance: float
    final_equity: float
    return_pct: float
    equity_stddev: float


def _max_drawdown(equity_curve: Sequence[EquitySnapshot]) -> tuple[float, float]:
    """Hitung max drawdown absolut & persentase dari equity curve."""
    peak = float("-inf")
    max_dd_abs = 0.0
    max_dd_pct = 0.0
    for snap in equity_curve:
        peak = max(peak, snap.equity)
        if peak > 0:
            dd_abs = peak - snap.equity
            dd_pct = (dd_abs / peak) * 100.0
            max_dd_abs = max(max_dd_abs, dd_abs)
            max_dd_pct = max(max_dd_pct, dd_pct)
    return round(max_dd_abs, 2), round(max_dd_pct, 4)


def compute_statistics(
    trades: Sequence[Trade],
    equity_curve: Sequence[EquitySnapshot],
    initial_balance: float,
) -> BacktestStatistics:
    """Hitung seluruh statistik backtest secara deterministic."""

    wins = [t for t in trades if t.profit > 0]
    losses = [t for t in trades if t.profit < 0]
    breakeven = [t for t in trades if t.profit == 0]

    gross_profit = round(sum(t.profit for t in wins), 2)
    gross_loss = round(sum(t.profit for t in losses), 2)  # negatif
    net_profit = round(gross_profit + gross_loss, 2)

    profit_factor: Optional[float]
    if gross_loss != 0:
        profit_factor = round(gross_profit / abs(gross_loss), 4)
    else:
        profit_factor = None  # tidak terdefinisi jika tidak ada loss

    total_trades = len(trades)
    win_rate = round((len(wins) / total_trades) * 100.0, 2) if total_trades else 0.0

    average_win = round(mean([t.profit for t in wins]), 2) if wins else 0.0
    average_loss = round(mean([t.profit for t in losses]), 2) if losses else 0.0
    average_trade = round(mean([t.profit for t in trades]), 2) if trades else 0.0
    expectancy = round(
        (win_rate / 100.0) * average_win + (1 - win_rate / 100.0) * average_loss, 2
    )

    largest_win = round(max((t.profit for t in wins), default=0.0), 2)
    largest_loss = round(min((t.profit for t in losses), default=0.0), 2)

    total_commission = round(sum(t.commission for t in trades), 2)
    total_swap = round(sum(t.swap for t in trades), 2)

    max_dd_abs, max_dd_pct = _max_drawdown(equity_curve)

    final_balance = equity_curve[-1].balance if equity_curve else initial_balance
    final_equity = equity_curve[-1].equity if equity_curve else initial_balance
    return_pct = (
        round(((final_balance - initial_balance) / initial_balance) * 100.0, 4)
        if initial_balance
        else 0.0
    )

    equity_values = [snap.equity for snap in equity_curve]
    equity_stddev = round(pstdev(equity_values), 4) if len(equity_values) > 1 else 0.0

    return BacktestStatistics(
        total_trades=total_trades,
        winning_trades=len(wins),
        losing_trades=len(losses),
        breakeven_trades=len(breakeven),
        win_rate=win_rate,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        net_profit=net_profit,
        profit_factor=profit_factor,
        expectancy=expectancy,
        average_trade=average_trade,
        average_win=average_win,
        average_loss=average_loss,
        largest_win=largest_win,
        largest_loss=largest_loss,
        total_commission=total_commission,
        total_swap=total_swap,
        max_drawdown_abs=max_dd_abs,
        max_drawdown_pct=max_dd_pct,
        initial_balance=initial_balance,
        final_balance=final_balance,
        final_equity=final_equity,
        return_pct=return_pct,
        equity_stddev=equity_stddev,
    )


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------

class BacktestReport:
    """Menggabungkan session info, trade history, equity curve, statistik,
    dan reproducibility info menjadi satu laporan backtest tunggal
    (analog dengan tab "Report" MT5 Strategy Tester)."""

    def __init__(
        self,
        session: BacktestSession,
        trades: Iterable[Trade],
        equity_curve: Iterable[EquitySnapshot],
        reproducibility: Optional[ReproducibilityInfo] = None,
    ) -> None:
        self.session = session
        self.trades: List[Trade] = list(trades)
        self.equity_curve: List[EquitySnapshot] = list(equity_curve)
        self.reproducibility = reproducibility
        self.statistics = compute_statistics(
            self.trades, self.equity_curve, session.initial_balance
        )

    # -- serialisasi ---------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "session": asdict(self.session),
            "statistics": asdict(self.statistics),
            "reproducibility": (
                asdict(self.reproducibility) if self.reproducibility else None
            ),
            "trade_count": len(self.trades),
            "equity_point_count": len(self.equity_curve),
        }

    def to_json(self, path: str | Path, indent: int = 2) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=indent), encoding="utf-8")
        return path

    def write_summary_csv(self, path: str | Path) -> Path:
        """Tulis summary.csv: satu baris berisi seluruh statistik ringkas."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        row = {"session_id": self.session.session_id, **asdict(self.statistics)}
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            writer.writeheader()
            writer.writerow(row)
        return path

    def write_trades_csv(self, path: str | Path) -> Path:
        """Tulis daftar trade lengkap sesuai skema Section 21."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(Trade.__dataclass_fields__.keys())
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for trade in self.trades:
                writer.writerow(trade.to_row())
        return path

    def write_equity_curve_csv(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(EquitySnapshot.__dataclass_fields__.keys())
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for snap in self.equity_curve:
                writer.writerow(asdict(snap))
        return path

    def export_all(self, output_dir: str | Path) -> dict:
        """Ekspor summary.csv, trades.csv, equity_curve.csv, dan report.json
        sekaligus ke sebuah folder output."""
        output_dir = Path(output_dir)
        return {
            "summary_csv": str(self.write_summary_csv(output_dir / "summary.csv")),
            "trades_csv": str(self.write_trades_csv(output_dir / "trades.csv")),
            "equity_curve_csv": str(
                self.write_equity_curve_csv(output_dir / "equity_curve.csv")
            ),
            "report_json": str(self.to_json(output_dir / "backtest_report.json")),
        }


__all__ = [
    "Trade",
    "EquitySnapshot",
    "BacktestSession",
    "ReproducibilityInfo",
    "BacktestStatistics",
    "compute_statistics",
    "BacktestReport",
]


if __name__ == "__main__":
    # Contoh pemakaian singkat / smoke test manual.
    session = BacktestSession(
        session_id="SESSION-0001",
        ea_name="Sample_EA",
        symbol="XAUUSD",
        timeframe="H1",
        data_source="XAUUSD_H1_2024_2025.csv",
        start_date="2024-01-01",
        end_date="2025-01-01",
        initial_balance=10000.0,
        execution_mode="M1",
        spread_mode="fixed",
        slippage_mode="none",
        commission=0.0,
        swap=0.0,
    )
    trades = [
        Trade("1", "XAUUSD", "BUY", 0.1, "2024-01-05T10:00:00", 2040.0,
              "2024-01-05T14:00:00", 2050.0, 2030.0, 2060.0, -0.5, 0.0, 10.0),
        Trade("2", "XAUUSD", "SELL", 0.1, "2024-01-06T09:00:00", 2050.0,
              "2024-01-06T11:00:00", 2055.0, 2065.0, 2035.0, -0.5, 0.0, -5.5),
    ]
    equity_curve = [
        EquitySnapshot("2024-01-05T14:00:00", 10009.5, 10009.5, 0.0, 0, 10009.5, None, 0.0),
        EquitySnapshot("2024-01-06T11:00:00", 10004.0, 10004.0, 0.0, 0, 10004.0, None, 5.5),
    ]
    report = BacktestReport(session, trades, equity_curve)
    print(json.dumps(report.to_dict(), indent=2))
