from datetime import datetime, timezone, timedelta
from .engine import BacktestEngine, BacktestConfig
from .data_feed import MarketBar


def test_basic_buy_tp():
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    bars = [
        MarketBar(t, 100, 100, 100, 100),
        MarketBar(t + timedelta(minutes=1), 100, 105, 99, 104),
    ]
    def strategy(bar, ctx):
        if bar.time == bars[0].time:
            return {"action": "BUY", "volume": 1, "tp": 104}
    result = BacktestEngine(BacktestConfig(point=0.01)).run(bars, strategy)
    assert result.statistics["trades"] == 1
    assert result.trades[0]["profit"] == 4


if __name__ == "__main__":
    test_basic_buy_tp()
    print("PASS")
