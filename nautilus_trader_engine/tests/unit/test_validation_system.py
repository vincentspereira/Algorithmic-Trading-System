"""
Unit Tests for Validation System.

Tests the validation functionality including:
- Signal validation
- Data quality validation
- System health validation
- Validation rule management
- Alert generation and event publishing
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from nautilus_trader_engine.core.validation_system import (
    ValidationStatus,
    ValidationType,
    ValidationResult,
    ValidationRule,
    ValidationMetrics,
    SignalValidator,
    DataQualityValidator,
    SystemHealthValidator,
    ValidationManager,
    validate_signal,
    validate_market_data,
    validate_system_health,
    get_validation_manager
)
from nautilus_trader_engine.core.interfaces import SignalStrength, MarketRegime, RiskLevel
from nautilus_trader_engine.core.event_system import EventType, EventPriority


class TestValidationResult:

    def test_initialization(self):
        """Test validation result initialization."""
        result = ValidationResult(
            validation_type=ValidationType.SIGNAL_VALIDATION,
            status=ValidationStatus.VALID,
            confidence=0.85,
            message="Validation passed",
            timestamp=1234567890.0,
            validator_id="test_validator",
            severity_score=0.1
        )

        assert result.validation_type == ValidationType.SIGNAL_VALIDATION
        assert result.status == ValidationStatus.VALID
        assert result.confidence == 0.85
        assert result.message == "Validation passed"
        assert result.timestamp == 1234567890.0
        assert result.validator_id == "test_validator"
        assert result.severity_score == 0.1
        assert result.details == {}
        assert result.recommended_actions == []


class TestValidationRule:

    def test_initialization(self):
        """Test validation rule initialization."""
        rule = ValidationRule(
            rule_id="test_rule",
            name="Test Rule",
            validation_type=ValidationType.SIGNAL_VALIDATION,
            description="A test validation rule",
            enabled=True,
            priority=EventPriority.NORMAL,
            threshold_warning=0.7,
            threshold_critical=0.9,
            check_interval=60.0,
            max_violations=3,
            cooldown_period=300.0
        )

        assert rule.rule_id == "test_rule"
        assert rule.name == "Test Rule"
        assert rule.validation_type == ValidationType.SIGNAL_VALIDATION
        assert rule.description == "A test validation rule"
        assert rule.enabled is True
        assert rule.priority == EventPriority.NORMAL
        assert rule.threshold_warning == 0.7
        assert rule.threshold_critical == 0.9
        assert rule.check_interval == 60.0
        assert rule.max_violations == 3
        assert rule.cooldown_period == 300.0
        assert rule.last_triggered is None
        assert rule.violation_count == 0


class TestValidationMetrics:

    def test_initialization(self):
        """Test validation metrics initialization."""
        metrics = ValidationMetrics()
        assert metrics.total_validations == 0
        assert metrics.validations_passed == 0
        assert metrics.validations_failed == 0
        assert metrics.average_response_time == 0.0
        assert metrics.alerts_generated == 0
        assert metrics.rules_triggered == 0
        assert metrics.last_validation_time is None


class TestSignalValidator:

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SignalValidator()

    def test_initialization(self):
        """Test validator initialization."""
        assert self.validator.validator_id == "signal_validator"
        assert ValidationType.SIGNAL_VALIDATION in self.validator.supported_validation_types
        assert isinstance(self.validator._signal_history, dict)

    @pytest.mark.asyncio
    async def test_validate_high_confidence_signal(self):
        """Test validating a high confidence signal."""
        signal_data = {
            'signal_type': 'buy',
            'confidence': 0.9,
            'strength': 'strong',
            'indicator_name': 'RSI'
        }

        context = {
            'volatility': 0.3,
            'trend_strength': 0.8,
            'market_regime': 'bull'
        }

        result = await self.validator.validate(signal_data, context)

        assert result.validation_type == ValidationType.SIGNAL_VALIDATION
        assert result.status == ValidationStatus.VALID
        assert result.confidence > 0.5
        assert result.validator_id == "signal_validator"

    @pytest.mark.asyncio
    async def test_validate_low_confidence_signal(self):
        """Test validating a low confidence signal."""
        signal_data = {
            'signal_type': 'buy',
            'confidence': 0.2,
            'strength': 'weak',
            'indicator_name': 'RSI'
        }

        context = {
            'volatility': 0.8,
            'trend_strength': 0.2,
            'market_regime': 'bear'
        }

        result = await self.validator.validate(signal_data, context)

        assert result.status in [ValidationStatus.WARNING, ValidationStatus.CRITICAL]
        assert result.confidence < 0.5
        assert "Low confidence" in result.message

    @pytest.mark.asyncio
    async def test_signal_consistency_check(self):
        """Test signal consistency checking."""
        signal_data = {'signal_type': 'buy', 'confidence': 0.8}
        context = {'volatility': 0.2, 'trend_strength': 0.9}

        consistency = await self.validator._check_signal_consistency(signal_data, context)
        assert isinstance(consistency, float)
        assert 0.0 <= consistency <= 1.0

    @pytest.mark.asyncio
    async def test_market_regime_alignment(self):
        """Test market regime alignment checking."""
        signal_data = {'signal_type': 'buy'}
        context = {'market_regime': 'bull'}

        alignment = await self.validator._check_market_regime_alignment(signal_data, context)
        assert isinstance(alignment, float)
        assert 0.0 <= alignment <= 1.0


class TestDataQualityValidator:

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DataQualityValidator()

    def test_initialization(self):
        """Test validator initialization."""
        assert self.validator.validator_id == "data_quality_validator"
        assert ValidationType.DATA_QUALITY in self.validator.supported_validation_types
        assert ValidationType.MARKET_ANOMALY in self.validator.supported_validation_types

    @pytest.mark.asyncio
    async def test_validate_fresh_data(self):
        """Test validating fresh market data."""
        data = {
            'symbol': 'AAPL',
            'price': 150.0,
            'volume': 1000000,
            'timestamp': time.time()
        }

        context = {}
        result = await self.validator.validate(data, context)

        assert result.validation_type == ValidationType.DATA_QUALITY
        assert result.status == ValidationStatus.VALID
        assert result.validator_id == "data_quality_validator"

    @pytest.mark.asyncio
    async def test_validate_stale_data(self):
        """Test validating stale market data."""
        data = {
            'symbol': 'AAPL',
            'price': 150.0,
            'volume': 1000000,
            'timestamp': time.time() - 400  # 400 seconds old
        }

        context = {}
        result = await self.validator.validate(data, context)

        assert result.status in [ValidationStatus.WARNING, ValidationStatus.CRITICAL]
        assert "old" in result.message.lower()

    def test_data_completeness_check(self):
        """Test data completeness checking."""
        complete_data = {
            'symbol': 'AAPL',
            'price': 150.0,
            'volume': 1000000,
            'timestamp': time.time(),
            'bid': 149.9,
            'ask': 150.1
        }

        completeness = self.validator._check_data_completeness(complete_data)
        assert completeness > 0.8

        incomplete_data = {'symbol': 'AAPL'}  # Missing required fields
        completeness = self.validator._check_data_completeness(incomplete_data)
        assert completeness < 0.5


class TestSystemHealthValidator:

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SystemHealthValidator()

    def test_initialization(self):
        """Test validator initialization."""
        assert self.validator.validator_id == "system_health_validator"
        assert ValidationType.SYSTEM_HEALTH in self.validator.supported_validation_types

    @pytest.mark.asyncio
    async def test_validate_healthy_system(self):
        """Test validating a healthy system."""
        system_data = {
            'cpu_usage': 45.0,
            'memory_usage': 60.0,
            'disk_usage': 70.0,
            'network_latency': 50.0,
            'active_connections': 500,
            'queue_size': 1000
        }

        context = {}
        result = await self.validator.validate(system_data, context)

        assert result.validation_type == ValidationType.SYSTEM_HEALTH
        assert result.status == ValidationStatus.VALID
        assert result.validator_id == "system_health_validator"

    @pytest.mark.asyncio
    async def test_validate_unhealthy_system(self):
        """Test validating an unhealthy system."""
        system_data = {
            'cpu_usage': 95.0,
            'memory_usage': 92.0,
            'disk_usage': 85.0,
            'network_latency': 1200.0,
            'active_connections': 500,
            'queue_size': 1000
        }

        context = {}
        result = await self.validator.validate(system_data, context)

        assert result.status in [ValidationStatus.WARNING, ValidationStatus.CRITICAL]
        assert "CPU usage" in result.message or "memory usage" in result.message

    @pytest.mark.asyncio
    async def test_calculate_error_rate_no_history(self):
        """Test error rate calculation with no history."""
        error_rate = await self.validator._calculate_error_rate()
        assert error_rate == 0.0


class TestValidationManager:

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ValidationManager()

    def test_initialization(self):
        """Test manager initialization."""
        assert isinstance(self.manager._validators, dict)
        assert isinstance(self.manager._validation_rules, dict)
        assert isinstance(self.manager._validation_results, list)
        assert isinstance(self.manager._metrics, ValidationMetrics)

    @pytest.mark.asyncio
    async def test_validate_data_signal_validation(self):
        """Test validating signal data."""
        signal_data = {
            'signal_type': 'buy',
            'confidence': 0.8,
            'strength': 'strong',
            'indicator_name': 'RSI'
        }

        context = {'volatility': 0.3, 'market_regime': 'bull'}

        result = await self.manager.validate_data(ValidationType.SIGNAL_VALIDATION, signal_data, context)

        assert isinstance(result, ValidationResult)
        assert result.validation_type == ValidationType.SIGNAL_VALIDATION

    @pytest.mark.asyncio
    async def test_validate_data_unknown_type(self):
        """Test validating with unknown validation type."""
        data = {'test': 'data'}

        # Create a mock validation type that's not supported
        from enum import Enum
        class MockValidationType(Enum):
            UNKNOWN = "unknown"

        result = await self.manager.validate_data(MockValidationType.UNKNOWN, data)

        assert result.status == ValidationStatus.UNKNOWN
        assert "No validator available" in result.message

    def test_add_validation_rule(self):
        """Test adding a validation rule."""
        rule = ValidationRule(
            rule_id="test_rule",
            name="Test Rule",
            validation_type=ValidationType.SIGNAL_VALIDATION,
            description="Test rule description"
        )

        self.manager.add_validation_rule(rule)
        assert "test_rule" in self.manager._validation_rules

    def test_remove_validation_rule(self):
        """Test removing a validation rule."""
        rule = ValidationRule(
            rule_id="test_rule",
            name="Test Rule",
            validation_type=ValidationType.SIGNAL_VALIDATION,
            description="Test rule description"
        )

        self.manager.add_validation_rule(rule)
        assert self.manager.remove_validation_rule("test_rule") is True
        assert "test_rule" not in self.manager._validation_rules

    def test_get_validation_metrics(self):
        """Test getting validation metrics."""
        metrics = self.manager.get_validation_metrics()
        assert isinstance(metrics, dict)
        assert "total_validations" in metrics
        assert "success_rate" in metrics

    def test_get_recent_validation_results(self):
        """Test getting recent validation results."""
        results = self.manager.get_recent_validation_results()
        assert isinstance(results, list)

    def test_get_validation_rules(self):
        """Test getting validation rules."""
        rules = self.manager.get_validation_rules()
        assert isinstance(rules, dict)
        # Should have default rules
        assert len(rules) > 0


class TestGlobalFunctions:

    @pytest.mark.asyncio
    async def test_validate_signal_global(self):
        """Test global signal validation function."""
        signal_data = {
            'signal_type': 'buy',
            'confidence': 0.8,
            'strength': 'strong',
            'indicator_name': 'RSI'
        }

        result = await validate_signal(signal_data)
        assert isinstance(result, ValidationResult)

    @pytest.mark.asyncio
    async def test_validate_market_data_global(self):
        """Test global market data validation function."""
        data = {
            'symbol': 'AAPL',
            'price': 150.0,
            'volume': 1000000,
            'timestamp': time.time()
        }

        result = await validate_market_data(data)
        assert isinstance(result, ValidationResult)

    @pytest.mark.asyncio
    async def test_validate_system_health_global(self):
        """Test global system health validation function."""
        system_data = {
            'cpu_usage': 50.0,
            'memory_usage': 60.0,
            'disk_usage': 70.0,
            'network_latency': 100.0
        }

        result = await validate_system_health(system_data)
        assert isinstance(result, ValidationResult)

    def test_get_validation_manager(self):
        """Test getting global validation manager."""
        manager = get_validation_manager()
        assert isinstance(manager, ValidationManager)