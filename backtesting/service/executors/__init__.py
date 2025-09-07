#!/usr/bin/env python3
"""
Backtesting Executors Module
Provides execution engines for backtesting.
"""

from .nautilus_executor import BacktestExecutor

__all__ = [
    "BacktestExecutor"
]