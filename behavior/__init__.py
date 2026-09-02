"""
Behavior Analysis & Template Engine Module for EA Backtest Engine V3
Handles statistical feature extraction, event/session analysis, regime detection, 
AI interpretation, and template lifecycle management.
"""

from .feature_engine import FeatureEngine
from .event_analyzer import EventAnalyzer
from .regime_detector import RegimeDetector
from .pattern_detector import PatternDetector
from .behavior_engine import BehaviorEngine
from .ai_behavior import AIBehaviorAnalyst
from .template_engine import BehaviorTemplateEngine
from .template_validator import TemplateValidator

__all__ = [
    "FeatureEngine",
    "EventAnalyzer",
    "RegimeDetector",
    "PatternDetector",
    "BehaviorEngine",
    "AIBehaviorAnalyst",
    "BehaviorTemplateEngine",
    "TemplateValidator",
]