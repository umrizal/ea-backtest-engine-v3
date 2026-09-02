from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import hashlib
import json

@dataclass
class IRWarning:
    code: str
    message: str
    severity: str = "warning"

@dataclass
class StrategyMetadata:
    name: str = ""
    version: str = ""
    description: str = ""
    copyright: str = ""
    source_hash: str = ""

@dataclass
class InputParameter:
    name: str
    type: str
    default: Any = None
    group: Optional[str] = None
    description: str = ""

@dataclass
class VariableIR:
    name: str
    type: str
    scope: str = "global"
    initial_value: Any = None
    is_const: bool = False

@dataclass
class IndicatorIR:
    id: str
    kind: str
    function: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeframe: Any = None
    symbol: Any = None
    handle_variable: Optional[str] = None

@dataclass
class BufferIR:
    indicator_id: str
    buffer_index: int
    target_variable: Optional[str] = None

@dataclass
class ConditionIR:
    expression: str
    normalized: str = ""
    purpose: str = "entry"

@dataclass
class VolumeIR:
    mode: str = "fixed"
    value: Any = None
    risk_percent: Any = None

@dataclass
class PriceDistanceIR:
    mode: str = "points"
    value: Any = None
    source: str = ""

@dataclass
class EntryIR:
    id: str
    direction: str
    symbol: Any = "_Symbol"
    volume: VolumeIR = field(default_factory=VolumeIR)
    conditions: List[ConditionIR] = field(default_factory=list)
    sl: Optional[PriceDistanceIR] = None
    tp: Optional[PriceDistanceIR] = None
    source_function: str = ""

@dataclass
class ExitIR:
    id: str
    trigger: str = ""
    conditions: List[ConditionIR] = field(default_factory=list)
    source_function: str = ""

@dataclass
class RiskIR:
    max_spread: Any = None
    max_positions: Any = None
    risk_per_trade: Any = None
    max_drawdown: Any = None
    stop_out_level: Any = None

@dataclass
class SessionIR:
    enabled: bool = False
    start_hour: Any = None
    stop_hour: Any = None
    timezone: str = "broker"

@dataclass
class FunctionIR:
    name: str
    return_type: str = ""
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)
    is_event: bool = False

@dataclass
class StrategyIR:
    metadata: StrategyMetadata = field(default_factory=StrategyMetadata)
    inputs: List[InputParameter] = field(default_factory=list)
    variables: List[VariableIR] = field(default_factory=list)
    indicators: List[IndicatorIR] = field(default_factory=list)
    buffers: List[BufferIR] = field(default_factory=list)
    entries: List[EntryIR] = field(default_factory=list)
    exits: List[ExitIR] = field(default_factory=list)
    risk: RiskIR = field(default_factory=RiskIR)
    session: SessionIR = field(default_factory=SessionIR)
    functions: List[FunctionIR] = field(default_factory=list)
    warnings: List[IRWarning] = field(default_factory=list)
    parser_version: str = "3.0.0-foundation"
    quality_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, default=str)

    def calculate_quality(self) -> float:
        score = 0.0
        score += 15 if self.metadata.name or self.metadata.description else 5
        score += min(20, len(self.inputs) * 2)
        score += min(20, len(self.indicators) * 4)
        score += min(20, len(self.entries) * 10)
        score += min(10, len(self.functions) * 2)
        score += 10 if self.risk.max_spread is not None or self.risk.risk_per_trade is not None else 0
        score -= min(20, len(self.warnings) * 2)
        self.quality_score = max(0.0, min(100.0, score))
        return self.quality_score

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyIR":
        return cls(
            metadata=StrategyMetadata(**data.get("metadata", {})),
            inputs=[InputParameter(**x) for x in data.get("inputs", [])],
            variables=[VariableIR(**x) for x in data.get("variables", [])],
            indicators=[IndicatorIR(**x) for x in data.get("indicators", [])],
            buffers=[BufferIR(**x) for x in data.get("buffers", [])],
            entries=[EntryIR(**{
                **x,
                "volume": VolumeIR(**x.get("volume", {})),
                "conditions": [ConditionIR(**c) for c in x.get("conditions", [])],
                "sl": PriceDistanceIR(**x["sl"]) if x.get("sl") else None,
                "tp": PriceDistanceIR(**x["tp"]) if x.get("tp") else None,
            }) for x in data.get("entries", [])],
            exits=[ExitIR(**{
                **x,
                "conditions": [ConditionIR(**c) for c in x.get("conditions", [])]
            }) for x in data.get("exits", [])],
            risk=RiskIR(**data.get("risk", {})),
            session=SessionIR(**data.get("session", {})),
            functions=[FunctionIR(**x) for x in data.get("functions", [])],
            warnings=[IRWarning(**x) for x in data.get("warnings", [])],
            parser_version=data.get("parser_version", "3.0.0-foundation"),
            quality_score=data.get("quality_score", 0.0),
        )

    def source_hash(self) -> str:
        return self.metadata.source_hash

def calculate_source_hash(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()
