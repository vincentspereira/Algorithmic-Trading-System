"""
Trading Strategies Module

This module contains various trading strategy implementations
that can be used with different backtesting engines.

Author: Kilo Code
Version: 1.0.0
"""

from .moving_average_crossover import MovingAverageCrossover

__all__ = [
    'MovingAverageCrossover'
]

__version__ = '1.0.0'