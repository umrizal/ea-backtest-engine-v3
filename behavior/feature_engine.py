"""
Feature Engine Module for EA Backtest Engine V3
Extracts statistical features (Range, ATR, Volatility, Trend, Momentum, Drawdown, MFE/MAE) from OHLC data.
Deterministic Layer - Core calculations without AI manipulation.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional


class FeatureEngine:
    def __init__(self, pip_size: float = 0.01):
        # Default pip size for XAUUSD is 0.01
        self.pip_size = pip_size

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculates Average True Range (ATR)."""
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extracts market features from OHLC data.
        Expected columns: ['open', 'high', 'low', 'close', 'volume']
        """
        res = df.copy()
        
        # Range & Pips
        res['range'] = res['high'] - res['low']
        res['range_pips'] = res['range'] / self.pip_size
        res['body_size'] = (res['close'] - res['open']).abs() / self.pip_size
        
        # Volatility (ATR 14)
        res['atr_14'] = self.calculate_atr(res, 14)
        res['volatility_ratio'] = res['range'] / (res['atr_14'] + 1e-8)
        
        # Trend & Momentum
        res['returns'] = res['close'].pct_change()
        res['sma_20'] = res['close'].rolling(20).mean()
        res['sma_50'] = res['close'].rolling(50).mean()
        res['trend_direction'] = np.where(res['sma_20'] > res['sma_50'], 1, -1)
        res['momentum_10'] = res['close'] - res['close'].shift(10)
        
        return res

    def compute_window_metrics(self, df_window: pd.DataFrame, initial_price: Optional[float] = None) -> Dict[str, Any]:
        """Computes aggregate behavior metrics (MFE, MAE, Net Move, Range) for a specific time window."""
        if df_window.empty:
            return {}

        start_price = initial_price if initial_price is not None else df_window.iloc[0]['open']
        max_high = df_window['high'].max()
        min_low = df_window['low'].min()
        final_close = df_window.iloc[-1]['close']

        mfe = (max_high - start_price) / self.pip_size
        mae = (start_price - min_low) / self.pip_size
        net_move = (final_close - start_price) / self.pip_size
        total_range = (max_high - min_low) / self.pip_size

        return {
            "start_price": start_price,
            "final_close": final_close,
            "max_high": max_high,
            "min_low": min_low,
            "total_range_pips": round(total_range, 2),
            "net_move_pips": round(net_move, 2),
            "mfe_pips": round(mfe, 2),
            "mae_pips": round(mae, 2),
            "volatility_expansion": round(df_window['range'].mean() / self.pip_size, 2)
        }