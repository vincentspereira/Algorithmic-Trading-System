"""
Ensemble Methods for Technical Indicators
Combines multiple indicators using various ensemble techniques for improved accuracy.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Callable, Tuple, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from scipy import stats
import time

logger = logging.getLogger(__name__)


class EnsembleMethod(Enum):
    """Available ensemble methods."""
    SIMPLE_AVERAGE = "simple_average"
    WEIGHTED_AVERAGE = "weighted_average"
    VOTING = "voting"
    STACKED = "stacked"
    BOOSTING = "boosting"
    BAGGING = "bagging"
    ADAPTIVE = "adaptive"


class SignalType(Enum):
    """Types of signals that can be ensembled."""
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    COMPOSITE = "composite"


@dataclass
class IndicatorSignal:
    """Signal from a single indicator."""
    indicator_name: str
    signal_type: SignalType
    value: float
    confidence: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnsembleResult:
    """Result from ensemble processing."""
    ensemble_value: float
    confidence: float
    constituent_signals: List[IndicatorSignal]
    method_used: EnsembleMethod
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnsembleStrategy(ABC):
    """Base class for ensemble strategies."""

    @abstractmethod
    def combine_signals(self, signals: List[IndicatorSignal],
                       market_data: Optional[pd.DataFrame] = None) -> EnsembleResult:
        """Combine multiple signals into an ensemble result."""
        pass

    @abstractmethod
    def get_method_name(self) -> str:
        """Get the name of this ensemble method."""
        pass

    @abstractmethod
    def update_weights(self, signals: List[IndicatorSignal],
                      actual_performance: float) -> None:
        """Update weights based on performance feedback."""
        pass


class SimpleAverageEnsemble(EnsembleStrategy):
    """Simple averaging of indicator signals."""

    def combine_signals(self, signals: List[IndicatorSignal],
                       market_data: Optional[pd.DataFrame] = None) -> EnsembleResult:
        """Combine signals using simple averaging."""
        if not signals:
            return EnsembleResult(0.0, 0.0, [], EnsembleMethod.SIMPLE_AVERAGE)

        values = [s.value for s in signals]
        confidences = [s.confidence for s in signals]

        ensemble_value = np.mean(values)
        confidence = np.mean(confidences)

        return EnsembleResult(
            ensemble_value=ensemble_value,
            confidence=confidence,
            constituent_signals=signals,
            method_used=EnsembleMethod.SIMPLE_AVERAGE
        )

    def get_method_name(self) -> str:
        return "simple_average"

    def update_weights(self, signals: List[IndicatorSignal],
                      actual_performance: float) -> None:
        """Simple average doesn't use weights."""
        pass


class WeightedAverageEnsemble(EnsembleStrategy):
    """Weighted averaging based on indicator performance."""

    def __init__(self):
        self.weights: Dict[str, float] = {}
        self.performance_history: Dict[str, List[float]] = {}

    def combine_signals(self, signals: List[IndicatorSignal],
                       market_data: Optional[pd.DataFrame] = None) -> EnsembleResult:
        """Combine signals using weighted averaging."""
        if not signals:
            return EnsembleResult(0.0, 0.0, [], EnsembleMethod.WEIGHTED_AVERAGE)

        # Initialize weights if not set
        for signal in signals:
            if signal.indicator_name not in self.weights:
                self.weights[signal.indicator_name] = 1.0
                self.performance_history[signal.indicator_name] = []

        # Calculate weighted average
        total_weight = sum(self.weights[s.indicator_name] for s in signals)
        if total_weight == 0:
            return EnsembleResult(0.0, 0.0, signals, EnsembleMethod.WEIGHTED_AVERAGE)

        ensemble_value = sum(
            s.value * self.weights[s.indicator_name] for s in signals
        ) / total_weight

        # Weighted confidence
        confidence = sum(
            s.confidence * self.weights[s.indicator_name] for s in signals
        ) / total_weight

        return EnsembleResult(
            ensemble_value=ensemble_value,
            confidence=confidence,
            constituent_signals=signals,
            method_used=EnsembleMethod.WEIGHTED_AVERAGE
        )

    def get_method_name(self) -> str:
        return "weighted_average"

    def update_weights(self, signals: List[IndicatorSignal],
                      actual_performance: float) -> None:
        """Update weights based on performance."""
        for signal in signals:
            indicator_name = signal.indicator_name

            # Store performance history
            if indicator_name not in self.performance_history:
                self.performance_history[indicator_name] = []

            self.performance_history[indicator_name].append(actual_performance)

            # Keep only recent performance (last 50 entries)
            if len(self.performance_history[indicator_name]) > 50:
                self.performance_history[indicator_name].pop(0)

            # Update weight based on recent performance
            if len(self.performance_history[indicator_name]) >= 10:
                recent_performance = np.mean(self.performance_history[indicator_name][-10:])
                self.weights[indicator_name] = max(0.1, min(2.0, recent_performance))


class VotingEnsemble(EnsembleStrategy):
    """Voting-based ensemble for directional signals."""

    def __init__(self, threshold: float = 0.0):
        self.threshold = threshold

    def combine_signals(self, signals: List[IndicatorSignal],
                       market_data: Optional[pd.DataFrame] = None) -> EnsembleResult:
        """Combine signals using voting."""
        if not signals:
            return EnsembleResult(0.0, 0.0, [], EnsembleMethod.VOTING)

        # Count votes for positive and negative signals
        positive_votes = sum(1 for s in signals if s.value > self.threshold)
        negative_votes = sum(1 for s in signals if s.value < -self.threshold)
        neutral_votes = len(signals) - positive_votes - negative_votes

        # Determine ensemble signal
        if positive_votes > negative_votes and positive_votes > neutral_votes:
            ensemble_value = 1.0
        elif negative_votes > positive_votes and negative_votes > neutral_votes:
            ensemble_value = -1.0
        else:
            ensemble_value = 0.0

        # Calculate confidence based on vote majority
        total_votes = len(signals)
        majority_votes = max(positive_votes, negative_votes, neutral_votes)
        confidence = majority_votes / total_votes

        return EnsembleResult(
            ensemble_value=ensemble_value,
            confidence=confidence,
            constituent_signals=signals,
            method_used=EnsembleMethod.VOTING
        )

    def get_method_name(self) -> str:
        return "voting"

    def update_weights(self, signals: List[IndicatorSignal],
                      actual_performance: float) -> None:
        """Voting doesn't use weights."""
        pass


class StackedEnsemble(EnsembleStrategy):
    """Stacked ensemble using machine learning."""

    def __init__(self):
        self.meta_model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.trained = False
        self.feature_history: List[List[float]] = []
        self.target_history: List[float] = []

    def combine_signals(self, signals: List[IndicatorSignal],
                       market_data: Optional[pd.DataFrame] = None) -> EnsembleResult:
        """Combine signals using stacking."""
        if not signals:
            return EnsembleResult(0.0, 0.0, [], EnsembleMethod.STACKED)

        # Extract features from signals
        features = []
        for signal in signals:
            features.extend([
                signal.value,
                signal.confidence,
                signal.metadata.get('volatility', 0),
                signal.metadata.get('trend_strength', 0)
            ])

        # Add market data features if available
        if market_data is not None and not market_data.empty:
            features.extend([
                market_data['close'].pct_change().std() if 'close' in market_data.columns else 0,
                market_data['volume'].mean() if 'volume' in market_data.columns else 0
            ])

        # Use trained model if available
        if self.trained and len(features) == len(self.feature_history[0]) if self.feature_history else True:
            features_scaled = self.scaler.transform([features])
            ensemble_value = self.meta_model.predict(features_scaled)[0]
            confidence = 0.8  # High confidence for ML predictions
        else:
            # Fallback to simple average
            values = [s.value for s in signals]
            ensemble_value = np.mean(values)
            confidence = np.mean([s.confidence for s in signals])

        return EnsembleResult(
            ensemble_value=ensemble_value,
            confidence=confidence,
            constituent_signals=signals,
            method_used=EnsembleMethod.STACKED
        )

    def get_method_name(self) -> str:
        return "stacked"

    def update_weights(self, signals: List[IndicatorSignal],
                      actual_performance: float) -> None:
        """Update the meta-model with new training data."""
        # Extract features
        features = []
        for signal in signals:
            features.extend([
                signal.value,
                signal.confidence,
                signal.metadata.get('volatility', 0),
                signal.metadata.get('trend_strength', 0)
            ])

        # Store training data
        self.feature_history.append(features)
        self.target_history.append(actual_performance)

        # Train model if we have enough data
        if len(self.feature_history) >= 100 and not self.trained:
            X = np.array(self.feature_history)
            y = np.array(self.target_history)

            X_scaled = self.scaler.fit_transform(X)
            self.meta_model.fit(X_scaled, y)
            self.trained = True
            logger.info("Stacked ensemble model trained")


class AdaptiveEnsemble(EnsembleStrategy):
    """Adaptive ensemble that switches methods based on market conditions."""

    def __init__(self):
        self.strategies = {
            EnsembleMethod.SIMPLE_AVERAGE: SimpleAverageEnsemble(),
            EnsembleMethod.WEIGHTED_AVERAGE: WeightedAverageEnsemble(),
            EnsembleMethod.VOTING: VotingEnsemble(),
            EnsembleMethod.STACKED: StackedEnsemble()
        }
        self.performance_history: Dict[EnsembleMethod, List[float]] = {}
        self.current_method = EnsembleMethod.SIMPLE_AVERAGE

    def combine_signals(self, signals: List[IndicatorSignal],
                       market_data: Optional[pd.DataFrame] = None) -> EnsembleResult:
        """Combine signals using adaptive method selection."""
        if not signals:
            return EnsembleResult(0.0, 0.0, [], EnsembleMethod.ADAPTIVE)

        # Choose best method based on historical performance
        self.current_method = self._select_best_method(signals)

        # Use selected strategy
        strategy = self.strategies[self.current_method]
        result = strategy.combine_signals(signals, market_data)

        # Update result metadata
        result.metadata["selected_method"] = self.current_method.value

        return result

    def _select_best_method(self, signals: List[IndicatorSignal]) -> EnsembleMethod:
        """Select the best ensemble method based on historical performance."""
        if not self.performance_history:
            return EnsembleMethod.SIMPLE_AVERAGE

        # Calculate average performance for each method
        method_performance = {}
        for method, performances in self.performance_history.items():
            if performances:
                method_performance[method] = np.mean(performances[-20:])  # Last 20 performances

        if method_performance:
            best_method = max(method_performance, key=method_performance.get)
            return best_method

        return EnsembleMethod.SIMPLE_AVERAGE

    def get_method_name(self) -> str:
        return "adaptive"

    def update_weights(self, signals: List[IndicatorSignal],
                      actual_performance: float) -> None:
        """Update performance history for method selection."""
        if self.current_method not in self.performance_history:
            self.performance_history[self.current_method] = []

        self.performance_history[self.current_method].append(actual_performance)

        # Keep only recent history
        for method in self.performance_history:
            if len(self.performance_history[method]) > 100:
                self.performance_history[method] = self.performance_history[method][-50:]


class IndicatorEnsemble:
    """
    Main class for managing indicator ensembles.
    """

    def __init__(self, signal_type: SignalType, method: EnsembleMethod = EnsembleMethod.ADAPTIVE):
        self.signal_type = signal_type
        self.method = method
        self.strategies: Dict[EnsembleMethod, EnsembleStrategy] = {
            EnsembleMethod.SIMPLE_AVERAGE: SimpleAverageEnsemble(),
            EnsembleMethod.WEIGHTED_AVERAGE: WeightedAverageEnsemble(),
            EnsembleMethod.VOTING: VotingEnsemble(),
            EnsembleMethod.STACKED: StackedEnsemble(),
            EnsembleMethod.ADAPTIVE: AdaptiveEnsemble()
        }
        self.current_strategy = self.strategies[method]
        self.signal_history: List[EnsembleResult] = []

    def add_signals(self, signals: List[IndicatorSignal],
                   market_data: Optional[pd.DataFrame] = None) -> EnsembleResult:
        """Add signals and get ensemble result."""
        result = self.current_strategy.combine_signals(signals, market_data)

        # Store result
        self.signal_history.append(result)
        if len(self.signal_history) > 1000:  # Keep last 1000 results
            self.signal_history.pop(0)

        return result

    def update_performance(self, actual_performance: float) -> None:
        """Update strategy performance for learning."""
        if self.signal_history:
            last_result = self.signal_history[-1]
            self.current_strategy.update_weights(
                last_result.constituent_signals,
                actual_performance
            )

    def get_ensemble_statistics(self) -> Dict[str, Any]:
        """Get statistics about ensemble performance."""
        if not self.signal_history:
            return {}

        values = [r.ensemble_value for r in self.signal_history]
        confidences = [r.confidence for r in self.signal_history]

        return {
            "total_signals": len(self.signal_history),
            "mean_value": np.mean(values),
            "std_value": np.std(values),
            "mean_confidence": np.mean(confidences),
            "value_range": (min(values), max(values)),
            "method_used": self.method.value
        }

    def switch_method(self, new_method: EnsembleMethod) -> None:
        """Switch to a different ensemble method."""
        if new_method in self.strategies:
            self.method = new_method
            self.current_strategy = self.strategies[new_method]
            logger.info(f"Switched to ensemble method: {new_method.value}")


# Global ensemble manager
_ensemble_manager: Dict[SignalType, IndicatorEnsemble] = {}


def get_ensemble_manager(signal_type: SignalType,
                        method: EnsembleMethod = EnsembleMethod.ADAPTIVE) -> IndicatorEnsemble:
    """Get or create an ensemble manager for a signal type."""
    if signal_type not in _ensemble_manager:
        _ensemble_manager[signal_type] = IndicatorEnsemble(signal_type, method)

    return _ensemble_manager[signal_type]


# Convenience functions
def create_ensemble_signal(signals: List[IndicatorSignal],
                          signal_type: SignalType,
                          market_data: Optional[pd.DataFrame] = None,
                          method: EnsembleMethod = EnsembleMethod.ADAPTIVE) -> EnsembleResult:
    """Create an ensemble signal from multiple indicator signals."""
    manager = get_ensemble_manager(signal_type, method)
    return manager.add_signals(signals, market_data)


def update_ensemble_performance(signal_type: SignalType, actual_performance: float) -> None:
    """Update ensemble performance for learning."""
    if signal_type in _ensemble_manager:
        _ensemble_manager[signal_type].update_performance(actual_performance)


# Example usage
def create_sample_signals() -> List[IndicatorSignal]:
    """Create sample signals for testing."""
    return [
        IndicatorSignal("rsi", SignalType.MOMENTUM, -0.8, 0.7, metadata={"volatility": 0.2}),
        IndicatorSignal("macd", SignalType.MOMENTUM, 0.3, 0.8, metadata={"trend_strength": 0.6}),
        IndicatorSignal("bollinger_bands", SignalType.VOLATILITY, 0.1, 0.6, metadata={"volatility": 0.15}),
        IndicatorSignal("volume_profile", SignalType.VOLUME, 0.5, 0.9, metadata={"volume": 1000000})
    ]


if __name__ == "__main__":
    # Example usage
    signals = create_sample_signals()

    # Create ensemble signal
    result = create_ensemble_signal(signals, SignalType.MOMENTUM)
    print(f"Ensemble result: value={result.ensemble_value:.3f}, confidence={result.confidence:.3f}")
    print(f"Method used: {result.method_used.value}")

    # Update performance
    update_ensemble_performance(SignalType.MOMENTUM, 0.8)

    # Get statistics
    manager = get_ensemble_manager(SignalType.MOMENTUM)
    stats = manager.get_ensemble_statistics()
    print(f"Ensemble statistics: {stats}")