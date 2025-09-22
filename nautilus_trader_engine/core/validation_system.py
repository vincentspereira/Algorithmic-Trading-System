"""
Real-time Validation System for Institutional-Grade Trading.

This module provides comprehensive real-time validation capabilities for:
- Signal validation and cross-verification
- Market data quality assessment
- System health monitoring
- Risk validation and compliance checking
- Performance validation and anomaly detection
- Automated response and alerting systems

The validation system integrates with the 5-pillar institutional architecture
to provide continuous quality assurance and risk management.
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
from .interfaces import SignalStrength, MarketRegime, RiskLevel
from .event_system import EventBus, get_event_bus, EventType, EventPriority


class ValidationStatus(Enum):
    """Validation status levels."""
    VALID = "valid"
    WARNING = "warning"
    CRITICAL = "critical"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class ValidationType(Enum):
    """Types of validation checks."""
    SIGNAL_VALIDATION = "signal_validation"
    DATA_QUALITY = "data_quality"
    SYSTEM_HEALTH = "system_health"
    RISK_COMPLIANCE = "risk_compliance"
    PERFORMANCE_VALIDATION = "performance_validation"
    MARKET_ANOMALY = "market_anomaly"


@dataclass
class ValidationResult:
    """Result of a validation check."""
    validation_type: ValidationType
    status: ValidationStatus
    confidence: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    validator_id: str = ""
    severity_score: float = 0.0
    recommended_actions: List[str] = field(default_factory=list)


@dataclass
class ValidationRule:
    """Validation rule configuration."""
    rule_id: str
    name: str
    validation_type: ValidationType
    description: str
    enabled: bool = True
    priority: EventPriority = EventPriority.NORMAL
    threshold_warning: float = 0.7
    threshold_critical: float = 0.9
    check_interval: float = 60.0  # seconds
    max_violations: int = 3
    cooldown_period: float = 300.0  # seconds
    last_triggered: Optional[float] = None
    violation_count: int = 0


@dataclass
class ValidationMetrics:
    """Validation system performance metrics."""
    total_validations: int = 0
    validations_passed: int = 0
    validations_failed: int = 0
    average_response_time: float = 0.0
    alerts_generated: int = 0
    rules_triggered: int = 0
    last_validation_time: Optional[float] = None


class Validator(ABC):
    """Abstract base class for validators."""

    @abstractmethod
    async def validate(self, data: Any, context: Dict[str, Any]) -> ValidationResult:
        """Perform validation on the given data."""
        pass

    @property
    @abstractmethod
    def validator_id(self) -> str:
        """Return unique validator identifier."""
        pass

    @property
    @abstractmethod
    def supported_validation_types(self) -> Set[ValidationType]:
        """Return set of supported validation types."""
        pass


@injectable
@singleton
class SignalValidator(Validator):
    """Signal validation and cross-verification."""

    def __init__(self):
        self._signal_history: Dict[str, List[Dict[str, Any]]] = {}
        self._max_history_size = 1000

    @property
    def validator_id(self) -> str:
        return "signal_validator"

    @property
    def supported_validation_types(self) -> Set[ValidationType]:
        return {ValidationType.SIGNAL_VALIDATION}

    async def validate(self, signal_data: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
        """Validate trading signal quality and consistency."""
        signal_type = signal_data.get('signal_type', 'unknown')
        confidence = signal_data.get('confidence', 0.0)
        strength = signal_data.get('strength', 'weak')
        indicator_name = signal_data.get('indicator_name', 'unknown')

        # Cross-validation checks
        issues = []
        severity_score = 0.0

        # 1. Confidence validation
        if confidence < 0.3:
            issues.append("Low confidence signal")
            severity_score += 0.3
        elif confidence > 0.95:
            issues.append("Overly confident signal - possible overfitting")
            severity_score += 0.2

        # 2. Signal consistency check
        consistency_score = await self._check_signal_consistency(signal_data, context)
        if consistency_score < 0.5:
            issues.append("Signal inconsistent with market conditions")
            severity_score += 0.4

        # 3. Historical performance check
        performance_score = await self._check_historical_performance(indicator_name, signal_data)
        if performance_score < 0.4:
            issues.append("Poor historical performance for this indicator")
            severity_score += 0.3

        # 4. Market regime alignment
        regime_alignment = await self._check_market_regime_alignment(signal_data, context)
        if regime_alignment < 0.6:
            issues.append("Signal not aligned with current market regime")
            severity_score += 0.2

        # Determine status
        if severity_score >= 0.8:
            status = ValidationStatus.CRITICAL
        elif severity_score >= 0.5:
            status = ValidationStatus.WARNING
        elif severity_score >= 0.2:
            status = ValidationStatus.VALID
        else:
            status = ValidationStatus.VALID

        # Store signal for future validation
        await self._store_signal_history(signal_data)

        message = "Signal validation " + ("passed" if status == ValidationStatus.VALID else f"failed: {', '.join(issues)}")

        return ValidationResult(
            validation_type=ValidationType.SIGNAL_VALIDATION,
            status=status,
            confidence=max(0.1, 1.0 - severity_score),
            message=message,
            details={
                "signal_type": signal_type,
                "confidence": confidence,
                "strength": strength,
                "consistency_score": consistency_score,
                "performance_score": performance_score,
                "regime_alignment": regime_alignment,
                "issues": issues
            },
            validator_id=self.validator_id,
            severity_score=severity_score,
            recommended_actions=self._generate_recommendations(issues, signal_data)
        )

    async def _check_signal_consistency(self, signal_data: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Check signal consistency with market conditions."""
        volatility = context.get('volatility', 0.5)
        trend_strength = context.get('trend_strength', 0.5)
        signal_type = signal_data.get('signal_type', 'hold')

        consistency = 0.5  # Base consistency

        # Adjust based on market conditions
        if signal_type in ['buy', 'sell']:
            if volatility > 0.8:  # High volatility
                consistency -= 0.2  # Less consistent in high volatility
            if trend_strength > 0.7:  # Strong trend
                consistency += 0.2  # More consistent in strong trends

        return max(0.0, min(1.0, consistency))

    async def _check_historical_performance(self, indicator_name: str, signal_data: Dict[str, Any]) -> float:
        """Check historical performance of the indicator."""
        if indicator_name not in self._signal_history:
            return 0.5  # Neutral score for new indicators

        history = self._signal_history[indicator_name]
        if len(history) < 10:
            return 0.5  # Insufficient history

        # Calculate recent performance
        recent_signals = history[-20:]  # Last 20 signals
        success_rate = sum(1 for s in recent_signals if s.get('success', False)) / len(recent_signals)

        return success_rate

    async def _check_market_regime_alignment(self, signal_data: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Check if signal aligns with current market regime."""
        market_regime = context.get('market_regime', 'sideways')
        signal_type = signal_data.get('signal_type', 'hold')

        alignment = 0.5  # Base alignment

        # Regime-specific alignment
        if market_regime == 'bull' and signal_type == 'buy':
            alignment += 0.3
        elif market_regime == 'bear' and signal_type == 'sell':
            alignment += 0.3
        elif market_regime == 'sideways' and signal_type == 'hold':
            alignment += 0.2
        elif market_regime in ['high_volatility', 'ranging'] and signal_type in ['buy', 'sell']:
            alignment -= 0.2  # Less aligned in volatile/ranging markets

        return max(0.0, min(1.0, alignment))

    async def _store_signal_history(self, signal_data: Dict[str, Any]):
        """Store signal for future validation."""
        indicator_name = signal_data.get('indicator_name', 'unknown')

        if indicator_name not in self._signal_history:
            self._signal_history[indicator_name] = []

        self._signal_history[indicator_name].append({
            **signal_data,
            'timestamp': time.time()
        })

        # Maintain history size
        if len(self._signal_history[indicator_name]) > self._max_history_size:
            self._signal_history[indicator_name].pop(0)

    def _generate_recommendations(self, issues: List[str], signal_data: Dict[str, Any]) -> List[str]:
        """Generate recommended actions based on validation issues."""
        recommendations = []

        for issue in issues:
            if "Low confidence" in issue:
                recommendations.append("Increase signal confirmation requirements")
            elif "inconsistent" in issue:
                recommendations.append("Review signal generation parameters")
            elif "Poor historical performance" in issue:
                recommendations.append("Re-evaluate indicator parameters or replace indicator")
            elif "not aligned" in issue:
                recommendations.append("Adjust signal for current market regime")

        if not recommendations:
            recommendations.append("Signal validation passed - no action required")

        return recommendations


@injectable
@singleton
class DataQualityValidator(Validator):
    """Market data quality and integrity validation."""

    def __init__(self):
        self._data_history: Dict[str, List[Dict[str, Any]]] = {}
        self._anomaly_threshold = 3.0  # Standard deviations

    @property
    def validator_id(self) -> str:
        return "data_quality_validator"

    @property
    def supported_validation_types(self) -> Set[ValidationType]:
        return {ValidationType.DATA_QUALITY, ValidationType.MARKET_ANOMALY}

    async def validate(self, data: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
        """Validate market data quality and detect anomalies."""
        symbol = data.get('symbol', 'unknown')
        price = data.get('price', 0.0)
        volume = data.get('volume', 0.0)
        timestamp = data.get('timestamp', time.time())

        issues = []
        severity_score = 0.0

        # 1. Data staleness check
        age = time.time() - timestamp
        if age > 300:  # 5 minutes
            issues.append(f"Data is {age:.1f} seconds old")
            severity_score += 0.4
        elif age > 60:  # 1 minute
            issues.append(f"Data is {age:.1f} seconds old")
            severity_score += 0.2

        # 2. Price anomaly detection
        price_anomaly = await self._detect_price_anomaly(symbol, price, timestamp)
        if price_anomaly:
            issues.append("Price anomaly detected")
            severity_score += 0.6

        # 3. Volume anomaly detection
        volume_anomaly = await self._detect_volume_anomaly(symbol, volume, timestamp)
        if volume_anomaly:
            issues.append("Volume anomaly detected")
            severity_score += 0.4

        # 4. Data completeness check
        completeness = self._check_data_completeness(data)
        if completeness < 0.8:
            issues.append("Incomplete data fields")
            severity_score += 0.3

        # 5. Cross-market validation
        cross_validation = await self._cross_market_validation(data, context)
        if not cross_validation:
            issues.append("Failed cross-market validation")
            severity_score += 0.5

        # Store data for future validation
        await self._store_data_history(symbol, data)

        # Determine status
        if severity_score >= 0.8:
            status = ValidationStatus.CRITICAL
        elif severity_score >= 0.5:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.VALID

        message = "Data quality validation " + ("passed" if status == ValidationStatus.VALID else f"failed: {', '.join(issues)}")

        return ValidationResult(
            validation_type=ValidationType.DATA_QUALITY,
            status=status,
            confidence=max(0.1, 1.0 - severity_score),
            message=message,
            details={
                "symbol": symbol,
                "price": price,
                "volume": volume,
                "data_age": age,
                "completeness": completeness,
                "price_anomaly": price_anomaly,
                "volume_anomaly": volume_anomaly,
                "issues": issues
            },
            validator_id=self.validator_id,
            severity_score=severity_score,
            recommended_actions=self._generate_data_recommendations(issues, data)
        )

    async def _detect_price_anomaly(self, symbol: str, price: float, timestamp: float) -> bool:
        """Detect price anomalies using statistical methods."""
        if symbol not in self._data_history:
            return False

        history = self._data_history[symbol]
        if len(history) < 20:
            return False

        # Get recent prices
        recent_prices = [h['price'] for h in history[-20:] if 'price' in h]

        if len(recent_prices) < 10:
            return False

        # Calculate statistics
        mean_price = statistics.mean(recent_prices)
        std_price = statistics.stdev(recent_prices)

        if std_price == 0:
            return False

        # Check if current price is an outlier
        z_score = abs(price - mean_price) / std_price
        return z_score > self._anomaly_threshold

    async def _detect_volume_anomaly(self, symbol: str, volume: float, timestamp: float) -> bool:
        """Detect volume anomalies."""
        if symbol not in self._data_history:
            return False

        history = self._data_history[symbol]
        if len(history) < 20:
            return False

        # Get recent volumes
        recent_volumes = [h['volume'] for h in history[-20:] if 'volume' in h]

        if len(recent_volumes) < 10:
            return False

        # Calculate statistics
        mean_volume = statistics.mean(recent_volumes)
        std_volume = statistics.stdev(recent_volumes)

        if std_volume == 0:
            return False

        # Check if current volume is an outlier
        z_score = abs(volume - mean_volume) / std_volume
        return z_score > self._anomaly_threshold

    def _check_data_completeness(self, data: Dict[str, Any]) -> float:
        """Check completeness of data fields."""
        required_fields = ['symbol', 'price', 'volume', 'timestamp']
        optional_fields = ['bid', 'ask', 'open', 'high', 'low', 'close']

        required_present = sum(1 for field in required_fields if field in data and data[field] is not None)
        optional_present = sum(1 for field in optional_fields if field in data and data[field] is not None)

        total_fields = len(required_fields) + len(optional_fields)
        present_fields = required_present + optional_present

        return present_fields / total_fields

    async def _cross_market_validation(self, data: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Perform cross-market validation."""
        # This would validate data against multiple data sources
        # For now, return True as a placeholder
        return True

    async def _store_data_history(self, symbol: str, data: Dict[str, Any]):
        """Store data for future validation."""
        if symbol not in self._data_history:
            self._data_history[symbol] = []

        self._data_history[symbol].append({
            **data,
            'validation_timestamp': time.time()
        })

        # Maintain history size per symbol
        if len(self._data_history[symbol]) > 1000:
            self._data_history[symbol].pop(0)

    def _generate_data_recommendations(self, issues: List[str], data: Dict[str, Any]) -> List[str]:
        """Generate recommendations for data quality issues."""
        recommendations = []

        for issue in issues:
            if "old" in issue.lower():
                recommendations.append("Check data feed connectivity and refresh rate")
            elif "anomaly" in issue.lower():
                recommendations.append("Verify data source integrity and check for market events")
            elif "incomplete" in issue.lower():
                recommendations.append("Review data feed configuration and field mappings")
            elif "cross-market" in issue.lower():
                recommendations.append("Compare data with alternative sources for validation")

        if not recommendations:
            recommendations.append("Data quality validation passed - no action required")

        return recommendations


@injectable
@singleton
class SystemHealthValidator(Validator):
    """System health and performance validation."""

    def __init__(self):
        self._performance_history: List[Dict[str, Any]] = []
        self._error_history: List[Dict[str, Any]] = []
        self._resource_thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'network_latency': 1000.0  # ms
        }

    @property
    def validator_id(self) -> str:
        return "system_health_validator"

    @property
    def supported_validation_types(self) -> Set[ValidationType]:
        return {ValidationType.SYSTEM_HEALTH}

    async def validate(self, system_data: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
        """Validate system health and performance."""
        cpu_usage = system_data.get('cpu_usage', 0.0)
        memory_usage = system_data.get('memory_usage', 0.0)
        disk_usage = system_data.get('disk_usage', 0.0)
        network_latency = system_data.get('network_latency', 0.0)
        active_connections = system_data.get('active_connections', 0)
        queue_size = system_data.get('queue_size', 0)

        issues = []
        severity_score = 0.0

        # 1. Resource usage validation
        if cpu_usage > self._resource_thresholds['cpu_usage']:
            issues.append(f"High CPU usage: {cpu_usage:.1f}%")
            severity_score += 0.4

        if memory_usage > self._resource_thresholds['memory_usage']:
            issues.append(f"High memory usage: {memory_usage:.1f}%")
            severity_score += 0.5

        if disk_usage > self._resource_thresholds['disk_usage']:
            issues.append(f"High disk usage: {disk_usage:.1f}%")
            severity_score += 0.3

        # 2. Network performance
        if network_latency > self._resource_thresholds['network_latency']:
            issues.append(f"High network latency: {network_latency:.1f}ms")
            severity_score += 0.4

        # 3. System load
        if active_connections > 1000:
            issues.append(f"High connection count: {active_connections}")
            severity_score += 0.2

        if queue_size > 10000:
            issues.append(f"Large processing queue: {queue_size}")
            severity_score += 0.3

        # 4. Error rate analysis
        error_rate = await self._calculate_error_rate()
        if error_rate > 0.05:  # 5% error rate
            issues.append(f"High error rate: {error_rate:.2%}")
            severity_score += 0.6
        elif error_rate > 0.01:  # 1% error rate
            issues.append(f"Elevated error rate: {error_rate:.2%}")
            severity_score += 0.2

        # 5. Performance degradation
        performance_score = await self._check_performance_degradation()
        if performance_score < 0.7:
            issues.append("Performance degradation detected")
            severity_score += 0.4

        # Store system metrics
        await self._store_system_metrics(system_data)

        # Determine status
        if severity_score >= 0.8:
            status = ValidationStatus.CRITICAL
        elif severity_score >= 0.5:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.VALID

        message = "System health validation " + ("passed" if status == ValidationStatus.VALID else f"failed: {', '.join(issues)}")

        return ValidationResult(
            validation_type=ValidationType.SYSTEM_HEALTH,
            status=status,
            confidence=max(0.1, 1.0 - severity_score),
            message=message,
            details={
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "disk_usage": disk_usage,
                "network_latency": network_latency,
                "active_connections": active_connections,
                "queue_size": queue_size,
                "error_rate": error_rate,
                "performance_score": performance_score,
                "issues": issues
            },
            validator_id=self.validator_id,
            severity_score=severity_score,
            recommended_actions=self._generate_health_recommendations(issues, system_data)
        )

    async def _calculate_error_rate(self) -> float:
        """Calculate recent error rate."""
        if len(self._error_history) < 10:
            return 0.0

        # Calculate error rate over last hour
        one_hour_ago = time.time() - 3600
        recent_errors = [e for e in self._error_history if e['timestamp'] > one_hour_ago]
        total_events = len(self._performance_history)

        if total_events == 0:
            return 0.0

        return len(recent_errors) / total_events

    async def _check_performance_degradation(self) -> float:
        """Check for performance degradation trends."""
        if len(self._performance_history) < 20:
            return 1.0  # Assume good performance with insufficient data

        # Compare recent performance with historical average
        recent_metrics = self._performance_history[-10:]
        historical_metrics = self._performance_history[:-10]

        if not historical_metrics:
            return 1.0

        # Calculate average response times
        recent_avg = statistics.mean(m['response_time'] for m in recent_metrics if 'response_time' in m)
        historical_avg = statistics.mean(m['response_time'] for m in historical_metrics if 'response_time' in m)

        # Performance score (higher is better)
        if historical_avg == 0:
            return 1.0

        degradation_ratio = recent_avg / historical_avg
        return max(0.0, min(1.0, 2.0 - degradation_ratio))  # Score between 0 and 1

    async def _store_system_metrics(self, system_data: Dict[str, Any]):
        """Store system metrics for trend analysis."""
        self._performance_history.append({
            **system_data,
            'timestamp': time.time()
        })

        # Maintain history size
        if len(self._performance_history) > 1000:
            self._performance_history.pop(0)

    def _generate_health_recommendations(self, issues: List[str], system_data: Dict[str, Any]) -> List[str]:
        """Generate recommendations for system health issues."""
        recommendations = []

        for issue in issues:
            if "cpu" in issue.lower():
                recommendations.append("Optimize CPU-intensive operations or scale horizontally")
            elif "memory" in issue.lower():
                recommendations.append("Review memory usage patterns and implement garbage collection")
            elif "disk" in issue.lower():
                recommendations.append("Clean up old data and optimize storage usage")
            elif "network" in issue.lower():
                recommendations.append("Check network connectivity and consider CDN optimization")
            elif "connection" in issue.lower():
                recommendations.append("Implement connection pooling and rate limiting")
            elif "queue" in issue.lower():
                recommendations.append("Scale processing capacity or optimize queue management")
            elif "error rate" in issue.lower():
                recommendations.append("Review error handling and implement circuit breakers")
            elif "performance" in issue.lower():
                recommendations.append("Profile application and optimize bottlenecks")

        if not recommendations:
            recommendations.append("System health validation passed - no action required")

        return recommendations


@injectable
@singleton
class ValidationManager:
    """
    Real-time Validation Manager for Institutional-Grade Trading.

    Features:
    - Multi-validator orchestration
    - Real-time validation pipelines
    - Automated alerting and response
    - Performance monitoring and optimization
    - Rule-based validation engine
    - Historical validation tracking
    """

    def __init__(self, container: Optional[DependencyInjectionContainer] = None):
        self._container = container or get_container()
        self._event_bus = get_event_bus()
        self._validators: Dict[str, Validator] = {}
        self._validation_rules: Dict[str, ValidationRule] = {}
        self._validation_results: List[ValidationResult] = []
        self._metrics = ValidationMetrics()
        self._lock = asyncio.Lock()

        # Initialize validators
        self._initialize_validators()

        # Initialize default rules
        self._initialize_default_rules()

    def _initialize_validators(self):
        """Initialize validation components."""
        try:
            self._validators = {
                'signal': self._container.get_service(SignalValidator),
                'data_quality': self._container.get_service(DataQualityValidator),
                'system_health': self._container.get_service(SystemHealthValidator)
            }
        except Exception as e:
            logger.warning(f"Failed to initialize some validators: {e}")

    def _initialize_default_rules(self):
        """Initialize default validation rules."""
        default_rules = [
            ValidationRule(
                rule_id="signal_confidence_check",
                name="Signal Confidence Validation",
                validation_type=ValidationType.SIGNAL_VALIDATION,
                description="Validate signal confidence levels",
                threshold_warning=0.6,
                threshold_critical=0.3
            ),
            ValidationRule(
                rule_id="data_staleness_check",
                name="Data Staleness Validation",
                validation_type=ValidationType.DATA_QUALITY,
                description="Check for stale market data",
                threshold_warning=120.0,  # 2 minutes
                threshold_critical=300.0  # 5 minutes
            ),
            ValidationRule(
                rule_id="system_resource_check",
                name="System Resource Validation",
                validation_type=ValidationType.SYSTEM_HEALTH,
                description="Monitor system resource usage",
                threshold_warning=75.0,
                threshold_critical=90.0
            ),
            ValidationRule(
                rule_id="error_rate_check",
                name="Error Rate Validation",
                validation_type=ValidationType.SYSTEM_HEALTH,
                description="Monitor system error rates",
                threshold_warning=0.02,  # 2%
                threshold_critical=0.05  # 5%
            )
        ]

        for rule in default_rules:
            self._validation_rules[rule.rule_id] = rule

    async def validate_data(self, validation_type: ValidationType, data: Any,
                           context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Perform validation on the given data.

        Args:
            validation_type: Type of validation to perform
            data: Data to validate
            context: Additional context for validation

        Returns:
            Validation result
        """
        if context is None:
            context = {}

        start_time = time.time()

        try:
            # Find appropriate validator
            validator = None
            for v in self._validators.values():
                if validation_type in v.supported_validation_types:
                    validator = v
                    break

            if not validator:
                return ValidationResult(
                    validation_type=validation_type,
                    status=ValidationStatus.UNKNOWN,
                    confidence=0.0,
                    message=f"No validator available for {validation_type.value}",
                    validator_id="validation_manager"
                )

            # Perform validation
            result = await validator.validate(data, context)

            # Update metrics
            async with self._lock:
                self._metrics.total_validations += 1
                if result.status == ValidationStatus.VALID:
                    self._metrics.validations_passed += 1
                else:
                    self._metrics.validations_failed += 1

                response_time = time.time() - start_time
                self._metrics.average_response_time = (
                    (self._metrics.average_response_time * (self._metrics.total_validations - 1)) +
                    response_time
                ) / self._metrics.total_validations

                self._metrics.last_validation_time = time.time()

            # Store result
            async with self._lock:
                self._validation_results.append(result)
                if len(self._validation_results) > 10000:
                    self._validation_results.pop(0)

            # Check rules and generate alerts
            await self._check_validation_rules(result)

            # Publish validation event
            await self._publish_validation_event(result)

            return result

        except Exception as e:
            logger.error(f"Validation error: {e}")
            async with self._lock:
                self._metrics.validations_failed += 1

            return ValidationResult(
                validation_type=validation_type,
                status=ValidationStatus.INVALID,
                confidence=0.0,
                message=f"Validation failed: {str(e)}",
                validator_id="validation_manager",
                severity_score=1.0
            )

    async def _check_validation_rules(self, result: ValidationResult):
        """Check validation rules and trigger alerts if needed."""
        current_time = time.time()

        for rule in self._validation_rules.values():
            if not rule.enabled or rule.validation_type != result.validation_type:
                continue

            # Check cooldown period
            if (rule.last_triggered and
                current_time - rule.last_triggered < rule.cooldown_period):
                continue

            # Check if rule conditions are met
            should_trigger = False

            if result.status == ValidationStatus.CRITICAL:
                should_trigger = True
            elif result.status == ValidationStatus.WARNING:
                should_trigger = result.severity_score >= rule.threshold_warning
            elif result.severity_score >= rule.threshold_critical:
                should_trigger = True

            if should_trigger:
                rule.violation_count += 1
                rule.last_triggered = current_time

                # Generate alert
                await self._generate_alert(rule, result)

                async with self._lock:
                    self._metrics.alerts_generated += 1
                    self._metrics.rules_triggered += 1

    async def _generate_alert(self, rule: ValidationRule, result: ValidationResult):
        """Generate an alert for rule violation."""
        alert_data = {
            "alert_type": "validation_rule_violation",
            "rule_id": rule.rule_id,
            "rule_name": rule.name,
            "validation_type": result.validation_type.value,
            "severity": result.status.value,
            "message": result.message,
            "details": result.details,
            "recommended_actions": result.recommended_actions,
            "violation_count": rule.violation_count,
            "timestamp": time.time()
        }

        # Publish alert event
        await self._event_bus.publish_event(
            self._event_bus.create_event(
                EventType.ERROR_OCCURRED,
                "validation_system",
                alert_data,
                EventPriority.HIGH if result.status == ValidationStatus.CRITICAL else EventPriority.NORMAL
            )
        )

        logger.warning(f"Validation alert: {rule.name} - {result.message}")

    async def _publish_validation_event(self, result: ValidationResult):
        """Publish validation result event."""
        event_data = {
            "validation_type": result.validation_type.value,
            "status": result.status.value,
            "confidence": result.confidence,
            "message": result.message,
            "details": result.details,
            "validator_id": result.validator_id,
            "severity_score": result.severity_score
        }

        await self._event_bus.publish_event(
            self._event_bus.create_event(
                EventType.SYSTEM_HEALTH_CHANGED,
                "validation_system",
                event_data,
                EventPriority.LOW
            )
        )

    def add_validation_rule(self, rule: ValidationRule):
        """Add a new validation rule."""
        self._validation_rules[rule.rule_id] = rule
        logger.info(f"Added validation rule: {rule.name}")

    def remove_validation_rule(self, rule_id: str) -> bool:
        """Remove a validation rule."""
        if rule_id in self._validation_rules:
            del self._validation_rules[rule_id]
            logger.info(f"Removed validation rule: {rule_id}")
            return True
        return False

    def get_validation_metrics(self) -> Dict[str, Any]:
        """Get validation system metrics."""
        async with self._lock:
            return {
                "total_validations": self._metrics.total_validations,
                "validations_passed": self._metrics.validations_passed,
                "validations_failed": self._metrics.validations_failed,
                "success_rate": (
                    self._metrics.validations_passed / self._metrics.total_validations
                    if self._metrics.total_validations > 0 else 0
                ),
                "average_response_time": self._metrics.average_response_time,
                "alerts_generated": self._metrics.alerts_generated,
                "rules_triggered": self._metrics.rules_triggered,
                "active_rules": len([r for r in self._validation_rules.values() if r.enabled]),
                "last_validation_time": self._metrics.last_validation_time
            }

    def get_recent_validation_results(self, limit: int = 100) -> List[ValidationResult]:
        """Get recent validation results."""
        async with self._lock:
            return self._validation_results[-limit:]

    def get_validation_rules(self) -> Dict[str, ValidationRule]:
        """Get all validation rules."""
        return self._validation_rules.copy()


# Global validation manager instance
_validation_manager = ValidationManager()


def get_validation_manager() -> ValidationManager:
    """Get the global validation manager."""
    return _validation_manager


# Convenience functions
async def validate_signal(signal_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ValidationResult:
    """Validate a trading signal."""
    return await _validation_manager.validate_data(ValidationType.SIGNAL_VALIDATION, signal_data, context)


async def validate_market_data(data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ValidationResult:
    """Validate market data quality."""
    return await _validation_manager.validate_data(ValidationType.DATA_QUALITY, data, context)


async def validate_system_health(system_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> ValidationResult:
    """Validate system health."""
    return await _validation_manager.validate_data(ValidationType.SYSTEM_HEALTH, system_data, context)