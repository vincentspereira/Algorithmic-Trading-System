"""Traditional Technical Analysis Indicators

This module contains classic technical analysis indicators organized by category.
All indicators are implemented with proper mathematical foundations and optimized
for high-frequency trading applications.

Categories:
===========
- Trend Indicators: SMA, EMA, Hull MA, Kaufman AMA, DEMA, TEMA, WMA, etc.
- Momentum Indicators: RSI, MACD, Stochastic, Williams %R, CCI, ROC, PPO, TRIX, etc.
- Volatility Indicators: Bollinger Bands, ATR, Keltner Channels, Donchian Channels, etc.
- Volume Indicators: VWAP, OBV, A/D Line, MFI, Chaikin Oscillator, Volume ROC, etc.

Key Features:
=============
- Consistent alpha = 1.0 / period for all EMA calculations
- Multiple price variants (OHLC, typical price, high-low midpoint)
- Enhanced signal generation with boundaries and strength calculations
- Comprehensive error handling and input validation
- Optimized for performance with NumPy vectorization

Usage:
======
from nautilus_trader_engine.indicators.traditional import (
    trend_indicators,
    momentum_indicators,
    volatility_indicators,
    volume_indicators
)

# Calculate trend indicators
sma_20 = trend_indicators.calculate_sma(prices, period=20)
ema_12 = trend_indicators.calculate_ema(prices, period=12)

# Calculate momentum indicators
rsi_14 = momentum_indicators.calculate_rsi(prices, period=14)
macd_result = momentum_indicators.calculate_macd(prices)

# Calculate volatility indicators
bb_result = volatility_indicators.calculate_bollinger_bands(prices, period=20)
atr_14 = volatility_indicators.calculate_atr(high, low, close, period=14)

# Calculate volume indicators
vwap = volume_indicators.calculate_vwap(high, low, close, volume)
obv = volume_indicators.calculate_obv(close, volume)
"""

try:
    from . import trend_indicators
    from . import momentum_indicators
    from . import volatility_indicators
    from . import volume_indicators
    from . import technical_indicators
except ImportError:
    # Handle missing dependencies gracefully
    pass

__all__ = [
    'trend_indicators',
    'momentum_indicators',
    'volatility_indicators',
    'volume_indicators',
    'technical_indicators'
]