from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Iterable, Callable, Any
import uuid

from .state import SimulatorState
from .candle_player import CandlePlayer
from .tick_player import TickPlayer
from .playback import PlaybackController, VALID_SPEEDS


@dataclass
class SimulatorConfig:
    symbol: str = "XAUUSD"
    mode: str = "candle"
    speed: float = 1.0
    initial_balance: float = 10000.0
    reveal_only_until_current: bool = True


@dataclass
class SimulatorSnapshot:
    session_id: str
    state: dict
    market: dict
    visible_bars: list
    visible_ticks: list
    positions: list
    pending_orders: list
    trades: list
    indicators: dict
    markers: list

    def to_dict(self):
        return asdict(self)


class SimulatorSession:
    """Interactive playback session.

    The session is intentionally decoupled from Flask/API and from the
    browser. A route layer can call start/next/previous/jump/play/pause.
    """

    def __init__(self, config: SimulatorConfig | None = None,
                 candles: Iterable | None = None,
                 ticks: Iterable | None = None):
        self.config = config or SimulatorConfig()
        self.session_id = uuid.uuid4().hex
        self.candle_player = CandlePlayer(candles or [])
        self.tick_player = TickPlayer(ticks or [])
        self.playback = PlaybackController(self.config.speed)
        self.state = SimulatorState(
            status="STOPPED",
            mode=self.config.mode,
            total=self.candle_player.total if self.config.mode == "candle" else self.tick_player.total,
            speed=self.config.speed,
            balance=self.config.initial_balance,
            equity=self.config.initial_balance,
        )

        self.positions: list[dict] = []
        self.pending_orders: list[dict] = []
        self.trades: list[dict] = []
        self.indicators: dict = {}
        self.markers: list[dict] = []
        self.equity_curve: list[dict] = []
        self._on_step: Callable[[Any, "SimulatorSession"], Any] | None = None

    def set_step_callback(self, callback):
        self._on_step = callback

    def start(self):
        self.state.status = "PLAYING"
        self.playback.play()
        return self.snapshot()

    def pause(self):
        self.state.status = "PAUSED"
        self.playback.pause()
        return self.snapshot()

    def stop(self):
        self.state.status = "STOPPED"
        self.playback.stop()
        self.candle_player.reset()
        self.tick_player.reset()
        self._sync_state(None)
        return self.snapshot()

    def play(self):
        return self.start()

    def set_speed(self, speed):
        self.playback.set_speed(speed)
        self.state.speed = self.playback.speed
        return self.snapshot()

    def next(self):
        item = (self.candle_player.next() if self.config.mode == "candle"
                else self.tick_player.next())
        if item is None:
            self.state.status = "FINISHED"
            self.playback.stop()
            return self.snapshot()

        self._sync_state(item)
        if self._on_step:
            result = self._on_step(item, self)
            self._apply_callback_result(result)
        return self.snapshot()

    def previous(self):
        item = (self.candle_player.previous() if self.config.mode == "candle"
                else self.tick_player.previous())
        self._sync_state(item)
        return self.snapshot()

    def next_tick(self):
        if self.tick_player.total == 0:
            return self.snapshot()
        item = self.tick_player.next()
        if item is None:
            self.state.status = "FINISHED"
            return self.snapshot()
        self.config.mode = "tick"
        self.state.mode = "tick"
        self._sync_state(item)
        if self._on_step:
            self._apply_callback_result(self._on_step(item, self))
        return self.snapshot()

    def jump_to_index(self, index: int):
        item = (self.candle_player.jump_to_index(index)
                if self.config.mode == "candle"
                else self.tick_player.jump_to_index(index))
        self._sync_state(item)
        return self.snapshot()

    def jump_to_date(self, timestamp: datetime):
        item = (self.candle_player.jump_to_time(timestamp)
                if self.config.mode == "candle"
                else self.tick_player.jump_to_time(timestamp))
        self._sync_state(item)
        return self.snapshot()

    def jump_to_trade(self, ticket: int):
        for trade in self.trades:
            if int(trade.get("ticket", -1)) == int(ticket):
                ts = trade.get("entry_time") or trade.get("exit_time")
                if ts:
                    if isinstance(ts, str):
                        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    return self.jump_to_date(ts)
        raise KeyError(f"Trade ticket {ticket} not found")

    def set_indicators(self, values: dict):
        self.indicators = values or {}

    def add_marker(self, marker: dict):
        self.markers.append(dict(marker))

    def _apply_callback_result(self, result):
        if not result:
            return
        if isinstance(result, dict):
            if "positions" in result:
                self.positions = result["positions"]
            if "pending_orders" in result:
                self.pending_orders = result["pending_orders"]
            if "trades" in result:
                self.trades = result["trades"]
            if "indicators" in result:
                self.indicators = result["indicators"]
            if "markers" in result:
                self.markers.extend(result["markers"])

    def _sync_state(self, item):
        if item is None:
            self.state.index = -1
            self.state.current_time = None
            self.state.current_price = None
            self.state.active_trade_count = len(self.positions)
            self.state.completed_trade_count = len(self.trades)
            return

        player = self.candle_player if self.config.mode == "candle" else self.tick_player
        self.state.index = player.index
        self.state.current_time = item.time

        if hasattr(item, "close"):
            self.state.current_price = item.close
        elif hasattr(item, "mid"):
            self.state.current_price = item.mid

        self.state.active_trade_count = sum(
            1 for p in self.positions if str(p.get("status", "OPEN")).upper() == "OPEN"
        )
        self.state.completed_trade_count = sum(
            1 for t in self.trades if t.get("exit_time") is not None
        )

    def visible_data(self):
        if self.config.mode == "candle":
            return self.candle_player.candles[:self.candle_player.index + 1]
        return []

    def snapshot(self):
        visible_bars = [asdict(x) for x in self.visible_data()]
        visible_ticks = []
        if self.config.mode == "tick" and self.tick_player.index >= 0:
            visible_ticks = [asdict(x) for x in self.tick_player.ticks[:self.tick_player.index + 1]]
        market = {
            "symbol": self.config.symbol,
            "time": self.state.current_time,
            "price": self.state.current_price,
        }
        return SimulatorSnapshot(
            self.session_id, self.state.to_dict(), market,
            visible_bars, visible_ticks,
            list(self.positions), list(self.pending_orders),
            list(self.trades), dict(self.indicators), list(self.markers)
        )
