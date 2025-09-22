"""
Real-time Validation System for Technical Indicators
Provides continuous validation of indicator signals and data quality monitoring.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Callable, Tuple, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod
from scipy import stats
import time
from collections import deque
from threading import Lock
import asyncio

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Levels of validation severity."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationType(Enum):
    """Types of validation checks."""
    DATA_QUALITY = "data_quality"
    SIGNAL_CONSISTENCY = "signal_consistency"
    STATISTICAL_ANOMALY = "statistical_anomaly"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    CROSS_VALIDATION = "cross_validation"


@dataclass
class ValidationResult:
    """Result of a validation check."""
    validation_type: ValidationType
    level: ValidationLevel
    message: str
    indicator_name: str
    value: Any
    expected_value: Any = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationRule:
    """A validation rule with conditions and actions."""
    name: str
    validation_type: ValidationType
    condition: Callable[[Any, Dict[str, Any]], bool]
    level: ValidationLevel
    message_template: str
    enabled: bool = True
    cooldown_period: float = 60.0  # seconds
    last_triggered: float = 0


@dataclass
class IndicatorMetrics:
    """Metrics for tracking indicator performance."""
    indicator_name: str
    signal_history: deque = field(default_factory=lambda: deque(maxlen=1000))
    validation_history: List[ValidationResult] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)

    def add_signal(self, signal_value: float, timestamp: float) -> None:
        """Add a signal to the history."""
        self.signal_history.append((timestamp, signal_value))
        self.last_updated = timestamp

    def get_recent_signals(self, window_seconds: float = 300) -> List[Tuple[float, float]]:
        """Get signals within the recent time window."""
        current_time = time.time()
        return [(t, v) for t, v in self.signal_history if current_time - t <= window_seconds]


class ValidationEngine:
    """
    Real-time validation engine for indicator signals.
    """

    def __init__(self, max_history_size: int = 10000):
        self.rules: Dict[str, ValidationRule] = {}
        self.indicator_metrics: Dict[str, IndicatorMetrics] = {}
        self.validation_results: deque = deque(maxlen=max_history_size)
        self._lock = Lock()
        self._running = False
        self._validation_task: Optional[asyncio.Task] = None

    def add_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule."""
        with self._lock:
            self.rules[rule.name] = rule
            logger.info(f"Added validation rule: {rule.name}")

    def remove_rule(self, rule_name: str) -> None:
        """Remove a validation rule."""
        with self._lock:
            if rule_name in self.rules:
                del self.rules[rule_name]
                logger.info(f"Removed validation rule: {rule_name}")

    def validate_signal(self, indicator_name: str, signal_value: Any,
                       context: Optional[Dict[str, Any]] = None) -> List[ValidationResult]:
        """Validate a signal against all applicable rules."""
        context = context or {}
        results = []

        # Get or create metrics for this indicator
        if indicator_name not in self.indicator_metrics:
            self.indicator_metrics[indicator_name] = IndicatorMetrics(indicator_name)

        metrics = self.indicator_metrics[indicator_name]

        # Add signal to history
        timestamp = time.time()
        if isinstance(signal_value, (int, float)):
            metrics.add_signal(float(signal_value), timestamp)

        # Apply all rules
        for rule in self.rules.values():
            if not rule.enabled:
                continue

            # Check cooldown period
            if timestamp - rule.last_triggered < rule.cooldown_period:
                continue

            try:
                if rule.condition(signal_value, {**context, "metrics": metrics}):
                    result = ValidationResult(
                        validation_type=rule.validation_type,
                        level=rule.level,
                        message=rule.message_template.format(
                            indicator=indicator_name,
                            value=signal_value,
                            expected=getattr(rule, 'expected_value', 'N/A')
                        ),
                        indicator_name=indicator_name,
                        value=signal_value,
                        timestamp=timestamp
                    )
                    results.append(result)
                    rule.last_triggered = timestamp

            except Exception as e:
                logger.error(f"Error applying validation rule {rule.name}: {e}")

        # Store results
        with self._lock:
            self.validation_results.extend(results)

        return results

    def get_validation_summary(self, indicator_name: Optional[str] = None,
                             time_window: float = 3600) -> Dict[str, Any]:
        """Get a summary of validation results."""
        current_time = time.time()
        cutoff_time = current_time - time_window

        # Filter results
        relevant_results = [
            r for r in self.validation_results
            if r.timestamp >= cutoff_time and
            (indicator_name is None or r.indicator_name == indicator_name)
        ]

        # Count by level
        level_counts = {}
        for level in ValidationLevel:
            level_counts[level.value] = sum(1 for r in relevant_results if r.level == level)

        # Count by type
        type_counts = {}
        for vtype in ValidationType:
            type_counts[vtype.value] = sum(1 for r in relevant_results if r.validation_type == vtype)

        return {
            "total_validations": len(relevant_results),
            "level_counts": level_counts,
            "type_counts": type_counts,
            "time_window_seconds": time_window,
            "indicators_checked": len(set(r.indicator_name for r in relevant_results))
        }

    def get_indicator_health_score(self, indicator_name: str) -> float:
        """Calculate a health score for an indicator (0-100)."""
        if indicator_name not in self.indicator_metrics:
            return 100.0  # No data means healthy

        metrics = self.indicator_metrics[indicator_name]

        # Get recent validations (last hour)
        recent_results = [
            r for r in self.validation_results
            if r.indicator_name == indicator_name and
            time.time() - r.timestamp <= 3600
        ]

        if not recent_results:
            return 100.0

        # Calculate score based on validation levels
        error_weight = 20
        warning_weight = 5
        info_weight = 1

        total_penalty = 0
        for result in recent_results:
            if result.level == ValidationLevel.CRITICAL:
                total_penalty += error_weight * 3
            elif result.level == ValidationLevel.ERROR:
                total_penalty += error_weight * 2
            elif result.level == ValidationLevel.WARNING:
                total_penalty += warning_weight
            elif result.level == ValidationLevel.INFO:
                total_penalty += info_weight

        # Normalize to 0-100 scale
        health_score = max(0, 100 - total_penalty)
        return health_score


class DataQualityValidator:
    """Validator for data quality issues."""

    def __init__(self):
        self.nan_threshold = 0.05  # 5% NaN values
        self.outlier_threshold = 3.0  # 3 standard deviations

    def validate_data_quality(self, data: pd.DataFrame,
                            indicator_name: str) -> List[ValidationResult]:
        """Validate data quality."""
        results = []

        # Check for NaN values
        nan_ratio = data.isnull().sum().sum() / (data.shape[0] * data.shape[1])
        if nan_ratio > self.nan_threshold:
            results.append(ValidationResult(
                validation_type=ValidationType.DATA_QUALITY,
                level=ValidationLevel.WARNING,
                message=f"High NaN ratio in {indicator_name}: {nan_ratio:.2%}",
                indicator_name=indicator_name,
                value=nan_ratio,
                expected_value=f"< {self.nan_threshold:.2%}"
            ))

        # Check for outliers in numeric columns
        for column in data.select_dtypes(include=[np.number]).columns:
            series = data[column].dropna()
            if len(series) > 10:
                z_scores = np.abs(stats.zscore(series))
                outlier_count = (z_scores > self.outlier_threshold).sum()
                outlier_ratio = outlier_count / len(series)

                if outlier_ratio > 0.1:  # More than 10% outliers
                    results.append(ValidationResult(
                        validation_type=ValidationType.DATA_QUALITY,
                        level=ValidationLevel.WARNING,
                        message=f"High outlier ratio in {indicator_name}.{column}: {outlier_ratio:.2%}",
                        indicator_name=indicator_name,
                        value=outlier_ratio,
                        expected_value="< 10%"
                    ))

        return results


class SignalConsistencyValidator:
    """Validator for signal consistency."""

    def __init__(self):
        self.consistency_window = 50  # Check last 50 signals
        self.max_change_threshold = 2.0  # Maximum allowed change

    def validate_signal_consistency(self, signal_value: float,
                                  metrics: IndicatorMetrics) -> List[ValidationResult]:
        """Validate signal consistency."""
        results = []

        recent_signals = list(metrics.signal_history)[-self.consistency_window:]
        if len(recent_signals) < 10:
            return results

        values = [v for _, v in recent_signals]

        # Check for sudden jumps
        if len(values) >= 2:
            last_value = values[-2]
            change = abs(signal_value - last_value)
            max_historical_change = np.std(values) * 2

            if change > max_historical_change * self.max_change_threshold:
                results.append(ValidationResult(
                    validation_type=ValidationType.SIGNAL_CONSISTENCY,
                    level=ValidationLevel.WARNING,
                    message=f"Sudden signal jump in {metrics.indicator_name}: {change:.4f}",
                    indicator_name=metrics.indicator_name,
                    value=signal_value,
                    expected_value=f"within {max_historical_change * self.max_change_threshold:.4f} of {last_value:.4f}"
                ))

        # Check for signal oscillation
        if len(values) >= 20:
            # Calculate autocorrelation to detect oscillation
            autocorr = np.correlate(values - np.mean(values), values - np.mean(values), mode='full')
            autocorr = autocorr[autocorr.size // 2:]  # Get positive lags
            autocorr = autocorr / autocorr[0]  # Normalize

            # High autocorrelation at lag 2 might indicate oscillation
            if len(autocorr) > 2 and autocorr[2] > 0.8:
                results.append(ValidationResult(
                    validation_type=ValidationType.SIGNAL_CONSISTENCY,
                    level=ValidationLevel.INFO,
                    message=f"Potential signal oscillation in {metrics.indicator_name}",
                    indicator_name=metrics.indicator_name,
                    value=autocorr[2]
                ))

        return results


class StatisticalAnomalyValidator:
    """Validator for statistical anomalies."""

    def __init__(self):
        self.anomaly_threshold = 3.0  # Standard deviations
        self.min_samples = 30

    def validate_statistical_anomaly(self, signal_value: float,
                                   metrics: IndicatorMetrics) -> List[ValidationResult]:
        """Validate for statistical anomalies."""
        results = []

        recent_signals = list(metrics.signal_history)
        if len(recent_signals) < self.min_samples:
            return results

        values = [v for _, v in recent_signals]
        mean_val = np.mean(values)
        std_val = np.std(values)

        if std_val > 0:
            z_score = abs(signal_value - mean_val) / std_val

            if z_score > self.anomaly_threshold:
                results.append(ValidationResult(
                    validation_type=ValidationType.STATISTICAL_ANOMALY,
                    level=ValidationLevel.WARNING,
                    message=f"Statistical anomaly in {metrics.indicator_name}: z-score = {z_score:.2f}",
                    indicator_name=metrics.indicator_name,
                    value=signal_value,
                    expected_value=f"within {self.anomaly_threshold} std of {mean_val:.4f}"
                ))

        return results


class PerformanceDegradationValidator:
    """Validator for performance degradation."""

    def __init__(self):
        self.performance_window = 100
        self.degradation_threshold = 0.2  # 20% degradation

    def validate_performance_degradation(self, current_performance: float,
                                       metrics: IndicatorMetrics) -> List[ValidationResult]:
        """Validate for performance degradation."""
        results = []

        if "performance_history" not in metrics.performance_metrics:
            metrics.performance_metrics["performance_history"] = []

        perf_history = metrics.performance_metrics["performance_history"]
        perf_history.append(current_performance)

        # Keep only recent history
        if len(perf_history) > self.performance_window:
            perf_history.pop(0)

        if len(perf_history) >= 20:
            recent_avg = np.mean(perf_history[-10:])
            overall_avg = np.mean(perf_history)

            if recent_avg < overall_avg * (1 - self.degradation_threshold):
                degradation_pct = (overall_avg - recent_avg) / overall_avg * 100
                results.append(ValidationResult(
                    validation_type=ValidationType.PERFORMANCE_DEGRADATION,
                    level=ValidationLevel.ERROR,
                    message=f"Performance degradation in {metrics.indicator_name}: {degradation_pct:.1f}%",
                    indicator_name=metrics.indicator_name,
                    value=recent_avg,
                    expected_value=f"> {overall_avg * (1 - self.degradation_threshold):.4f}"
                ))

        return results


# Global validation engine instance
_validation_engine = ValidationEngine()


def get_validation_engine() -> ValidationEngine:
    """Get the global validation engine."""
    return _validation_engine


# Convenience functions
def validate_indicator_signal(indicator_name: str, signal_value: Any,
                            context: Optional[Dict[str, Any]] = None) -> List[ValidationResult]:
    """Validate an indicator signal globally."""
    return _validation_engine.validate_signal(indicator_name, signal_value, context)


def get_indicator_health_score(indicator_name: str) -> float:
    """Get health score for an indicator globally."""
    return _validation_engine.get_indicator_health_score(indicator_name)


def setup_default_validation_rules():
    """Set up default validation rules."""
    engine = get_validation_engine()

    # Data quality rules
    data_validator = DataQualityValidator()

    # Signal consistency rules
    consistency_validator = SignalConsistencyValidator()

    # Statistical anomaly rules
    anomaly_validator = StatisticalAnomalyValidator()

    # Performance degradation rules
    performance_validator = PerformanceDegradationValidator()

    # Add rules
    engine.add_rule(ValidationRule(
        name="nan_check",
        validation_type=ValidationType.DATA_QUALITY,
        condition=lambda value, context: isinstance(value, (int, float)) and np.isnan(value),
        level=ValidationLevel.ERROR,
        message_template="NaN value detected in {indicator}: {value}"
    ))

    engine.add_rule(ValidationRule(
        name="infinite_check",
        validation_type=ValidationType.DATA_QUALITY,
        condition=lambda value, context: isinstance(value, (int, float)) and not np.isfinite(value),
        level=ValidationLevel.ERROR,
        message_template="Infinite value detected in {indicator}: {value}"
    ))

    engine.add_rule(ValidationRule(
        name="signal_consistency",
        validation_type=ValidationType.SIGNAL_CONSISTENCY,
        condition=lambda value, context: bool(consistency_validator.validate_signal_consistency(value, context.get("metrics", IndicatorMetrics("")))),
        level=ValidationLevel.WARNING,
        message_template="Signal consistency issue in {indicator}"
    ))

    engine.add_rule(ValidationRule(
        name="statistical_anomaly",
        validation_type=ValidationType.STATISTICAL_ANOMALY,
        condition=lambda value, context: bool(anomaly_validator.validate_statistical_anomaly(value, context.get("metrics", IndicatorMetrics("")))),
        level=ValidationLevel.WARNING,
        message_template="Statistical anomaly detected in {indicator}"
    ))


if __name__ == "__main__":
    # Setup default rules
    setup_default_validation_rules()

    # Example usage
    engine = get_validation_engine()

    # Simulate some signals
    for i in range(100):
        signal_value = np.random.normal(0, 1)
        if i == 50:  # Inject an anomaly
            signal_value = 10.0

        results = validate_indicator_signal("test_indicator", signal_value)
        for result in results:
            print(f"[{result.level.value.upper()}] {result.message}")

    # Get health score
    health_score = get_indicator_health_score("test_indicator")
    print(f"Indicator health score: {health_score:.1f}")

    # Get validation summary
    summary = engine.get_validation_summary()
    print(f"Validation summary: {summary}")