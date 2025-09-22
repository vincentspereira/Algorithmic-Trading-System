"""
Chart Patterns Module

This module provides institutional-grade chart pattern analysis tools including:
- Head & Shoulders Pattern: Classic reversal pattern detection
- Double/Triple Top/Bottom: Trend reversal pattern recognition
- Triangle Patterns: Ascending, descending, and symmetrical triangle analysis
- Wedge Patterns: Rising and falling wedge pattern identification
- Flag & Pennant Patterns: Short-term continuation pattern detection
- Cup & Handle Patterns: Bullish continuation pattern recognition
- Multi-Timeframe Validation: Pattern confirmation across timeframes
- Volume-Weighted Pattern Strength: Volume confirmation for pattern validity
- Smart Money Integration: Institutional activity pattern validation
- Adaptive Confidence Scoring: Dynamic scoring based on pattern completeness
- Risk Management Integration: Pattern-based entry, stop, and target levels

All chart patterns include volume-weighting, multi-timeframe confirmation,
and integrated risk management.
"""

from .chart_patterns import (
    InstitutionalChartPatternAnalyzer, ChartPattern, ChartSignal,
    ChartPatternType, PatternCategory, PatternDirection, PatternCompleteness, PatternStrength,
    create_chart_pattern_analyzer, calculate_pattern_target, validate_pattern_geometry
)

__all__ = [
    "InstitutionalChartPatternAnalyzer",
    "ChartPattern",
    "ChartSignal",
    "ChartPatternType",
    "PatternCategory",
    "PatternDirection",
    "PatternCompleteness",
    "PatternStrength",
    "create_chart_pattern_analyzer",
    "calculate_pattern_target",
    "validate_pattern_geometry"
]