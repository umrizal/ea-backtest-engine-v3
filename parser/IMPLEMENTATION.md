# Parser Implementation Notes

## Design goals

1. Deterministic.
2. Tidak mengeksekusi source MQL5.
3. Menghasilkan Strategy IR yang dapat dipakai bersama oleh:
   - Backtest Engine
   - Visual Simulator
   - MT5 Comparator
   - Trading Behavior Engine

## Modular files

- `lexer.py`: tokenization.
- `parser.py`: static extraction menjadi IR.
- `semantic_analyzer.py`: semantic sanity checks.
- `variable_extractor.py`: variable layer.
- `function_extractor.py`: function/event layer.
- `indicator_extractor.py`: indicator + buffer layer.
- `trading_extractor.py`: order/risk/session layer.
- `strategy_ir.py`: canonical intermediate representation.

## Next hardening

- recursive-descent expression parser
- symbol table and scope resolution
- overloaded functions
- class/member resolution
- CTrade lifecycle
- OrderSend/MqlTradeRequest parsing
- SL/TP/trailing extraction
- grid/layer/re-entry detection
- multi-timeframe dependency graph
- indicator buffer semantics
- enum resolution
- include dependency graph
- regression corpus against real MQL5 EAs
