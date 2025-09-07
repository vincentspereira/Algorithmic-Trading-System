#!/usr/bin/env python3
"""
Backtesting Service Module
Provides service layer for backtesting operations.
"""

from .executors.nautilus_executor import BacktestExecutor

__all__ = [
    "BacktestExecutor"
]