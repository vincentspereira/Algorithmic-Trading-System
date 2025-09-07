"""
Backtesting Module for Nautilus Trader Engine

This module provides backtesting utilities and infrastructure for testing
trading strategies using multiple backtesting frameworks including backtrader
and TradingGym.

Author: Vincent S. Pereira
Version: 1.0.0
"""

from .base import BacktestEngine, BacktestResult

# Lazily import backtrader engine to avoid hard dependency during test collection
try:
    from .backtrader_engine import BacktraderEngine  # type: ignore
except Exception as e:
    BacktraderEngine = None  # type: ignore

# Lazily import trading gym engine as well
try:
    from .trading_gym_engine import TradingGymEngine  # type: ignore
except Exception:
    TradingGymEngine = None  # type: ignore

# Import other backtesting components
try:
    from .backtest_engine import BacktestEngine as BacktestEngineAlias  # type: ignore
except Exception:
    BacktestEngineAlias = None  # type: ignore

try:
    from .risk_manager import RiskManager  # type: ignore
except Exception:
    RiskManager = None  # type: ignore

try:
    from .performance_analyzer import PerformanceAnalyzer  # type: ignore
except Exception:
    PerformanceAnalyzer = None  # type: ignore

try:
    from .report_generator import ReportGenerator  # type: ignore
except Exception:
    ReportGenerator = None  # type: ignore

try:
    from .strategy_optimizer import StrategyOptimizer  # type: ignore
except Exception:
    StrategyOptimizer = None  # type: ignore

__all__ = [
    'BacktestEngine',
    'BacktestResult', 
    'BacktraderEngine',
    'TradingGymEngine',
    'RiskManager',
    'PerformanceAnalyzer',
    'ReportGenerator',
    'StrategyOptimizer'
]

__version__ = '1.0.0'