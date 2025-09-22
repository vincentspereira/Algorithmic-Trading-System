"""
Fibonacci Analysis Module

This module provides institutional-grade Fibonacci analysis tools including:
- Fibonacci Retracement: Dynamic retracement level calculation with confluence analysis
- Fibonacci Extension: Extension level analysis for profit targets
- Fibonacci Projection: Price projection using Fibonacci ratios
- Fibonacci Expansion: Advanced expansion analysis
- Confluence Detection: Multi-level confluence analysis
- Volume-weighted Strength: Volume confirmation for Fibonacci levels

All implementations include volume-weighting, smart money confirmation,
multi-timeframe analysis, adaptive confidence scoring, and integrated risk management.
"""

from .fibonacci_analysis import (
    InstitutionalFibonacciAnalyzer, FibonacciLevel, FibonacciSignal,
    FibonacciLevelType, FibonacciStrength, create_fibonacci_analyzer,
    calculate_fibonacci_retracement, calculate_fibonacci_extension,
    find_fibonacci_confluence
)

__all__ = [
    "InstitutionalFibonacciAnalyzer",
    "FibonacciLevel",
    "FibonacciSignal",
    "FibonacciLevelType",
    "FibonacciStrength",
    "create_fibonacci_analyzer",
    "calculate_fibonacci_retracement",
    "calculate_fibonacci_extension",
    "find_fibonacci_confluence"
]