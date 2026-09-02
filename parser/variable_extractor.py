from .strategy_ir import VariableIR

class VariableExtractor:
    def extract(self, ir):
        return list(ir.variables)
