"""
Unit Tests for Adaptive Parameters System.

Tests the adaptive parameter functionality including:
- Parameter adaptation strategies
- Market condition assessment
- Performance-based optimization
- Parameter bounds and constraints
- Adaptation history tracking
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock
from nautilus_trader_engine.core.adaptive_parameters import (
    AdaptiveParameter,
    ParameterBounds,
    ParameterType,
    AdaptationStrategy,
    MarketCondition,
    AdaptationContext,
    VolatilityBasedAdapter,
    TrendStrengthAdapter,
    MarketRegimeAdapter,
    PerformanceBasedAdapter,
    AdaptiveParameterManager,
    create_adaptive_parameter,
    get_adaptive_manager
)
from nautilus_trader_engine.core.interfaces import MarketRegime, SignalStrength, RiskLevel


class TestAdaptiveParameter:

    def setup_method(self):
        """Set up test fixtures."""
        self.bounds = ParameterBounds(min_value=5.0, max_value=50.0, step_size=1.0)
        self.param = AdaptiveParameter(
            name="test_period",
            parameter_type=ParameterType.PERIOD,
            base_value=20.0,
            bounds=self.bounds,
            adaptation_strategy=AdaptationStrategy.VOLATILITY_BASED
        )

    def test_initialization(self):
        """Test parameter initialization."""
        assert self.param.name == "test_period"
        assert self.param.parameter_type == ParameterType.PERIOD
        assert self.param.base_value == 20.0
        assert self.param.current_value == 20.0
        assert self.param.adaptation_weight == 1.0
        assert self.param.smoothing_factor == 0.1

    def test_update_value_within_bounds(self):
        """Test updating parameter value within bounds."""
        self.param.update_value(25.0)
        assert self.param.current_value == 25.0

    def test_update_value_below_min(self):
        """Test updating parameter value below minimum."""
        self.param.update_value(2.0)
        assert self.param.current_value == 5.0

    def test_update_value_above_max(self):
        """Test updating parameter value above maximum."""
        self.param.update_value(60.0)
        assert self.param.current_value == 50.0

    def test_update_value_with_smoothing(self):
        """Test updating parameter value with smoothing."""
        self.param.update_value(30.0)
        # With smoothing factor 0.1, new value should be closer to current
        expected = 0.1 * 30.0 + 0.9 * 20.0
        assert abs(self.param.current_value - expected) < 0.01

    def test_reset_to_base(self):
        """Test resetting parameter to base value."""
        self.param.update_value(30.0)
        assert self.param.current_value != 20.0

        self.param.reset_to_base()
        assert self.param.current_value == 20.0

    def test_get_adaptation_stats_empty(self):
        """Test getting adaptation stats with no history."""
        stats = self.param.get_adaptation_stats()
        assert stats == {}

    def test_get_adaptation_stats_with_history(self):
        """Test getting adaptation stats with history."""
        self.param.update_value(25.0)
        self.param.update_value(30.0)
        self.param.update_value(28.0)

        stats = self.param.get_adaptation_stats()
        assert "mean" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats
        assert stats["adaptations_count"] == 3


class TestParameterBounds:

    def test_initialization(self):
        """Test bounds initialization."""
        bounds = ParameterBounds(min_value=0.0, max_value=100.0, step_size=0.5)
        assert bounds.min_value == 0.0
        assert bounds.max_value == 100.0
        assert bounds.step_size == 0.5
        assert bounds.allowed_values is None
        assert bounds.transformation == "linear"


class TestVolatilityBasedAdapter:

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = VolatilityBasedAdapter()

    def test_get_adaptation_strategy(self):
        """Test getting adaptation strategy."""
        assert self.adapter.get_adaptation_strategy() == AdaptationStrategy.VOLATILITY_BASED

    @pytest.mark.asyncio
    async def test_adapt_parameters_high_volatility(self):
        """Test adapting parameters in high volatility."""
        market_condition = MarketCondition(
            volatility=0.8,
            trend_strength=0.5,
            volume_confirmation=0.6,
            market_regime=MarketRegime.HIGH_VOLATILITY,
            risk_level=RiskLevel.HIGH
        )

        context = AdaptationContext(
            market_condition=market_condition,
            indicator_performance={},
            timeframe="1h",
            symbol="AAPL"
        )

        bounds = ParameterBounds(min_value=5.0, max_value=50.0)
        param = AdaptiveParameter(
            name="period",
            parameter_type=ParameterType.PERIOD,
            base_value=20.0,
            bounds=bounds,
            adaptation_strategy=AdaptationStrategy.VOLATILITY_BASED
        )

        parameters = {"period": param}

        adaptations = await self.adapter.adapt_parameters(parameters, context)

        # High volatility should increase period
        assert adaptations["period"] > 20.0

    @pytest.mark.asyncio
    async def test_adapt_parameters_low_volatility(self):
        """Test adapting parameters in low volatility."""
        market_condition = MarketCondition(
            volatility=0.2,
            trend_strength=0.5,
            volume_confirmation=0.6,
            market_regime=MarketRegime.LOW_VOLATILITY,
            risk_level=RiskLevel.LOW
        )

        context = AdaptationContext(
            market_condition=market_condition,
            indicator_performance={},
            timeframe="1h",
            symbol="AAPL"
        )

        bounds = ParameterBounds(min_value=5.0, max_value=50.0)
        param = AdaptiveParameter(
            name="period",
            parameter_type=ParameterType.PERIOD,
            base_value=20.0,
            bounds=bounds,
            adaptation_strategy=AdaptationStrategy.VOLATILITY_BASED
        )

        parameters = {"period": param}

        adaptations = await self.adapter.adapt_parameters(parameters, context)

        # Low volatility should decrease period
        assert adaptations["period"] < 20.0


class TestTrendStrengthAdapter:

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = TrendStrengthAdapter()

    def test_get_adaptation_strategy(self):
        """Test getting adaptation strategy."""
        assert self.adapter.get_adaptation_strategy() == AdaptationStrategy.TREND_STRENGTH

    @pytest.mark.asyncio
    async def test_adapt_parameters_strong_trend(self):
        """Test adapting parameters in strong trend."""
        market_condition = MarketCondition(
            volatility=0.5,
            trend_strength=0.8,
            volume_confirmation=0.6,
            market_regime=MarketRegime.TRENDING,
            risk_level=RiskLevel.MODERATE
        )

        context = AdaptationContext(
            market_condition=market_condition,
            indicator_performance={},
            timeframe="1h",
            symbol="AAPL"
        )

        bounds = ParameterBounds(min_value=0.1, max_value=2.0)
        param = AdaptiveParameter(
            name="sensitivity",
            parameter_type=ParameterType.SENSITIVITY,
            base_value=1.0,
            bounds=bounds,
            adaptation_strategy=AdaptationStrategy.TREND_STRENGTH
        )

        parameters = {"sensitivity": param}

        adaptations = await self.adapter.adapt_parameters(parameters, context)

        # Strong trend should increase sensitivity
        assert adaptations["sensitivity"] > 1.0


class TestMarketRegimeAdapter:

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = MarketRegimeAdapter()

    def test_get_adaptation_strategy(self):
        """Test getting adaptation strategy."""
        assert self.adapter.get_adaptation_strategy() == AdaptationStrategy.MARKET_REGIME

    @pytest.mark.asyncio
    async def test_adapt_parameters_bull_market(self):
        """Test adapting parameters in bull market."""
        market_condition = MarketCondition(
            volatility=0.3,
            trend_strength=0.7,
            volume_confirmation=0.8,
            market_regime=MarketRegime.BULL,
            risk_level=RiskLevel.MODERATE
        )

        context = AdaptationContext(
            market_condition=market_condition,
            indicator_performance={},
            timeframe="1h",
            symbol="AAPL"
        )

        bounds = ParameterBounds(min_value=5.0, max_value=50.0)
        param = AdaptiveParameter(
            name="period",
            parameter_type=ParameterType.PERIOD,
            base_value=20.0,
            bounds=bounds,
            adaptation_strategy=AdaptationStrategy.MARKET_REGIME
        )

        parameters = {"period": param}

        adaptations = await self.adapter.adapt_parameters(parameters, context)

        # Bull market should decrease period
        assert adaptations["period"] < 20.0


class TestPerformanceBasedAdapter:

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = PerformanceBasedAdapter()

    def test_get_adaptation_strategy(self):
        """Test getting adaptation strategy."""
        assert self.adapter.get_adaptation_strategy() == AdaptationStrategy.PERFORMANCE_BASED

    @pytest.mark.asyncio
    async def test_adapt_parameters_good_performance(self):
        """Test adapting parameters with good performance."""
        market_condition = MarketCondition(
            volatility=0.5,
            trend_strength=0.5,
            volume_confirmation=0.5,
            market_regime=MarketRegime.SIDEWAYS,
            risk_level=RiskLevel.MODERATE
        )

        context = AdaptationContext(
            market_condition=market_condition,
            indicator_performance={
                "accuracy": 0.8,
                "win_rate": 0.75,
                "profit_factor": 1.8
            },
            timeframe="1h",
            symbol="AAPL"
        )

        bounds = ParameterBounds(min_value=5.0, max_value=50.0)
        param = AdaptiveParameter(
            name="period",
            parameter_type=ParameterType.PERIOD,
            base_value=20.0,
            bounds=bounds,
            adaptation_strategy=AdaptationStrategy.PERFORMANCE_BASED
        )

        parameters = {"period": param}

        adaptations = await self.adapter.adapt_parameters(parameters, context)

        # Should return adapted value
        assert "period" in adaptations


class TestAdaptiveParameterManager:

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = AdaptiveParameterManager()

    def test_initialization(self):
        """Test manager initialization."""
        assert isinstance(self.manager._adapters, dict)
        assert isinstance(self.manager._indicator_parameters, dict)
        assert isinstance(self.manager._market_conditions, list)

    def test_register_indicator_parameters(self):
        """Test registering indicator parameters."""
        bounds = ParameterBounds(min_value=5.0, max_value=50.0)
        param = AdaptiveParameter(
            name="period",
            parameter_type=ParameterType.PERIOD,
            base_value=20.0,
            bounds=bounds,
            adaptation_strategy=AdaptationStrategy.VOLATILITY_BASED
        )

        parameters = {"period": param}
        self.manager.register_indicator_parameters("test_indicator", parameters)

        assert "test_indicator" in self.manager._indicator_parameters
        assert self.manager._indicator_parameters["test_indicator"] == parameters

    def test_update_market_condition(self):
        """Test updating market condition."""
        condition = MarketCondition(
            volatility=0.5,
            trend_strength=0.6,
            volume_confirmation=0.7,
            market_regime=MarketRegime.SIDEWAYS,
            risk_level=RiskLevel.MODERATE
        )

        self.manager.update_market_condition(condition)
        assert len(self.manager._market_conditions) == 1
        assert self.manager._market_conditions[0] == condition

    @pytest.mark.asyncio
    async def test_adapt_indicator_parameters_no_registration(self):
        """Test adapting parameters for unregistered indicator."""
        adaptations = await self.manager.adapt_indicator_parameters("unknown_indicator")
        assert adaptations == {}

    @pytest.mark.asyncio
    async def test_adapt_indicator_parameters_with_registration(self):
        """Test adapting parameters for registered indicator."""
        # Register parameters
        bounds = ParameterBounds(min_value=5.0, max_value=50.0)
        param = AdaptiveParameter(
            name="period",
            parameter_type=ParameterType.PERIOD,
            base_value=20.0,
            bounds=bounds,
            adaptation_strategy=AdaptationStrategy.VOLATILITY_BASED
        )

        parameters = {"period": param}
        self.manager.register_indicator_parameters("test_indicator", parameters)

        # Update market condition
        condition = MarketCondition(
            volatility=0.8,
            trend_strength=0.5,
            volume_confirmation=0.6,
            market_regime=MarketRegime.HIGH_VOLATILITY,
            risk_level=RiskLevel.HIGH
        )
        self.manager.update_market_condition(condition)

        # Adapt parameters
        adaptations = await self.manager.adapt_indicator_parameters("test_indicator")

        assert "period" in adaptations
        assert isinstance(adaptations["period"], float)

    def test_get_adaptation_history(self):
        """Test getting adaptation history."""
        history = self.manager.get_adaptation_history("test_indicator")
        assert isinstance(history, list)

    def test_get_parameter_stats_no_registration(self):
        """Test getting parameter stats for unregistered indicator."""
        stats = self.manager.get_parameter_stats("unknown_indicator")
        assert stats == {}

    def test_get_parameter_stats_with_registration(self):
        """Test getting parameter stats for registered indicator."""
        bounds = ParameterBounds(min_value=5.0, max_value=50.0)
        param = AdaptiveParameter(
            name="period",
            parameter_type=ParameterType.PERIOD,
            base_value=20.0,
            bounds=bounds,
            adaptation_strategy=AdaptationStrategy.VOLATILITY_BASED
        )

        parameters = {"period": param}
        self.manager.register_indicator_parameters("test_indicator", parameters)

        stats = self.manager.get_parameter_stats("test_indicator")

        assert "period" in stats
        assert "current_value" in stats["period"]
        assert "base_value" in stats["period"]
        assert "adaptation_stats" in stats["period"]

    def test_reset_indicator_parameters(self):
        """Test resetting indicator parameters."""
        bounds = ParameterBounds(min_value=5.0, max_value=50.0)
        param = AdaptiveParameter(
            name="period",
            parameter_type=ParameterType.PERIOD,
            base_value=20.0,
            bounds=bounds,
            adaptation_strategy=AdaptationStrategy.VOLATILITY_BASED
        )

        parameters = {"period": param}
        self.manager.register_indicator_parameters("test_indicator", parameters)

        # Modify parameter
        param.update_value(30.0)
        assert param.current_value != 20.0

        # Reset
        self.manager.reset_indicator_parameters("test_indicator")
        assert param.current_value == 20.0


class TestGlobalFunctions:

    def test_get_adaptive_manager(self):
        """Test getting global adaptive manager."""
        manager = get_adaptive_manager()
        assert isinstance(manager, AdaptiveParameterManager)

    def test_create_adaptive_parameter(self):
        """Test creating adaptive parameter."""
        bounds = ParameterBounds(min_value=5.0, max_value=50.0)
        param = create_adaptive_parameter(
            name="test_param",
            parameter_type=ParameterType.PERIOD,
            base_value=20.0,
            bounds=bounds,
            adaptation_strategy=AdaptationStrategy.VOLATILITY_BASED
        )

        assert isinstance(param, AdaptiveParameter)
        assert param.name == "test_param"
        assert param.parameter_type == ParameterType.PERIOD
        assert param.base_value == 20.0
        assert param.adaptation_strategy == AdaptationStrategy.VOLATILITY_BASED


class TestMarketCondition:

    def test_initialization(self):
        """Test market condition initialization."""
        condition = MarketCondition(
            volatility=0.5,
            trend_strength=0.6,
            volume_confirmation=0.7,
            market_regime=MarketRegime.BULL,
            risk_level=RiskLevel.MODERATE
        )

        assert condition.volatility == 0.5
        assert condition.trend_strength == 0.6
        assert condition.volume_confirmation == 0.7
        assert condition.market_regime == MarketRegime.BULL
        assert condition.risk_level == RiskLevel.MODERATE
        assert isinstance(condition.timestamp, float)


class TestAdaptationContext:

    def test_initialization(self):
        """Test adaptation context initialization."""
        market_condition = MarketCondition(
            volatility=0.5,
            trend_strength=0.6,
            volume_confirmation=0.7,
            market_regime=MarketRegime.BULL,
            risk_level=RiskLevel.MODERATE
        )

        context = AdaptationContext(
            market_condition=market_condition,
            indicator_performance={"accuracy": 0.8},
            timeframe="1h",
            symbol="AAPL"
        )

        assert context.market_condition == market_condition
        assert context.indicator_performance == {"accuracy": 0.8}
        assert context.timeframe == "1h"
        assert context.symbol == "AAPL"
        assert context.adaptation_factors == {}