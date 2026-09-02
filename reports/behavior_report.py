"""
reports/behavior_report.py
============================

Modul laporan untuk Module 10 - Market Behavior Engine, AI Behavior
Analyst, dan Trading Behavior Template Engine.

Referensi PRD:
    - Section 26 (Module 10 - Market Behavior Engine)
    - Section 27 (Event Behavior Analysis)     -> window T-60m .. T+120m
    - Section 28 (Behavior Metrics)            -> metrik per event
    - Section 29 (Session Behavior)            -> metrik per sesi
    - Section 30 (Market Regime)               -> label regime
    - Section 31 (AI Behavior Analyst)         -> AI hanya interpretasi
    - Section 32 (Trading Behavior Template)   -> skema template
    - Section 33 (Template Versioning)         -> riwayat versi
    - Section 34 (Template Validation)         -> status DRAFT/VALIDATED/...
    - Section 36 (Output 2 - Trading Behavior Template)

Core Principle (Section 4) yang WAJIB dijaga di modul ini:
    "AI tidak boleh mengubah angka statistik."
AI (Layer 3) hanya boleh menghasilkan teks interpretasi (Behavior
Interpretation, Market Context, Observed Pattern, Potential Trading
Implication, Risk Consideration) — bukan mengubah sample_size, probability,
range, ataupun metrik numerik lain yang sudah dihitung secara deterministic
oleh Python.
"""

from __future__ import annotations

import copy
import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Event window (Section 27)
# ---------------------------------------------------------------------------

EVENT_WINDOWS = [
    "T-60m", "T-30m", "T-15m", "T-5m", "T0",
    "T+5m", "T+15m", "T+30m", "T+60m", "T+120m",
]

KNOWN_EVENTS = [
    "CPI", "NFP", "FOMC", "PPI", "Interest Rate", "GDP",
    "Unemployment", "Powell Speech",
]


# ---------------------------------------------------------------------------
# Behavior metrics (Section 28 - per event, Section 29 - per session)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EventBehaviorMetrics:
    """Metrik behavior untuk satu event pada satu window (Section 28)."""

    event: str
    window: str
    sample_size: int
    average_range: float
    median_range: float
    maximum_range: float
    minimum_range: float
    initial_direction: str          # "UP" | "DOWN" | "MIXED"
    retracement_probability: float
    continuation_probability: float
    reversal_probability: float
    false_breakout_probability: float
    maximum_favorable_excursion: float
    maximum_adverse_excursion: float
    volatility_expansion: float


@dataclass(frozen=True)
class SessionBehaviorMetrics:
    """Metrik behavior untuk satu sesi trading (Section 29)."""

    session: str  # "Asian" | "London" | "New York" | "London/New York Overlap"
    sample_size: int
    average_range: float
    trend_probability: float
    breakout_probability: float
    reversal_probability: float
    volatility: float
    average_move: float


class MarketRegime(str, Enum):
    """Section 30 - Market Regime, regime dapat dikombinasikan dengan
    event (mis. "CPI + Compression")."""

    TRENDING = "Trending"
    RANGE = "Range"
    COMPRESSION = "Compression"
    EXPANSION = "Expansion"
    HIGH_VOLATILITY = "High Volatility"
    LOW_VOLATILITY = "Low Volatility"
    BREAKOUT = "Breakout"
    PULLBACK = "Pullback"
    REVERSAL = "Reversal"


# ---------------------------------------------------------------------------
# AI Behavior Analyst (Section 31) - interpretasi teks saja
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AIInterpretation:
    """AI hanya menerima statistical feature dataset dan menghasilkan teks
    interpretasi. AI TIDAK diperbolehkan mengubah angka statistik apa pun."""

    behavior_interpretation: str
    market_context: str
    observed_pattern: str
    potential_trading_implication: str
    risk_consideration: str


def request_ai_interpretation(
    statistical_features: dict,
    interpreter: Callable[[dict], AIInterpretation],
) -> AIInterpretation:
    """Panggil fungsi/model AI eksternal (`interpreter`) untuk menghasilkan
    interpretasi dari `statistical_features`, dengan safeguard yang
    memastikan input numerik tidak diubah oleh proses AI (Core Principle
    Section 4: AI hanya untuk interpretasi behavior, bukan menghitung).
    """
    snapshot_before = copy.deepcopy(statistical_features)
    interpretation = interpreter(statistical_features)
    if statistical_features != snapshot_before:
        raise RuntimeError(
            "AI interpreter mengubah statistical_features. "
            "Ini melanggar Core Principle PRD: AI tidak boleh mengubah "
            "angka statistik."
        )
    if not isinstance(interpretation, AIInterpretation):
        raise TypeError(
            "interpreter harus mengembalikan instance AIInterpretation "
            "(hanya field teks, tanpa field numerik)."
        )
    return interpretation


# ---------------------------------------------------------------------------
# Trading Behavior Template (Section 32-34)
# ---------------------------------------------------------------------------

class TemplateStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    STABLE = "STABLE"
    DEPRECATED = "DEPRECATED"


@dataclass
class TradingBehaviorTemplate:
    """Skema persis sesuai Section 32."""

    template_id: str
    symbol: str
    event: str
    sample_size: int
    pre_event: dict
    reaction: dict
    retracement: dict
    continuation: dict
    direction: dict
    risk: dict
    confidence: float
    version: int = 1
    status: TemplateStatus = TemplateStatus.DRAFT
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    ai_interpretation: Optional[AIInterpretation] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass(frozen=True)
class TemplateVersionRecord:
    """Riwayat versi wajib disimpan setiap kali template diperbarui
    (Section 33): sample_size, previous_version, new_evidence,
    changed_metrics, confidence_change, creation_date."""

    template_id: str
    previous_version: int
    new_version: int
    sample_size: int
    new_evidence: int
    changed_metrics: List[str]
    confidence_change: float
    creation_date: str


def create_new_template_version(
    previous: TradingBehaviorTemplate,
    updated_fields: dict,
    new_evidence_count: int,
) -> tuple[TradingBehaviorTemplate, TemplateVersionRecord]:
    """Buat versi baru dari template tanpa menimpa versi lama, sesuai
    Section 33 (contoh: XAUUSD_CPI_V1 -> XAUUSD_CPI_V2)."""

    changed_metrics = [
        key for key, value in updated_fields.items()
        if key != "confidence" and getattr(previous, key, None) != value
    ]
    new_confidence = updated_fields.get("confidence", previous.confidence)
    confidence_change = round(new_confidence - previous.confidence, 4)

    new_version_number = previous.version + 1
    new_template = TradingBehaviorTemplate(
        template_id=_bump_template_id(previous.template_id, new_version_number),
        symbol=previous.symbol,
        event=previous.event,
        sample_size=updated_fields.get(
            "sample_size", previous.sample_size + new_evidence_count
        ),
        pre_event=updated_fields.get("pre_event", previous.pre_event),
        reaction=updated_fields.get("reaction", previous.reaction),
        retracement=updated_fields.get("retracement", previous.retracement),
        continuation=updated_fields.get("continuation", previous.continuation),
        direction=updated_fields.get("direction", previous.direction),
        risk=updated_fields.get("risk", previous.risk),
        confidence=new_confidence,
        version=new_version_number,
        status=TemplateStatus.DRAFT,
    )
    record = TemplateVersionRecord(
        template_id=previous.template_id,
        previous_version=previous.version,
        new_version=new_version_number,
        sample_size=new_template.sample_size,
        new_evidence=new_evidence_count,
        changed_metrics=changed_metrics,
        confidence_change=confidence_change,
        creation_date=new_template.created_at,
    )
    return new_template, record


def _bump_template_id(template_id: str, new_version: int) -> str:
    """"XAUUSD_CPI_V1" -> "XAUUSD_CPI_V2" (Section 33)."""
    if "_V" in template_id:
        base = template_id.rsplit("_V", 1)[0]
        return f"{base}_V{new_version}"
    return f"{template_id}_V{new_version}"


# ---------------------------------------------------------------------------
# Template validation (Section 34) & usage/matching (Section 35)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TemplateValidationResult:
    template_id: str
    status: TemplateStatus
    validation_sample_size: int
    out_of_sample_accuracy: float
    notes: str = ""


def validate_template(
    template: TradingBehaviorTemplate,
    out_of_sample_accuracy: float,
    validation_sample_size: int,
    stable_threshold: float = 0.75,
    validated_threshold: float = 0.6,
) -> TemplateValidationResult:
    """Uji template dengan out-of-sample data (Section 34)."""
    if out_of_sample_accuracy >= stable_threshold and validation_sample_size >= template.sample_size:
        status = TemplateStatus.STABLE
    elif out_of_sample_accuracy >= validated_threshold:
        status = TemplateStatus.VALIDATED
    else:
        status = TemplateStatus.DEPRECATED
    return TemplateValidationResult(
        template_id=template.template_id,
        status=status,
        validation_sample_size=validation_sample_size,
        out_of_sample_accuracy=out_of_sample_accuracy,
    )


@dataclass(frozen=True)
class TemplateMatch:
    """Output template matching untuk kondisi market baru (Section 35)."""

    matching_template_id: str
    similarity_pct: float
    historical_sample_size: int
    observed_behavior_summary: str
    disclaimer: str = "Template merupakan reference, bukan jaminan arah market."


# ---------------------------------------------------------------------------
# Report generator (Output #2, Section 36)
# ---------------------------------------------------------------------------

class BehaviorReport:
    """Menggabungkan event behavior, session behavior, regime, template,
    dan (opsional) interpretasi AI menjadi satu laporan behavior."""

    def __init__(
        self,
        symbol: str,
        event_metrics: Sequence[EventBehaviorMetrics] = (),
        session_metrics: Sequence[SessionBehaviorMetrics] = (),
        regimes_observed: Sequence[MarketRegime] = (),
        templates: Sequence[TradingBehaviorTemplate] = (),
    ) -> None:
        self.symbol = symbol
        self.event_metrics = list(event_metrics)
        self.session_metrics = list(session_metrics)
        self.regimes_observed = list(regimes_observed)
        self.templates = list(templates)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "event_metrics": [asdict(m) for m in self.event_metrics],
            "session_metrics": [asdict(m) for m in self.session_metrics],
            "regimes_observed": [r.value for r in self.regimes_observed],
            "templates": [t.to_dict() for t in self.templates],
        }

    # -- ekspor ------------------------------------------------------------

    def to_json(self, path: str | Path, indent: int = 2) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=indent), encoding="utf-8")
        return path

    def write_event_metrics_csv(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(EventBehaviorMetrics.__dataclass_fields__.keys())
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for m in self.event_metrics:
                writer.writerow(asdict(m))
        return path

    def write_session_metrics_csv(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(SessionBehaviorMetrics.__dataclass_fields__.keys())
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for m in self.session_metrics:
                writer.writerow(asdict(m))
        return path

    def write_templates_json(self, path: str | Path, indent: int = 2) -> Path:
        """Ekspor seluruh Trading Behavior Template (Output #2 utama)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [t.to_dict() for t in self.templates]
        path.write_text(json.dumps(payload, indent=indent), encoding="utf-8")
        return path

    def export_all(self, output_dir: str | Path) -> dict:
        output_dir = Path(output_dir)
        return {
            "event_metrics_csv": str(
                self.write_event_metrics_csv(output_dir / "event_behavior.csv")
            ),
            "session_metrics_csv": str(
                self.write_session_metrics_csv(output_dir / "session_behavior.csv")
            ),
            "templates_json": str(
                self.write_templates_json(output_dir / "behavior_templates.json")
            ),
            "behavior_report_json": str(
                self.to_json(output_dir / "behavior_report.json")
            ),
        }


__all__ = [
    "EVENT_WINDOWS",
    "KNOWN_EVENTS",
    "EventBehaviorMetrics",
    "SessionBehaviorMetrics",
    "MarketRegime",
    "AIInterpretation",
    "request_ai_interpretation",
    "TemplateStatus",
    "TradingBehaviorTemplate",
    "TemplateVersionRecord",
    "create_new_template_version",
    "TemplateValidationResult",
    "validate_template",
    "TemplateMatch",
    "BehaviorReport",
]


if __name__ == "__main__":
    event_metrics = EventBehaviorMetrics(
        event="CPI", window="T+15m", sample_size=32,
        average_range=185.4, median_range=170.0, maximum_range=420.0,
        minimum_range=45.0, initial_direction="UP",
        retracement_probability=0.68, continuation_probability=0.72,
        reversal_probability=0.28, false_breakout_probability=0.12,
        maximum_favorable_excursion=210.5, maximum_adverse_excursion=-90.2,
        volatility_expansion=2.4,
    )
    template = TradingBehaviorTemplate(
        template_id="XAUUSD_CPI_V1",
        symbol="XAUUSD",
        event="CPI",
        sample_size=32,
        pre_event={"avg_range_pre_60m": 60.2},
        reaction={"avg_initial_expansion": 185.4, "direction": "UP"},
        retracement={"probability": 0.68},
        continuation={"probability": 0.72},
        direction={"up": 0.6, "down": 0.4},
        risk={"max_adverse_excursion": -90.2},
        confidence=0.84,
    )

    def dummy_interpreter(features: dict) -> AIInterpretation:
        return AIInterpretation(
            behavior_interpretation="Market cenderung expand tajam lalu retrace.",
            market_context="CPI rilis pada sesi New York dengan volatilitas tinggi.",
            observed_pattern="Initial expansion diikuti retracement ~68% kasus.",
            potential_trading_implication="Fade awal breakout berpotensi profitable.",
            risk_consideration="MAE historis cukup besar, perlu SL lebar.",
        )

    interpretation = request_ai_interpretation(asdict(event_metrics), dummy_interpreter)

    report = BehaviorReport(
        symbol="XAUUSD",
        event_metrics=[event_metrics],
        regimes_observed=[MarketRegime.COMPRESSION, MarketRegime.HIGH_VOLATILITY],
        templates=[template],
    )
    print(json.dumps(report.to_dict(), indent=2, default=str))
    print("\nAI Interpretation:", asdict(interpretation))
