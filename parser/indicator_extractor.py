from .strategy_ir import IndicatorIR, BufferIR

class IndicatorExtractor:
    def extract(self, ir):
        return {"indicators": list(ir.indicators), "buffers": list(ir.buffers)}
