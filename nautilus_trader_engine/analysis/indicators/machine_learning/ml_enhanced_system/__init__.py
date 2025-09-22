"""
ML-Enhanced Indicator System.

This module provides a comprehensive system for enhancing trading signals with machine
learning models. It includes components for market regime detection, meta-labeling,
probabilistic forecasting, and signal decay.
"""

from .data_models import (
    MarketRegime,
    SignalQuality,
    MLConfig,
    MarketRegimeData,
    MetaLabelResult,
    ProbabilisticForecast,
)
from .market_regime_detector import MarketRegimeDetector
from .meta_labeling_system import MetaLabelingSystem
from .probabilistic_forecaster import ProbabilisticForecaster
from .signal_decay_model import SignalDecayModel
from .ml_enhanced_indicator_system import MLEnhancedIndicatorSystem
from .factory import create_ml_enhanced_system

__all__ = [
    # Enums
    "MarketRegime",
    "SignalQuality",
    # Dataclasses
    "MLConfig",
    "MarketRegimeData",
    "MetaLabelResult",
    "ProbabilisticForecast",
    # Classes
    "MarketRegimeDetector",
    "MetaLabelingSystem",
    "ProbabilisticForecaster",
    "SignalDecayModel",
    "MLEnhancedIndicatorSystem",
    # Functions
    "create_ml_enhanced_system",
]