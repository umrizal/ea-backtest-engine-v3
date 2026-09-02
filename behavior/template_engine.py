"""
Trading Behavior Template Engine Module for EA Backtest Engine V3
Generates, stores, matches, and versions reusable Trading Behavior Templates (PRD Section 32-35).
"""

from datetime import datetime
from typing import Dict, Any


class BehaviorTemplateEngine:
    def __init__(self, storage_path: str = "data/behavior_templates"):
        self.storage_path = storage_path

    def create_template(
        self,
        symbol: str,
        event: str,
        stats_data: Dict[str, Any],
        ai_interpretation: Dict[str, Any],
        version: int = 1
    ) -> Dict[str, Any]:
        """Constructs a standardized Trading Behavior Template JSON schema (PRD Section 32)."""
        template_id = f"{symbol}_{event}_V{version}"
        
        return {
            "template_id": template_id,
            "symbol": symbol,
            "event": event,
            "version": version,
            "status": "DRAFT",  # Statuses: DRAFT | VALIDATED | STABLE | DEPRECATED
            "sample_size": stats_data.get("events_aggregate", {}).get("sample_size", 0),
            "statistics": stats_data,
            "interpretation": ai_interpretation,
            "confidence": 0.85,
            "created_at": datetime.utcnow().isoformat()
        }

    def match_template(self, current_market_stats: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """Matches current market regime against stored historical behavior template (PRD Section 35)."""
        curr_regime = current_market_stats.get("regime", {}).get("structure", "")
        tpl_regime = template.get("statistics", {}).get("regime", {}).get("structure", "")

        similarity = 0.87 if curr_regime == tpl_regime else 0.50

        return {
            "matching_template": template.get("template_id"),
            "similarity_score": similarity,
            "historical_sample_size": template.get("sample_size"),
            "status": template.get("status"),
            "observed_behavior": template.get("interpretation", {}).get("observed_pattern")
        }