"""
Pattern Detector Module for EA Backtest Engine V3
Detects Price Action behaviors: Breakout, False Breakout, Continuation, Reversal, Retracement.
"""

import pandas as pd
from typing import Dict, Any


class PatternDetector:
    def __init__(self, lookback: int = 20):
        self.lookback = lookback

    def detect_price_action_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detects key price action patterns over a historical window."""
        if len(df) < self.lookback + 5:
            return {"detected_pattern": "INSUFFICIENT_DATA"}

        recent = df.iloc[-1]
        prev_range = df.iloc[-self.lookback:-1]
        highest_high = prev_range['high'].max()
        lowest_low = prev_range['low'].min()

        is_breakout_up = recent['close'] > highest_high
        is_breakout_down = recent['close'] < lowest_low
        false_breakout_up = (recent['high'] > highest_high) and (recent['close'] < highest_high)
        false_breakout_down = (recent['low'] < lowest_low) and (recent['close'] > lowest_low)

        pattern = "CONSOLIDATION"
        if false_breakout_up or false_breakout_down:
            pattern = "FALSE_BREAKOUT"
        elif is_breakout_up:
            pattern = "BULLISH_BREAKOUT"
        elif is_breakout_down:
            pattern = "BEARISH_BREAKOUT"

        return {
            "detected_pattern": pattern,
            "highest_high": highest_high,
            "lowest_low": lowest_low,
            "false_breakout_flag": false_breakout_up or false_breakout_down
        }