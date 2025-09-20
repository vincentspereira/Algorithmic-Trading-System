"""Data models for pairs trading."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict

import numpy as np
import pandas as pd


class PairType(Enum):
    """Types of pair relationships."""

    SPREAD = "spread"
    RATIO = "ratio"
    LOG_RATIO = "log_ratio"
    VOLUME_WEIGHTED_SPREAD = "vw_spread"
    VOLUME_WEIGHTED_RATIO = "vw_ratio"


class SignalType(Enum):
    """Trading signal types."""

    CONVERGENCE = "convergence"
    DIVERGENCE = "divergence"
    NEUTRAL = "neutral"
    STRONG_CONVERGENCE = "strong_convergence"
    STRONG_DIVERGENCE = "strong_divergence"


@dataclass
class PairData:
    """Container for pair OHLCV data."""

    symbol_a: str
    symbol_b: str
    open_a: np.ndarray
    high_a: np.ndarray
    low_a: np.ndarray
    close_a: np.ndarray
    volume_a: np.ndarray
    open_b: np.ndarray
    high_b: np.ndarray
    low_b: np.ndarray
    close_b: np.ndarray
    volume_b: np.ndarray
    timestamps: np.ndarray


@dataclass
class SpreadRatioData:
    """Container for calculated spread/ratio data."""

    spread_open: np.ndarray
    spread_high: np.ndarray
    spread_low: np.ndarray
    spread_close: np.ndarray
    spread_volume: np.ndarray
    ratio_open: np.ndarray
    ratio_high: np.ndarray
    ratio_low: np.ndarray
    ratio_close: np.ndarray
    ratio_volume: np.ndarray
    vw_spread_close: np.ndarray
    vw_ratio_close: np.ndarray
    log_ratio_close: np.ndarray


@dataclass
class PairStatistics:
    """Statistical measures for pair relationship."""

    correlation: float
    cointegration_pvalue: float
    beta: float
    r_squared: float
    half_life: float
    volatility_ratio: float
    is_cointegrated: bool
    hedge_ratio: float


@dataclass
class TradingSignal:
    """Trading signal with metadata."""

    signal_type: SignalType
    strength: float
    confidence: float
    entry_price_a: float
    entry_price_b: float
    stop_loss: float
    take_profit: float
    position_size_a: float
    position_size_b: float
    timestamp: pd.Timestamp
    metadata: Dict