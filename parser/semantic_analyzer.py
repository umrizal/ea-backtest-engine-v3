"""Semantic checks for parsed Strategy IR."""
from .strategy_ir import StrategyIR, IRWarning

class SemanticAnalyzer:
    def analyze(self, ir: StrategyIR) -> StrategyIR:
        names = {x.name for x in ir.inputs}
        for v in ir.variables:
            if v.name in names:
                ir.warnings.append(IRWarning(
                    "SEM001", f"Variable '{v.name}' shadows an input parameter.", "warning"
                ))
        if not ir.entries:
            ir.warnings.append(IRWarning(
                "SEM002", "No BUY/SELL entry operation was detected.", "warning"
            ))
        if ir.entries and not any(e.sl or e.tp for e in ir.entries):
            ir.warnings.append(IRWarning(
                "SEM003", "Entry detected without statically detected SL/TP.", "info"
            ))
        ir.calculate_quality()
        return ir
