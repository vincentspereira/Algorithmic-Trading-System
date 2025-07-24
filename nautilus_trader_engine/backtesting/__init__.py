"""
Backtesting Module for Nautilus Trader Engine

This module provides backtesting utilities and infrastructure for testing
trading strategies using multiple backtesting frameworks including backtrader
and TradingGym.

Author: Kilo Code
Version: 1.0.0
"""

from .base import BacktestEngine, BacktestResult
from .backtrader_engine import BacktraderEngine
from .trading_gym_engine import TradingGymEngine

__all__ = [
    'BacktestEngine',
    'BacktestResult', 
    'BacktraderEngine',
    'TradingGymEngine'
]

__version__ = '1.0.0'