"""
A comprehensive chart pattern detection module for financial markets.

This module provides a robust framework for identifying various chart patterns
in price data, including single-candle, multi-candle, and complex chart formations.
It is designed for high-performance, real-time analysis and can be integrated
into automated trading systems, market scanners, and analytical dashboards.

Features:
- Detection of a wide range of bullish, bearish, and neutral patterns.
- Confidence scoring based on pattern quality and volume confirmation.
- Strength analysis to gauge the potential impact of a pattern.
- Integration with volume profile and smart money flow analysis.
- Customizable and extensible for adding new patterns.

Available Components:
- `PatternType`: Enum for classifying patterns (e.g., REVERSAL, CONTINUATION).
- `PatternStrength`: Enum for pattern strength levels (e.g., WEAK, STRONG).
- `VolumeProfile`: Enum for volume characteristics (e.g., HIGH, LOW).
- `PatternAnalysis`: Dataclass for storing detailed pattern information.
- `CandleProperties`: Helper class for candle-specific calculations.
- `ConsolidatedPatternDetector`: Main class for detecting and analyzing patterns.

Usage:
    from nautilus_trader_engine.indicators.patterns.chart_patterns import ConsolidatedPatternDetector

    detector = ConsolidatedPatternDetector()

    for bar in price_data:
        analysis = detector.calculate(bar)
        if analysis:
            print(f"Pattern detected: {analysis.pattern_name} with confidence {analysis.confidence}")

"""

from .base import (
    PatternType,
    PatternStrength,
    VolumeProfile,
    PatternAnalysis,
    CandleProperties,
)
from .detector import ConsolidatedPatternDetector

__all__ = [
    "PatternType",
    "PatternStrength",
    "VolumeProfile",
    "PatternAnalysis",
    "CandleProperties",
    "ConsolidatedPatternDetector",
]