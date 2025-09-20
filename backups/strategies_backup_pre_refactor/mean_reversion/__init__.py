#!/usr/bin/env python3
"""
Mean Reversion Strategies Module

This module contains mean reversion trading strategies that capitalize on the tendency
of asset prices to revert to their historical mean or average value.

Strategies included:
- RSI(2) Mean Reversion Strategy: Uses 2-period RSI for short-term mean reversion signals
- Bollinger Band Mean Reversion: Uses Bollinger Band extremes for mean reversion
- Statistical Arbitrage: Pairs trading based on statistical relationships

Key Features:
- Advanced market regime detection
- Multi-factor signal generation
- Comprehensive risk management
- Performance analytics integration
"""

from .rsi2_strategy import RSI2Strategy, RSI2Config, create_rsi2_strategy as create_rsi2_alt
from .rsi2_mean_reversion_strategy import (
    RSI2MeanReversionStrategy,
    create_rsi2_strategy
)
from ..core.mean_reversion.rsi2_mean_reversion_strategy import (
    MarketRegimeClassifier
)

__all__ = [
    'RSI2Strategy',
    'RSI2MeanReversionStrategy',
    'MarketRegimeClassifier',
    'create_rsi2_strategy',
    'RSI2Config',
    'create_rsi2_alt'
]

__version__ = '1.0.0'
__author__ = 'Algorithmic Trading System'
__description__ = 'Mean reversion trading strategies with advanced analytics'