"""
reports/
========
Package laporan untuk EA Backtest Engine V3.

- backtest_report.py    -> Laporan hasil Python Backtest Engine (statistik,
                            trade history, equity curve) sesuai Section 40-41 PRD.
- comparison_report.py  -> Laporan Output #1: MT5 vs Python (comparison.csv,
                            summary.csv, equity_comparison.csv, discrepancies.csv)
                            sesuai Section 20-25 & 36 PRD.
- behavior_report.py    -> Laporan Output #2: Trading Behavior Template
                            (event/session behavior, regime, AI interpretation
                            teks-saja, template versioning & validation)
                            sesuai Section 26-35 & 36 PRD.

Prinsip inti (Section 4 PRD): seluruh angka statistik dihitung
deterministic oleh Python. AI (bila digunakan) hanya menghasilkan teks
interpretasi pada `behavior_report.py` dan tidak pernah mengubah angka.
"""

from .backtest_report import (
    BacktestReport,
    BacktestSession,
    BacktestStatistics,
    EquitySnapshot,
    ReproducibilityInfo,
    Trade,
    compute_statistics,
)
from .comparison_report import (
    ComparisonReport,
    DiscrepancyCategory,
    EquityComparisonPoint,
    MatchStatus,
    ParityScore,
    TradeMatch,
    build_equity_comparison,
    compute_parity_score,
    find_first_divergence,
    match_trades,
)
from .behavior_report import (
    AIInterpretation,
    BehaviorReport,
    EventBehaviorMetrics,
    MarketRegime,
    SessionBehaviorMetrics,
    TemplateMatch,
    TemplateStatus,
    TemplateValidationResult,
    TemplateVersionRecord,
    TradingBehaviorTemplate,
    create_new_template_version,
    request_ai_interpretation,
    validate_template,
)

__all__ = [
    # backtest_report
    "BacktestReport", "BacktestSession", "BacktestStatistics",
    "EquitySnapshot", "ReproducibilityInfo", "Trade", "compute_statistics",
    # comparison_report
    "ComparisonReport", "DiscrepancyCategory", "EquityComparisonPoint",
    "MatchStatus", "ParityScore", "TradeMatch", "build_equity_comparison",
    "compute_parity_score", "find_first_divergence", "match_trades",
    # behavior_report
    "AIInterpretation", "BehaviorReport", "EventBehaviorMetrics",
    "MarketRegime", "SessionBehaviorMetrics", "TemplateMatch",
    "TemplateStatus", "TemplateValidationResult", "TemplateVersionRecord",
    "TradingBehaviorTemplate", "create_new_template_version",
    "request_ai_interpretation", "validate_template",
]
