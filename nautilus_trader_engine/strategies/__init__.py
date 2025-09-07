"""
Trading Strategies Module

This module contains various trading strategy implementations
that can be used with different backtesting engines.

Author: Vincent S. Pereira
Version: 1.0.0
"""

from .moving_average_crossover import MovingAverageCrossover
from .multi_asset_strategy_engine import MultiAssetStrategyEngine, StrategyConfig, StrategyResult

__all__ = [
    'MovingAverageCrossover',
    'MultiAssetStrategyEngine',
    'StrategyConfig',
    'StrategyResult'
]

__version__ = '1.0.0'