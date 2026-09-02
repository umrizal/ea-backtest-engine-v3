from .strategy_ir import FunctionIR

class FunctionExtractor:
    def extract(self, ir):
        return list(ir.functions)
