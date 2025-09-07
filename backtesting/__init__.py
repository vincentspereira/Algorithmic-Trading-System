#!/usr/bin/env python3
"""
Backtesting Module
Provides backtesting capabilities for algorithmic trading strategies.
"""

__version__ = "1.0.0"
__author__ = "Algorithmic Trading System"

from .service.executors.nautilus_executor import BacktestExecutor

__all__ = [
    "BacktestExecutor"
]