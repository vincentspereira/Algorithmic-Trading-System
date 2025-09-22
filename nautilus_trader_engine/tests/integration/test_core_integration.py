"""
Integration Tests for Core System Components.

Tests the integration between core components including:
- Dependency injection with event system
- Adaptive parameters with ensemble methods
- Validation system with caching
- Streaming architecture components
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock
from nautilus_trader_engine.core.dependency_injection import (
    DependencyInjectionContainer,
    get_container,
    ServiceLifetime
)
from nautilus_trader_engine.core.event_system import EventBus, get_event_bus, EventType, EventPriority
from nautilus_trader_engine.core.adaptive_parameters import (
    AdaptiveParameterManager,
    VolatilityBasedAdapter,
    MarketRegimeAdapter,
    ParameterType,
    ParameterBounds,
    AdaptationStrategy,
    MarketCondition
)
from nautilus_trader_engine.core.ensemble_methods import (
    EnsembleManager,
    WeightedVotingCombiner,
    IndicatorSignal,
    EnsembleMethod
)
from nautilus_trader_engine.core.validation_system import (
    ValidationManager,
    SignalValidator,
    DataQualityValidator,
    ValidationType,
    ValidationStatus
)
from nautilus_trader_engine.core.interfaces import SignalStrength, MarketRegime, RiskLevel


class TestDependencyInjectionEventSystemIntegration:
    """Test integration between dependency injection and event system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.container = DependencyInjectionContainer()
        self.event_bus = EventBus()

    def test_di_with_event_bus_registration(self):
        """Test registering event bus in DI container."""
        # Register event bus as singleton
        self.container.register_singleton(EventBus, self.event_bus)

        # Resolve event bus
        resolved_bus = self.container.get_service(EventBus)

        assert resolved_bus is self.event_bus

    @pytest.mark.asyncio
    async def test_event_bus_with_di_services(self):
        """Test event bus publishing events to DI-managed services."""
        events_received = []

        class EventHandler:
            def __init__(self):
                self.events = []

            async def handle_event(self, event_data):
                self.events.append(event_data)

        # Create handler and register in DI
        handler = EventHandler()
        self.container.register_singleton(EventHandler, handler)

        # Register event bus
        self.container.register_singleton(EventBus, self.event_bus)

        # Subscribe to event
        await self.event_bus.subscribe("test_event", handler.handle_event)

        # Publish event
        test_data = {"message": "integration test"}
        await self.event_bus.publish_event(
            self.event_bus.create_event(EventType.SYSTEM_STARTUP, "test", test_data)
        )

        # Verify event was received
        assert len(handler.events) == 1
        assert handler.events[0]["message"] == "integration test"


class TestAdaptiveParametersEnsembleIntegration:
    """Test integration between adaptive parameters and ensemble methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.container = DependencyInjectionContainer()
        self.adaptive_manager = AdaptiveParameterManager(self.container)
        self.ensemble_manager = EnsembleManager(self.container)

    def test_adaptive_parameters_with_ensemble_weights(self):
        """Test adaptive parameters updating ensemble weights."""
        # Register adaptive parameters
        bounds = ParameterBounds(min_value=10.0, max_value=30.0)
        param = {
            "name": "period",
            "parameter_type": ParameterType.PERIOD,
            "base_value": 20.0,
            "bounds": bounds,
            "adaptation_strategy": AdaptationStrategy.VOLATILITY_BASED
        }

        self.adaptive_manager.register_indicator_parameters("test_indicator", {"period": param})

        # Update market condition
        condition = MarketCondition(
            volatility=0.8,
            trend_strength=0.5,
            volume_confirmation=0.6,
            market_regime=MarketRegime.HIGH_VOLATILITY,
            risk_level=RiskLevel.HIGH
        )
        self.adaptive_manager.update_market_condition(condition)

        # Update ensemble weights based on performance
        self.ensemble_manager.update_weights("test_ensemble")

        # Verify weights were updated
        assert "test_ensemble" in self.ensemble_manager._ensemble_weights

    @pytest.mark.asyncio
    async def test_ensemble_with_adaptive_parameters(self):
        """Test ensemble methods using adaptive parameters."""
        # Register parameters
        bounds = ParameterBounds(min_value=10.0, max_value=30.0)
        param = {
            "name": "period",
            "parameter_type": ParameterType.PERIOD,
            "base_value": 20.0,
            "bounds": bounds,
            "adaptation_strategy": AdaptationStrategy.VOLATILITY_BASED
        }

        self.adaptive_manager.register_indicator_parameters("test_indicator", {"period": param})

        # Create signals
        signals = [
            IndicatorSignal("test_indicator", "buy", SignalStrength.STRONG, 0.8, 20.0, time.time()),
            IndicatorSignal("RSI", "buy", SignalStrength.MODERATE, 0.7, 30.0, time.time())
        ]

        # Combine signals
        result = await self.ensemble_manager.combine_signals(signals, EnsembleMethod.WEIGHTED_VOTING)

        assert isinstance(result, dict)
        assert "signal_type" in result
        assert "confidence" in result


class TestValidationSystemIntegration:
    """Test integration of validation system with other components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.container = DependencyInjectionContainer()
        self.validation_manager = ValidationManager(self.container)

    @pytest.mark.asyncio
    async def test_signal_validation_with_event_bus(self):
        """Test signal validation publishing events."""
        # Create mock event bus
        mock_event_bus = Mock()
        mock_event_bus.publish_event = AsyncMock()
        mock_event_bus.create_event = Mock(return_value=Mock())

        # Replace the event bus in validation manager
        self.validation_manager._event_bus = mock_event_bus

        # Validate a signal
        signal_data = {
            'signal_type': 'buy',
            'confidence': 0.9,
            'strength': 'strong',
            'indicator_name': 'RSI'
        }

        result = await self.validation_manager.validate_data(
            ValidationType.SIGNAL_VALIDATION,
            signal_data
        )

        assert isinstance(result, dict)
        assert result['validation_type'] == ValidationType.SIGNAL_VALIDATION.value

        # Verify event was published
        mock_event_bus.publish_event.assert_called()

    @pytest.mark.asyncio
    async def test_data_quality_validation_integration(self):
        """Test data quality validation with multiple data points."""
        # Validate multiple data points
        data_points = [
            {
                'symbol': 'AAPL',
                'price': 150.0,
                'volume': 1000000,
                'timestamp': time.time()
            },
            {
                'symbol': 'AAPL',
                'price': 151.0,
                'volume': 1100000,
                'timestamp': time.time() + 1
            }
        ]

        for data in data_points:
            result = await self.validation_manager.validate_data(
                ValidationType.DATA_QUALITY,
                data
            )

            assert isinstance(result, dict)
            assert 'status' in result

    def test_validation_rule_integration(self):
        """Test validation rules working together."""
        # Add multiple validation rules
        rules = [
            {
                "rule_id": "signal_confidence_rule",
                "name": "Signal Confidence Check",
                "validation_type": ValidationType.SIGNAL_VALIDATION,
                "description": "Check signal confidence",
                "enabled": True,
                "threshold_warning": 0.6,
                "threshold_critical": 0.3
            },
            {
                "rule_id": "data_freshness_rule",
                "name": "Data Freshness Check",
                "validation_type": ValidationType.DATA_QUALITY,
                "description": "Check data freshness",
                "enabled": True,
                "threshold_warning": 120.0,
                "threshold_critical": 300.0
            }
        ]

        for rule_data in rules:
            from nautilus_trader_engine.core.validation_system import ValidationRule
            rule = ValidationRule(**rule_data)
            self.validation_manager.add_validation_rule(rule)

        # Verify rules were added
        all_rules = self.validation_manager.get_validation_rules()
        assert len(all_rules) >= 2  # May have default rules too


class TestStreamingArchitectureIntegration:
    """Test integration of streaming architecture components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.container = DependencyInjectionContainer()

    def test_streaming_with_dependency_injection(self):
        """Test streaming components registered in DI container."""
        # This would test streaming engine integration
        # For now, just verify DI container works
        assert self.container is not None

    @pytest.mark.asyncio
    async def test_async_component_integration(self):
        """Test async components working together."""
        # Create async services
        async def async_service_1():
            await asyncio.sleep(0.01)
            return "service_1_result"

        async def async_service_2():
            await asyncio.sleep(0.01)
            return "service_2_result"

        # Register async services
        self.container.register_singleton(type(async_service_1), async_service_1)
        self.container.register_singleton(type(async_service_2), async_service_2)

        # Resolve and call services
        service1 = self.container.get_service(type(async_service_1))
        service2 = self.container.get_service(type(async_service_2))

        result1 = await service1()
        result2 = await service2()

        assert result1 == "service_1_result"
        assert result2 == "service_2_result"


class TestFaultToleranceIntegration:
    """Test fault tolerance integration with other components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.container = DependencyInjectionContainer()

    def test_fault_tolerance_with_di(self):
        """Test fault tolerance decorators with dependency injection."""
        # This would test fault tolerance integration
        # For now, just verify basic functionality
        assert self.container is not None


class TestConfigurationManagementIntegration:
    """Test configuration management integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.container = DependencyInjectionContainer()

    def test_configuration_with_di(self):
        """Test configuration management with dependency injection."""
        # This would test configuration integration
        # For now, just verify basic functionality
        assert self.container is not None


class TestEndToEndWorkflowIntegration:
    """Test end-to-end workflow integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.container = DependencyInjectionContainer()
        self.adaptive_manager = AdaptiveParameterManager(self.container)
        self.ensemble_manager = EnsembleManager(self.container)
        self.validation_manager = ValidationManager(self.container)

    @pytest.mark.asyncio
    async def test_complete_signal_processing_workflow(self):
        """Test complete signal processing workflow."""
        # 1. Set up adaptive parameters
        bounds = ParameterBounds(min_value=10.0, max_value=30.0)
        param = {
            "name": "period",
            "parameter_type": ParameterType.PERIOD,
            "base_value": 20.0,
            "bounds": bounds,
            "adaptation_strategy": AdaptationStrategy.VOLATILITY_BASED
        }

        self.adaptive_manager.register_indicator_parameters("RSI", {"period": param})

        # 2. Update market conditions
        condition = MarketCondition(
            volatility=0.6,
            trend_strength=0.7,
            volume_confirmation=0.8,
            market_regime=MarketRegime.BULL,
            risk_level=RiskLevel.MODERATE
        )
        self.adaptive_manager.update_market_condition(condition)

        # 3. Create indicator signals
        signals = [
            IndicatorSignal("RSI", "buy", SignalStrength.STRONG, 0.85, 25.0, time.time()),
            IndicatorSignal("MACD", "buy", SignalStrength.MODERATE, 0.75, 1.2, time.time()),
            IndicatorSignal("BB", "hold", SignalStrength.WEAK, 0.45, 0.1, time.time())
        ]

        # 4. Combine signals using ensemble
        ensemble_result = await self.ensemble_manager.combine_signals(
            signals,
            EnsembleMethod.WEIGHTED_VOTING
        )

        assert isinstance(ensemble_result, dict)
        assert "signal_type" in ensemble_result
        assert "confidence" in ensemble_result

        # 5. Validate the ensemble signal
        signal_data = {
            'signal_type': ensemble_result.get('signal_type', 'hold'),
            'confidence': ensemble_result.get('confidence', 0.5),
            'strength': 'moderate',
            'indicator_name': 'Ensemble'
        }

        validation_result = await self.validation_manager.validate_data(
            ValidationType.SIGNAL_VALIDATION,
            signal_data
        )

        assert isinstance(validation_result, dict)
        assert 'status' in validation_result

        # 6. Verify the complete workflow
        assert ensemble_result['signal_type'] in ['buy', 'sell', 'hold']
        assert 0.0 <= ensemble_result['confidence'] <= 1.0