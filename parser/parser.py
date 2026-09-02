"""Pragmatic MQL5 EA parser -> Strategy IR.

Security rule: this parser ONLY analyzes source text. It never executes MQL5.
"""
import re
from typing import List, Dict, Any
from .lexer import MQL5Lexer
from .strategy_ir import (
    StrategyIR, StrategyMetadata, InputParameter, VariableIR, IndicatorIR,
    BufferIR, ConditionIR, EntryIR, VolumeIR, PriceDistanceIR, RiskIR,
    SessionIR, FunctionIR, IRWarning, calculate_source_hash
)

INDICATOR_MAP = {
    "iMA": "MA", "iRSI": "RSI", "iATR": "ATR", "iMACD": "MACD",
    "iStochastic": "STOCHASTIC", "iADX": "ADX", "iBands": "BOLLINGER",
    "iCCI": "CCI", "iMomentum": "MOMENTUM", "iMFI": "MFI", "iOBV": "OBV",
    "iSAR": "SAR", "iFractals": "FRACTALS", "iIchimoku": "ICHIMOKU"
}

class EAParser:
    def parse(self, source: str) -> StrategyIR:
        ir = StrategyIR()
        ir.metadata.source_hash = calculate_source_hash(source)
        self._metadata(source, ir)
        self._inputs(source, ir)
        self._variables(source, ir)
        self._indicators(source, ir)
        self._buffers(source, ir)
        self._functions(source, ir)
        self._entries(source, ir)
        self._risk(source, ir)
        self._session(source, ir)
        self._security(source, ir)
        ir.calculate_quality()
        return ir

    def _metadata(self, s, ir):
        for key, attr in [
            ("version", "version"), ("description", "description"), ("copyright", "copyright")
        ]:
            m = re.search(r"#property\s+" + key + r"\s+(.+)", s, re.I)
            if m:
                setattr(ir.metadata, attr, m.group(1).strip().strip('"'))
        m = re.search(r'(?://|/\*)\s*(?:EA|Expert Advisor)\s*[:\-]?\s*([^\n*]+)', s, re.I)
        ir.metadata.name = m.group(1).strip() if m else ""

    def _inputs(self, s, ir):
        pat = re.compile(
            r'\binput\s+([A-Za-z_][\w]*)\s+([A-Za-z_]\w*)\s*(?:=\s*([^;]+))?\s*;',
            re.I
        )
        for m in pat.finditer(s):
            default = m.group(3).strip() if m.group(3) else None
            ir.inputs.append(InputParameter(m.group(2), m.group(1), default))

    def _variables(self, s, ir):
        pat = re.compile(
            r'\b(?:(const|static)\s+)?(bool|char|uchar|short|ushort|int|uint|long|ulong|float|double|string|datetime)\s+([A-Za-z_]\w*)\s*(?:=\s*([^;]+))?\s*;',
            re.I
        )
        inputs = {x.name for x in ir.inputs}
        for m in pat.finditer(s):
            name = m.group(3)
            if name in inputs:
                continue
            scope = "global" if s[:m.start()].count("{") == s[:m.start()].count("}") else "local"
            ir.variables.append(VariableIR(
                name=name, type=m.group(2), scope=scope,
                initial_value=m.group(4).strip() if m.group(4) else None,
                is_const=bool(m.group(1) and m.group(1).lower() == "const")
            ))

    def _indicators(self, s, ir):
        counter = 0
        for fn, kind in INDICATOR_MAP.items():
            for m in re.finditer(r'\b' + re.escape(fn) + r'\s*\(([^;\n]*)\)', s):
                counter += 1
                args = self._split_args(m.group(1))
                params = {f"arg{i}": a.strip() for i, a in enumerate(args)}
                handle = self._find_handle_before(s, m.start())
                ir.indicators.append(IndicatorIR(
                    id=f"ind_{counter}", kind=kind, function=fn,
                    parameters=params, handle_variable=handle
                ))

    def _find_handle_before(self, s, pos):
        prefix = s[max(0, pos-500):pos]
        m = re.search(r'\b(?:int|long)\s+([A-Za-z_]\w*)\s*=\s*$', prefix)
        return m.group(1) if m else None

    def _buffers(self, s, ir):
        for m in re.finditer(r'CopyBuffer\s*\(\s*([A-Za-z_]\w*)\s*,\s*(\d+)\s*,', s):
            handle = m.group(1)
            idx = int(m.group(2))
            indicator = next((x for x in ir.indicators if x.handle_variable == handle), None)
            if indicator:
                ir.buffers.append(BufferIR(indicator.id, idx))

    def _functions(self, s, ir):
        pat = re.compile(
            r'\b([A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*\{',
            re.M
        )
        for m in pat.finditer(s):
            ret, name, params = m.groups()
            if name in {"if", "for", "while", "switch"}:
                continue
            plist = []
            for p in self._split_args(params):
                p = p.strip()
                if not p:
                    continue
                bits = p.split()
                plist.append({"type": bits[-2] if len(bits) >= 2 else "", "name": bits[-1]})
            body = self._extract_block(s, m.end()-1)
            calls = sorted(set(re.findall(r'\b([A-Za-z_]\w*)\s*\(', body)))
            ir.functions.append(FunctionIR(
                name=name, return_type=ret, parameters=plist,
                calls=[x for x in calls if x not in {"if","for","while","switch"}],
                is_event=name in {"OnInit","OnTick","OnDeinit","OnTimer","OnTrade","OnTradeTransaction"}
            ))

    def _entries(self, s, ir):
        # Detect common CTrade and OrderSend entry patterns.
        patterns = [
            (r'\.Buy\s*\(([^;]*)\)', "BUY"),
            (r'\.Sell\s*\(([^;]*)\)', "SELL"),
            (r'ORDER_TYPE_BUY\b', "BUY"),
            (r'ORDER_TYPE_SELL\b', "SELL"),
        ]
        count = 0
        for pat, direction in patterns:
            for m in re.finditer(pat, s, re.I):
                count += 1
                context = s[max(0, m.start()-1200):m.start()]
                cond = self._nearest_condition(context)
                volume = self._volume_from_context(context, m.group(1) if m.lastindex else "")
                ir.entries.append(EntryIR(
                    id=f"entry_{count}", direction=direction,
                    volume=volume,
                    conditions=[ConditionIR(cond, purpose="entry")] if cond else [],
                    source_function=self._nearest_function(s, m.start())
                ))

    def _risk(self, s, ir):
        def get(names):
            for n in names:
                m = re.search(r'\b' + re.escape(n) + r'\b\s*(?:=\s*)?([0-9]+(?:\.[0-9]+)?)', s, re.I)
                if m:
                    return m.group(1)
            return None
        ir.risk = RiskIR(
            max_spread=get(["MaxSpread","MaxSpreadPoints","InpMaxSpread"]),
            max_positions=get(["MaxPositions","MaxPosition","InpMaxPositions"]),
            risk_per_trade=get(["RiskPerTrade","RiskPercent","InpRiskPercent"]),
            max_drawdown=get(["MaxDrawdown","MaxDD"]),
            stop_out_level=get(["StopOutLevel"])
        )

    def _session(self, s, ir):
        start = self._number_near(s, ["StartHour","TradingStartHour","FixedStartHour"])
        stop = self._number_near(s, ["StopHour","TradingStopHour","FixedStopHour"])
        if start is not None or stop is not None:
            ir.session = SessionIR(True, start, stop, "broker")

    def _security(self, s, ir):
        checks = [
            (r'\b#import\b', "SEC001", "MQL5 import directive detected; external DLL/API dependency requires sandbox review."),
            (r'\bShellExecute\b|\bWinExec\b|\bCreateProcess\b', "SEC002", "OS process execution API detected."),
            (r'\bWebRequest\b', "SEC003", "Network request API detected."),
            (r'\bFileOpen\b|\bFileWrite\b|\bFileRead\b', "SEC004", "Filesystem access detected; runtime should enforce sandbox paths."),
            (r'#include\s*[<"]\s*Win', "SEC005", "Windows/system include detected.")
        ]
        for pat, code, msg in checks:
            if re.search(pat, s, re.I):
                ir.warnings.append(IRWarning(code, msg, "high" if code in {"SEC001","SEC002","SEC003"} else "warning"))

    def _volume_from_context(self, context, args):
        text = (context + " " + args).strip()
        for name in ["RiskPerTrade","RiskPercent","risk_percent"]:
            m = re.search(r'\b' + re.escape(name) + r'\b', text, re.I)
            if m:
                return VolumeIR(mode="risk_percent", risk_percent=name)
        m = re.search(r'\b(?:lot|lots|volume)\s*[=:]\s*([A-Za-z_]\w*|[0-9.]+)', text, re.I)
        if m:
            return VolumeIR(mode="fixed", value=m.group(1))
        return VolumeIR(mode="expression", value=args.strip() if args.strip() else None)

    def _nearest_condition(self, context):
        matches = list(re.finditer(r'\bif\s*\((.*?)\)', context, re.S))
        return matches[-1].group(1).strip() if matches else ""

    def _nearest_function(self, s, pos):
        matches = list(re.finditer(r'\b[A-Za-z_]\w*\s+[A-Za-z_]\w*\s*\([^)]*\)\s*\{', s[:pos]))
        return matches[-1].group(0).split("(")[0].strip().split()[-1] if matches else ""

    def _extract_block(self, s, brace_pos):
        depth = 0
        for i in range(brace_pos, len(s)):
            if s[i] == "{": depth += 1
            elif s[i] == "}":
                depth -= 1
                if depth == 0:
                    return s[brace_pos+1:i]
        return s[brace_pos+1:]

    def _split_args(self, text):
        out, cur, depth, quote = [], "", 0, None
        for ch in text:
            if quote:
                cur += ch
                if ch == quote:
                    quote = None
            elif ch in (chr(39) + chr(34)):
                quote = ch; cur += ch
            elif ch in "([{":
                depth += 1; cur += ch
            elif ch in ")]}":
                depth -= 1; cur += ch
            elif ch == "," and depth == 0:
                out.append(cur); cur = ""
            else:
                cur += ch
        if cur.strip():
            out.append(cur)
        return out

    def _number_near(self, s, names):
        for n in names:
            m = re.search(r'\b' + re.escape(n) + r'\b\s*(?:=\s*)?([0-9]+)', s, re.I)
            if m:
                return int(m.group(1))
        return None

def parse_mql5(source: str) -> StrategyIR:
    return EAParser().parse(source)
