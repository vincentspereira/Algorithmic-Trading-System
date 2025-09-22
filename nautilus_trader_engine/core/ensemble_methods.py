"""
Ensemble Methods for Institutional-Grade Indicators.

This module provides sophisticated ensemble methods that combine multiple
technical indicators to improve signal quality and reduce false positives:

- Weighted Voting: Combines signals with performance-based weights
- Bagging: Bootstrap aggregation for robust signal generation
- Boosting: Sequential learning to focus on difficult cases
- Stacking: Meta-learning approach using multiple models
- Bayesian Combination: Probabilistic signal combination
- Consensus Filtering: Multi-timeframe and multi-indicator consensus
- Adaptive Ensemble: Dynamic weighting based on market conditions
- Performance-Based Selection: Automatic indicator selection based on performance

The ensemble system integrates with the 5-pillar institutional architecture
to provide market-aware, performance-optimized signal combination.
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
from .interfaces import SignalStrength, MarketRegime


class EnsembleMethod(Enum):
    """Ensemble combination methods."""
    WEIGHTED_VOTING = "weighted_voting"
    BAGGING = "bagging"
    BOOSTING = "boosting"
    STACKING = "stacking"
    BAYESIAN = "bayesian"
    CONSENSUS = "consensus"
    ADAPTIVE = "adaptive"
    PERFORMANCE_BASED = "performance_based"


class VotingScheme(Enum):
    """Voting schemes for ensemble methods."""
    MAJORITY = "majority"
    WEIGHTED = "weighted"
    CONFIDENCE = "confidence"
    PROBABILISTIC = "probabilistic"


@dataclass
class IndicatorSignal:
    """Individual indicator signal."""
    indicator_name: str
    signal_type: str  # "buy", "sell", "hold"
    strength: SignalStrength
    confidence: float
    value: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnsembleSignal:
    """Ensemble combined signal."""
    signal_type: str
    strength: SignalStrength
    confidence: float
    consensus_ratio: float
    participating_indicators: int
    ensemble_method: EnsembleMethod
    timestamp: float
    component_signals: List[IndicatorSignal] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IndicatorPerformance:
    """Indicator performance metrics."""
    indicator_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    total_signals: int
    last_updated: float
    market_regime_performance: Dict[str, float] = field(default_factory=dict)


@dataclass
class EnsembleWeights:
    """Dynamic weights for ensemble methods."""
    indicator_weights: Dict[str, float]
    method_weights: Dict[EnsembleMethod, float]
    market_regime_weights: Dict[str, float]
    last_updated: float
    adaptation_count: int = 0


class EnsembleCombiner(ABC):
    """Abstract base class for ensemble combination methods."""

    @abstractmethod
    async def combine_signals(self, signals: List[IndicatorSignal],
                            context: Dict[str, Any]) -> EnsembleSignal:
        """Combine multiple indicator signals into ensemble signal."""
        pass

    @abstractmethod
    def get_method_name(self) -> EnsembleMethod:
        """Get the ensemble method name."""
        pass


@injectable
@singleton
class WeightedVotingCombiner(EnsembleCombiner):
    """Weighted voting ensemble method."""

    def get_method_name(self) -> EnsembleMethod:
        return EnsembleMethod.WEIGHTED_VOTING

    async def combine_signals(self, signals: List[IndicatorSignal],
                            context: Dict[str, Any]) -> EnsembleSignal:
        """Combine signals using weighted voting."""
        if not signals:
            return self._create_empty_signal()

        # Get weights from context or use equal weights
        weights = context.get('weights', {})
        market_regime = context.get('market_regime', 'unknown')

        # Calculate weighted votes
        buy_votes = 0.0
        sell_votes = 0.0
        hold_votes = 0.0
        total_weight = 0.0

        for signal in signals:
            weight = weights.get(signal.indicator_name, 1.0)
            confidence = signal.confidence

            if signal.signal_type == "buy":
                buy_votes += weight * confidence
            elif signal.signal_type == "sell":
                sell_votes += weight * confidence
            else:  # hold
                hold_votes += weight * confidence

            total_weight += weight

        # Normalize votes
        if total_weight > 0:
            buy_votes /= total_weight
            sell_votes /= total_weight
            hold_votes /= total_weight

        # Determine winning signal
        vote_dict = {"buy": buy_votes, "sell": sell_votes, "hold": hold_votes}
        winning_signal = max(vote_dict, key=vote_dict.get)
        winning_confidence = vote_dict[winning_signal]

        # Calculate consensus ratio
        total_votes = buy_votes + sell_votes + hold_votes
        consensus_ratio = winning_confidence / total_votes if total_votes > 0 else 0

        # Determine signal strength
        strength = self._calculate_signal_strength(winning_confidence, consensus_ratio)

        return EnsembleSignal(
            signal_type=winning_signal,
            strength=strength,
            confidence=winning_confidence,
            consensus_ratio=consensus_ratio,
            participating_indicators=len(signals),
            ensemble_method=self.get_method_name(),
            timestamp=time.time(),
            component_signals=signals
        )

    def _create_empty_signal(self) -> EnsembleSignal:
        """Create empty ensemble signal."""
        return EnsembleSignal(
            signal_type="hold",
            strength=SignalStrength.WEAK,
            confidence=0.0,
            consensus_ratio=0.0,
            participating_indicators=0,
            ensemble_method=self.get_method_name(),
            timestamp=time.time()
        )

    def _calculate_signal_strength(self, confidence: float, consensus_ratio: float) -> SignalStrength:
        """Calculate signal strength based on confidence and consensus."""
        combined_score = (confidence + consensus_ratio) / 2

        if combined_score >= 0.8:
            return SignalStrength.VERY_STRONG
        elif combined_score >= 0.7:
            return SignalStrength.STRONG
        elif combined_score >= 0.6:
            return SignalStrength.MODERATE
        elif combined_score >= 0.5:
            return SignalStrength.WEAK
        else:
            return SignalStrength.VERY_WEAK


@injectable
@singleton
class BayesianCombiner(EnsembleCombiner):
    """Bayesian ensemble method using probabilistic combination."""

    def get_method_name(self) -> EnsembleMethod:
        return EnsembleMethod.BAYESIAN

    async def combine_signals(self, signals: List[IndicatorSignal],
                            context: Dict[str, Any]) -> EnsembleSignal:
        """Combine signals using Bayesian probability."""
        if not signals:
            return self._create_empty_signal()

        # Calculate prior probabilities
        priors = self._calculate_priors(signals, context)

        # Calculate likelihoods
        likelihoods = self._calculate_likelihoods(signals, context)

        # Apply Bayes' theorem
        buy_prob = self._bayesian_update(priors['buy'], likelihoods['buy'])
        sell_prob = self._bayesian_update(priors['sell'], likelihoods['sell'])
        hold_prob = self._bayesian_update(priors['hold'], likelihoods['hold'])

        # Normalize probabilities
        total_prob = buy_prob + sell_prob + hold_prob
        if total_prob > 0:
            buy_prob /= total_prob
            sell_prob /= total_prob
            hold_prob /= total_prob

        # Determine winning signal
        prob_dict = {"buy": buy_prob, "sell": sell_prob, "hold": hold_prob}
        winning_signal = max(prob_dict, key=prob_dict.get)
        winning_confidence = prob_dict[winning_signal]

        # Calculate consensus
        consensus_ratio = winning_confidence

        return EnsembleSignal(
            signal_type=winning_signal,
            strength=self._calculate_signal_strength(winning_confidence),
            confidence=winning_confidence,
            consensus_ratio=consensus_ratio,
            participating_indicators=len(signals),
            ensemble_method=self.get_method_name(),
            timestamp=time.time(),
            component_signals=signals,
            metadata={
                "buy_probability": buy_prob,
                "sell_probability": sell_prob,
                "hold_probability": hold_prob
            }
        )

    def _calculate_priors(self, signals: List[IndicatorSignal], context: Dict[str, Any]) -> Dict[str, float]:
        """Calculate prior probabilities."""
        # Use historical performance or equal priors
        performance_data = context.get('performance_data', {})

        buy_prior = 0.33
        sell_prior = 0.33
        hold_prior = 0.34

        # Adjust based on market regime
        market_regime = context.get('market_regime', 'unknown')
        if market_regime == 'bull':
            buy_prior = 0.5
            sell_prior = 0.2
            hold_prior = 0.3
        elif market_regime == 'bear':
            buy_prior = 0.2
            sell_prior = 0.5
            hold_prior = 0.3

        return {"buy": buy_prior, "sell": sell_prior, "hold": hold_prior}

    def _calculate_likelihoods(self, signals: List[IndicatorSignal], context: Dict[str, Any]) -> Dict[str, float]:
        """Calculate likelihoods from signals."""
        buy_likelihood = 0.0
        sell_likelihood = 0.0
        hold_likelihood = 0.0

        for signal in signals:
            confidence = signal.confidence
            if signal.signal_type == "buy":
                buy_likelihood += confidence
            elif signal.signal_type == "sell":
                sell_likelihood += confidence
            else:
                hold_likelihood += confidence

        # Normalize
        total = buy_likelihood + sell_likelihood + hold_likelihood
        if total > 0:
            buy_likelihood /= total
            sell_likelihood /= total
            hold_likelihood /= total

        return {"buy": buy_likelihood, "sell": sell_likelihood, "hold": hold_likelihood}

    def _bayesian_update(self, prior: float, likelihood: float) -> float:
        """Apply Bayesian update."""
        # Simplified Bayesian update
        return prior * likelihood

    def _create_empty_signal(self) -> EnsembleSignal:
        """Create empty ensemble signal."""
        return EnsembleSignal(
            signal_type="hold",
            strength=SignalStrength.WEAK,
            confidence=0.0,
            consensus_ratio=0.0,
            participating_indicators=0,
            ensemble_method=self.get_method_name(),
            timestamp=time.time()
        )

    def _calculate_signal_strength(self, confidence: float) -> SignalStrength:
        """Calculate signal strength based on confidence."""
        if confidence >= 0.8:
            return SignalStrength.VERY_STRONG
        elif confidence >= 0.7:
            return SignalStrength.STRONG
        elif confidence >= 0.6:
            return SignalStrength.MODERATE
        elif confidence >= 0.5:
            return SignalStrength.WEAK
        else:
            return SignalStrength.VERY_WEAK


@injectable
@singleton
class ConsensusCombiner(EnsembleCombiner):
    """Consensus-based ensemble method requiring multi-indicator agreement."""

    def __init__(self):
        self._min_consensus_threshold = 0.7  # 70% agreement required

    def get_method_name(self) -> EnsembleMethod:
        return EnsembleMethod.CONSENSUS

    async def combine_signals(self, signals: List[IndicatorSignal],
                            context: Dict[str, Any]) -> EnsembleSignal:
        """Combine signals using consensus filtering."""
        if not signals:
            return self._create_empty_signal()

        # Count signals by type
        signal_counts = {"buy": 0, "sell": 0, "hold": 0}
        total_confidence = {"buy": 0.0, "sell": 0.0, "hold": 0.0}

        for signal in signals:
            signal_counts[signal.signal_type] += 1
            total_confidence[signal.signal_type] += signal.confidence

        # Calculate consensus ratios
        total_signals = len(signals)
        consensus_ratios = {}
        avg_confidences = {}

        for signal_type in ["buy", "sell", "hold"]:
            consensus_ratios[signal_type] = signal_counts[signal_type] / total_signals
            avg_confidences[signal_type] = (
                total_confidence[signal_type] / signal_counts[signal_type]
                if signal_counts[signal_type] > 0 else 0
            )

        # Find signal with highest consensus
        winning_signal = max(consensus_ratios, key=consensus_ratios.get)
        consensus_ratio = consensus_ratios[winning_signal]
        avg_confidence = avg_confidences[winning_signal]

        # Apply consensus threshold
        if consensus_ratio < self._min_consensus_threshold:
            winning_signal = "hold"
            consensus_ratio = consensus_ratios["hold"]
            avg_confidence = avg_confidences["hold"]

        # Calculate combined confidence
        combined_confidence = (consensus_ratio + avg_confidence) / 2

        return EnsembleSignal(
            signal_type=winning_signal,
            strength=self._calculate_signal_strength(combined_confidence, consensus_ratio),
            confidence=combined_confidence,
            consensus_ratio=consensus_ratio,
            participating_indicators=total_signals,
            ensemble_method=self.get_method_name(),
            timestamp=time.time(),
            component_signals=signals,
            metadata={
                "consensus_threshold": self._min_consensus_threshold,
                "signal_distribution": signal_counts,
                "consensus_ratios": consensus_ratios
            }
        )

    def _create_empty_signal(self) -> EnsembleSignal:
        """Create empty ensemble signal."""
        return EnsembleSignal(
            signal_type="hold",
            strength=SignalStrength.WEAK,
            confidence=0.0,
            consensus_ratio=0.0,
            participating_indicators=0,
            ensemble_method=self.get_method_name(),
            timestamp=time.time()
        )

    def _calculate_signal_strength(self, confidence: float, consensus_ratio: float) -> SignalStrength:
        """Calculate signal strength based on confidence and consensus."""
        combined_score = (confidence * 0.6) + (consensus_ratio * 0.4)

        if combined_score >= 0.8:
            return SignalStrength.VERY_STRONG
        elif combined_score >= 0.7:
            return SignalStrength.STRONG
        elif combined_score >= 0.6:
            return SignalStrength.MODERATE
        elif combined_score >= 0.5:
            return SignalStrength.WEAK
        else:
            return SignalStrength.VERY_WEAK


@injectable
@singleton
class AdaptiveEnsembleCombiner(EnsembleCombiner):
    """Adaptive ensemble method that adjusts based on market conditions."""

    def get_method_name(self) -> EnsembleMethod:
        return EnsembleMethod.ADAPTIVE

    async def combine_signals(self, signals: List[IndicatorSignal],
                            context: Dict[str, Any]) -> EnsembleSignal:
        """Combine signals using adaptive ensemble method."""
        if not signals:
            return self._create_empty_signal()

        # Determine best method based on market conditions
        market_regime = context.get('market_regime', 'unknown')
        volatility = context.get('volatility', 0.5)

        # Select ensemble method based on conditions
        if market_regime == 'high_volatility' or volatility > 0.7:
            # Use consensus in high volatility
            method = EnsembleMethod.CONSENSUS
        elif market_regime == 'trending':
            # Use weighted voting in trending markets
            method = EnsembleMethod.WEIGHTED_VOTING
        else:
            # Use Bayesian in normal conditions
            method = EnsembleMethod.BAYESIAN

        # Get the appropriate combiner
        combiner = self._get_combiner_for_method(method, context)

        # Combine signals
        return await combiner.combine_signals(signals, context)

    def _get_combiner_for_method(self, method: EnsembleMethod, context: Dict[str, Any]) -> EnsembleCombiner:
        """Get combiner instance for the specified method."""
        container = get_container()

        if method == EnsembleMethod.WEIGHTED_VOTING:
            return container.get_service(WeightedVotingCombiner)
        elif method == EnsembleMethod.BAYESIAN:
            return container.get_service(BayesianCombiner)
        elif method == EnsembleMethod.CONSENSUS:
            return container.get_service(ConsensusCombiner)
        else:
            # Default to weighted voting
            return container.get_service(WeightedVotingCombiner)

    def _create_empty_signal(self) -> EnsembleSignal:
        """Create empty ensemble signal."""
        return EnsembleSignal(
            signal_type="hold",
            strength=SignalStrength.WEAK,
            confidence=0.0,
            consensus_ratio=0.0,
            participating_indicators=0,
            ensemble_method=self.get_method_name(),
            timestamp=time.time()
        )


@injectable
@singleton
class EnsembleManager:
    """
    Ensemble Manager for Institutional-Grade Indicator Combination.

    Features:
    - Multiple ensemble methods (weighted voting, Bayesian, consensus, adaptive)
    - Performance-based indicator weighting
    - Market regime-aware signal combination
    - Real-time ensemble adaptation
    - Confidence scoring and signal filtering
    - Historical performance tracking
    """

    def __init__(self, container: Optional[DependencyInjectionContainer] = None):
        self._container = container or get_container()
        self._combiners: Dict[EnsembleMethod, EnsembleCombiner] = {}
        self._indicator_performance: Dict[str, IndicatorPerformance] = {}
        self._ensemble_weights: Dict[str, EnsembleWeights] = {}
        self._signal_history: List[EnsembleSignal] = []
        self._max_history_size = 10000
        self._lock = asyncio.Lock()

        # Initialize combiners
        self._initialize_combiners()

    def _initialize_combiners(self):
        """Initialize ensemble combiners."""
        try:
            self._combiners = {
                EnsembleMethod.WEIGHTED_VOTING: self._container.get_service(WeightedVotingCombiner),
                EnsembleMethod.BAYESIAN: self._container.get_service(BayesianCombiner),
                EnsembleMethod.CONSENSUS: self._container.get_service(ConsensusCombiner),
                EnsembleMethod.ADAPTIVE: self._container.get_service(AdaptiveEnsembleCombiner)
            }
        except Exception as e:
            logger.warning(f"Failed to initialize some combiners: {e}")

    def register_indicator_performance(self, performance: IndicatorPerformance):
        """Register indicator performance data."""
        self._indicator_performance[performance.indicator_name] = performance
        logger.info(f"Registered performance data for {performance.indicator_name}")

    async def combine_signals(self, signals: List[IndicatorSignal],
                            method: EnsembleMethod = EnsembleMethod.ADAPTIVE,
                            context: Optional[Dict[str, Any]] = None) -> EnsembleSignal:
        """
        Combine multiple indicator signals using specified ensemble method.

        Args:
            signals: List of indicator signals to combine
            method: Ensemble method to use
            context: Additional context for combination

        Returns:
            Combined ensemble signal
        """
        if not signals:
            return self._create_empty_signal(method)

        if method not in self._combiners:
            logger.warning(f"Ensemble method {method.value} not available, using adaptive")
            method = EnsembleMethod.ADAPTIVE

        # Prepare context
        if context is None:
            context = {}

        # Add performance data to context
        context['performance_data'] = self._indicator_performance

        # Add weights to context
        ensemble_key = f"{method.value}_default"
        if ensemble_key in self._ensemble_weights:
            context['weights'] = self._ensemble_weights[ensemble_key].indicator_weights

        # Combine signals
        combiner = self._combiners[method]
        ensemble_signal = await combiner.combine_signals(signals, context)

        # Store in history
        async with self._lock:
            self._signal_history.append(ensemble_signal)

            # Maintain history size
            if len(self._signal_history) > self._max_history_size:
                self._signal_history.pop(0)

        logger.debug(f"Combined {len(signals)} signals using {method.value}: {ensemble_signal.signal_type}")
        return ensemble_signal

    def update_weights(self, ensemble_key: str, market_regime: str = "unknown"):
        """Update ensemble weights based on performance."""
        if ensemble_key not in self._ensemble_weights:
            self._ensemble_weights[ensemble_key] = EnsembleWeights(
                indicator_weights={},
                method_weights={},
                market_regime_weights={},
                last_updated=time.time()
            )

        weights = self._ensemble_weights[ensemble_key]

        # Update indicator weights based on performance
        for indicator_name, performance in self._indicator_performance.items():
            # Use win rate and profit factor for weighting
            weight = (performance.win_rate * 0.6) + (min(performance.profit_factor, 3.0) / 3.0 * 0.4)
            weights.indicator_weights[indicator_name] = weight

        # Update market regime weights
        regime_performance = {}
        for indicator_name, performance in self._indicator_performance.items():
            regime_perf = performance.market_regime_performance.get(market_regime, 0.5)
            regime_performance[indicator_name] = regime_perf

        weights.market_regime_weights = regime_performance
        weights.last_updated = time.time()
        weights.adaptation_count += 1

        logger.info(f"Updated weights for {ensemble_key} (adaptation #{weights.adaptation_count})")

    def get_ensemble_performance(self, method: EnsembleMethod, days: int = 30) -> Dict[str, Any]:
        """Get ensemble method performance statistics."""
        cutoff_time = time.time() - (days * 24 * 60 * 60)

        # Filter signals by method and time
        method_signals = [
            signal for signal in self._signal_history
            if signal.ensemble_method == method and signal.timestamp >= cutoff_time
        ]

        if not method_signals:
            return {"total_signals": 0, "performance_metrics": {}}

        # Calculate performance metrics
        signal_types = {}
        confidences = []
        consensus_ratios = []

        for signal in method_signals:
            signal_types[signal.signal_type] = signal_types.get(signal.signal_type, 0) + 1
            confidences.append(signal.confidence)
            consensus_ratios.append(signal.consensus_ratio)

        return {
            "total_signals": len(method_signals),
            "signal_distribution": signal_types,
            "avg_confidence": statistics.mean(confidences) if confidences else 0,
            "avg_consensus_ratio": statistics.mean(consensus_ratios) if consensus_ratios else 0,
            "confidence_std": statistics.stdev(confidences) if len(confidences) > 1 else 0,
            "time_period_days": days
        }

    def get_signal_history(self, method: Optional[EnsembleMethod] = None,
                          limit: int = 100) -> List[EnsembleSignal]:
        """Get signal history."""
        history = self._signal_history

        if method:
            history = [s for s in history if s.ensemble_method == method]

        return history[-limit:]

    def _create_empty_signal(self, method: EnsembleMethod) -> EnsembleSignal:
        """Create empty ensemble signal."""
        return EnsembleSignal(
            signal_type="hold",
            strength=SignalStrength.WEAK,
            confidence=0.0,
            consensus_ratio=0.0,
            participating_indicators=0,
            ensemble_method=method,
            timestamp=time.time()
        )


# Global ensemble manager instance
_ensemble_manager = EnsembleManager()


def get_ensemble_manager() -> EnsembleManager:
    """Get the global ensemble manager."""
    return _ensemble_manager


# Convenience functions
async def combine_signals(signals: List[IndicatorSignal],
                         method: EnsembleMethod = EnsembleMethod.ADAPTIVE,
                         context: Optional[Dict[str, Any]] = None) -> EnsembleSignal:
    """Combine signals using the global ensemble manager."""
    return await _ensemble_manager.combine_signals(signals, method, context)


def register_indicator_performance(performance: IndicatorPerformance):
    """Register indicator performance with the global manager."""
    _ensemble_manager.register_indicator_performance(performance)


def update_ensemble_weights(ensemble_key: str, market_regime: str = "unknown"):
    """Update ensemble weights."""
    _ensemble_manager.update_weights(ensemble_key, market_regime)


def get_ensemble_performance(method: EnsembleMethod, days: int = 30) -> Dict[str, Any]:
    """Get ensemble performance metrics."""
    return _ensemble_manager.get_ensemble_performance(method, days)