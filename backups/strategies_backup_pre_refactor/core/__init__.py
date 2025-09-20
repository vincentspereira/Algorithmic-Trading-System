"""Core Strategy Implementations

This module contains the core trading strategy implementations organized by category.
Each category represents a different trading approach with specialized strategies.

Categories:
===========
- mean_reversion: Strategies that profit from price reversions to mean
- trend_following: Strategies that follow market trends and momentum
- volatility: Strategies based on volatility patterns and breakouts
- multi_asset: Strategies that trade across multiple asset classes
- machine_learning: AI/ML-powered trading strategies

Usage:
======
from nautilus_trader_engine.strategies.core.mean_reversion import RSI2MeanReversionStrategy
from nautilus_trader_engine.strategies.core.trend_following import MovingAverageCrossoverStrategy
from nautilus_trader_engine.strategies.core.machine_learning import RLStrategy
"""

# Import base strategy components
from .base_strategy import (
    BaseStrategy,
    StrategyConfig,
    Signal,
    Position,
    SignalType,
    PositionSide,
    OrderType,
    StrategyManager,
    create_signal,
    validate_ohlcv_data,
    SimpleMovingAverageStrategy
)

# Import all strategy categories
try:
    from . import mean_reversion
    from . import trend_following
    from . import volatility
    from . import multi_asset
    from . import machine_learning
except ImportError:
    # Graceful handling during development
    pass

__all__ = [
    # Base strategy components
    'BaseStrategy',
    'StrategyConfig',
    'Signal',
    'Position',
    'SignalType',
    'PositionSide',
    'OrderType',
    'StrategyManager',
    'create_signal',
    'validate_ohlcv_data',
    'SimpleMovingAverageStrategy',
    # Strategy categories
    'mean_reversion',
    'trend_following',
    'volatility',
    'multi_asset',
    'machine_learning'
]