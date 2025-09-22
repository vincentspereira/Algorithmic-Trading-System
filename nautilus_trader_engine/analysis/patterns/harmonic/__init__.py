"""
Harmonic Patterns Module

This module provides institutional-grade harmonic pattern analysis tools including:
- Gartley Pattern Recognition: Classic 5-point harmonic patterns with precise Fibonacci ratios
- Butterfly Pattern Detection: Advanced harmonic pattern analysis
- Bat Pattern Identification: Precise Fibonacci ratio validation
- Crab Pattern Recognition: Extreme harmonic movement patterns
- Multi-Timeframe Validation: Pattern confirmation across different timeframes
- Volume-Weighted Pattern Strength: Volume confirmation for pattern validity
- Smart Money Integration: Institutional activity pattern validation
- Adaptive Confidence Scoring: Dynamic scoring based on pattern completeness
- Risk Management Integration: Pattern-based entry, stop, and target levels

All harmonic patterns use precise Fibonacci ratios and include volume-weighting,
multi-timeframe confirmation, and integrated risk management.
"""

from .harmonic_patterns import (
    InstitutionalHarmonicAnalyzer, HarmonicPattern, HarmonicSignal,
    HarmonicPatternType, PatternDirection, PatternCompleteness, PatternStrength,
    HarmonicPoint, create_harmonic_analyzer, calculate_fibonacci_ratio,
    validate_harmonic_ratio
)

__all__ = [
    "InstitutionalHarmonicAnalyzer",
    "HarmonicPattern",
    "HarmonicSignal",
    "HarmonicPatternType",
    "PatternDirection",
    "PatternCompleteness",
    "PatternStrength",
    "HarmonicPoint",
    "create_harmonic_analyzer",
    "calculate_fibonacci_ratio",
    "validate_harmonic_ratio"
]