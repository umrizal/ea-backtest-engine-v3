"""
Event Analyzer Module for EA Backtest Engine V3
Analyzes economic events (CPI, NFP, FOMC, etc.) across time windows:
Pre-event: T-60m, T-30m, T-15m, T-5m
Event: T0
Post-event: T+5m, T+15m, T+30m, T+60m, T+120m
"""

import pandas as pd
from typing import Dict, List, Any
from .feature_engine import FeatureEngine


class EventAnalyzer:
    WINDOWS = {
        "pre_60m": (-60, -30),
        "pre_30m": (-30, -15),
        "pre_15m": (-15, -5),
        "pre_5m": (-5, 0),
        "t0": (0, 5),
        "post_5m": (5, 15),
        "post_15m": (15, 30),
        "post_30m": (30, 60),
        "post_60m": (60, 120)
    }

    def __init__(self, feature_engine: FeatureEngine):
        self.feature_engine = feature_engine

    def analyze_event_occurrence(self, df: pd.DataFrame, event_time: pd.Timestamp) -> Dict[str, Any]:
        """Analyzes price action around a single news event occurrence."""
        analysis = {"event_time": str(event_time), "windows": {}}
        
        if not isinstance(df.index, pd.DatetimeIndex):
            df = df.set_index('datetime') if 'datetime' in df.columns else df

        t0_price = df.loc[event_time]['open'] if event_time in df.index else None

        for win_name, (start_min, end_min) in self.WINDOWS.items():
            win_start = event_time + pd.Timedelta(minutes=start_min)
            win_end = event_time + pd.Timedelta(minutes=end_min)
            sub_df = df.loc[win_start:win_end]
            if not sub_df.empty:
                analysis["windows"][win_name] = self.feature_engine.compute_window_metrics(sub_df, initial_price=t0_price)

        return analysis

    def aggregate_event_metrics(self, event_instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregates statistical metrics across multiple historical occurrences (Sample Size)."""
        if not event_instances:
            return {"sample_size": 0}

        sample_size = len(event_instances)
        aggregated = {"sample_size": sample_size, "metrics": {}}

        t0_ranges = []
        initial_expansions = []

        for inst in event_instances:
            t0_data = inst.get("windows", {}).get("t0", {})
            if t0_data:
                t0_ranges.append(t0_data.get("total_range_pips", 0))
                # Threshold > 30 pips considered as initial expansion
                initial_expansions.append(1 if t0_data.get("mfe_pips", 0) > 30 else 0)

        if t0_ranges:
            s_ranges = pd.Series(t0_ranges)
            aggregated["metrics"]["avg_t0_range_pips"] = round(float(s_ranges.mean()), 2)
            aggregated["metrics"]["median_t0_range_pips"] = round(float(s_ranges.median()), 2)
            aggregated["metrics"]["max_t0_range_pips"] = round(float(s_ranges.max()), 2)
            aggregated["metrics"]["min_t0_range_pips"] = round(float(s_ranges.min()), 2)
            aggregated["metrics"]["initial_expansion_prob"] = round(float(pd.Series(initial_expansions).mean()), 2)

        return aggregated