# EA Backtest Engine V3 — Visual Simulator Package

Playback/session engine untuk menggerakkan data historis secara interaktif.
Package ini tidak bergantung pada browser atau Flask sehingga dapat dipasang
di route API dan frontend V3.

## Fitur

- Play / Pause / Stop
- Previous / Next candle
- Next tick
- Speed: 0.25x, 0.5x, 1x, 2x, 5x, 10x, 50x, 100x
- Jump by index/date/trade
- Candle visibility sampai posisi playback saat ini
- Tick playback
- Position / pending order / trade state
- Indicator state
- BUY/SELL/entry/exit/SL/TP/trailing markers melalui callback
- Session ID untuk multi-session
- Snapshot JSON-ready untuk API/frontend
- Equity/account state siap diisi oleh Backtest Engine

## Integrasi dengan Backtest Engine

Simulator sebaiknya menggunakan library dan runtime yang sama dengan backtest.
Callback dapat menjalankan satu langkah strategy/runtime:

```python
session.set_step_callback(
    lambda bar, session: strategy_runtime_step(bar, session)
)
```

Callback dapat mengembalikan:

```python
{
    "positions": [...],
    "pending_orders": [...],
    "trades": [...],
    "indicators": {...},
    "markers": [
        {"type": "BUY", "price": 100.5, "time": "..."}
    ]
}
```

## API route yang disiapkan untuk tahap berikut

- `POST /api/simulator/start`
- `POST /api/simulator/next`
- `POST /api/simulator/previous`
- `POST /api/simulator/next-tick`
- `POST /api/simulator/pause`
- `POST /api/simulator/stop`
- `POST /api/simulator/speed`
- `POST /api/simulator/jump-date`
- `POST /api/simulator/jump-trade`
- `GET  /api/simulator/{session_id}`

## Prinsip arsitektur

Simulator adalah playback/state layer, bukan backtest engine kedua.
Perhitungan trading tetap berasal dari Runtime + Backtest/Execution Engine.
Dengan demikian visual simulator dan batch backtest dapat memakai aturan
strategy, indicator, market dan trading yang sama.

## Catatan

File ini adalah foundation simulator. Rendering candlestick/chart, WebSocket,
dan route Flask akan dipasang pada layer `api/` + `frontend/` berikutnya.
