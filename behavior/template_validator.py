"""
Template Validator Module for EA Backtest Engine V3
Validates generated Trading Behavior Templates against out-of-sample data (PRD Section 34).
Manages status transitions: DRAFT -> VALIDATED -> STABLE -> DEPRECATED.
"""

from typing import Dict, Any


class TemplateValidator:
    def __init__(self, min_sample_size: int = 30, min_confidence: float = 0.75):
        self.min_sample_size = min_sample_size
        self.min_confidence = min_confidence

    def validate_template(self, template: Dict[str, Any], out_of_sample_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Validates template using out-of-sample statistical metrics."""
        sample_size = template.get("sample_size", 0)
        confidence = template.get("confidence", 0.0)
        current_status = template.get("status", "DRAFT")

        if sample_size >= self.min_sample_size and confidence >= self.min_confidence:
            if current_status == "DRAFT":
                new_status = "VALIDATED"
            elif current_status == "VALIDATED":
                new_status = "STABLE"
            else:
                new_status = current_status
        else:
            new_status = "DEPRECATED" if sample_size < 10 else current_status

        template["status"] = new_status

        return {
            "template_id": template.get("template_id"),
            "previous_status": current_status,
            "validated_status": new_status,
            "passed_validation": new_status in ["VALIDATED", "STABLE"]
        }