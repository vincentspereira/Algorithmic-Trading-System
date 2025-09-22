"""
Gann Analysis Module

This module provides institutional-grade Gann analysis tools including:
- Gann Angles: Dynamic angle calculation with multi-timeframe validation
- Gann Fans: Fan analysis for potential support/resistance levels
- Gann Squares: Square of 9 and other geometric analysis tools
- Gann Retracements: Unique Gann retracement levels
- Gann Pattern Recognition: Detection of classic Gann chart patterns

All implementations include volume-weighting, smart money confirmation,
multi-timeframe analysis, adaptive confidence scoring, and integrated risk management.
"""

from .gann_angles import (
    InstitutionalGannAngles, GannAngle, GannAngleSignal,
    GannAngleType, GannAngleDirection, create_gann_angles_analyzer,
    calculate_gann_angle_price, find_significant_pivots
)

__all__ = [
    "InstitutionalGannAngles",
    "GannAngle",
    "GannAngleSignal",
    "GannAngleType",
    "GannAngleDirection",
    "create_gann_angles_analyzer",
    "calculate_gann_angle_price",
    "find_significant_pivots"
]