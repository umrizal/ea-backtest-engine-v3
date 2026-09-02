from __future__ import annotations


class TickPlayer:
    def __init__(self, ticks):
        self.ticks = list(ticks)
        self.index = -1

    @property
    def total(self):
        return len(self.ticks)

    @property
    def current(self):
        if 0 <= self.index < self.total:
            return self.ticks[self.index]
        return None

    def reset(self):
        self.index = -1

    def next(self):
        if self.index + 1 >= self.total:
            return None
        self.index += 1
        return self.current

    def previous(self):
        if self.index - 1 < 0:
            self.index = -1
            return None
        self.index -= 1
        return self.current

    def jump_to_index(self, index: int):
        if self.total == 0:
            self.index = -1
            return None
        self.index = max(-1, min(index, self.total - 1))
        return self.current

    def jump_to_time(self, timestamp):
        for i, tick in enumerate(self.ticks):
            if tick.time >= timestamp:
                self.index = i
                return tick
        self.index = self.total - 1
        return self.current
