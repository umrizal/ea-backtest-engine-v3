"""
Market Regime Detector Module for EA Backtest Engine V3
Detects: Trending, Range, Compression, Expansion, High Volatility, Low Volatility.
"""

import pandas as pd
from typing import Dict, Any


class RegimeDetector:
    def __init__(self, atr_period: int = 14, trend_period: int = 50):
        self.atr_period = atr_period
        self.trend_period = trend_period

    def detect_regime(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detects current market regime based on statistical thresholds."""
        if len(df) < self.trend_period:
            return {"primary_regime": "UNKNOWN", "confidence": 0.0}

        atr_avg = df['range'].rolling(self.atr_period * 5).mean().iloc[-1]
        current_atr = df['range'].rolling(self.atr_period).mean().iloc[-1]

        # Volatility Classification
        volatility_status = "NORMAL_VOLATILITY"
        if current_atr > 1.5 * atr_avg:
            volatility_status = "HIGH_VOLATILITY"
        elif current_atr < 0.7 * atr_avg:
            volatility_status = "LOW_VOLATILITY"

        # Structure Classification
        sma_short = df['close'].rolling(20).mean().iloc[-1]
        sma_long = df['close'].rolling(50).mean().iloc[-1]
        std_20 = df['close'].rolling(20).std().iloc[-1]

        structure_status = "RANGE"
        if std_20 < (atr_avg * 0.5):
            structure_status = "COMPRESSION"
        elif abs(sma_short - sma_long) > (atr_avg * 1.2):
            structure_status = "TRENDING_UP" if sma_short > sma_long else "TRENDING_DOWN"
        elif current_atr > 2.0 * atr_avg:
            structure_status = "EXPANSION"

        return {
            "primary_regime": f"{structure_status} + {volatility_status}",
            "structure": structure_status,
            "volatility": volatility_status,
            "current_atr": round(current_atr, 4),
            "atr_baseline": round(atr_avg, 4)
        }