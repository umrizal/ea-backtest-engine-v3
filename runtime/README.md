# EA Backtest Engine V3 — Runtime

Runtime layer untuk menjalankan **Strategy IR** secara aman dan deterministik.

## Arsitektur

```text
MQL5
  ↓
Parser
  ↓
Strategy IR
  ↓
Runtime
  ├── RuntimeContext
  ├── MT5Compatibility
  └── SafeExpressionEvaluator
  ↓
TradeRequest
  ↓
Backtest Execution Engine
```

Runtime **tidak menjalankan source MQL5**.

## File

- `context.py`
  - MarketState
  - AccountState
  - Position
  - PendingOrder
  - TradeRequest
  - TradeResult
  - RuntimeContext

- `mt5_compatibility.py`
  - facade API bergaya MT5
  - SymbolInfoDouble
  - SymbolInfoInteger
  - PositionsTotal
  - PositionSelect
  - CopyBuffer
  - OrderSend

- `runtime.py`
  - StrategyRuntime
  - input loading
  - market update
  - indicator/buffer injection
  - safe condition evaluation
  - entry request generation

## Contoh

```python
from parser import EAParser
from runtime import StrategyRuntime, MarketState

source = open("MyEA.mq5", encoding="utf-8").read()
ir = EAParser().parse(source)

market = MarketState(
    symbol="XAUUSD",
    timeframe="M15",
    bid=4000.10,
    ask=4000.30,
    open=3995.00,
    high=4005.00,
    low=3990.00,
    close=4000.10,
    spread_points=20,
)

runtime = StrategyRuntime(ir, market=market)

result = runtime.step()
print(result)
```

## Prinsip penting

Runtime hanya menghasilkan **TradeRequest**.

Pengisian order, slippage, spread, commission, swap, margin, SL/TP hit, trailing, hedging/netting, dan lifecycle posisi harus dilakukan oleh `backtest/execution_engine.py`, bukan runtime.

Dengan pemisahan ini:

```text
Strategy Logic
      ↓
Runtime
      ↓
Trade Request
      ↓
Execution Engine
      ↓
Position / Account
```

hasil lebih mudah dibandingkan dengan MT5 Strategy Tester.
