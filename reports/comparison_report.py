"""
reports/comparison_report.py
=============================

Modul laporan untuk Module 9 - MT5 Comparator. Menjadikan hasil MT5
Strategy Tester sebagai ground truth, dibandingkan trade-by-trade dan
equity-by-equity dengan hasil Python Backtest Engine.

Referensi PRD:
    - Section 20 (Module 9 - MT5 Comparator)
    - Section 21 (CSV Standardization)      -> skema trade dari 2 sumber
    - Section 22 (Trade Matching)           -> status matching
    - Section 23 (Equity Comparison)        -> first divergence point
    - Section 24 (Discrepancy Analysis)     -> kategori penyebab selisih
    - Section 25 (MT5 Parity Score)         -> skor kemiripan akhir
    - Section 36 (Output 1 - Backtest Comparison) -> comparison.csv,
      summary.csv, equity_comparison.csv, discrepancies.csv

Catatan penting PRD: "Score tidak boleh dianggap sebagai jaminan
kesamaan absolut" — parity score adalah indikator, bukan bukti mutlak
bahwa dua hasil identik.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Sequence

try:
    from .backtest_report import Trade  # skema trade standar (Section 21)
except ImportError:  # dijalankan langsung sebagai skrip, bukan sebagai package
    from backtest_report import Trade


# ---------------------------------------------------------------------------
# Trade matching (Section 22)
# ---------------------------------------------------------------------------

class MatchStatus(str, Enum):
    MATCH = "MATCH"
    WARNING = "WARNING"
    MISMATCH = "MISMATCH"
    MISSING_MT5 = "MISSING_MT5"
    MISSING_PYTHON = "MISSING_PYTHON"
    EXTRA_PYTHON = "EXTRA_PYTHON"


# Kategori penyebab discrepancy (Section 24)
class DiscrepancyCategory(str, Enum):
    ENTRY_TIME = "entry_time"
    ENTRY_PRICE = "entry_price"
    EXIT_TIME = "exit_time"
    EXIT_PRICE = "exit_price"
    VOLUME = "volume"
    SL = "sl"
    TP = "tp"
    SPREAD = "spread"
    COMMISSION = "commission"
    SWAP = "swap"
    INDICATOR = "indicator"
    INTRABAR_EXECUTION = "intrabar_execution"
    SLIPPAGE = "slippage"
    TIMEZONE = "timezone"
    MARKET_DATA = "market_data"


# Toleransi default untuk menentukan MATCH vs WARNING vs MISMATCH.
# Bisa dioverride sesuai kebutuhan (mis. spread/commodity berbeda).
DEFAULT_TOLERANCE = {
    "time_seconds": 60,        # toleransi waktu (proximity) -> Section 22
    "price": 0.05,             # toleransi harga
    "volume": 0.001,
    "profit": 0.5,
}


@dataclass(frozen=True)
class TradeMatch:
    """Hasil pencocokan satu pasang trade MT5 <-> Python."""

    mt5_ticket: Optional[str]
    python_ticket: Optional[str]
    status: MatchStatus
    discrepancy_categories: List[DiscrepancyCategory]
    entry_time_diff_seconds: Optional[float]
    entry_price_diff: Optional[float]
    exit_time_diff_seconds: Optional[float]
    exit_price_diff: Optional[float]
    volume_diff: Optional[float]
    profit_diff: Optional[float]

    def to_row(self) -> dict:
        row = asdict(self)
        row["status"] = self.status.value
        row["discrepancy_categories"] = ",".join(
            c.value for c in self.discrepancy_categories
        )
        return row


def _seconds_between(t1: str, t2: str) -> float:
    from datetime import datetime

    return abs((datetime.fromisoformat(t1) - datetime.fromisoformat(t2)).total_seconds())


def match_trades(
    mt5_trades: Sequence[Trade],
    python_trades: Sequence[Trade],
    tolerance: Optional[dict] = None,
) -> List[TradeMatch]:
    """Cocokkan trade MT5 dengan trade Python berdasarkan matching priority
    Section 22: symbol -> direction -> time proximity -> volume ->
    entry price -> exit time."""

    tol = {**DEFAULT_TOLERANCE, **(tolerance or {})}
    remaining_python = list(python_trades)
    matches: List[TradeMatch] = []

    for mt5_trade in mt5_trades:
        candidate = None
        best_score = float("inf")
        for py_trade in remaining_python:
            if py_trade.symbol != mt5_trade.symbol:
                continue
            if py_trade.direction != mt5_trade.direction:
                continue
            time_diff = _seconds_between(mt5_trade.entry_time, py_trade.entry_time)
            if time_diff > tol["time_seconds"] * 10:
                continue
            score = time_diff
            if score < best_score:
                best_score = score
                candidate = py_trade

        if candidate is None:
            matches.append(
                TradeMatch(
                    mt5_ticket=mt5_trade.ticket,
                    python_ticket=None,
                    status=MatchStatus.MISSING_PYTHON,
                    discrepancy_categories=[],
                    entry_time_diff_seconds=None,
                    entry_price_diff=None,
                    exit_time_diff_seconds=None,
                    exit_price_diff=None,
                    volume_diff=None,
                    profit_diff=None,
                )
            )
            continue

        remaining_python.remove(candidate)
        matches.append(_build_trade_match(mt5_trade, candidate, tol))

    # Trade Python yang tidak pernah cocok dengan MT5 manapun.
    for py_trade in remaining_python:
        matches.append(
            TradeMatch(
                mt5_ticket=None,
                python_ticket=py_trade.ticket,
                status=MatchStatus.EXTRA_PYTHON,
                discrepancy_categories=[],
                entry_time_diff_seconds=None,
                entry_price_diff=None,
                exit_time_diff_seconds=None,
                exit_price_diff=None,
                volume_diff=None,
                profit_diff=None,
            )
        )

    return matches


def _build_trade_match(mt5_trade: Trade, py_trade: Trade, tol: dict) -> TradeMatch:
    entry_time_diff = _seconds_between(mt5_trade.entry_time, py_trade.entry_time)
    exit_time_diff = _seconds_between(mt5_trade.exit_time, py_trade.exit_time)
    entry_price_diff = round(abs(mt5_trade.entry_price - py_trade.entry_price), 5)
    exit_price_diff = round(abs(mt5_trade.exit_price - py_trade.exit_price), 5)
    volume_diff = round(abs(mt5_trade.volume - py_trade.volume), 5)
    profit_diff = round(abs(mt5_trade.profit - py_trade.profit), 2)

    categories: List[DiscrepancyCategory] = []
    if entry_time_diff > tol["time_seconds"]:
        categories.append(DiscrepancyCategory.ENTRY_TIME)
    if entry_price_diff > tol["price"]:
        categories.append(DiscrepancyCategory.ENTRY_PRICE)
    if exit_time_diff > tol["time_seconds"]:
        categories.append(DiscrepancyCategory.EXIT_TIME)
    if exit_price_diff > tol["price"]:
        categories.append(DiscrepancyCategory.EXIT_PRICE)
    if volume_diff > tol["volume"]:
        categories.append(DiscrepancyCategory.VOLUME)
    if abs(mt5_trade.commission - py_trade.commission) > tol["price"]:
        categories.append(DiscrepancyCategory.COMMISSION)
    if abs(mt5_trade.swap - py_trade.swap) > tol["price"]:
        categories.append(DiscrepancyCategory.SWAP)
    if mt5_trade.sl is not None and py_trade.sl is not None:
        if abs(mt5_trade.sl - py_trade.sl) > tol["price"]:
            categories.append(DiscrepancyCategory.SL)
    if mt5_trade.tp is not None and py_trade.tp is not None:
        if abs(mt5_trade.tp - py_trade.tp) > tol["price"]:
            categories.append(DiscrepancyCategory.TP)

    if not categories:
        status = MatchStatus.MATCH
    elif len(categories) <= 2 and profit_diff <= tol["profit"]:
        status = MatchStatus.WARNING
    else:
        status = MatchStatus.MISMATCH

    return TradeMatch(
        mt5_ticket=mt5_trade.ticket,
        python_ticket=py_trade.ticket,
        status=status,
        discrepancy_categories=categories,
        entry_time_diff_seconds=entry_time_diff,
        entry_price_diff=entry_price_diff,
        exit_time_diff_seconds=exit_time_diff,
        exit_price_diff=exit_price_diff,
        volume_diff=volume_diff,
        profit_diff=profit_diff,
    )


# ---------------------------------------------------------------------------
# Equity comparison (Section 23)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EquityComparisonPoint:
    timestamp: str
    mt5_balance: float
    python_balance: float
    balance_difference: float
    mt5_equity: float
    python_equity: float
    equity_difference: float


def build_equity_comparison(
    mt5_points: Sequence[dict], python_points: Sequence[dict]
) -> List[EquityComparisonPoint]:
    """Gabungkan dua deret equity (per timestamp) menjadi equity_comparison.
    Setiap dict input diharapkan punya key: timestamp, balance, equity."""

    python_by_ts = {p["timestamp"]: p for p in python_points}
    result: List[EquityComparisonPoint] = []
    for mt5_point in mt5_points:
        ts = mt5_point["timestamp"]
        py_point = python_by_ts.get(ts)
        if py_point is None:
            continue
        result.append(
            EquityComparisonPoint(
                timestamp=ts,
                mt5_balance=mt5_point["balance"],
                python_balance=py_point["balance"],
                balance_difference=round(
                    mt5_point["balance"] - py_point["balance"], 2
                ),
                mt5_equity=mt5_point["equity"],
                python_equity=py_point["equity"],
                equity_difference=round(
                    mt5_point["equity"] - py_point["equity"], 2
                ),
            )
        )
    return result


def find_first_divergence(
    equity_comparison: Sequence[EquityComparisonPoint],
    threshold: float = 0.01,
) -> Optional[EquityComparisonPoint]:
    """Titik pertama di mana equity_difference melampaui threshold
    (contoh PRD Section 23: 2026-01-05 13:00, MT5 10,120 vs Python 10,115,
    difference 5)."""
    for point in equity_comparison:
        if abs(point.equity_difference) > threshold:
            return point
    return None


# ---------------------------------------------------------------------------
# MT5 Parity Score (Section 25)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ParityScore:
    trade_matching: float
    entry_accuracy: float
    exit_accuracy: float
    volume_accuracy: float
    sl_accuracy: float
    tp_accuracy: float
    profit_accuracy: float
    equity_accuracy: float
    overall_parity_score: float
    note: str = (
        "Parity score adalah indikator kemiripan, bukan jaminan "
        "kesamaan absolut antara hasil MT5 dan Python."
    )


def _accuracy_from_matches(
    matches: Sequence[TradeMatch], category: Optional[DiscrepancyCategory]
) -> float:
    matched = [m for m in matches if m.status in (MatchStatus.MATCH, MatchStatus.WARNING, MatchStatus.MISMATCH)]
    if not matched:
        return 0.0
    if category is None:
        clean = [m for m in matched if not m.discrepancy_categories]
    else:
        clean = [m for m in matched if category not in m.discrepancy_categories]
    return round((len(clean) / len(matched)) * 100.0, 2)


def compute_parity_score(
    matches: Sequence[TradeMatch],
    equity_comparison: Sequence[EquityComparisonPoint],
    equity_tolerance: float = 0.01,
) -> ParityScore:
    total = len(matches)
    matched_count = sum(
        1 for m in matches
        if m.status in (MatchStatus.MATCH, MatchStatus.WARNING)
    )
    trade_matching = round((matched_count / total) * 100.0, 2) if total else 0.0

    entry_accuracy = _accuracy_from_matches(
        matches, DiscrepancyCategory.ENTRY_PRICE
    )
    exit_accuracy = _accuracy_from_matches(matches, DiscrepancyCategory.EXIT_PRICE)
    volume_accuracy = _accuracy_from_matches(matches, DiscrepancyCategory.VOLUME)
    sl_accuracy = _accuracy_from_matches(matches, DiscrepancyCategory.SL)
    tp_accuracy = _accuracy_from_matches(matches, DiscrepancyCategory.TP)

    matched = [
        m for m in matches
        if m.status in (MatchStatus.MATCH, MatchStatus.WARNING) and m.profit_diff is not None
    ]
    profit_accurate = [m for m in matched if m.profit_diff <= 0.5]
    profit_accuracy = (
        round((len(profit_accurate) / len(matched)) * 100.0, 2) if matched else 0.0
    )

    if equity_comparison:
        equity_accurate = [
            p for p in equity_comparison if abs(p.equity_difference) <= equity_tolerance
        ]
        equity_accuracy = round(
            (len(equity_accurate) / len(equity_comparison)) * 100.0, 2
        )
    else:
        equity_accuracy = 0.0

    components = [
        trade_matching, entry_accuracy, exit_accuracy, volume_accuracy,
        sl_accuracy, tp_accuracy, profit_accuracy, equity_accuracy,
    ]
    overall = round(sum(components) / len(components), 2)

    return ParityScore(
        trade_matching=trade_matching,
        entry_accuracy=entry_accuracy,
        exit_accuracy=exit_accuracy,
        volume_accuracy=volume_accuracy,
        sl_accuracy=sl_accuracy,
        tp_accuracy=tp_accuracy,
        profit_accuracy=profit_accuracy,
        equity_accuracy=equity_accuracy,
        overall_parity_score=overall,
    )


# ---------------------------------------------------------------------------
# Report generator (Section 36 - Output 1)
# ---------------------------------------------------------------------------

class ComparisonReport:
    """Menghasilkan 4 file Output #1 sesuai PRD Section 36:
    comparison.csv, summary.csv, equity_comparison.csv, discrepancies.csv."""

    def __init__(
        self,
        session_id: str,
        mt5_trades: Sequence[Trade],
        python_trades: Sequence[Trade],
        mt5_equity_points: Sequence[dict],
        python_equity_points: Sequence[dict],
        tolerance: Optional[dict] = None,
    ) -> None:
        self.session_id = session_id
        self.matches = match_trades(mt5_trades, python_trades, tolerance)
        self.equity_comparison = build_equity_comparison(
            mt5_equity_points, python_equity_points
        )
        self.first_divergence = find_first_divergence(self.equity_comparison)
        self.parity_score = compute_parity_score(self.matches, self.equity_comparison)

    # -- akses cepat -----------------------------------------------------

    @property
    def discrepancies(self) -> List[TradeMatch]:
        return [
            m for m in self.matches
            if m.status in (
                MatchStatus.WARNING, MatchStatus.MISMATCH,
                MatchStatus.MISSING_MT5, MatchStatus.MISSING_PYTHON,
                MatchStatus.EXTRA_PYTHON,
            )
        ]

    def to_summary_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "total_matches": len(self.matches),
            "match_count": sum(1 for m in self.matches if m.status == MatchStatus.MATCH),
            "warning_count": sum(1 for m in self.matches if m.status == MatchStatus.WARNING),
            "mismatch_count": sum(1 for m in self.matches if m.status == MatchStatus.MISMATCH),
            "missing_mt5_count": sum(1 for m in self.matches if m.status == MatchStatus.MISSING_MT5),
            "missing_python_count": sum(1 for m in self.matches if m.status == MatchStatus.MISSING_PYTHON),
            "extra_python_count": sum(1 for m in self.matches if m.status == MatchStatus.EXTRA_PYTHON),
            "first_divergence": (
                asdict(self.first_divergence) if self.first_divergence else None
            ),
            "parity_score": asdict(self.parity_score),
        }

    # -- ekspor file -------------------------------------------------------

    def write_comparison_csv(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(TradeMatch.__dataclass_fields__.keys())
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for m in self.matches:
                writer.writerow(m.to_row())
        return path

    def write_discrepancies_csv(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(TradeMatch.__dataclass_fields__.keys())
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for m in self.discrepancies:
                writer.writerow(m.to_row())
        return path

    def write_equity_comparison_csv(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(EquityComparisonPoint.__dataclass_fields__.keys())
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for point in self.equity_comparison:
                writer.writerow(asdict(point))
        return path

    def write_summary_csv(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        summary = self.to_summary_dict()
        flat = {
            "session_id": summary["session_id"],
            "total_matches": summary["total_matches"],
            "match_count": summary["match_count"],
            "warning_count": summary["warning_count"],
            "mismatch_count": summary["mismatch_count"],
            "missing_mt5_count": summary["missing_mt5_count"],
            "missing_python_count": summary["missing_python_count"],
            "extra_python_count": summary["extra_python_count"],
            **{f"parity_{k}": v for k, v in summary["parity_score"].items() if k != "note"},
        }
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(flat.keys()))
            writer.writeheader()
            writer.writerow(flat)
        return path

    def to_json(self, path: str | Path, indent: int = 2) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_summary_dict(), indent=indent), encoding="utf-8")
        return path

    def export_all(self, output_dir: str | Path) -> dict:
        output_dir = Path(output_dir)
        return {
            "comparison_csv": str(self.write_comparison_csv(output_dir / "comparison.csv")),
            "summary_csv": str(self.write_summary_csv(output_dir / "summary.csv")),
            "equity_comparison_csv": str(
                self.write_equity_comparison_csv(output_dir / "equity_comparison.csv")
            ),
            "discrepancies_csv": str(
                self.write_discrepancies_csv(output_dir / "discrepancies.csv")
            ),
        }


__all__ = [
    "MatchStatus",
    "DiscrepancyCategory",
    "TradeMatch",
    "match_trades",
    "EquityComparisonPoint",
    "build_equity_comparison",
    "find_first_divergence",
    "ParityScore",
    "compute_parity_score",
    "ComparisonReport",
]


if __name__ == "__main__":
    mt5_trades = [
        Trade("101", "XAUUSD", "BUY", 0.1, "2024-01-05T10:00:05", 2040.0,
              "2024-01-05T14:00:00", 2050.0, 2030.0, 2060.0, -0.5, 0.0, 10.0),
    ]
    python_trades = [
        Trade("1", "XAUUSD", "BUY", 0.1, "2024-01-05T10:00:00", 2040.02,
              "2024-01-05T14:00:00", 2050.0, 2030.0, 2060.0, -0.5, 0.0, 9.98),
    ]
    mt5_equity = [{"timestamp": "2024-01-05T14:00:00", "balance": 10010.0, "equity": 10010.0}]
    py_equity = [{"timestamp": "2024-01-05T14:00:00", "balance": 10009.98, "equity": 10009.98}]

    report = ComparisonReport("SESSION-0001", mt5_trades, python_trades, mt5_equity, py_equity)
    print(json.dumps(report.to_summary_dict(), indent=2, default=str))
