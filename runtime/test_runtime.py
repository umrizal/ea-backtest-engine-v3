from types import SimpleNamespace
from runtime import StrategyRuntime, MarketState

def test_runtime_entry():
    condition = SimpleNamespace(expression="RSI < 30")
    entry = SimpleNamespace(
        direction="BUY",
        symbol="_Symbol",
        conditions=[condition],
        volume=SimpleNamespace(mode="fixed", value="0.10"),
    )

    ir = SimpleNamespace(
        inputs=[
            SimpleNamespace(name="RSI", type="double", default="25")
        ],
        entries=[entry],
    )

    market = MarketState(
        symbol="XAUUSD",
        timeframe="M15",
        bid=4000.0,
        ask=4000.2,
        spread_points=20,
    )

    runtime = StrategyRuntime(ir, market=market)
    result = runtime.step()

    assert result["entry_count"] == 1
    assert result["requests"][0]["direction"] == "BUY"
    assert result["requests"][0]["volume"] == 0.10

if __name__ == "__main__":
    test_runtime_entry()
    print("PASS")
