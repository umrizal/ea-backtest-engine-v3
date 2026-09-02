"""Small MT5-compatible facade for Strategy IR runtime.

This is a compatibility layer, not the MetaTrader 5 Python package.
Methods return deterministic values from RuntimeContext.
"""
from typing import Any, Optional
from .context import RuntimeContext, TradeRequest


class MT5Compatibility:
    # Common MT5 constants
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5

    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5

    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1

    PRICE_OPEN = 0
    PRICE_HIGH = 1
    PRICE_LOW = 2
    PRICE_CLOSE = 3

    def __init__(self, context: RuntimeContext):
        self.context = context

    def Symbol(self) -> str:
        return self.context.symbol()

    def SymbolInfoDouble(self, symbol: str, prop: str) -> float:
        if symbol != self.context.symbol():
            return 0.0

        mapping = {
            "SYMBOL_BID": self.context.bid(),
            "SYMBOL_ASK": self.context.ask(),
            "SYMBOL_POINT": self.context.point(),
        }
        return float(mapping.get(prop, 0.0))

    def SymbolInfoInteger(self, symbol: str, prop: str) -> int:
        if symbol != self.context.symbol():
            return 0

        mapping = {
            "SYMBOL_DIGITS": self.context.digits(),
            "SYMBOL_SPREAD": int(round(self.context.spread_points())),
        }
        return int(mapping.get(prop, 0))

    def PositionsTotal(self) -> int:
        return self.context.position_count()

    def PositionSelect(self, symbol: str) -> bool:
        return self.context.has_position(symbol)

    def CopyBuffer(
        self,
        handle: str,
        buffer_num: int,
        start_pos: int,
        count: int,
        target: Optional[list] = None,
    ) -> int:
        key = f"{handle}:{buffer_num}"
        values = self.context.buffers.get(key, [])

        selected = values[start_pos:start_pos + count]
        if target is not None:
            target.clear()
            target.extend(selected)

        return len(selected)

    def OrderSend(self, request: Any) -> Any:
        """Translate a normalized request into RuntimeContext.

        The returned object is deliberately simple. The execution engine
        later decides whether/how the request is filled.
        """
        if isinstance(request, dict):
            req = TradeRequest(
                action=str(request.get("action", "DEAL")),
                symbol=str(request.get("symbol", self.context.symbol())),
                direction=request.get("direction"),
                volume=float(request.get("volume", 0.0)),
                price=request.get("price"),
                sl=request.get("sl"),
                tp=request.get("tp"),
                deviation=int(request.get("deviation", 0)),
                magic=int(request.get("magic", 0)),
                comment=str(request.get("comment", "")),
            )
        else:
            req = TradeRequest(
                action=getattr(request, "action", "DEAL"),
                symbol=getattr(request, "symbol", self.context.symbol()),
                direction=getattr(request, "direction", None),
                volume=float(getattr(request, "volume", 0.0)),
                price=getattr(request, "price", None),
                sl=getattr(request, "sl", None),
                tp=getattr(request, "tp", None),
                deviation=int(getattr(request, "deviation", 0)),
                magic=int(getattr(request, "magic", 0)),
                comment=str(getattr(request, "comment", "")),
            )

        return self.context.submit(req)
