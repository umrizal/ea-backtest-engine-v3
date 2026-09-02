"""Runtime state and deterministic execution context.

The runtime is intentionally independent from MQL5 execution.
Strategy IR is evaluated against this controlled context.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class MarketState:
    symbol: str
    timeframe: str = "M1"
    timestamp: Optional[datetime] = None

    bid: float = 0.0
    ask: float = 0.0
    last: float = 0.0

    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0

    spread_points: float = 0.0
    point: float = 0.00001
    digits: int = 5

    indicators: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    ticket: int
    symbol: str
    direction: str
    volume: float
    entry_price: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    magic: int = 0
    comment: str = ""
    open_time: Optional[datetime] = None
    floating_profit: float = 0.0


@dataclass
class PendingOrder:
    ticket: int
    symbol: str
    order_type: str
    volume: float
    price: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    magic: int = 0
    comment: str = ""
    created_time: Optional[datetime] = None


@dataclass
class AccountState:
    balance: float = 10000.0
    equity: float = 10000.0
    margin: float = 0.0
    free_margin: float = 10000.0
    margin_level: float = 0.0

    leverage: int = 100
    currency: str = "USD"

    positions: List[Position] = field(default_factory=list)
    pending_orders: List[PendingOrder] = field(default_factory=list)


@dataclass
class TradeRequest:
    action: str
    symbol: str
    direction: Optional[str] = None
    volume: float = 0.0
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    deviation: int = 0
    magic: int = 0
    comment: str = ""


@dataclass
class TradeResult:
    success: bool
    retcode: int
    message: str
    ticket: Optional[int] = None
    price: Optional[float] = None
    volume: Optional[float] = None


class RuntimeContext:
    """Controlled API exposed to strategy execution."""

    def __init__(
        self,
        market: Optional[MarketState] = None,
        account: Optional[AccountState] = None,
    ):
        self.market = market or MarketState(symbol="XAUUSD")
        self.account = account or AccountState()

        self.inputs: Dict[str, Any] = {}
        self.variables: Dict[str, Any] = {}
        self.handles: Dict[str, Any] = {}
        self.buffers: Dict[str, List[float]] = {}

        self.trade_requests: List[TradeRequest] = []
        self.trade_results: List[TradeResult] = []

        self._next_ticket = 1

    def next_ticket(self) -> int:
        ticket = self._next_ticket
        self._next_ticket += 1
        return ticket

    # ------------------------------------------------------------------
    # Market API
    # ------------------------------------------------------------------

    def symbol(self) -> str:
        return self.market.symbol

    def bid(self) -> float:
        return self.market.bid

    def ask(self) -> float:
        return self.market.ask

    def point(self) -> float:
        return self.market.point

    def digits(self) -> int:
        return self.market.digits

    def spread_points(self) -> float:
        return self.market.spread_points

    def bar(self) -> Dict[str, float]:
        return {
            "open": self.market.open,
            "high": self.market.high,
            "low": self.market.low,
            "close": self.market.close,
            "volume": self.market.volume,
        }

    # ------------------------------------------------------------------
    # Indicator API
    # ------------------------------------------------------------------

    def set_indicator(self, name: str, value: Any) -> None:
        self.market.indicators[name] = value

    def indicator(self, name: str, default: Any = None) -> Any:
        return self.market.indicators.get(name, default)

    def set_buffer(self, name: str, values: List[float]) -> None:
        self.buffers[name] = list(values)

    def buffer(self, name: str, shift: int = 0) -> Optional[float]:
        values = self.buffers.get(name, [])
        if shift < 0 or shift >= len(values):
            return None
        return values[shift]

    # ------------------------------------------------------------------
    # Position API
    # ------------------------------------------------------------------

    def positions(self, symbol: Optional[str] = None) -> List[Position]:
        if symbol is None:
            return list(self.account.positions)
        return [p for p in self.account.positions if p.symbol == symbol]

    def position_count(self, symbol: Optional[str] = None) -> int:
        return len(self.positions(symbol))

    def has_position(self, symbol: str, direction: Optional[str] = None) -> bool:
        positions = self.positions(symbol)
        if direction is None:
            return bool(positions)
        return any(p.direction.upper() == direction.upper() for p in positions)

    # ------------------------------------------------------------------
    # Controlled trading request API
    # ------------------------------------------------------------------

    def submit(self, request: TradeRequest) -> TradeResult:
        """Record a trade request.

        Actual fill/execution belongs to the Backtest Execution Engine.
        Runtime does not directly touch a broker or OS.
        """
        self.trade_requests.append(request)
        result = TradeResult(
            success=True,
            retcode=10000,
            message="REQUEST_ACCEPTED",
            volume=request.volume,
            price=request.price,
        )
        self.trade_results.append(result)
        return result
