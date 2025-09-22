"""Initialisation for the pair trading indicators module."""
from __future__ import annotations

from .data_models.data_models import (
    PairData,
    PairStatistics,
    PairType,
    SignalType,
    SpreadRatioData,
    TradingSignal,
)
from .engine import PairsTradingEngine
from .indicator_suite import PairsIndicatorSuite
from .pair_selection import PairSelectionModule
from .spread_ratio_calculator import SpreadRatioCalculator
from .strategies.convergence_strategy import ConvergenceStrategy
from .strategies.divergence_strategy import DivergenceStrategy

__all__ = [
    # Data Models
    "PairData",
    "PairStatistics",
    "PairType",
    "SignalType",
    "SpreadRatioData",
    "TradingSignal",
    # Core Components
    "PairsTradingEngine",
    "PairsIndicatorSuite",
    "PairSelectionModule",
    "SpreadRatioCalculator",
    # Strategies
    "ConvergenceStrategy",
    "DivergenceStrategy",
]