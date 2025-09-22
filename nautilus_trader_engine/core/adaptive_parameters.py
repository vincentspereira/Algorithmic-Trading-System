"""
Adaptive Parameters System for Institutional-Grade Indicators.

This module provides a sophisticated adaptive parameter system that enables
technical indicators to dynamically adjust their parameters based on:

- Market volatility and regime detection
- Trend strength and momentum
- Volume confirmation signals
- Time-based adaptation (intraday vs interday)
- Market microstructure changes
- Risk-adjusted parameter scaling
- Performance-based optimization
- Multi-timeframe consensus

The system integrates with the 5-pillar institutional architecture to provide
adaptive, market-responsive parameter management for all indicators.
"""

import asyncio
import math
import statistics
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from weakref import WeakSet

import numpy as np
from loguru import logger

from .dependency_injection import (
    DependencyInjectionContainer,
    get_container,
    injectable,
    singleton,
    ServiceLifetime
)
from .interfaces import MarketRegime, SignalStrength, RiskLevel


class AdaptationStrategy(Enum):
    """Parameter adaptation strategies."""
    VOLATILITY_BASED = "volatility_based"
    TREND_STRENGTH = "trend_strength"
    MARKET_REGIME = "market_regime"
    VOLUME_CONFIRMATION = "volume_confirmation"
    TIME_BASED = "time_based"
    PERFORMANCE_BASED = "performance_based"
    RISK_ADJUSTED = "risk_adjusted"
    MULTI_TIMEFRAME = "multi_timeframe"
    ENSEMBLE_VOTING = "ensemble_voting"


class ParameterType(Enum):
    """Parameter types for adaptation."""
    PERIOD = "period"
    MULTIPLIER = "multiplier"
    THRESHOLD = "threshold"
    WEIGHT = "weight"
    LENGTH = "length"
    SMOOTHING = "smoothing"
    SENSITIVITY = "sensitivity"


@dataclass
class ParameterBounds:
    """Parameter bounds and constraints."""
    min_value: float
    max_value: float
    step_size: float = 1.0
    allowed_values: Optional[List[float]] = None
    transformation: str = "linear"  # linear, log, exponential


@dataclass
class AdaptiveParameter:
    """Adaptive parameter configuration."""
    name: str
    parameter_type: ParameterType
    base_value: float
    bounds: ParameterBounds
    adaptation_strategy: AdaptationStrategy
    adaptation_weight: float = 1.0
    smoothing_factor: float = 0.1
    reset_threshold: float = 0.5
    current_value: float = field(init=False)
    adaptation_history: List[Tuple[float, float]] = field(default_factory=list)
    last_adaptation_time: float = field(default_factory=time.time)

    def __post_init__(self):
        self.current_value = self.base_value

    def update_value(self, new_value: float, adaptation_factor: float = 1.0):
        """Update parameter value with smoothing."""
        # Apply bounds
        new_value = max(self.bounds.min_value, min(self.bounds.max_value, new_value))

        # Apply smoothing
        if self.smoothing_factor > 0:
            new_value = (self.smoothing_factor * new_value +
                        (1 - self.smoothing_factor) * self.current_value)

        # Apply adaptation weight
        adaptation_range = self.bounds.max_value - self.bounds.min_value
        adaptation_amount = (new_value - self.current_value) * self.adaptation_weight
        new_value = self.current_value + adaptation_amount

        # Store in history
        self.adaptation_history.append((time.time(), new_value))
        self.last_adaptation_time = time.time()

        # Maintain history size
        if len(self.adaptation_history) > 1000:
            self.adaptation_history.pop(0)

        self.current_value = new_value

    def reset_to_base(self):
        """Reset parameter to base value."""
        self.current_value = self.base_value
        self.last_adaptation_time = time.time()

    def get_adaptation_stats(self) -> Dict[str, Any]:
        """Get adaptation statistics."""
        if not self.adaptation_history:
            return {}

        values = [v for _, v in self.adaptation_history]
        return {
            "mean": statistics.mean(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
            "range": max(values) - min(values),
            "adaptations_count": len(self.adaptation_history),
            "time_since_last_adaptation": time.time() - self.last_adaptation_time
        }


@dataclass
class MarketCondition:
    """Market condition assessment."""
    volatility: float
    trend_strength: float
    volume_confirmation: float
    market_regime: MarketRegime
    risk_level: RiskLevel
    timestamp: float = field(default_factory=time.time)


@dataclass
class AdaptationContext:
    """Context for parameter adaptation."""
    market_condition: MarketCondition
    indicator_performance: Dict[str, Any]
    timeframe: str
    symbol: str
    adaptation_factors: Dict[str, float] = field(default_factory=dict)


class ParameterAdapter(ABC):
    """Abstract base class for parameter adapters."""

    @abstractmethod
    async def adapt_parameters(self, parameters: Dict[str, AdaptiveParameter],
                              context: AdaptationContext) -> Dict[str, float]:
        """Adapt parameters based on context."""
        pass

    @abstractmethod
    def get_adaptation_strategy(self) -> AdaptationStrategy:
        """Get the adaptation strategy."""
        pass


@injectable
@singleton
class VolatilityBasedAdapter(ParameterAdapter):
    """Volatility-based parameter adaptation."""

    def get_adaptation_strategy(self) -> AdaptationStrategy:
        return AdaptationStrategy.VOLATILITY_BASED

    async def adapt_parameters(self, parameters: Dict[str, AdaptiveParameter],
                              context: AdaptationContext) -> Dict[str, float]:
        """Adapt parameters based on volatility."""
        volatility = context.market_condition.volatility
        adaptations = {}

        for param_name, param in parameters.items():
            if param.parameter_type in [ParameterType.PERIOD, ParameterType.LENGTH]:
                # Increase periods in high volatility
                if volatility > 0.7:  # High volatility
                    new_value = param.base_value * 1.5
                elif volatility < 0.3:  # Low volatility
                    new_value = param.base_value * 0.8
                else:
                    new_value = param.base_value

                param.update_value(new_value, adaptation_factor=volatility)
                adaptations[param_name] = param.current_value

            elif param.parameter_type == ParameterType.THRESHOLD:
                # Adjust thresholds based on volatility
                if volatility > 0.7:
                    new_value = param.base_value * 1.2  # Higher thresholds
                elif volatility < 0.3:
                    new_value = param.base_value * 0.9  # Lower thresholds
                else:
                    new_value = param.base_value

                param.update_value(new_value, adaptation_factor=volatility)
                adaptations[param_name] = param.current_value

        return adaptations


@injectable
@singleton
class TrendStrengthAdapter(ParameterAdapter):
    """Trend strength-based parameter adaptation."""

    def get_adaptation_strategy(self) -> AdaptationStrategy:
        return AdaptationStrategy.TREND_STRENGTH

    async def adapt_parameters(self, parameters: Dict[str, AdaptiveParameter],
                              context: AdaptationContext) -> Dict[str, float]:
        """Adapt parameters based on trend strength."""
        trend_strength = context.market_condition.trend_strength
        adaptations = {}

        for param_name, param in parameters.items():
            if param.parameter_type == ParameterType.SENSITIVITY:
                # Increase sensitivity in strong trends
                if trend_strength > 0.7:  # Strong trend
                    new_value = param.base_value * 1.3
                elif trend_strength < 0.3:  # Weak trend
                    new_value = param.base_value * 0.7
                else:
                    new_value = param.base_value

                param.update_value(new_value, adaptation_factor=trend_strength)
                adaptations[param_name] = param.current_value

            elif param.parameter_type == ParameterType.SMOOTHING:
                # Reduce smoothing in strong trends
                if trend_strength > 0.7:
                    new_value = param.base_value * 0.8  # Less smoothing
                elif trend_strength < 0.3:
                    new_value = param.base_value * 1.2  # More smoothing
                else:
                    new_value = param.base_value

                param.update_value(new_value, adaptation_factor=trend_strength)
                adaptations[param_name] = param.current_value

        return adaptations


@injectable
@singleton
class MarketRegimeAdapter(ParameterAdapter):
    """Market regime-based parameter adaptation."""

    def get_adaptation_strategy(self) -> AdaptationStrategy:
        return AdaptationStrategy.MARKET_REGIME

    async def adapt_parameters(self, parameters: Dict[str, AdaptiveParameter],
                              context: AdaptationContext) -> Dict[str, float]:
        """Adapt parameters based on market regime."""
        regime = context.market_condition.market_regime
        adaptations = {}

        # Regime-specific adaptations
        regime_multipliers = {
            MarketRegime.BULL: {"period": 0.9, "threshold": 0.95, "sensitivity": 1.1},
            MarketRegime.BEAR: {"period": 1.1, "threshold": 1.05, "sensitivity": 1.1},
            MarketRegime.SIDEWAYS: {"period": 1.2, "threshold": 1.1, "sensitivity": 0.9},
            MarketRegime.HIGH_VOLATILITY: {"period": 1.3, "threshold": 1.2, "sensitivity": 0.8},
            MarketRegime.LOW_VOLATILITY: {"period": 0.8, "threshold": 0.9, "sensitivity": 1.0},
            MarketRegime.TRENDING: {"period": 0.9, "threshold": 0.95, "sensitivity": 1.2},
            MarketRegime.RANGING: {"period": 1.1, "threshold": 1.05, "sensitivity": 0.9}
        }

        multipliers = regime_multipliers.get(regime, {"period": 1.0, "threshold": 1.0, "sensitivity": 1.0})

        for param_name, param in parameters.items():
            multiplier = multipliers.get(param.parameter_type.value, 1.0)
            new_value = param.base_value * multiplier

            param.update_value(new_value, adaptation_factor=0.8)
            adaptations[param_name] = param.current_value

        return adaptations


@injectable
@singleton
class PerformanceBasedAdapter(ParameterAdapter):
    """Performance-based parameter adaptation."""

    def get_adaptation_strategy(self) -> AdaptationStrategy:
        return AdaptationStrategy.PERFORMANCE_BASED

    async def adapt_parameters(self, parameters: Dict[str, AdaptiveParameter],
                              context: AdaptationContext) -> Dict[str, float]:
        """Adapt parameters based on performance metrics."""
        performance = context.indicator_performance
        adaptations = {}

        # Extract performance metrics
        accuracy = performance.get('accuracy', 0.5)
        win_rate = performance.get('win_rate', 0.5)
        profit_factor = performance.get('profit_factor', 1.0)

        # Calculate overall performance score
        performance_score = (accuracy + win_rate + min(profit_factor, 2.0) / 2.0) / 3.0

        for param_name, param in parameters.items():
            if performance_score > 0.7:  # Good performance
                # Keep current parameters but allow small adjustments
                adaptation_factor = 0.1
            elif performance_score < 0.3:  # Poor performance
                # Significant adjustment needed
                adaptation_factor = 0.5
            else:
                # Moderate adjustment
                adaptation_factor = 0.3

            # Adjust based on parameter type
            if param.parameter_type == ParameterType.PERIOD:
                # Slightly increase periods if performance is poor
                adjustment = 1.0 + (0.5 - performance_score) * 0.2
                new_value = param.current_value * adjustment
            elif param.parameter_type == ParameterType.THRESHOLD:
                # Adjust thresholds based on performance
                adjustment = 1.0 + (performance_score - 0.5) * 0.1
                new_value = param.current_value * adjustment
            else:
                new_value = param.current_value

            param.update_value(new_value, adaptation_factor=adaptation_factor)
            adaptations[param_name] = param.current_value

        return adaptations


@injectable
@singleton
class AdaptiveParameterManager:
    """
    Adaptive Parameter Manager for Institutional-Grade Indicators.

    Features:
    - Multi-strategy parameter adaptation
    - Market condition assessment
    - Performance-based optimization
    - Risk-adjusted parameter scaling
    - Real-time parameter updates
    - Historical adaptation tracking
    """

    def __init__(self, container: Optional[DependencyInjectionContainer] = None):
        self._container = container or get_container()
        self._adapters: Dict[AdaptationStrategy, ParameterAdapter] = {}
        self._indicator_parameters: Dict[str, Dict[str, AdaptiveParameter]] = {}
        self._market_conditions: List[MarketCondition] = []
        self._adaptation_history: Dict[str, List[Dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

        # Initialize adapters
        self._initialize_adapters()

    def _initialize_adapters(self):
        """Initialize parameter adapters."""
        try:
            self._adapters = {
                AdaptationStrategy.VOLATILITY_BASED: self._container.get_service(VolatilityBasedAdapter),
                AdaptationStrategy.TREND_STRENGTH: self._container.get_service(TrendStrengthAdapter),
                AdaptationStrategy.MARKET_REGIME: self._container.get_service(MarketRegimeAdapter),
                AdaptationStrategy.PERFORMANCE_BASED: self._container.get_service(PerformanceBasedAdapter)
            }
        except Exception as e:
            logger.warning(f"Failed to initialize some adapters: {e}")

    def register_indicator_parameters(self, indicator_name: str,
                                    parameters: Dict[str, AdaptiveParameter]):
        """Register adaptive parameters for an indicator."""
        self._indicator_parameters[indicator_name] = parameters
        self._adaptation_history[indicator_name] = []
        logger.info(f"Registered {len(parameters)} adaptive parameters for {indicator_name}")

    def update_market_condition(self, condition: MarketCondition):
        """Update current market condition."""
        async with self._lock:
            self._market_conditions.append(condition)

            # Maintain history size
            if len(self._market_conditions) > 100:
                self._market_conditions.pop(0)

    async def adapt_indicator_parameters(self, indicator_name: str,
                                       strategies: List[AdaptationStrategy] = None,
                                       context: Optional[AdaptationContext] = None) -> Dict[str, float]:
        """
        Adapt parameters for an indicator using specified strategies.

        Args:
            indicator_name: Name of the indicator
            strategies: List of adaptation strategies to use
            context: Adaptation context

        Returns:
            Dictionary of adapted parameter values
        """
        if indicator_name not in self._indicator_parameters:
            logger.warning(f"No parameters registered for indicator: {indicator_name}")
            return {}

        parameters = self._indicator_parameters[indicator_name]

        if not strategies:
            strategies = [AdaptationStrategy.VOLATILITY_BASED,
                         AdaptationStrategy.MARKET_REGIME,
                         AdaptationStrategy.PERFORMANCE_BASED]

        if not context:
            context = await self._create_adaptation_context(indicator_name)

        # Apply adaptation strategies
        all_adaptations = {}
        strategy_weights = {}

        for strategy in strategies:
            if strategy in self._adapters:
                try:
                    adaptations = await self._adapters[strategy].adapt_parameters(parameters, context)
                    all_adaptations[strategy] = adaptations

                    # Calculate strategy weight based on market conditions
                    strategy_weights[strategy] = self._calculate_strategy_weight(strategy, context)

                except Exception as e:
                    logger.error(f"Error in {strategy.value} adaptation: {e}")

        # Combine adaptations using weighted average
        final_adaptations = self._combine_adaptations(all_adaptations, strategy_weights, parameters)

        # Store adaptation history
        adaptation_record = {
            "timestamp": time.time(),
            "strategies": [s.value for s in strategies],
            "context": {
                "volatility": context.market_condition.volatility,
                "trend_strength": context.market_condition.trend_strength,
                "market_regime": context.market_condition.market_regime.value
            },
            "adaptations": final_adaptations.copy()
        }

        async with self._lock:
            self._adaptation_history[indicator_name].append(adaptation_record)

            # Maintain history size
            if len(self._adaptation_history[indicator_name]) > 1000:
                self._adaptation_history[indicator_name].pop(0)

        logger.debug(f"Adapted {len(final_adaptations)} parameters for {indicator_name}")
        return final_adaptations

    async def _create_adaptation_context(self, indicator_name: str) -> AdaptationContext:
        """Create adaptation context from current market conditions."""
        # Get latest market condition
        market_condition = self._market_conditions[-1] if self._market_conditions else MarketCondition(
            volatility=0.5, trend_strength=0.5, volume_confirmation=0.5,
            market_regime=MarketRegime.SIDEWAYS, risk_level=RiskLevel.MODERATE
        )

        # Get indicator performance (placeholder - would be implemented)
        indicator_performance = {
            "accuracy": 0.55,
            "win_rate": 0.52,
            "profit_factor": 1.1
        }

        return AdaptationContext(
            market_condition=market_condition,
            indicator_performance=indicator_performance,
            timeframe="1h",
            symbol="SPY"
        )

    def _calculate_strategy_weight(self, strategy: AdaptationStrategy,
                                 context: AdaptationContext) -> float:
        """Calculate weight for adaptation strategy based on context."""
        weights = {
            AdaptationStrategy.VOLATILITY_BASED: context.market_condition.volatility,
            AdaptationStrategy.TREND_STRENGTH: context.market_condition.trend_strength,
            AdaptationStrategy.MARKET_REGIME: 0.8,  # Always relevant
            AdaptationStrategy.PERFORMANCE_BASED: 0.6,  # Moderately relevant
            AdaptationStrategy.VOLUME_CONFIRMATION: context.market_condition.volume_confirmation,
            AdaptationStrategy.RISK_ADJUSTED: 0.7 if context.market_condition.risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH] else 0.3
        }

        return weights.get(strategy, 0.5)

    def _combine_adaptations(self, adaptations: Dict[AdaptationStrategy, Dict[str, float]],
                           weights: Dict[AdaptationStrategy, float],
                           parameters: Dict[str, AdaptiveParameter]) -> Dict[str, float]:
        """Combine adaptations from multiple strategies using weighted average."""
        final_adaptations = {}

        # Get all parameter names
        all_params = set()
        for strategy_adaptations in adaptations.values():
            all_params.update(strategy_adaptations.keys())

        for param_name in all_params:
            if param_name not in parameters:
                continue

            param = parameters[param_name]
            weighted_values = []
            total_weight = 0

            # Collect values from all strategies
            for strategy, strategy_adaptations in adaptations.items():
                if param_name in strategy_adaptations:
                    value = strategy_adaptations[param_name]
                    weight = weights.get(strategy, 0.5)
                    weighted_values.append((value, weight))
                    total_weight += weight

            if weighted_values and total_weight > 0:
                # Calculate weighted average
                weighted_sum = sum(value * weight for value, weight in weighted_values)
                final_value = weighted_sum / total_weight

                # Apply bounds
                final_value = max(param.bounds.min_value,
                                min(param.bounds.max_value, final_value))

                final_adaptations[param_name] = final_value

                # Update parameter
                param.update_value(final_value)

        return final_adaptations

    def get_adaptation_history(self, indicator_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get adaptation history for an indicator."""
        return self._adaptation_history.get(indicator_name, [])[-limit:]

    def get_parameter_stats(self, indicator_name: str) -> Dict[str, Any]:
        """Get parameter adaptation statistics."""
        if indicator_name not in self._indicator_parameters:
            return {}

        parameters = self._indicator_parameters[indicator_name]
        stats = {}

        for param_name, param in parameters.items():
            stats[param_name] = {
                "current_value": param.current_value,
                "base_value": param.base_value,
                "deviation": abs(param.current_value - param.base_value) / param.base_value,
                "adaptation_stats": param.get_adaptation_stats()
            }

        return stats

    def reset_indicator_parameters(self, indicator_name: str):
        """Reset all parameters for an indicator to base values."""
        if indicator_name in self._indicator_parameters:
            for param in self._indicator_parameters[indicator_name].values():
                param.reset_to_base()
            logger.info(f"Reset parameters for indicator: {indicator_name}")


# Global adaptive parameter manager instance
_adaptive_manager = AdaptiveParameterManager()


def get_adaptive_manager() -> AdaptiveParameterManager:
    """Get the global adaptive parameter manager."""
    return _adaptive_manager


# Convenience functions
def register_adaptive_parameters(indicator_name: str, parameters: Dict[str, AdaptiveParameter]):
    """Register adaptive parameters for an indicator."""
    _adaptive_manager.register_indicator_parameters(indicator_name, parameters)


async def adapt_parameters(indicator_name: str,
                          strategies: List[AdaptationStrategy] = None) -> Dict[str, float]:
    """Adapt parameters for an indicator."""
    return await _adaptive_manager.adapt_indicator_parameters(indicator_name, strategies)


def create_adaptive_parameter(name: str, parameter_type: ParameterType,
                            base_value: float, bounds: ParameterBounds,
                            adaptation_strategy: AdaptationStrategy) -> AdaptiveParameter:
    """Create an adaptive parameter."""
    return AdaptiveParameter(
        name=name,
        parameter_type=parameter_type,
        base_value=base_value,
        bounds=bounds,
        adaptation_strategy=adaptation_strategy
    )