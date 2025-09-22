"""
Adaptive Parameters System for Technical Indicators
Provides dynamic parameter adjustment based on market conditions and performance.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod
import time
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class AdaptationStrategy(Enum):
    """Strategies for parameter adaptation."""
    FIXED = "fixed"
    VOLATILITY_BASED = "volatility_based"
    TREND_STRENGTH = "trend_strength"
    MARKET_REGIME = "market_regime"
    PERFORMANCE_BASED = "performance_based"
    MACHINE_LEARNING = "machine_learning"
    GENETIC_ALGORITHM = "genetic_algorithm"


class MarketRegime(Enum):
    """Market regime classifications."""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


@dataclass
class ParameterBounds:
    """Bounds for parameter values."""
    min_value: float
    max_value: float
    step_size: float = 1.0
    allowed_values: Optional[List[float]] = None


@dataclass
class AdaptiveParameter:
    """Definition of an adaptive parameter."""
    name: str
    default_value: float
    bounds: ParameterBounds
    adaptation_strategy: AdaptationStrategy
    current_value: float = field(init=False)
    adaptation_history: List[Tuple[float, float]] = field(default_factory=list)  # (timestamp, value)
    performance_score: float = 0.0

    def __post_init__(self):
        self.current_value = self.default_value


@dataclass
class MarketCondition:
    """Current market conditions for adaptation."""
    volatility: float
    trend_strength: float
    volume: float
    regime: MarketRegime
    timestamp: float = field(default_factory=time.time)


class ParameterAdapter(ABC):
    """Base class for parameter adaptation strategies."""

    @abstractmethod
    def adapt_parameters(self, parameters: Dict[str, AdaptiveParameter],
                        market_condition: MarketCondition,
                        performance_metrics: Dict[str, float]) -> Dict[str, float]:
        """Adapt parameters based on market conditions and performance."""
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of this adaptation strategy."""
        pass


class VolatilityBasedAdapter(ParameterAdapter):
    """Adapts parameters based on market volatility."""

    def adapt_parameters(self, parameters: Dict[str, AdaptiveParameter],
                        market_condition: MarketCondition,
                        performance_metrics: Dict[str, float]) -> Dict[str, float]:
        """Adapt parameters based on volatility."""
        adapted_values = {}

        # Volatility scaling factor (higher volatility = more conservative parameters)
        volatility_factor = min(2.0, max(0.5, market_condition.volatility / 0.2))

        for name, param in parameters.items():
            if param.adaptation_strategy == AdaptationStrategy.VOLATILITY_BASED:
                if "period" in name.lower():
                    # Increase periods in high volatility
                    new_value = param.default_value * volatility_factor
                elif "multiplier" in name.lower():
                    # Decrease multipliers in high volatility
                    new_value = param.default_value / volatility_factor
                else:
                    new_value = param.default_value

                # Ensure bounds
                new_value = max(param.bounds.min_value,
                              min(param.bounds.max_value, new_value))
                adapted_values[name] = new_value
                param.current_value = new_value
            else:
                adapted_values[name] = param.current_value

        return adapted_values

    def get_strategy_name(self) -> str:
        return "volatility_based"


class TrendStrengthAdapter(ParameterAdapter):
    """Adapts parameters based on trend strength."""

    def adapt_parameters(self, parameters: Dict[str, AdaptiveParameter],
                        market_condition: MarketCondition,
                        performance_metrics: Dict[str, float]) -> Dict[str, float]:
        """Adapt parameters based on trend strength."""
        adapted_values = {}

        # Trend strength factor (stronger trend = more aggressive parameters)
        trend_factor = min(2.0, max(0.5, market_condition.trend_strength))

        for name, param in parameters.items():
            if param.adaptation_strategy == AdaptationStrategy.TREND_STRENGTH:
                if "period" in name.lower():
                    # Decrease periods in strong trends for faster response
                    new_value = param.default_value / trend_factor
                elif "threshold" in name.lower():
                    # Adjust thresholds based on trend strength
                    new_value = param.default_value * trend_factor
                else:
                    new_value = param.default_value

                new_value = max(param.bounds.min_value,
                              min(param.bounds.max_value, new_value))
                adapted_values[name] = new_value
                param.current_value = new_value
            else:
                adapted_values[name] = param.current_value

        return adapted_values

    def get_strategy_name(self) -> str:
        return "trend_strength"


class PerformanceBasedAdapter(ParameterAdapter):
    """Adapts parameters based on historical performance."""

    def __init__(self, learning_rate: float = 0.1):
        self.learning_rate = learning_rate
        self.performance_history: List[Dict[str, float]] = []

    def adapt_parameters(self, parameters: Dict[str, AdaptiveParameter],
                        market_condition: MarketCondition,
                        performance_metrics: Dict[str, float]) -> Dict[str, float]:
        """Adapt parameters based on performance metrics."""
        adapted_values = {}

        # Store performance history
        self.performance_history.append(performance_metrics)
        if len(self.performance_history) > 100:  # Keep last 100 entries
            self.performance_history.pop(0)

        # Calculate performance trends
        if len(self.performance_history) >= 10:
            recent_performance = np.mean([p.get('sharpe_ratio', 0) for p in self.performance_history[-10:]])
            overall_performance = np.mean([p.get('sharpe_ratio', 0) for p in self.performance_history])

            performance_factor = recent_performance / max(overall_performance, 0.01)
            performance_factor = min(2.0, max(0.5, performance_factor))
        else:
            performance_factor = 1.0

        for name, param in parameters.items():
            if param.adaptation_strategy == AdaptationStrategy.PERFORMANCE_BASED:
                # Adjust based on performance
                if performance_factor > 1.1:  # Good performance, keep similar parameters
                    new_value = param.current_value
                elif performance_factor < 0.9:  # Poor performance, try different parameters
                    # Add some random exploration
                    change = np.random.normal(0, param.default_value * 0.1)
                    new_value = param.current_value + change
                else:
                    new_value = param.current_value

                new_value = max(param.bounds.min_value,
                              min(param.bounds.max_value, new_value))
                adapted_values[name] = new_value
                param.current_value = new_value
            else:
                adapted_values[name] = param.current_value

        return adapted_values

    def get_strategy_name(self) -> str:
        return "performance_based"


class MachineLearningAdapter(ParameterAdapter):
    """Uses machine learning to adapt parameters."""

    def __init__(self):
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        self.trained = False
        self.feature_history: List[List[float]] = []
        self.target_history: List[float] = []

    def adapt_parameters(self, parameters: Dict[str, AdaptiveParameter],
                        market_condition: MarketCondition,
                        performance_metrics: Dict[str, float]) -> Dict[str, float]:
        """Adapt parameters using machine learning."""
        adapted_values = {}

        # Extract features from market condition
        features = [
            market_condition.volatility,
            market_condition.trend_strength,
            market_condition.volume,
            1 if market_condition.regime == MarketRegime.TRENDING_UP else 0,
            1 if market_condition.regime == MarketRegime.HIGH_VOLATILITY else 0
        ]

        # Use performance as target
        target = performance_metrics.get('sharpe_ratio', 0)

        # Store data for training
        self.feature_history.append(features)
        self.target_history.append(target)

        # Train model if we have enough data
        if len(self.feature_history) >= 50 and not self.trained:
            X = np.array(self.feature_history)
            y = np.array(self.target_history)

            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled, y)
            self.trained = True

        for name, param in parameters.items():
            if param.adaptation_strategy == AdaptationStrategy.MACHINE_LEARNING:
                if self.trained:
                    # Predict optimal parameter value
                    features_scaled = self.scaler.transform([features])
                    predicted_performance = self.model.predict(features_scaled)[0]

                    # Adjust parameter based on prediction
                    if predicted_performance > 0.5:
                        new_value = param.default_value * 1.2  # More aggressive
                    elif predicted_performance < -0.5:
                        new_value = param.default_value * 0.8  # More conservative
                    else:
                        new_value = param.default_value
                else:
                    new_value = param.default_value

                new_value = max(param.bounds.min_value,
                              min(param.bounds.max_value, new_value))
                adapted_values[name] = new_value
                param.current_value = new_value
            else:
                adapted_values[name] = param.current_value

        return adapted_values

    def get_strategy_name(self) -> str:
        return "machine_learning"


class AdaptiveParameterManager:
    """
    Manages adaptive parameters for indicators with multiple adaptation strategies.
    """

    def __init__(self):
        self.adapters: Dict[str, ParameterAdapter] = {
            "volatility_based": VolatilityBasedAdapter(),
            "trend_strength": TrendStrengthAdapter(),
            "performance_based": PerformanceBasedAdapter(),
            "machine_learning": MachineLearningAdapter()
        }
        self.indicator_parameters: Dict[str, Dict[str, AdaptiveParameter]] = {}
        self.market_history: List[MarketCondition] = []

    def register_indicator_parameters(self, indicator_name: str,
                                    parameters: Dict[str, AdaptiveParameter]) -> None:
        """Register parameters for an indicator."""
        self.indicator_parameters[indicator_name] = parameters
        logger.info(f"Registered {len(parameters)} adaptive parameters for {indicator_name}")

    def adapt_indicator_parameters(self, indicator_name: str,
                                 market_condition: MarketCondition,
                                 performance_metrics: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Adapt parameters for a specific indicator."""
        if indicator_name not in self.indicator_parameters:
            logger.warning(f"No parameters registered for indicator: {indicator_name}")
            return {}

        parameters = self.indicator_parameters[indicator_name]
        performance_metrics = performance_metrics or {}

        # Store market condition
        self.market_history.append(market_condition)
        if len(self.market_history) > 1000:  # Keep last 1000 entries
            self.market_history.pop(0)

        adapted_values = {}

        # Apply each adaptation strategy
        for adapter_name, adapter in self.adapters.items():
            try:
                adapter_values = adapter.adapt_parameters(
                    parameters, market_condition, performance_metrics
                )

                # Merge with existing values
                for param_name, value in adapter_values.items():
                    if param_name not in adapted_values:
                        adapted_values[param_name] = value

            except Exception as e:
                logger.error(f"Error in adapter {adapter_name}: {e}")

        # Update parameter history
        timestamp = time.time()
        for param_name, value in adapted_values.items():
            if param_name in parameters:
                parameters[param_name].adaptation_history.append((timestamp, value))

        return adapted_values

    def get_optimal_parameters(self, indicator_name: str,
                             market_condition: MarketCondition) -> Dict[str, float]:
        """Get optimal parameters for current market conditions."""
        return self.adapt_indicator_parameters(indicator_name, market_condition)

    def analyze_parameter_performance(self, indicator_name: str) -> Dict[str, Any]:
        """Analyze the performance of parameter adaptations."""
        if indicator_name not in self.indicator_parameters:
            return {}

        parameters = self.indicator_parameters[indicator_name]
        analysis = {}

        for param_name, param in parameters.items():
            if param.adaptation_history:
                values = [v for _, v in param.adaptation_history]
                analysis[param_name] = {
                    "current_value": param.current_value,
                    "default_value": param.default_value,
                    "min_value": min(values),
                    "max_value": max(values),
                    "mean_value": np.mean(values),
                    "std_value": np.std(values),
                    "adaptations_count": len(param.adaptation_history)
                }

        return analysis

    def reset_parameters(self, indicator_name: str) -> None:
        """Reset parameters to default values."""
        if indicator_name in self.indicator_parameters:
            for param in self.indicator_parameters[indicator_name].values():
                param.current_value = param.default_value
                param.adaptation_history.clear()
            logger.info(f"Reset parameters for indicator: {indicator_name}")


# Global parameter manager instance
_parameter_manager = AdaptiveParameterManager()


def get_parameter_manager() -> AdaptiveParameterManager:
    """Get the global parameter manager."""
    return _parameter_manager


# Convenience functions
def register_indicator_parameters(indicator_name: str,
                                parameters: Dict[str, AdaptiveParameter]) -> None:
    """Register parameters for an indicator globally."""
    _parameter_manager.register_indicator_parameters(indicator_name, parameters)


def adapt_indicator_parameters(indicator_name: str,
                             market_condition: MarketCondition,
                             performance_metrics: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    """Adapt parameters for an indicator globally."""
    return _parameter_manager.adapt_indicator_parameters(
        indicator_name, market_condition, performance_metrics
    )


# Example usage with RSI indicator
def create_rsi_parameters() -> Dict[str, AdaptiveParameter]:
    """Create adaptive parameters for RSI indicator."""
    return {
        "period": AdaptiveParameter(
            name="period",
            default_value=14,
            bounds=ParameterBounds(min_value=5, max_value=50, step_size=1),
            adaptation_strategy=AdaptationStrategy.VOLATILITY_BASED
        ),
        "overbought_threshold": AdaptiveParameter(
            name="overbought_threshold",
            default_value=70,
            bounds=ParameterBounds(min_value=60, max_value=90, step_size=1),
            adaptation_strategy=AdaptationStrategy.TREND_STRENGTH
        ),
        "oversold_threshold": AdaptiveParameter(
            name="oversold_threshold",
            default_value=30,
            bounds=ParameterBounds(min_value=10, max_value=40, step_size=1),
            adaptation_strategy=AdaptationStrategy.TREND_STRENGTH
        )
    }


if __name__ == "__main__":
    # Example usage
    manager = get_parameter_manager()

    # Register RSI parameters
    rsi_params = create_rsi_parameters()
    register_indicator_parameters("rsi", rsi_params)

    # Create market condition
    market_condition = MarketCondition(
        volatility=0.25,
        trend_strength=0.7,
        volume=1000000,
        regime=MarketRegime.TRENDING_UP
    )

    # Adapt parameters
    adapted = adapt_indicator_parameters("rsi", market_condition)
    print(f"Adapted RSI parameters: {adapted}")

    # Analyze performance
    analysis = manager.analyze_parameter_performance("rsi")
    print(f"Parameter analysis: {analysis}")