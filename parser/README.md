# Parser Module — EA Backtest Engine V3

## 1. Tujuan

Folder `parser/` adalah lapisan yang bertugas membaca source code MQL5 (`.mq5` / `.mqh`) dan mengubahnya menjadi **Strategy Intermediate Representation (Strategy IR)**.

Parser **tidak boleh mengeksekusi source MQL5 secara langsung**.

Alur utama:

```text
EA.mq5
  │
  ▼
Lexer
  │
  ▼
Parser / AST
  │
  ▼
Semantic Analyzer
  │
  ├── Variable Extractor
  ├── Function Extractor
  ├── Indicator Extractor
  └── Trading Extractor
  │
  ▼
Strategy IR
  │
  ▼
Virtual MT5 Runtime
```

Strategy IR menjadi kontrak antara Parser dengan:

- Backtest Engine
- Visual Simulator
- Signal Engine
- Runtime
- EA Builder
- Comparator
- Behavior/analysis tooling

---

# 2. Struktur Folder

```text
parser/
├── README.md
├── lexer.py
├── parser.py
├── ast.py
├── semantic_analyzer.py
├── variable_extractor.py
├── function_extractor.py
├── indicator_extractor.py
├── trading_extractor.py
└── strategy_ir.py
```

## Tanggung jawab

| File | Tanggung Jawab |
|---|---|
| `lexer.py` | Tokenisasi source MQL5 |
| `parser.py` | Membentuk AST |
| `ast.py` | Model node AST |
| `semantic_analyzer.py` | Analisis makna/dependency |
| `variable_extractor.py` | Extract input/variable/constant/enum/struct |
| `function_extractor.py` | Extract event handler dan custom function |
| `indicator_extractor.py` | Extract indikator dan buffer |
| `trading_extractor.py` | Extract order/position/trading API |
| `strategy_ir.py` | Model final Strategy IR |

---

# 3. Design Principles

## 3.1 Never Execute MQL5

Parser hanya membaca dan memahami source code.

Tidak boleh:

```text
MQL5 -> Python eval()
MQL5 -> shell
MQL5 -> subprocess
MQL5 -> arbitrary OS command
```

Parser menghasilkan data terstruktur.

---

## 3.2 Deterministic

Source yang sama harus menghasilkan Strategy IR yang sama.

Contoh:

```text
same EA source
+
same parser version
=
same Strategy IR
```

---

## 3.3 Preserve Source Information

Parser harus mempertahankan informasi penting seperti:

- line number
- column
- original identifier
- source expression
- source function
- parser warning

Contoh:

```json
{
  "name": "EMA_Fast",
  "line": 14,
  "source": "input int EMA_Fast = 21;"
}
```

---

# 4. Lexer

`lexer.py` bertanggung jawab memecah source menjadi token.

Contoh:

```cpp
input int EMA_Period = 21;
```

menjadi konsep:

```text
KEYWORD(input)
TYPE(int)
IDENTIFIER(EMA_Period)
OPERATOR(=)
NUMBER(21)
DELIMITER(;)
```

## Token Types

Minimal:

```text
KEYWORD
TYPE
IDENTIFIER
NUMBER
FLOAT
STRING
CHAR
OPERATOR
DELIMITER
COMMENT
PREPROCESSOR
EOF
```

Lexer harus menangani:

```text
// comment

/*
   multiline comment
*/

#define
#include
#property
```

---

# 5. AST

`ast.py` mendefinisikan struktur Abstract Syntax Tree.

Minimal node:

```text
Program
├── Preprocessor
├── Property
├── Include
├── VariableDeclaration
├── InputDeclaration
├── ConstantDeclaration
├── EnumDeclaration
├── StructDeclaration
├── FunctionDeclaration
├── Expression
├── IfStatement
├── ForStatement
├── WhileStatement
├── ReturnStatement
├── CallExpression
└── Assignment
```

Contoh:

```cpp
if(rsi < 30)
{
    trade.Buy(0.1);
}
```

harus dapat direpresentasikan sebagai:

```text
IfStatement
├── Condition
│   └── BinaryExpression
│       ├── Identifier(rsi)
│       ├── Operator(<)
│       └── Literal(30)
└── Body
    └── CallExpression
        ├── Object(trade)
        ├── Method(Buy)
        └── Argument(0.1)
```

---

# 6. Semantic Analyzer

AST saja belum cukup.

`semantic_analyzer.py` harus menentukan hubungan antar node.

Contoh:

```cpp
double rsi = iRSI(...);
if(rsi < RSI_Oversold)
    trade.Buy(...);
```

Semantic Analyzer harus memahami:

```text
RSI
  ↓
rsi
  ↓
comparison
  ↓
BUY signal
```

## Responsibilities

- Symbol table
- Variable scope
- Function dependency
- Indicator dependency
- Signal dependency
- Trading dependency
- Type checking dasar
- Undefined identifier warning
- Unsupported construct detection

---

# 7. Variable Extractor

`variable_extractor.py`

Harus mendeteksi:

### Input

```cpp
input double Lots = 0.10;
input int StopLoss = 500;
input int TakeProfit = 1000;
```

Output:

```json
{
  "name": "Lots",
  "type": "double",
  "default": 0.1,
  "source": "input"
}
```

### Global Variable

```cpp
double LastPrice = 0;
```

### Static

```cpp
static int Counter = 0;
```

### Constant

```cpp
#define MAGIC 123456
```

atau:

```cpp
const int MAGIC = 123456;
```

### Enum

```cpp
enum TradeMode
{
    BUY_ONLY,
    SELL_ONLY,
    BOTH
};
```

### Struct

```cpp
struct TradeConfig
{
    double lot;
    double sl;
    double tp;
};
```

### Array

```cpp
double prices[];
```

---

# 8. Function Extractor

`function_extractor.py`

Harus mengenali event:

```text
OnInit()
OnTick()
OnTimer()
OnTrade()
OnTradeTransaction()
OnDeinit()
```

dan custom functions.

Contoh:

```cpp
void CheckEntry()
{
    ...
}
```

Output:

```json
{
  "name": "CheckEntry",
  "return_type": "void",
  "parameters": [],
  "event": false
}
```

Untuk:

```cpp
void OnTick()
```

output:

```json
{
  "name": "OnTick",
  "event": true,
  "event_type": "OnTick"
}
```

---

# 9. Indicator Extractor

`indicator_extractor.py`

Parser harus mengenali MQL5 indicator API.

Minimal:

```text
iMA
iRSI
iATR
iMACD
iStochastic
iADX
iBands
iCCI
iMomentum
iMFI
iOBV
iSAR
iFractals
iIchimoku
```

Contoh:

```cpp
int rsiHandle = iRSI(
    _Symbol,
    PERIOD_M15,
    14,
    PRICE_CLOSE
);
```

Harus menjadi:

```json
{
  "type": "RSI",
  "alias": "iRSI",
  "symbol": "_Symbol",
  "timeframe": "PERIOD_M15",
  "period": 14,
  "price": "PRICE_CLOSE",
  "handle": "rsiHandle"
}
```

---

# 10. CopyBuffer Analysis

Parser harus menghubungkan indicator handle dengan buffer access.

Contoh:

```cpp
double rsi[];
CopyBuffer(
    rsiHandle,
    0,
    0,
    3,
    rsi
);
```

Harus menghasilkan dependency:

```text
iRSI
  ↓
rsiHandle
  ↓
CopyBuffer
  ↓
rsi[]
  ↓
Entry condition
```

Output:

```json
{
  "source": "CopyBuffer",
  "handle": "rsiHandle",
  "buffer": 0,
  "start": 0,
  "count": 3,
  "target": "rsi"
}
```

---

# 11. Trading Extractor

`trading_extractor.py`

Harus mengenali:

## CTrade

```cpp
CTrade trade;
```

## BUY

```cpp
trade.Buy(
    0.10,
    _Symbol,
    ask,
    sl,
    tp
);
```

## SELL

```cpp
trade.Sell(
    0.10,
    _Symbol,
    bid,
    sl,
    tp
);
```

## Position

```text
PositionSelect
PositionClose
PositionModify
PositionGetDouble
PositionGetInteger
```

## Order

```text
OrderSend
OrderCheck
OrderGetTicket
OrderGetDouble
OrderGetInteger
```

Parser harus mendeteksi:

```text
direction
volume
symbol
entry price
SL
TP
comment
magic
order type
```

---

# 12. Signal Extraction

Parser harus berusaha menemukan kondisi signal.

Contoh:

```cpp
if(
    rsi < 30 &&
    emaFast > emaSlow
)
{
    trade.Buy(0.1);
}
```

Strategy IR:

```json
{
  "signal": {
    "type": "BUY",
    "conditions": [
      {
        "left": "RSI",
        "operator": "<",
        "right": 30
      },
      {
        "left": "EMA_FAST",
        "operator": ">",
        "right": "EMA_SLOW"
      }
    ],
    "logic": "AND"
  }
}
```

---

# 13. Strategy IR

`strategy_ir.py` adalah model utama.

Contoh struktur:

```json
{
  "schema_version": "3.0",
  "strategy": {
    "name": "ExampleEA",
    "version": "1.0"
  },
  "metadata": {},
  "inputs": [],
  "variables": [],
  "constants": [],
  "enums": [],
  "structs": [],
  "functions": [],
  "indicators": [],
  "buffers": [],
  "signals": [],
  "entries": [],
  "exits": [],
  "orders": [],
  "positions": [],
  "risk": {},
  "sessions": {},
  "runtime_events": [],
  "warnings": []
}
```

---

# 14. Entry IR

Contoh:

```json
{
  "id": "entry_001",
  "direction": "BUY",
  "conditions": [
    {
      "type": "comparison",
      "left": "RSI",
      "operator": "<",
      "right": 30
    }
  ],
  "volume": {
    "type": "fixed",
    "value": 0.10
  },
  "sl": {
    "type": "points",
    "value": 500
  },
  "tp": {
    "type": "points",
    "value": 1000
  }
}
```

---

# 15. Exit IR

Contoh:

```json
{
  "id": "exit_001",
  "conditions": [
    {
      "left": "RSI",
      "operator": ">",
      "right": 70
    }
  ]
}
```

SL/TP/trailing harus disimpan secara terpisah dari signal exit.

---

# 16. Risk IR

Contoh:

```json
{
  "position_sizing": {
    "type": "risk_percent",
    "value": 1.0
  },
  "max_positions": 1,
  "max_spread": 35,
  "max_daily_loss": null
}
```

Jika EA menggunakan autolot:

```text
Risk %
    ↓
SL distance
    ↓
Tick value
    ↓
Contract size
    ↓
Lot calculation
```

---

# 17. Session Extraction

Parser harus mendeteksi pembatasan waktu.

Contoh:

```cpp
if(hour < 1 || hour >= 22)
    return;
```

Dapat direpresentasikan:

```json
{
  "session": {
    "server_time": true,
    "start": "01:00",
    "stop": "22:00"
  }
}
```

Parser harus memberi warning jika time logic terlalu kompleks untuk diekstrak secara deterministik.

---

# 18. Magic Number

Deteksi:

```cpp
trade.SetExpertMagicNumber(123456);
```

atau:

```cpp
input long MagicNumber = 123456;
```

Output:

```json
{
  "magic_number": 123456
}
```

---

# 19. Unsupported Constructs

Tidak semua MQL5 harus langsung didukung.

Parser harus menghasilkan warning, bukan crash.

Contoh:

```json
{
  "severity": "WARNING",
  "code": "UNSUPPORTED_CONSTRUCT",
  "line": 144,
  "message": "External DLL call is not supported.",
  "action": "Manual review required."
}
```

Severity:

```text
INFO
WARNING
ERROR
BLOCKING
```

---

# 20. Parser Confidence

Setiap Strategy IR sebaiknya memiliki:

```json
{
  "parser_quality": {
    "coverage": 0.96,
    "confidence": 0.91,
    "blocking_warnings": 0,
    "warnings": 3
  }
}
```

Coverage bukan probabilitas trading.

Ini hanya menunjukkan seberapa lengkap parser memahami source EA.

---

# 21. Source Hash

Strategy IR harus menyimpan:

```json
{
  "source_hash": "sha256:...",
  "parser_version": "3.0.0",
  "ir_schema_version": "3.0"
}
```

Tujuannya untuk reproducibility.

---

# 22. Example

Input:

```cpp
#property version "1.00"

input int RSI_Period = 14;
input double Lots = 0.10;

int rsiHandle;

int OnInit()
{
    rsiHandle = iRSI(
        _Symbol,
        PERIOD_M15,
        RSI_Period,
        PRICE_CLOSE
    );

    return INIT_SUCCEEDED;
}

void OnTick()
{
    double rsi[];

    if(CopyBuffer(
        rsiHandle,
        0,
        0,
        1,
        rsi
    ) <= 0)
        return;

    if(rsi[0] < 30)
    {
        trade.Buy(Lots);
    }
}
```

Expected conceptual IR:

```json
{
  "strategy": {
    "version": "1.00"
  },
  "inputs": [
    {
      "name": "RSI_Period",
      "type": "int",
      "default": 14
    },
    {
      "name": "Lots",
      "type": "double",
      "default": 0.1
    }
  ],
  "indicators": [
    {
      "type": "RSI",
      "alias": "iRSI",
      "timeframe": "PERIOD_M15",
      "period": "RSI_Period",
      "price": "PRICE_CLOSE",
      "handle": "rsiHandle"
    }
  ],
  "buffers": [
    {
      "handle": "rsiHandle",
      "buffer": 0,
      "target": "rsi"
    }
  ],
  "entries": [
    {
      "direction": "BUY",
      "condition": {
        "left": "rsi[0]",
        "operator": "<",
        "right": 30
      },
      "volume": {
        "type": "fixed",
        "value": "Lots"
      }
    }
  ]
}
```

---

# 23. Parser Pipeline

Implementasi harus mengikuti pipeline:

```text
1. Load source
       ↓
2. Calculate SHA256
       ↓
3. Preprocess
       ↓
4. Lexical analysis
       ↓
5. AST generation
       ↓
6. Symbol table
       ↓
7. Semantic analysis
       ↓
8. Variable extraction
       ↓
9. Function extraction
       ↓
10. Indicator extraction
       ↓
11. Trading extraction
       ↓
12. Signal extraction
       ↓
13. Build Strategy IR
       ↓
14. Validate IR
       ↓
15. Generate warnings
       ↓
16. Return IR
```

---

# 24. Error Handling

Parser tidak boleh gagal total hanya karena menemukan construct yang belum didukung.

Contoh:

```text
Supported code
       +
Unsupported code
       =
Strategy IR
+
Warning
```

Parser hanya boleh menghentikan proses jika terjadi:

```text
Syntax corruption
Fatal AST error
Invalid source encoding
Unrecoverable parser state
```

---

# 25. Testing

## Lexer

Test:

- comments
- strings
- numbers
- operators
- preprocessor
- MQL5 keywords

## AST

Test:

- variable
- input
- if
- loop
- function
- call
- assignment

## Semantic

Test:

- scope
- dependencies
- undefined variable
- indicator handle
- buffer dependency

## Extractors

Test:

- input
- variables
- functions
- indicators
- CopyBuffer
- Buy
- Sell
- SL/TP
- trailing
- magic number

## End-to-End

```text
EA.mq5
  ↓
Parser
  ↓
Strategy IR
  ↓
Validation
```

---

# 26. Acceptance Criteria

Parser V3 dianggap selesai jika:

- [ ] `.mq5` dapat dibaca.
- [ ] `.mqh` dapat dikenali sebagai include/dependency.
- [ ] Input variables diekstrak.
- [ ] Global/local/static variables diekstrak.
- [ ] Constants/enums/structs dikenali.
- [ ] Event functions dikenali.
- [ ] Custom functions dikenali.
- [ ] Indicator calls dikenali.
- [ ] Indicator handle dikenali.
- [ ] CopyBuffer dependency dikenali.
- [ ] CTrade dikenali.
- [ ] BUY/SELL dikenali.
- [ ] Position APIs dikenali.
- [ ] Order APIs dikenali.
- [ ] SL/TP dikenali jika dapat ditentukan.
- [ ] Trailing dikenali jika dapat ditentukan.
- [ ] Magic number dikenali.
- [ ] Session/time restriction dikenali jika sederhana.
- [ ] Signal conditions diekstrak jika dapat direpresentasikan.
- [ ] Strategy IR valid.
- [ ] Unsupported construct menghasilkan warning.
- [ ] Source hash tersedia.
- [ ] Parser version tersedia.
- [ ] Parser tidak pernah mengeksekusi source EA.

---

# 27. Integrasi dengan app.py

Endpoint:

```http
POST /api/parse-ea
```

Input multipart:

```text
file = ExampleEA.mq5
```

atau JSON:

```json
{
  "filename": "ExampleEA.mq5",
  "source": "... MQL5 source ..."
}
```

Response:

```json
{
  "success": true,
  "run_id": "parse_...",
  "filename": "ExampleEA.mq5",
  "source_hash": "sha256:...",
  "strategy_ir": {}
}
```

---

# 28. Hubungan dengan Modul V3

```text
                 parser/
                    │
                    ▼
              Strategy IR
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
   Runtime      Backtest     Simulator
       │            │            │
       └────────────┼────────────┘
                    ▼
              MT5 Comparator
```

Indicator dependency:

```text
parser
   │
   ▼
IndicatorRegistry
   │
   ├── Backtest
   ├── Simulator
   ├── EA Builder
   └── Behavior Engine
```

---

# 29. Future Parser Versions

## V3.1

- Better expression parsing.
- More MQL5 syntax.
- More built-in functions.
- Better signal extraction.

## V3.2

- Advanced dependency graph.
- Automatic strategy flow graph.
- Better complex condition normalization.

## V3.3

- Wider MQL5 API coverage.
- More accurate conversion to Strategy IR.
- Automated parser regression corpus.

## V4.0

Potentially:

```text
MQL5
  ↓
Full Semantic AST
  ↓
Universal Strategy IR
  ↓
Python Runtime
  ↓
MT5 Runtime
  ↓
Live/Backtest/Simulation
```

---

# 30. Final Rule

`parser/` harus menjadi **translation and understanding layer**, bukan execution layer.

Prinsip:

```text
MQL5 Source
    ↓
UNDERSTAND
    ↓
NORMALIZE
    ↓
STRATEGY IR
    ↓
EXECUTE SAFELY IN PYTHON RUNTIME
```

Dengan desain ini, parser dapat dikembangkan secara bertahap tanpa membuat backtest engine bergantung langsung pada syntax MQL5.
