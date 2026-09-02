from .parser import EAParser

SAMPLE = r"""
#property version "1.10"
#property description "RSI AO Cross EA"

input int RSI_Period = 14;
input double RiskPercent = 1.0;
input int MaxSpread = 35;

int rsiHandle;

int OnInit()
{
   rsiHandle = iRSI(_Symbol, PERIOD_M15, RSI_Period, PRICE_CLOSE);
   return(INIT_SUCCEEDED);
}

void OnTick()
{
   double rsi[];
   CopyBuffer(rsiHandle, 0, 0, 3, rsi);

   if(rsi[0] < 30 && SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) < MaxSpread)
   {
      trade.Buy(0.10, _Symbol);
   }

   if(rsi[0] > 70)
   {
      trade.Sell(0.10, _Symbol);
   }
}
"""

def test_parser():
    ir = EAParser().parse(SAMPLE)
    assert len(ir.inputs) == 3
    assert len(ir.indicators) >= 1
    assert len(ir.entries) >= 2
    assert ir.metadata.source_hash

if __name__ == "__main__":
    test_parser()
    print("PASS")
