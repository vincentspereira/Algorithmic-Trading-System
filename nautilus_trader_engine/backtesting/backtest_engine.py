"""
Backtest Engine Module

This module provides the BacktestEngine class that serves as the main interface
for running backtests in the system. It imports from the base module to maintain
compatibility with existing test files that expect this import path.
"""

# Import the BacktestEngine and BacktestResult from base to maintain compatibility
from .base import BacktestEngine, BacktestResult

# For backward compatibility, also import any specific engine implementations
# that might be expected by tests
from .backtrader_engine import BacktraderEngine
from .trading_gym_engine import TradingGymEngine

__all__ = [
    'BacktestEngine',
    'BacktestResult',
    'BacktraderEngine',
    'TradingGymEngine'
]