"""
Composite Indicators Analysis Suite for NautilusTrader Engine

This comprehensive suite provides institutional-grade composite indicator analysis tools including:
- Composite Indicators: Advanced combination of multiple technical indicators into sophisticated signals
- Signal Aggregation: Weighted combination of momentum, trend, volatility, and volume indicators
- Market Regime Detection: Automatic market condition assessment for signal filtering
- Divergence Analysis: Detection of divergences between composite signals and price
- Confluence Scoring: Multi-factor confirmation scoring for enhanced reliability

All implementations include volume-weighting, smart money confirmation,
multi-timeframe analysis, adaptive confidence scoring, and integrated risk management.
"""

from .composite_indicators import (
    CompositeIndicators, CompositeSignal, CompositeType, SignalStrength,
    CompositeComponent
)

__all__ = [
    # Composite Indicators
    'CompositeIndicators', 'CompositeSignal', 'CompositeType', 'SignalStrength',
    'CompositeComponent'
]