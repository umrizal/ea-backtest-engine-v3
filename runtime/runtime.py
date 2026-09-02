"""Strategy IR runtime coordinator.

Responsibilities:
- load Strategy IR
- initialize controlled context
- expose compatibility API
- evaluate normalized conditions
- convert entries into TradeRequest objects

It does NOT execute MQL5 source.
"""
import ast
import operator
import re
from typing import Any, Dict, Optional

from .context import (
    RuntimeContext,
    MarketState,
    AccountState,
    TradeRequest,
)
from .mt5_compatibility import MT5Compatibility


class SafeExpressionEvaluator:
    """Restricted expression evaluator for simple Strategy IR conditions."""

    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.And: lambda a, b: a and b,
        ast.Or: lambda a, b: a or b,
    }

    def evaluate(self, expression: str, variables: Dict[str, Any]) -> bool:
        expression = self._normalize(expression)
        try:
            tree = ast.parse(expression, mode="eval")
            value = self._visit(tree.body, variables)
            return bool(value)
        except Exception:
            # Unsupported/unsafe expressions must not silently trigger trades.
            return False

    def _normalize(self, expression: str) -> str:
        expression = expression.replace("&&", " and ")
        expression = expression.replace("||", " or ")
        expression = re.sub(r"(?<![=!<>])!(?!=)", " not ", expression)
        expression = re.sub(r"\btrue\b", "True", expression, flags=re.I)
        expression = re.sub(r"\bfalse\b", "False", expression, flags=re.I)

        # Basic array access normalization: rsi[0] remains valid Python.
        # MQL5 member syntax is not accepted by this restricted evaluator.
        expression = expression.replace("Math.", "")
        return expression

    def _visit(self, node, variables):
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            if node.id not in variables:
                raise ValueError(f"Unknown variable: {node.id}")
            return variables[node.id]

        if isinstance(node, ast.Subscript):
            value = self._visit(node.value, variables)
            index = self._visit(node.slice, variables)
            return value[index]

        if isinstance(node, ast.UnaryOp):
            operand = self._visit(node.operand, variables)
            if isinstance(node.op, ast.Not):
                return not operand
            if isinstance(node.op, ast.USub):
                return -operand
            if isinstance(node.op, ast.UAdd):
                return +operand
            raise ValueError("Unsupported unary operator")

        if isinstance(node, ast.BoolOp):
            values = [self._visit(v, variables) for v in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            if isinstance(node.op, ast.Or):
                return any(values)

        if isinstance(node, ast.BinOp):
            left = self._visit(node.left, variables)
            right = self._visit(node.right, variables)
            fn = self.OPERATORS.get(type(node.op))
            if not fn:
                raise ValueError("Unsupported binary operator")
            return fn(left, right)

        if isinstance(node, ast.Compare):
            left = self._visit(node.left, variables)
            for op_node, comparator in zip(node.ops, node.comparators):
                right = self._visit(comparator, variables)
                fn = self.OPERATORS.get(type(op_node))
                if not fn or not fn(left, right):
                    return False
                left = right
            return True

        raise ValueError(f"Unsupported AST node: {type(node).__name__}")


class StrategyRuntime:
    """Controlled runtime for a parsed Strategy IR."""

    def __init__(
        self,
        strategy_ir: Any,
        market: Optional[MarketState] = None,
        account: Optional[AccountState] = None,
    ):
        self.strategy_ir = strategy_ir
        self.context = RuntimeContext(market=market, account=account)
        self.mt5 = MT5Compatibility(self.context)
        self.evaluator = SafeExpressionEvaluator()

        self._load_inputs()

    def _load_inputs(self) -> None:
        for item in getattr(self.strategy_ir, "inputs", []):
            value = item.default
            self.context.inputs[item.name] = self._parse_scalar(value)

    def _parse_scalar(self, value: Any) -> Any:
        if value is None:
            return None

        if not isinstance(value, str):
            return value

        value = value.strip().strip('"')

        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False

        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value

    def set_input(self, name: str, value: Any) -> None:
        self.context.inputs[name] = value

    def update_market(self, market: MarketState) -> None:
        self.context.market = market

    def set_indicator(self, name: str, value: Any) -> None:
        self.context.set_indicator(name, value)

    def set_buffer(self, name: str, values) -> None:
        self.context.set_buffer(name, values)

    def variables(self) -> Dict[str, Any]:
        variables = dict(self.context.inputs)
        variables.update(self.context.variables)

        variables.update({
            "_Symbol": self.context.market.symbol,
            "Bid": self.context.market.bid,
            "Ask": self.context.market.ask,
            "Open": self.context.market.open,
            "High": self.context.market.high,
            "Low": self.context.market.low,
            "Close": self.context.market.close,
            "Volume": self.context.market.volume,
            "Spread": self.context.market.spread_points,
        })

        return variables

    def evaluate_condition(self, expression: str) -> bool:
        return self.evaluator.evaluate(expression, self.variables())

    def evaluate_entry(self, entry: Any) -> bool:
        if not entry.conditions:
            return True

        return all(
            self.evaluate_condition(condition.expression)
            for condition in entry.conditions
            if condition.expression
        )

    def generate_entry_requests(self):
        """Generate normalized trade requests from currently valid entries."""
        requests = []

        for entry in getattr(self.strategy_ir, "entries", []):
            if not self.evaluate_entry(entry):
                continue

            volume = self._resolve_volume(entry.volume)
            if volume <= 0:
                continue

            request = TradeRequest(
                action="DEAL",
                symbol=entry.symbol if entry.symbol not in (None, "") else self.context.symbol(),
                direction=entry.direction.upper(),
                volume=volume,
                price=(
                    self.context.ask()
                    if entry.direction.upper() == "BUY"
                    else self.context.bid()
                ),
                magic=0,
                comment="EA-BACKTEST-V3",
            )
            requests.append(request)

        return requests

    def _resolve_volume(self, volume_ir: Any) -> float:
        mode = getattr(volume_ir, "mode", "fixed")
        value = getattr(volume_ir, "value", None)

        if mode == "fixed":
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0

        if mode == "risk_percent":
            # Actual risk-based lot sizing belongs to Risk/Account Engine.
            # Runtime deliberately does not invent broker contract specs.
            return 0.0

        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def step(self) -> Dict[str, Any]:
        """One deterministic strategy evaluation step."""
        requests = self.generate_entry_requests()

        return {
            "symbol": self.context.symbol(),
            "timestamp": self.context.market.timestamp.isoformat()
            if self.context.market.timestamp else None,
            "entry_count": len(requests),
            "requests": [
                {
                    "action": x.action,
                    "symbol": x.symbol,
                    "direction": x.direction,
                    "volume": x.volume,
                    "price": x.price,
                    "sl": x.sl,
                    "tp": x.tp,
                    "magic": x.magic,
                    "comment": x.comment,
                }
                for x in requests
            ],
        }
