class TradingExtractor:
    def extract(self, ir):
        return {
            "entries": list(ir.entries),
            "exits": list(ir.exits),
            "risk": ir.risk,
            "session": ir.session,
        }
