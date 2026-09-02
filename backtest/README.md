# EA Backtest Engine V3 — Backtest Package

Fondasi deterministic backtesting untuk EA Backtest Engine V3.

## Modul

- `data_feed.py` — OHLC/tick feed dan normalisasi CSV.
- `market_engine.py` — bid/ask, spread, snapshot, intrabar path.
- `order_engine.py` — market/limit/stop/stop-limit order lifecycle.
- `position_engine.py` — position lifecycle, floating P/L, SL/TP.
- `account_engine.py` — balance, equity, margin, free margin, drawdown.
- `execution_engine.py` — deterministic fill, slippage, commission dan trade ledger.
- `statistics.py` — statistik performa.
- `engine.py` — orchestrator utama.

## Execution modes

`conservative`, `optimistic`, `heuristic`, `m1_reconstruction`, `real_tick`.

Package ini menyediakan fondasi untuk kelima mode; `m1_reconstruction` dan
`real_tick` membutuhkan feed M1/tick yang sesuai pada integrasi berikutnya.

## Strategy callback

```python
from backtest import BacktestEngine, BacktestConfig, MarketBar

def strategy(bar, ctx):
    if bar.close > bar.open:
        return {
            "action": "BUY",
            "volume": 0.01,
            "sl": bar.close - 2,
            "tp": bar.close + 4,
        }

engine = BacktestEngine(BacktestConfig(symbol="XAUUSD"))
result = engine.run(bars, strategy)

print(result.statistics)
```

## CSV format

Minimum:

```csv
time,open,high,low,close
2026-01-01T00:00:00+00:00,100,101,99,100.5
```

Optional:

```csv
time,open,high,low,close,volume,spread_points
```

## Prinsip

- Tidak ada broker/network call.
- Deterministic.
- Tidak mengeksekusi MQL5 secara langsung.
- Runtime/Strategy IR menjadi sumber request trading.
- Trade ledger dan equity curve siap dipakai comparator MT5.

## Catatan kompatibilitas

Ini adalah **foundation backtest V3**, bukan klaim parity MT5 100%.
Akurasi parity membutuhkan data historis yang sama, timezone yang sama,
spread/slippage/commission/swap yang sama, serta execution model yang sama.
