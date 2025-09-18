"""Pattern Recognition and Chart Pattern Analysis

This module provides comprehensive pattern recognition capabilities including
candlestick patterns, chart patterns, and institutional pattern analysis.
All patterns include volume confirmation and trend context analysis.

Components:
===========
- institutional_candlestick_patterns: Professional-grade candlestick pattern recognition
- pattern_indicators: Chart pattern detection and analysis

Key Features:
=============
- 75+ candlestick pattern recognition
- Volume confirmation for enhanced reliability
- Trend context analysis (bullish/bearish/neutral)
- Pattern strength scoring and confidence levels
- Real-time pattern detection
- Institutional-grade pattern analysis

Candlestick Patterns:
====================
Reversal Patterns:
- Hammer/Hanging Man (trend context dependent)
- Shooting Star/Inverted Hammer
- Engulfing (Bullish/Bearish)
- Morning Star/Evening Star (3-candle patterns)
- Doji variations (Dragonfly, Gravestone, Long-legged)
- Harami (Bullish/Bearish)
- Piercing Line/Dark Cloud Cover

Continuation Patterns:
- Marubozu (strong directional)
- Spinning Top (indecision)
- Three White Soldiers/Three Black Crows
- Rising/Falling Three Methods

Indecision Patterns:
- Doji (various types)
- Spinning Top
- High Wave Candles

Chart Patterns:
===============
- Head and Shoulders
- Double Top/Bottom
- Triangle Patterns (Ascending, Descending, Symmetrical)
- Flag and Pennant Patterns
- Cup and Handle
- Wedge Patterns

Usage:
======
from nautilus_trader_engine.indicators.patterns import (
    institutional_candlestick_patterns,
    pattern_indicators
)

# Detect candlestick patterns
patterns = institutional_candlestick_patterns.detect_patterns(
    ohlc_data,
    volume_data,
    include_volume_confirmation=True
)

# Analyze pattern strength
for pattern in patterns:
    print(f"Pattern: {pattern['name']}")
    print(f"Strength: {pattern['strength']}")
    print(f"Confidence: {pattern['confidence']}")
    print(f"Volume Confirmed: {pattern['volume_confirmed']}")

# Detect chart patterns
chart_patterns = pattern_indicators.detect_chart_patterns(
    price_data,
    volume_data,
    lookback_period=50
)

# Real-time pattern monitoring
pattern_monitor = institutional_candlestick_patterns.PatternMonitor()
pattern_monitor.add_data(new_ohlc_bar)
current_patterns = pattern_monitor.get_active_patterns()
"""

try:
    from . import institutional_candlestick_patterns
    from . import pattern_indicators
except ImportError:
    # Handle missing dependencies gracefully
    pass

__all__ = [
    'institutional_candlestick_patterns',
    'pattern_indicators'
]