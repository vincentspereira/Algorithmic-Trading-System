"""
Unit Tests for Ensemble Methods System.

Tests the ensemble signal combination functionality including:
- Weighted voting combination
- Bayesian combination
- Consensus filtering
- Adaptive ensemble methods
- Performance tracking and weighting
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock
from nautilus_trader_engine.core.ensemble_methods import (
    EnsembleMethod,
    VotingScheme,
    IndicatorSignal,
    EnsembleSignal,
    IndicatorPerformance,
    EnsembleWeights,
    WeightedVotingCombiner,
    BayesianCombiner,
    ConsensusCombiner,
    AdaptiveEnsembleCombiner,
    EnsembleManager,
    combine_signals,
    register_indicator_performance,
    get_ensemble_manager
)
from nautilus_trader_engine.core.interfaces import SignalStrength, MarketRegime


class TestIndicatorSignal:

    def test_initialization(self):
        """Test indicator signal initialization."""
        signal = IndicatorSignal(
            indicator_name="RSI",
            signal_type="buy",
            strength=SignalStrength.STRONG,
            confidence=0.8,
            value=70.5,
            timestamp=1234567890.0
        )

        assert signal.indicator_name == "RSI"
        assert signal.signal_type == "buy"
        assert signal.strength == SignalStrength.STRONG
        assert signal.confidence == 0.8
        assert signal.value == 70.5
        assert signal.timestamp == 1234567890.0
        assert signal.metadata == {}


class TestEnsembleSignal:

    def test_initialization(self):
        """Test ensemble signal initialization."""
        signal = EnsembleSignal(
            signal_type="buy",
            strength=SignalStrength.STRONG,
            confidence=0.75,
            consensus_ratio=0.8,
            participating_indicators=5,
            ensemble_method=EnsembleMethod.WEIGHTED_VOTING,
            timestamp=1234567890.0
        )

        assert signal.signal_type == "buy"
        assert signal.strength == SignalStrength.STRONG
        assert signal.confidence == 0.75
        assert signal.consensus_ratio == 0.8
        assert signal.participating_indicators == 5
        assert signal.ensemble_method == EnsembleMethod.WEIGHTED_VOTING
        assert signal.timestamp == 1234567890.0
        assert signal.component_signals == []
        assert signal.metadata == {}


class TestIndicatorPerformance:

    def test_initialization(self):
        """Test indicator performance initialization."""
        performance = IndicatorPerformance(
            indicator_name="RSI",
            accuracy=0.75,
            precision=0.8,
            recall=0.7,
            f1_score=0.74,
            win_rate=0.65,
            profit_factor=1.5,
            max_drawdown=0.15,
            sharpe_ratio=1.2,
            total_signals=1000,
            last_updated=1234567890.0
        )

        assert performance.indicator_name == "RSI"
        assert performance.accuracy == 0.75
        assert performance.precision == 0.8
        assert performance.recall == 0.7
        assert performance.f1_score == 0.74
        assert performance.win_rate == 0.65
        assert performance.profit_factor == 1.5
        assert performance.max_drawdown == 0.15
        assert performance.sharpe_ratio == 1.2
        assert performance.total_signals == 1000
        assert performance.last_updated == 1234567890.0
        assert performance.market_regime_performance == {}


class TestWeightedVotingCombiner:

    def setup_method(self):
        """Set up test fixtures."""
        self.combiner = WeightedVotingCombiner()

    def test_get_method_name(self):
        """Test getting method name."""
        assert self.combiner.get_method_name() == EnsembleMethod.WEIGHTED_VOTING

    @pytest.mark.asyncio
    async def test_combine_signals_empty(self):
        """Test combining empty signal list."""
        result = await self.combiner.combine_signals([], {})
        assert result.signal_type == "hold"
        assert result.confidence == 0.0
        assert result.participating_indicators == 0

    @pytest.mark.asyncio
    async def test_combine_signals_buy_majority(self):
        """Test combining signals with buy majority."""
        signals = [
            IndicatorSignal("RSI", "buy", SignalStrength.STRONG, 0.8, 70.0, time.time()),
            IndicatorSignal("MACD", "buy", SignalStrength.MODERATE, 0.7, 0.5, time.time()),
            IndicatorSignal("BB", "sell", SignalStrength.WEAK, 0.4, 1.2, time.time())
        ]

        result = await self.combiner.combine_signals(signals, {})

        assert result.signal_type == "buy"
        assert result.participating_indicators == 3
        assert result.confidence > 0.5
        assert result.ensemble_method == EnsembleMethod.WEIGHTED_VOTING

    @pytest.mark.asyncio
    async def test_combine_signals_with_weights(self):
        """Test combining signals with custom weights."""
        signals = [
            IndicatorSignal("RSI", "buy", SignalStrength.STRONG, 0.8, 70.0, time.time()),
            IndicatorSignal("MACD", "sell", SignalStrength.MODERATE, 0.6, -0.3, time.time())
        ]

        weights = {"RSI": 2.0, "MACD": 1.0}
        context = {"weights": weights}

        result = await self.combiner.combine_signals(signals, context)

        # RSI should have more influence due to higher weight
        assert result.signal_type == "buy"
        assert result.participating_indicators == 2


class TestBayesianCombiner:

    def setup_method(self):
        """Set up test fixtures."""
        self.combiner = BayesianCombiner()

    def test_get_method_name(self):
        """Test getting method name."""
        assert self.combiner.get_method_name() == EnsembleMethod.BAYESIAN

    @pytest.mark.asyncio
    async def test_combine_signals_empty(self):
        """Test combining empty signal list."""
        result = await self.combiner.combine_signals([], {})
        assert result.signal_type == "hold"
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_combine_signals_bull_market(self):
        """Test combining signals in bull market context."""
        signals = [
            IndicatorSignal("RSI", "buy", SignalStrength.STRONG, 0.8, 70.0, time.time()),
            IndicatorSignal("MACD", "buy", SignalStrength.MODERATE, 0.7, 0.5, time.time())
        ]

        context = {"market_regime": "bull"}

        result = await self.combiner.combine_signals(signals, context)

        assert result.signal_type == "buy"
        assert "buy_probability" in result.metadata
        assert "sell_probability" in result.metadata
        assert "hold_probability" in result.metadata

    @pytest.mark.asyncio
    async def test_calculate_priors_bull_market(self):
        """Test prior calculation for bull market."""
        signals = [IndicatorSignal("RSI", "buy", SignalStrength.STRONG, 0.8, 70.0, time.time())]
        context = {"market_regime": "bull"}

        priors = self.combiner._calculate_priors(signals, context)

        # Bull market should have higher buy prior
        assert priors["buy"] > priors["sell"]
        assert priors["buy"] > 0.4


class TestConsensusCombiner:

    def setup_method(self):
        """Set up test fixtures."""
        self.combiner = ConsensusCombiner()

    def test_get_method_name(self):
        """Test getting method name."""
        assert self.combiner.get_method_name() == EnsembleMethod.CONSENSUS

    @pytest.mark.asyncio
    async def test_combine_signals_empty(self):
        """Test combining empty signal list."""
        result = await self.combiner.combine_signals([], {})
        assert result.signal_type == "hold"
        assert result.consensus_ratio == 0.0

    @pytest.mark.asyncio
    async def test_combine_signals_high_consensus(self):
        """Test combining signals with high consensus."""
        signals = [
            IndicatorSignal("RSI", "buy", SignalStrength.STRONG, 0.8, 70.0, time.time()),
            IndicatorSignal("MACD", "buy", SignalStrength.STRONG, 0.9, 0.5, time.time()),
            IndicatorSignal("BB", "buy", SignalStrength.MODERATE, 0.7, 1.0, time.time())
        ]

        result = await self.combiner.combine_signals(signals, {})

        assert result.signal_type == "buy"
        assert result.consensus_ratio == 1.0  # All signals agree
        assert result.participating_indicators == 3
        assert "consensus_threshold" in result.metadata

    @pytest.mark.asyncio
    async def test_combine_signals_low_consensus(self):
        """Test combining signals with low consensus."""
        signals = [
            IndicatorSignal("RSI", "buy", SignalStrength.STRONG, 0.8, 70.0, time.time()),
            IndicatorSignal("MACD", "sell", SignalStrength.STRONG, 0.9, -0.5, time.time()),
            IndicatorSignal("BB", "hold", SignalStrength.WEAK, 0.3, 0.0, time.time())
        ]

        result = await self.combiner.combine_signals(signals, {})

        # Low consensus should result in hold
        assert result.signal_type == "hold"
        assert result.consensus_ratio < 0.5


class TestAdaptiveEnsembleCombiner:

    def setup_method(self):
        """Set up test fixtures."""
        self.combiner = AdaptiveEnsembleCombiner()

    def test_get_method_name(self):
        """Test getting method name."""
        assert self.combiner.get_method_name() == EnsembleMethod.ADAPTIVE

    @pytest.mark.asyncio
    async def test_combine_signals_empty(self):
        """Test combining empty signal list."""
        result = await self.combiner.combine_signals([], {})
        assert result.signal_type == "hold"
        assert result.ensemble_method == EnsembleMethod.ADAPTIVE

    @pytest.mark.asyncio
    async def test_combine_signals_high_volatility(self):
        """Test adaptive selection in high volatility."""
        signals = [
            IndicatorSignal("RSI", "buy", SignalStrength.STRONG, 0.8, 70.0, time.time()),
            IndicatorSignal("MACD", "buy", SignalStrength.MODERATE, 0.7, 0.5, time.time())
        ]

        context = {"market_regime": "high_volatility", "volatility": 0.8}

        result = await self.combiner.combine_signals(signals, context)

        # Should use consensus method for high volatility
        assert result.ensemble_method == EnsembleMethod.ADAPTIVE


class TestEnsembleManager:

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = EnsembleManager()

    def test_initialization(self):
        """Test manager initialization."""
        assert isinstance(self.manager._combiners, dict)
        assert isinstance(self.manager._indicator_performance, dict)
        assert isinstance(self.manager._signal_history, list)

    def test_register_indicator_performance(self):
        """Test registering indicator performance."""
        performance = IndicatorPerformance(
            indicator_name="RSI",
            accuracy=0.75,
            precision=0.8,
            recall=0.7,
            f1_score=0.74,
            win_rate=0.65,
            profit_factor=1.5,
            max_drawdown=0.15,
            sharpe_ratio=1.2,
            total_signals=1000,
            last_updated=time.time()
        )

        self.manager.register_indicator_performance(performance)
        assert "RSI" in self.manager._indicator_performance

    @pytest.mark.asyncio
    async def test_combine_signals_empty(self):
        """Test combining empty signals."""
        result = await self.manager.combine_signals([])
        assert result.signal_type == "hold"
        assert result.participating_indicators == 0

    @pytest.mark.asyncio
    async def test_combine_signals_weighted_voting(self):
        """Test combining signals with weighted voting."""
        signals = [
            IndicatorSignal("RSI", "buy", SignalStrength.STRONG, 0.8, 70.0, time.time()),
            IndicatorSignal("MACD", "buy", SignalStrength.MODERATE, 0.7, 0.5, time.time())
        ]

        result = await self.manager.combine_signals(signals, EnsembleMethod.WEIGHTED_VOTING)

        assert result.signal_type == "buy"
        assert result.ensemble_method == EnsembleMethod.WEIGHTED_VOTING
        assert result.participating_indicators == 2

    def test_update_weights(self):
        """Test updating ensemble weights."""
        # Register performance data
        performance = IndicatorPerformance(
            indicator_name="RSI",
            accuracy=0.75,
            precision=0.8,
            recall=0.7,
            f1_score=0.74,
            win_rate=0.65,
            profit_factor=1.5,
            max_drawdown=0.15,
            sharpe_ratio=1.2,
            total_signals=1000,
            last_updated=time.time()
        )

        self.manager.register_indicator_performance(performance)

        # Update weights
        self.manager.update_weights("test_ensemble")

        assert "test_ensemble" in self.manager._ensemble_weights
        weights = self.manager._ensemble_weights["test_ensemble"]
        assert "RSI" in weights.indicator_weights
        assert weights.adaptation_count == 1

    def test_get_ensemble_performance_no_history(self):
        """Test getting performance with no history."""
        performance = self.manager.get_ensemble_performance(EnsembleMethod.WEIGHTED_VOTING)
        assert performance["total_signals"] == 0

    def test_get_signal_history(self):
        """Test getting signal history."""
        history = self.manager.get_signal_history()
        assert isinstance(history, list)

    def test_get_signal_history_with_limit(self):
        """Test getting signal history with limit."""
        history = self.manager.get_signal_history(limit=10)
        assert isinstance(history, list)


class TestGlobalFunctions:

    def test_get_ensemble_manager(self):
        """Test getting global ensemble manager."""
        manager = get_ensemble_manager()
        assert isinstance(manager, EnsembleManager)

    def test_register_indicator_performance_global(self):
        """Test registering performance globally."""
        performance = IndicatorPerformance(
            indicator_name="MACD",
            accuracy=0.7,
            precision=0.75,
            recall=0.65,
            f1_score=0.7,
            win_rate=0.6,
            profit_factor=1.3,
            max_drawdown=0.2,
            sharpe_ratio=0.9,
            total_signals=800,
            last_updated=time.time()
        )

        register_indicator_performance(performance)

        manager = get_ensemble_manager()
        assert "MACD" in manager._indicator_performance

    @pytest.mark.asyncio
    async def test_combine_signals_global(self):
        """Test global signal combination."""
        signals = [
            IndicatorSignal("RSI", "buy", SignalStrength.STRONG, 0.8, 70.0, time.time()),
            IndicatorSignal("MACD", "sell", SignalStrength.MODERATE, 0.6, -0.2, time.time())
        ]

        result = await combine_signals(signals, EnsembleMethod.WEIGHTED_VOTING)

        assert isinstance(result, EnsembleSignal)
        assert result.participating_indicators == 2

    def test_update_ensemble_weights_global(self):
        """Test updating weights globally."""
        update_ensemble_weights("global_test")
        manager = get_ensemble_manager()
        assert "global_test" in manager._ensemble_weights

    def test_get_ensemble_performance_global(self):
        """Test getting performance globally."""
        performance = get_ensemble_performance(EnsembleMethod.WEIGHTED_VOTING)
        assert isinstance(performance, dict)
        assert "total_signals" in performance