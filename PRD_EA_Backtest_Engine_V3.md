# PRD — EA Backtest Engine V3

**Version:** 3.0  
**Date:** 2026-09-02  
**Status:** Product Requirements Document

## 1. Product Overview

EA Backtest Engine V3 adalah platform backtesting EA berbasis Python yang dirancang untuk mendekati perilaku MetaTrader 5 Strategy Tester, menyediakan Visual Simulator, membandingkan hasil Python dengan hasil backtest MT5, dan membangun Trading Behavior Template dari data historis.

### Dua output utama

1. **Trading Comparison**
   - Perbandingan Python Backtest Simulator vs hasil real MT5.
   - Trade-by-trade, equity, profit, execution, dan discrepancy.
2. **Trading Behavior Template**
   - Template perilaku market berdasarkan sejarah.
   - Mendukung event ekonomi, session, trend, volatility, breakout, retracement, reversal, dan regime.

### Prinsip utama

- Tidak ada AI Explainer untuk menjelaskan kode EA.
- Perhitungan backtest harus deterministic.
- AI hanya digunakan pada analisis perilaku market/trading.
- EA Parser menghasilkan Strategy Intermediate Representation (Strategy IR).
- Parser, Builder, Simulator, Backtest Engine, dan Behavior Engine menggunakan library indikator/signal yang sama.

## 2. Problem Statement

Backtest Python sering menghasilkan hasil yang berbeda dari MT5 karena perbedaan Bid/Ask, spread, tick vs OHLC, intrabar execution, slippage, commission, swap, pending order, SL/TP, trailing stop, hedging/netting, margin, timezone, indikator, dan historical data.

V3 harus menyediakan mekanisme untuk menemukan **titik pertama ketika hasil Python mulai berbeda dari MT5**.

## 3. Goals

- Parse file `.mq5`.
- Mengekstrak input, variable, function, indicator, signal, order, position, dan market API.
- Mengubah EA menjadi Strategy IR.
- Menjalankan strategy melalui Python runtime.
- Menyediakan simulator visual seperti MT5 Visual Mode.
- Menghasilkan backtest yang reproducible.
- Membandingkan hasil Python dengan CSV hasil MT5.
- Mendeteksi first divergence.
- Menganalisis perilaku market historis.
- Membuat dan memvalidasi Behavior Template.
- Mencocokkan kondisi market saat ini dengan template historis.

### Non-Goals

- Menjalankan arbitrary MQL5/system command secara langsung.
- Menggunakan AI untuk menentukan hasil matematis backtest.
- Mengklaim Behavior Template sebagai sinyal trading yang pasti.
- Menggantikan MT5 secara absolut pada tahap awal.

## 4. Architecture

```text
EA .MQ5
   |
   v
EA Parser (AST + Semantic Analysis)
   |
   v
Strategy IR
   |
   +--> Indicator Library
   +--> Signal Library
   +--> Trading Library
   |
   v
Virtual MT5 Runtime
   |
   v
Python Backtest Engine
   |
   +--> Visual Simulator
   |
   +--> Python Results --> MT5 Comparator --> Trading Comparison

Historical Market Data
   |
   v
Behavior Feature Engine
   |
   v
Event / Regime / Pattern Analysis
   |
   v
AI Behavior Analyst
   |
   v
Trading Behavior Template
```

## 5. Project Structure

```text
ea-backtest-engine-v3/
├── README.md
├── PRD_EA_Backtest_Engine_V3.md
├── requirements.txt
├── .env.example
├── .gitignore
├── config.yaml
├── app.py
├── parser/
├── libraries/
│   ├── indicators/
│   ├── signals/
│   ├── market/
│   ├── trading/
│   └── account/
├── runtime/
├── backtest/
├── simulator/
├── comparator/
├── behavior/
├── reports/
├── api/
├── frontend/
├── data/
└── tests/
```

## 6. EA Parser

Parser membaca `.mq5` dan menghasilkan Strategy IR tanpa mengeksekusi arbitrary code.

### Extraction

**Metadata**
- EA name
- Version
- Copyright
- Description
- Magic number

**Inputs**
- input variables
- type
- default value
- range/enum jika tersedia

**Variables**
- Global
- Local
- Static
- Arrays
- Constants
- Enums
- Structs
- Handles

**Functions**
- OnInit
- OnTick
- OnTimer
- OnTrade
- OnTradeTransaction
- OnDeinit
- Custom functions

**Indicators**
- iMA
- iRSI
- iATR
- iMACD
- iStochastic
- iADX
- iBands
- iCCI
- iMomentum
- iMFI
- iOBV
- iSAR
- iFractals
- iIchimoku

**Data access**
- CopyBuffer
- CopyRates
- CopyClose
- CopyOpen
- CopyHigh
- CopyLow
- CopyTickVolume

**Trading API**
- CTrade
- Buy
- Sell
- PositionClose
- PositionModify
- OrderSend
- OrderCheck

**Market API**
- SymbolInfoDouble
- SymbolInfoInteger
- SymbolInfoTick

## 7. Strategy Intermediate Representation

Strategy IR menjadi kontrak bersama antara Parser dan Runtime.

```json
{
  "strategy": {
    "name": "ExampleEA",
    "version": "1.0"
  },
  "inputs": {},
  "indicators": [],
  "conditions": [],
  "entries": [],
  "exits": [],
  "orders": [],
  "risk": {},
  "runtime_events": []
}
```

IR harus menyimpan input parameters, indicator definitions/dependencies, signal conditions, entry/exit rules, SL/TP, trailing, position sizing, sessions, magic number, order type, position model, runtime events, dan parser warnings.

## 8. Shared Indicator Library

Semua komponen menggunakan satu `IndicatorRegistry`.

Minimal:
- SMA, EMA, WMA, SMMA, LWMA, HMA, DEMA, TEMA
- RSI, MACD, Stochastic, CCI, Williams %R, ROC, Momentum
- ATR, Bollinger Bands, Standard Deviation, Keltner Channel, Donchian Channel
- ADX, +DI, -DI, Aroon
- OBV, MFI, Accumulation/Distribution, VWAP
- Highest, Lowest, Pivot, Fractal, Swing High/Low, candle patterns

MQL5 aliases:
```text
iMA -> MA
iRSI -> RSI
iATR -> ATR
iMACD -> MACD
iADX -> ADX
iBands -> Bollinger Bands
```

## 9. Signal Library

Minimal:
```text
crossover()
crossunder()
above()
below()
equal()
rising()
falling()
breakout()
breakdown()
retest()
reversal()
higher_high()
lower_low()
higher_low()
lower_high()
```

Composite conditions:
```text
AND
OR
NOT
N-of-M
```

## 10. Virtual MT5 Runtime

### Market
Bid, Ask, Spread, Point, Digits, Tick Size, Tick Value, Contract Size, Symbol, Time, Timeframe, Session.

### Account
Balance, Equity, Margin, Free Margin, Margin Level.

### Orders
Market, Limit, Stop, Stop-Limit.

### Positions
Open, Modify, Close, Partial Close, SL, TP, Trailing.

Runtime menyediakan simulated server time.

## 11. Python Backtest Engine

Engine mendukung:
- OHLC backtest
- M1-assisted execution
- Tick mode jika tersedia
- Market/Limit/Stop/Stop-Limit
- SL/TP
- Trailing
- Spread
- Slippage
- Commission
- Swap
- Hedging
- Netting
- Multiple positions
- Pending orders
- Grid
- Margin
- Free margin
- Stop-out

## 12. Intrabar Execution Model

Untuk data OHLC, engine mendukung:

```text
PATH_A: Open -> High -> Low -> Close
PATH_B: Open -> Low -> High -> Close
```

Execution modes:
```text
conservative
optimistic
heuristic
m1_reconstruction
real_tick
```

Setiap hasil wajib mencatat execution mode.

## 13. Visual Simulator

Konsep seperti MT5 Visual Mode.

### Controls
- Play
- Pause
- Stop
- Previous candle
- Next candle
- Next tick
- Speed
- Jump to date
- Jump to trade

Speed:
`0.25x, 0.5x, 1x, 2x, 5x, 10x, 50x, 100x`

### Chart
Candlestick, volume, indicators, BUY/SELL markers, entry/exit, SL/TP, trailing, pending orders, grid, current price.

### Account
Initial balance, Balance, Equity, Floating P/L, Margin, Free Margin, Margin Level, Drawdown.

### History
Ticket, Symbol, Direction, Volume, Entry Time, Entry Price, Exit Time, Exit Price, SL, TP, Commission, Swap, Profit.

## 14. MT5 Comparator

### Common trade schema

```text
ticket,symbol,direction,volume,entry_time,entry_price,exit_time,exit_price,sl,tp,commission,swap,profit
```

### Matching

Menggunakan kombinasi:
- Symbol
- Direction
- Volume
- Entry time
- Entry price
- Exit time
- Exit price

### Status

```text
MATCH
WARNING
MISMATCH
MISSING_MT5
MISSING_PYTHON
EXTRA_PYTHON
```

### Outputs

```text
trade_comparison.csv
equity_comparison.csv
summary.csv
discrepancies.csv
```

## 15. First Divergence Point

Comparator menemukan trade/candle pertama ketika state Python != state MT5.

Kategori:
- Entry time/price
- Exit time/price
- Volume
- SL/TP
- Spread
- Commission
- Swap
- Indicator
- Intrabar execution
- Slippage
- Timezone
- Market data

## 16. Parity Score

Komponen:
- Trade Matching
- Entry Accuracy
- Exit Accuracy
- Volume Accuracy
- SL/TP Accuracy
- Profit Accuracy
- Equity Accuracy

Target:
- Initial: >95%
- Mature: >99%

Parity score bukan jaminan identik dengan MT5.

## 17. Trading Behavior Engine

Behavior Engine hanya mempelajari data historis dan tidak menjalankan trading.

### Input
OHLC, Tick, Spread, Volume, Indicator, Session, Economic Event, Trading History.

### Features
Range, Body, Wick, ATR, MFE, MAE, Trend, Range, Compression, Expansion, Breakout, Pullback, Reversal, False Breakout.

### Sessions
Asia, London, New York, London/New York overlap.

## 18. Economic Event Analysis

Events:
- CPI
- NFP
- FOMC
- Interest Rate
- PPI
- GDP
- Unemployment
- Central Bank Speech

Windows:
```text
T-60m
T-30m
T-15m
T-5m
T0
T+5m
T+15m
T+30m
T+60m
T+120m
```

Metrics:
- Initial direction
- Range
- Maximum movement
- Retracement
- Continuation
- Reversal
- False breakout
- Volatility expansion
- MFE
- MAE

## 19. Market Regime Detection

Minimal regimes:
```text
TRENDING
RANGING
COMPRESSION
EXPANSION
HIGH_VOLATILITY
LOW_VOLATILITY
BREAKOUT
PULLBACK
REVERSAL
```

Semua raw calculations deterministic.

## 20. AI Behavior Analyst

AI menerima feature/statistical dataset.

Output:
- Market Context
- Observed Pattern
- Historical Behavior
- Potential Trading Implication
- Risk Consideration
- Confidence

AI tidak boleh mengubah OHLC, probability, profit, indicator, atau trade result.

## 21. Trading Behavior Template

```json
{
  "template_id": "XAUUSD_CPI_V1",
  "symbol": "XAUUSD",
  "event": "CPI",
  "sample_size": 120,
  "pre_event": {},
  "reaction": {},
  "retracement": {},
  "continuation": {},
  "direction": {},
  "risk": {},
  "confidence": 0.82,
  "created_at": "2026-09-02",
  "version": 1,
  "status": "VALIDATED"
}
```

Status:
`DRAFT, VALIDATED, STABLE, DEPRECATED`

## 22. Template Validation

Historical dataset dibagi menjadi:
- Training
- Validation
- Out-of-Sample

Template menjadi STABLE hanya jika pola tetap konsisten pada out-of-sample data.

## 23. Template Matching

Current market dibandingkan dengan template berdasarkan:
- Symbol
- Session
- Event
- Volatility
- ATR
- Trend regime
- Momentum
- Range
- Price structure

Output similarity dan historical reference.

Template adalah referensi historis, bukan jaminan signal.

## 24. API

```http
POST /api/parse-ea
POST /api/run-backtest
POST /api/simulator/start
POST /api/simulator/next
POST /api/compare-mt5
POST /api/analyze-behavior
POST /api/behavior/match
```

## 25. Reproducibility

Setiap run menyimpan:
```text
EA source hash
Strategy IR hash
Historical data hash
Config hash
Engine version
Indicator library version
Execution mode
Random seed
```

## 26. Storage

```text
strategies
strategy_inputs
strategy_ir
backtest_runs
backtest_trades
backtest_equity
mt5_runs
comparison_runs
comparison_trades
discrepancies
behavior_features
behavior_templates
template_versions
```

## 27. Reports

### Backtest Report
Initial/final balance, net profit, gross profit/loss, profit factor, expectancy, win rate, drawdown, Sharpe, Sortino, Calmar, stagnation, trade statistics.

### Comparison Report
MT5 result, Python result, difference, first divergence, parity score, discrepancy categories.

### Behavior Report
Market regime, event reaction, session behavior, direction probability, retracement, continuation, reversal, MFE/MAE, risk characteristics, template version.

## 28. Development Phases

1. Foundation — restructuring, data models, Strategy IR, CSV schema, database, config.
2. EA Parser — lexer, AST, semantic analysis, extraction.
3. Indicator & Signal Library — registry, implementations, aliases, conditions.
4. Backtest Engine — data feed, market, execution, order, position, account, statistics.
5. Visual Simulator — playback, chart, tick player, markers, equity.
6. MT5 Comparator — loaders, normalizer, matcher, equity, divergence, parity.
7. Behavior Engine — features, events, regimes, patterns.
8. AI Behavior Analyst — statistical interpretation and template generation.
9. Integration — UI, APIs, reports, regression tests, optimization.

## 29. Testing

### Unit
Indicator, signal, order, position, account, parser.

### Integration
`MQ5 -> Parser -> Strategy IR -> Runtime -> Backtest -> Result`

### MT5 Regression
EA yang sama dijalankan di MT5 dan Python kemudian dibandingkan.

### Behavior Regression
Template diuji pada training, validation, dan out-of-sample.

## 30. Acceptance Criteria

### Parser
- [ ] `.mq5` terbaca
- [ ] Input terdeteksi
- [ ] Variable terdeteksi
- [ ] Function terdeteksi
- [ ] Indicator terdeteksi
- [ ] CopyBuffer terdeteksi
- [ ] Trading API terdeteksi
- [ ] Strategy IR dibuat
- [ ] Warning untuk construct unsupported

### Backtest
- [ ] Market orders
- [ ] Pending orders
- [ ] SL/TP
- [ ] Trailing
- [ ] Spread
- [ ] Commission
- [ ] Swap
- [ ] Hedging/netting
- [ ] Margin
- [ ] Equity
- [ ] Drawdown

### Simulator
- [ ] Play/Pause/Stop
- [ ] Next candle/tick
- [ ] Speed control
- [ ] Jump date
- [ ] Trade markers
- [ ] Equity
- [ ] Trading history

### Comparator
- [ ] MT5 CSV import
- [ ] Python CSV import
- [ ] Trade matching
- [ ] Equity comparison
- [ ] First divergence
- [ ] Discrepancy classification
- [ ] Four output CSV
- [ ] Parity score

### Behavior
- [ ] Historical features
- [ ] Event analysis
- [ ] Session analysis
- [ ] Regime analysis
- [ ] Pattern analysis
- [ ] Template generation
- [ ] Validation
- [ ] Versioning
- [ ] Matching

## 31. Security

EA source harus dijalankan dalam sandbox.

Dilarang:
- Arbitrary OS command
- Arbitrary filesystem access
- Arbitrary network access
- Membaca secret/API key
- Menjalankan executable eksternal

Runtime hanya memberikan API yang diizinkan.

## 32. Performance

Target awal:
- Vectorized indicator calculation.
- Streaming data feed.
- Indicator cache.
- Incremental playback calculation.
- Parallel backtest untuk optimization.
- Parquet untuk dataset besar.

## 33. Observability

Setiap run memiliki:
```text
run_id
strategy_id
start_time
end_time
engine_version
data_version
execution_mode
status
error
```

Log:
`DEBUG, INFO, WARNING, ERROR`

## 34. Roadmap

### V3.1
More MQL5 constructs, better Strategy IR, more indicators, better MT5 parity.

### V3.2
Advanced optimization, genetic optimization, walk-forward testing, Monte Carlo.

### V3.3
Portfolio engine, multi-symbol simulation, correlation analysis.

### V4.0
Distributed backtesting, cloud execution, advanced market behavior knowledge base, live template matching, MT5 live bridge.

## 35. Final Product Definition

EA Backtest Engine V3 terdiri dari tiga lapisan:

```text
1. STRATEGY ENGINE
   EA -> Parser -> Strategy IR -> Backtest

2. VALIDATION ENGINE
   Python Backtest <-> MT5 Strategy Tester

3. MARKET KNOWLEDGE ENGINE
   Historical Market -> Behavior Analysis -> Trading Behavior Template
```

Dua pertanyaan utama yang dijawab:

**1. Apakah simulator Python saya benar?**  
Melalui MT5 vs Python Trading Comparison.

**2. Bagaimana kebiasaan market berdasarkan sejarah?**  
Melalui Trading Behavior Template.

Kedua output tetap terpisah agar validasi backtest tidak tercampur dengan interpretasi AI terhadap perilaku market.
