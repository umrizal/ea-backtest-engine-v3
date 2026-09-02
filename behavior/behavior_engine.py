"""
Behavior Engine Module for EA Backtest Engine V3
Main orchestrator for statistical analysis, session tracking, event evaluation, and regime identification.
"""

import pandas as pd
from typing import Dict, Any, List, Optional
from .feature_engine import FeatureEngine
from .event_analyzer import EventAnalyzer
from .regime_detector import RegimeDetector
from .pattern_detector import PatternDetector


class BehaviorEngine:
    # Trading Sessions in UTC hours
    SESSIONS = {
        "Asian": (0, 8),
        "London": (7, 16),
        "New_York": (13, 21),
        "London_NY_Overlap": (13, 16)
    }

    def __init__(self, pip_size: float = 0.01):
        self.feature_engine = FeatureEngine(pip_size=pip_size)
        self.event_analyzer = EventAnalyzer(self.feature_engine)
        self.regime_detector = RegimeDetector()
        self.pattern_detector = PatternDetector()

    def analyze_session_behavior(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyzes behavior breakdown per trading session."""
        if not isinstance(df.index, pd.DatetimeIndex):
            df = df.set_index('datetime') if 'datetime' in df.columns else df

        session_stats = {}
        for session_name, (start_hour, end_hour) in self.SESSIONS.items():
            session_df = df[(df.index.hour >= start_hour) & (df.index.hour < end_hour)]
            if not session_df.empty:
                avg_range = session_df['high'] - session_df['low']
                session_stats[session_name] = {
                    "sample_candles": len(session_df),
                    "avg_range_pips": round(avg_range.mean() / self.feature_engine.pip_size, 2),
                    "max_range_pips": round(avg_range.max() / self.feature_engine.pip_size, 2),
                    "volatility_std": round(session_df['close'].pct_change().std(), 5)
                }

        return session_stats

    def process_market_behavior(self, df: pd.DataFrame, event_timestamps: Optional[List[pd.Timestamp]] = None) -> Dict[str, Any]:
        """Full pipeline to extract deterministic behavior metrics from historical market data."""
        df_featured = self.feature_engine.extract_features(df)
        regime = self.regime_detector.detect_regime(df_featured)
        pattern = self.pattern_detector.detect_price_action_patterns(df_featured)
        session_behavior = self.analyze_session_behavior(df_featured)

        events_summary = {}
        if event_timestamps:
            event_results = [self.event_analyzer.analyze_event_occurrence(df_featured, t) for t in event_timestamps]
            events_summary = self.event_analyzer.aggregate_event_metrics(event_results)

        return {
            "symbol": "XAUUSD",
            "regime": regime,
            "pattern": pattern,
            "sessions": session_behavior,
            "events_aggregate": events_summary
        }