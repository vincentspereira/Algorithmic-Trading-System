from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np


class MarketRegime(Enum):
    """Market regime classifications"""

    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"
    UNKNOWN = "unknown"


class SignalQuality(Enum):
    """Signal quality classifications"""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    FILTERED = "filtered"


@dataclass
class MLConfig:
    """Configuration for ML enhancements"""

    enable_regime_detection: bool = True
    enable_meta_labeling: bool = True
    enable_probabilistic_forecasting: bool = True
    enable_factor_validation: bool = True
    enable_signal_decay: bool = True

    # Model parameters
    regime_lookback_period: int = 100
    meta_labeling_period: int = 50
    monte_carlo_simulations: int = 1000
    confidence_threshold: float = 0.7

    # Factor validation
    correlation_threshold: float = 0.6
    factor_weight: float = 0.3

    # Signal decay
    signal_half_life: float = 10.0  # periods
    decay_function: str = "exponential"  # exponential, linear, power


@dataclass
class MarketRegimeData:
    """Market regime detection data"""

    regime: MarketRegime
    confidence: float
    volatility: float
    trend_strength: float
    momentum: float
    volume_profile: str
    timestamp: datetime
    features: Dict[str, float] = field(default_factory=dict)


@dataclass
class MetaLabelResult:
    """Meta-labeling result"""

    signal_quality: SignalQuality
    predicted_profitability: float
    confidence: float
    risk_score: float
    recommended_position_size: float
    features_used: List[str]
    model_version: str


@dataclass
class ProbabilisticForecast:
    """Probabilistic forecast result"""

    mean_prediction: float
    std_prediction: float
    confidence_intervals: Dict[str, Tuple[float, float]]  # e.g., {'95%': (lower, upper)}
    probability_distributions: Dict[str, float]  # e.g., {'above_vwap': 0.75}
    scenario_probabilities: Dict[str, float]
    monte_carlo_paths: Optional[np.ndarray] = None