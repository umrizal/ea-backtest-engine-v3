from datetime import datetime, timezone, timedelta
from .session import SimulatorSession, SimulatorConfig
from .candle_player import CandlePlayer
from .playback import VALID_SPEEDS
from backtest.data_feed import MarketBar


def sample_bars():
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        MarketBar(t, 100, 101, 99, 100.5),
        MarketBar(t + timedelta(minutes=1), 100.5, 102, 100, 101.5),
        MarketBar(t + timedelta(minutes=2), 101.5, 103, 101, 102.5),
    ]


def test_candle_player():
    p = CandlePlayer(sample_bars())
    assert p.total == 3
    assert p.next().close == 100.5
    assert p.next().close == 101.5
    assert p.previous().close == 100.5
    assert p.jump_to_index(2).close == 102.5


def test_session_playback():
    s = SimulatorSession(SimulatorConfig(speed=1.0), candles=sample_bars())
    assert s.state.status == "STOPPED"
    s.start()
    s.next()
    assert s.state.index == 0
    assert s.state.current_price == 100.5
    s.set_speed(50)
    assert s.state.speed == 50
    s.pause()
    assert s.state.status == "PAUSED"


if __name__ == "__main__":
    test_candle_player()
    test_session_playback()
    print("PASS")
