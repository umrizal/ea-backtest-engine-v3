from __future__ import annotations
from dataclasses import dataclass


VALID_SPEEDS = (0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 50.0, 100.0)


@dataclass
class PlaybackController:
    speed: float = 1.0
    playing: bool = False

    def set_speed(self, speed: float):
        speed = float(speed)
        if speed not in VALID_SPEEDS:
            raise ValueError(f"Unsupported speed {speed}; use one of {VALID_SPEEDS}")
        self.speed = speed
        return self.speed

    def play(self):
        self.playing = True

    def pause(self):
        self.playing = False

    def stop(self):
        self.playing = False

    def toggle(self):
        self.playing = not self.playing
        return self.playing

    def multiplier(self):
        return self.speed
