"""Volume-Weighted Technical Indicators

This module contains volume-weighted variants of traditional technical indicators
using the methodology: (price × volume).ewm() / volume.ewm() for enhanced accuracy
in volume-sensitive market analysis.

Components:
===========
- volume_weighted_indicators: Core volume-weighted indicator calculations
- institutional_volume_profile: Professional volume profile analysis
- volume_confirmation: Volume-based signal confirmation system

Key Features:
=============
- Proper volume weighting using exponential weighted moving averages
- Institutional-grade volume profile analysis
- Volume confirmation for enhanced signal reliability
- Support for multiple price variants (OHLC, typical price, etc.)
- Optimized calculations for high-frequency trading

Volume-Weighted Indicators:
==========================
- VW SMA: Volume-Weighted Simple Moving Average
- VW EMA: Volume-Weighted Exponential Moving Average
- VW MACD: Volume-Weighted MACD
- VW RSI: Volume-Weighted RSI
- VW ATR: Volume-Weighted Average True Range
- VW MFI: Volume-Weighted Money Flow Index
- VW Bollinger Bands: Volume-Weighted Bollinger Bands

Usage:
======
from nautilus_trader_engine.indicators.volume_weighted import (
    volume_weighted_indicators,
    institutional_volume_profile,
    volume_confirmation
)

# Calculate volume-weighted indicators
vw_sma = volume_weighted_indicators.calculate_vw_sma(prices, volumes, period=20)
vw_ema = volume_weighted_indicators.calculate_vw_ema(prices, volumes, period=12)
vw_macd = volume_weighted_indicators.calculate_vw_macd(prices, volumes)

# Analyze volume profile
volume_profile = institutional_volume_profile.analyze_volume_profile(ohlcv_data)
poc_level = volume_profile['point_of_control']

# Confirm signals with volume
confirmation = volume_confirmation.confirm_signal(
    signal_strength=0.8,
    volume_data=volume_data,
    price_data=price_data
)
"""

try:
    from . import volume_weighted_indicators
    from . import institutional_volume_profile
    from . import volume_confirmation
except ImportError:
    # Handle missing dependencies gracefully
    pass

__all__ = [
    'volume_weighted_indicators',
    'institutional_volume_profile',
    'volume_confirmation'
]