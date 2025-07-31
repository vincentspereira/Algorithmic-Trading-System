"""
Intelligent Alerting System
Advanced alerting with anomaly detection, root cause analysis automation,
alert correlation and deduplication, and actionable alert recommendations.
"""

import asyncio
import logging
import time
import json
import hashlib
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import statistics
import threading
from abc import ABC, abstractmethod

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    stats = None


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AlertCategory(Enum):
    """Alert categories"""
    PERFORMANCE = "performance"
    SYSTEM = "system"
    BUSINESS = "business"
    SECURITY = "security"
    TRADING = "trading"
    RISK = "risk"


class AnomalyType(Enum):
    """Types of anomalies"""
    THRESHOLD = "threshold"
    STATISTICAL = "statistical"
    TREND = "trend"
    SEASONAL = "seasonal"
    CORRELATION = "correlation"


@dataclass
class MetricData:
    """Metric data point"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Alert information"""
    alert_id: str
    title: str
    description: str
    severity: AlertSeverity
    category: AlertCategory
    source: str
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    
    # Status
    status: AlertStatus = AlertStatus.ACTIVE
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    
    # Context
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    tags: Dict[str, str] = field(default_factory=dict)
    
    # Analysis
    anomaly_type: Optional[AnomalyType] = None
    confidence_score: float = 0.0
    root_causes: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Correlation
    related_alerts: List[str] = field(default_factory=list)
    correlation_score: float = 0.0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertRule:
    """Alert rule configuration"""
    rule_id: str
    name: str
    description: str
    metric_name: str
    condition: str  # e.g., "> 100", "< 0.5", "anomaly"
    severity: AlertSeverity
    category: AlertCategory
    
    # Thresholds
    threshold_value: Optional[float] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    
    # Timing
    evaluation_window: timedelta = timedelta(minutes=5)
    cooldown_period: timedelta = timedelta(minutes=15)
    
    # Filtering
    tags_filter: Dict[str, str] = field(default_factory=dict)
    
    # Configuration
    enabled: bool = True
    suppress_duplicates: bool = True
    auto_resolve: bool = False
    auto_resolve_timeout: timedelta = timedelta(hours=1)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class AnomalyDetector(ABC):
    """Abstract base class for anomaly detection algorithms"""
    
    @abstractmethod
    async def detect_anomaly(self, metric_data: List[MetricData]) -> Tuple[bool, float, str]:
        """
        Detect anomaly in metric data
        Returns: (is_anomaly, confidence_score, description)
        """
        pass


class ThresholdAnomalyDetector(AnomalyDetector):
    """Simple threshold-based anomaly detection"""
    
    def __init__(self, threshold: float, operator: str = ">"):
        self.threshold = threshold
        self.operator = operator
    
    async def detect_anomaly(self, metric_data: List[MetricData]) -> Tuple[bool, float, str]:
        """Detect threshold violations"""
        if not metric_data:
            return False, 0.0, "No data available"
        
        latest_value = metric_data[-1].value
        
        if self.operator == ">":
            is_anomaly = latest_value > self.threshold
            description = f"Value {latest_value} exceeds threshold {self.threshold}"
        elif self.operator == "<":
            is_anomaly = latest_value < self.threshold
            description = f"Value {latest_value} below threshold {self.threshold}"
        elif self.operator == ">=":
            is_anomaly = latest_value >= self.threshold
            description = f"Value {latest_value} at or above threshold {self.threshold}"
        elif self.operator == "<=":
            is_anomaly = latest_value <= self.threshold
            description = f"Value {latest_value} at or below threshold {self.threshold}"
        else:
            return False, 0.0, f"Unknown operator: {self.operator}"
        
        confidence = 1.0 if is_anomaly else 0.0
        return is_anomaly, confidence, description


class StatisticalAnomalyDetector(AnomalyDetector):
    """Statistical anomaly detection using z-score"""
    
    def __init__(self, z_threshold: float = 3.0, min_samples: int = 10):
        self.z_threshold = z_threshold
        self.min_samples = min_samples
    
    async def detect_anomaly(self, metric_data: List[MetricData]) -> Tuple[bool, float, str]:
        """Detect statistical anomalies using z-score"""
        if len(metric_data) < self.min_samples:
            return False, 0.0, f"Insufficient data: {len(metric_data)} < {self.min_samples}"
        
        values = [data.value for data in metric_data]
        latest_value = values[-1]
        
        # Calculate z-score
        if NUMPY_AVAILABLE:
            mean = np.mean(values[:-1])  # Exclude latest value from baseline
            std = np.std(values[:-1])
        else:
            mean = statistics.mean(values[:-1])
            std = statistics.stdev(values[:-1]) if len(values) > 2 else 0
        
        if std == 0:
            return False, 0.0, "Zero standard deviation"
        
        z_score = abs(latest_value - mean) / std
        is_anomaly = z_score > self.z_threshold
        confidence = min(z_score / self.z_threshold, 1.0) if is_anomaly else 0.0
        
        description = f"Z-score {z_score:.2f} {'exceeds' if is_anomaly else 'within'} threshold {self.z_threshold}"
        
        return is_anomaly, confidence, description


class TrendAnomalyDetector(AnomalyDetector):
    """Trend-based anomaly detection"""
    
    def __init__(self, trend_threshold: float = 0.1, min_samples: int = 5):
        self.trend_threshold = trend_threshold  # Minimum trend slope to consider anomalous
        self.min_samples = min_samples
    
    async def detect_anomaly(self, metric_data: List[MetricData]) -> Tuple[bool, float, str]:
        """Detect trend anomalies"""
        if len(metric_data) < self.min_samples:
            return False, 0.0, f"Insufficient data for trend analysis: {len(metric_data)}"
        
        # Calculate trend using linear regression
        values = [data.value for data in metric_data]
        x = list(range(len(values)))
        
        if NUMPY_AVAILABLE:
            # Use numpy for more accurate calculation
            slope, intercept = np.polyfit(x, values, 1)
            r_squared = np.corrcoef(x, values)[0, 1] ** 2
        else:
            # Simple linear regression
            n = len(values)
            sum_x = sum(x)
            sum_y = sum(values)
            sum_xy = sum(x[i] * values[i] for i in range(n))
            sum_x2 = sum(xi ** 2 for xi in x)
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
            r_squared = 0.5  # Rough estimate
        
        # Normalize slope by value range
        value_range = max(values) - min(values)
        normalized_slope = abs(slope) / value_range if value_range > 0 else 0
        
        is_anomaly = normalized_slope > self.trend_threshold
        confidence = min(normalized_slope / self.trend_threshold, 1.0) if is_anomaly else 0.0
        
        trend_direction = "increasing" if slope > 0 else "decreasing"
        description = f"Strong {trend_direction} trend detected (slope: {slope:.4f})"
        
        return is_anomaly, confidence, description


class AlertEvaluator:
    """Evaluates alert rules against metric data"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.detectors = {
            AnomalyType.THRESHOLD: ThresholdAnomalyDetector,
            AnomalyType.STATISTICAL: StatisticalAnomalyDetector,
            AnomalyType.TREND: TrendAnomalyDetector
        }
    
    async def evaluate_rule(self, rule: AlertRule, metric_data: List[MetricData]) -> Optional[Alert]:
        """Evaluate a single alert rule"""
        try:
            if not rule.enabled:
                return None
            
            # Filter metric data by tags if specified
            filtered_data = self._filter_metric_data(metric_data, rule.tags_filter)
            
            if not filtered_data:
                return None
            
            # Determine detection method
            if rule.condition == "anomaly":
                # Use statistical anomaly detection
                detector = StatisticalAnomalyDetector()
                is_anomaly, confidence, description = await detector.detect_anomaly(filtered_data)
                anomaly_type = AnomalyType.STATISTICAL
            elif any(op in rule.condition for op in [">", "<", ">=", "<="]):
                # Parse threshold condition
                threshold, operator = self._parse_threshold_condition(rule.condition)
                detector = ThresholdAnomalyDetector(threshold, operator)
                is_anomaly, confidence, description = await detector.detect_anomaly(filtered_data)
                anomaly_type = AnomalyType.THRESHOLD
            else:
                self.logger.warning(f"Unknown condition format: {rule.condition}")
                return None
            
            if not is_anomaly:
                return None
            
            # Create alert
            alert_id = self._generate_alert_id(rule, filtered_data[-1])
            
            alert = Alert(
                alert_id=alert_id,
                title=f"{rule.name} - {rule.metric_name}",
                description=f"{rule.description}\n{description}",
                severity=rule.severity,
                category=rule.category,
                source=f"rule:{rule.rule_id}",
                metric_name=rule.metric_name,
                metric_value=filtered_data[-1].value,
                threshold=rule.threshold_value,
                tags=filtered_data[-1].tags,
                anomaly_type=anomaly_type,
                confidence_score=confidence
            )
            
            return alert
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate rule {rule.rule_id}: {e}")
            return None
    
    def _filter_metric_data(self, metric_data: List[MetricData], tags_filter: Dict[str, str]) -> List[MetricData]:
        """Filter metric data by tags"""
        if not tags_filter:
            return metric_data
        
        filtered = []
        for data in metric_data:
            if all(data.tags.get(key) == value for key, value in tags_filter.items()):
                filtered.append(data)
        
        return filtered
    
    def _parse_threshold_condition(self, condition: str) -> Tuple[float, str]:
        """Parse threshold condition string"""
        condition = condition.strip()
        
        if condition.startswith(">="):
            return float(condition[2:].strip()), ">="
        elif condition.startswith("<="):
            return float(condition[2:].strip()), "<="
        elif condition.startswith(">"):
            return float(condition[1:].strip()), ">"
        elif condition.startswith("<"):
            return float(condition[1:].strip()), "<"
        else:
            raise ValueError(f"Invalid threshold condition: {condition}")
    
    def _generate_alert_id(self, rule: AlertRule, metric_data: MetricData) -> str:
        """Generate unique alert ID"""
        # Create hash from rule ID, metric name, and tags
        content = f"{rule.rule_id}:{rule.metric_name}:{sorted(metric_data.tags.items())}"
        return hashlib.md5(content.encode()).hexdigest()[:16]


class RootCauseAnalyzer:
    """Analyzes root causes of alerts"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.correlation_rules = []
        self.causal_patterns = {}
    
    async def analyze_root_cause(self, alert: Alert, recent_alerts: List[Alert], 
                               metric_history: Dict[str, List[MetricData]]) -> List[str]:
        """Analyze potential root causes for an alert"""
        try:
            root_causes = []
            
            # 1. Check for correlated alerts
            correlated_causes = await self._analyze_correlated_alerts(alert, recent_alerts)
            root_causes.extend(correlated_causes)
            
            # 2. Check for metric correlations
            metric_causes = await self._analyze_metric_correlations(alert, metric_history)
            root_causes.extend(metric_causes)
            
            # 3. Check for known patterns
            pattern_causes = await self._analyze_known_patterns(alert, metric_history)
            root_causes.extend(pattern_causes)
            
            # 4. Check for system-level issues
            system_causes = await self._analyze_system_issues(alert, recent_alerts)
            root_causes.extend(system_causes)
            
            return list(set(root_causes))  # Remove duplicates
            
        except Exception as e:
            self.logger.error(f"Failed to analyze root cause for alert {alert.alert_id}: {e}")
            return []
    
    async def _analyze_correlated_alerts(self, alert: Alert, recent_alerts: List[Alert]) -> List[str]:
        """Analyze correlated alerts for root causes"""
        causes = []
        
        # Look for alerts in the same category that occurred recently
        related_alerts = [
            a for a in recent_alerts 
            if a.category == alert.category and 
               a.alert_id != alert.alert_id and
               (alert.created_at - a.created_at).total_seconds() < 300  # Within 5 minutes
        ]
        
        if related_alerts:
            causes.append(f"Correlated with {len(related_alerts)} other {alert.category.value} alerts")
        
        # Look for upstream system alerts
        if alert.category == AlertCategory.PERFORMANCE:
            system_alerts = [
                a for a in recent_alerts
                if a.category == AlertCategory.SYSTEM and
                   (alert.created_at - a.created_at).total_seconds() < 600  # Within 10 minutes
            ]
            
            if system_alerts:
                causes.append("Potential system resource constraints detected")
        
        return causes
    
    async def _analyze_metric_correlations(self, alert: Alert, 
                                         metric_history: Dict[str, List[MetricData]]) -> List[str]:
        """Analyze metric correlations for root causes"""
        causes = []
        
        if not alert.metric_name or alert.metric_name not in metric_history:
            return causes
        
        alert_metric_data = metric_history[alert.metric_name]
        
        # Look for correlated metrics that changed around the same time
        for metric_name, metric_data in metric_history.items():
            if metric_name == alert.metric_name:
                continue
            
            correlation = await self._calculate_correlation(alert_metric_data, metric_data)
            
            if abs(correlation) > 0.7:  # Strong correlation
                # Check if the correlated metric also shows anomalous behavior
                detector = StatisticalAnomalyDetector()
                is_anomaly, confidence, _ = await detector.detect_anomaly(metric_data)
                
                if is_anomaly:
                    direction = "positively" if correlation > 0 else "negatively"
                    causes.append(f"Strongly {direction} correlated with anomalous {metric_name}")
        
        return causes
    
    async def _calculate_correlation(self, data1: List[MetricData], data2: List[MetricData]) -> float:
        """Calculate correlation between two metric series"""
        try:
            # Align data by timestamp (simplified - assumes same timestamps)
            min_length = min(len(data1), len(data2))
            values1 = [d.value for d in data1[-min_length:]]
            values2 = [d.value for d in data2[-min_length:]]
            
            if min_length < 3:
                return 0.0
            
            if NUMPY_AVAILABLE:
                correlation = np.corrcoef(values1, values2)[0, 1]
                return correlation if not np.isnan(correlation) else 0.0
            else:
                # Simple correlation calculation
                mean1 = statistics.mean(values1)
                mean2 = statistics.mean(values2)
                
                numerator = sum((v1 - mean1) * (v2 - mean2) for v1, v2 in zip(values1, values2))
                denominator = (sum((v1 - mean1) ** 2 for v1 in values1) * 
                              sum((v2 - mean2) ** 2 for v2 in values2)) ** 0.5
                
                return numerator / denominator if denominator > 0 else 0.0
                
        except Exception as e:
            self.logger.error(f"Failed to calculate correlation: {e}")
            return 0.0
    
    async def _analyze_known_patterns(self, alert: Alert, 
                                    metric_history: Dict[str, List[MetricData]]) -> List[str]:
        """Analyze known causal patterns"""
        causes = []
        
        # Trading-specific patterns
        if alert.category == AlertCategory.TRADING:
            if "latency" in alert.metric_name.lower():
                causes.append("High trading latency may indicate network or system issues")
            elif "volume" in alert.metric_name.lower():
                causes.append("Unusual trading volume may indicate market events or system issues")
            elif "error" in alert.metric_name.lower():
                causes.append("Trading errors may indicate connectivity or data quality issues")
        
        # Performance patterns
        elif alert.category == AlertCategory.PERFORMANCE:
            if "memory" in alert.metric_name.lower():
                causes.append("Memory pressure may indicate memory leaks or increased load")
            elif "cpu" in alert.metric_name.lower():
                causes.append("High CPU usage may indicate inefficient algorithms or increased load")
            elif "disk" in alert.metric_name.lower():
                causes.append("Disk issues may indicate storage problems or excessive logging")
        
        return causes
    
    async def _analyze_system_issues(self, alert: Alert, recent_alerts: List[Alert]) -> List[str]:
        """Analyze system-level issues"""
        causes = []
        
        # Check for cascading failures
        if len(recent_alerts) > 10:  # Many recent alerts
            causes.append("Potential cascading system failure detected")
        
        # Check for resource exhaustion patterns
        resource_alerts = [
            a for a in recent_alerts
            if any(keyword in a.metric_name.lower() for keyword in ["memory", "cpu", "disk", "network"])
        ]
        
        if len(resource_alerts) > 3:
            causes.append("Multiple resource constraints detected")
        
        return causes


class AlertCorrelator:
    """Correlates and deduplicates alerts"""
    
    def __init__(self, correlation_window: timedelta = timedelta(minutes=10)):
        self.correlation_window = correlation_window
        self.logger = logging.getLogger(__name__)
    
    async def correlate_alerts(self, new_alert: Alert, existing_alerts: List[Alert]) -> List[str]:
        """Find correlated alerts"""
        correlated = []
        
        for existing_alert in existing_alerts:
            if existing_alert.alert_id == new_alert.alert_id:
                continue
            
            # Check time correlation
            time_diff = abs((new_alert.created_at - existing_alert.created_at).total_seconds())
            if time_diff > self.correlation_window.total_seconds():
                continue
            
            correlation_score = await self._calculate_alert_correlation(new_alert, existing_alert)
            
            if correlation_score > 0.5:  # Significant correlation
                correlated.append(existing_alert.alert_id)
        
        return correlated
    
    async def _calculate_alert_correlation(self, alert1: Alert, alert2: Alert) -> float:
        """Calculate correlation score between two alerts"""
        score = 0.0
        
        # Category correlation
        if alert1.category == alert2.category:
            score += 0.3
        
        # Metric correlation
        if alert1.metric_name and alert2.metric_name:
            if alert1.metric_name == alert2.metric_name:
                score += 0.4
            elif any(word in alert2.metric_name for word in alert1.metric_name.split("_")):
                score += 0.2
        
        # Tag correlation
        if alert1.tags and alert2.tags:
            common_tags = set(alert1.tags.items()) & set(alert2.tags.items())
            tag_score = len(common_tags) / max(len(alert1.tags), len(alert2.tags))
            score += tag_score * 0.3
        
        return min(score, 1.0)
    
    async def deduplicate_alert(self, new_alert: Alert, existing_alerts: List[Alert]) -> bool:
        """Check if alert should be deduplicated"""
        for existing_alert in existing_alerts:
            if existing_alert.status == AlertStatus.RESOLVED:
                continue
            
            # Check for exact duplicates
            if (existing_alert.metric_name == new_alert.metric_name and
                existing_alert.tags == new_alert.tags and
                existing_alert.severity == new_alert.severity):
                
                # Check time window
                time_diff = (new_alert.created_at - existing_alert.created_at).total_seconds()
                if time_diff < 300:  # Within 5 minutes
                    return True  # Deduplicate
        
        return False  # Don't deduplicate


class RecommendationEngine:
    """Generates actionable recommendations for alerts"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.recommendation_rules = self._load_recommendation_rules()
    
    async def generate_recommendations(self, alert: Alert, root_causes: List[str]) -> List[str]:
        """Generate actionable recommendations for an alert"""
        try:
            recommendations = []
            
            # Category-specific recommendations
            category_recs = await self._get_category_recommendations(alert)
            recommendations.extend(category_recs)
            
            # Root cause-specific recommendations
            cause_recs = await self._get_root_cause_recommendations(root_causes)
            recommendations.extend(cause_recs)
            
            # Severity-specific recommendations
            severity_recs = await self._get_severity_recommendations(alert)
            recommendations.extend(severity_recs)
            
            # Metric-specific recommendations
            metric_recs = await self._get_metric_recommendations(alert)
            recommendations.extend(metric_recs)
            
            return list(set(recommendations))  # Remove duplicates
            
        except Exception as e:
            self.logger.error(f"Failed to generate recommendations for alert {alert.alert_id}: {e}")
            return []
    
    async def _get_category_recommendations(self, alert: Alert) -> List[str]:
        """Get recommendations based on alert category"""
        recommendations = []
        
        if alert.category == AlertCategory.PERFORMANCE:
            recommendations.extend([
                "Check system resource utilization (CPU, memory, disk)",
                "Review recent deployments or configuration changes",
                "Analyze application logs for errors or warnings"
            ])
        
        elif alert.category == AlertCategory.TRADING:
            recommendations.extend([
                "Verify market data connectivity and quality",
                "Check order management system status",
                "Review trading strategy parameters and risk limits"
            ])
        
        elif alert.category == AlertCategory.SYSTEM:
            recommendations.extend([
                "Check system health and service status",
                "Review system logs for errors",
                "Verify network connectivity and infrastructure"
            ])
        
        elif alert.category == AlertCategory.RISK:
            recommendations.extend([
                "Review current positions and exposures",
                "Check risk limit configurations",
                "Analyze market conditions and volatility"
            ])
        
        return recommendations
    
    async def _get_root_cause_recommendations(self, root_causes: List[str]) -> List[str]:
        """Get recommendations based on root causes"""
        recommendations = []
        
        for cause in root_causes:
            if "memory" in cause.lower():
                recommendations.extend([
                    "Investigate memory leaks in application code",
                    "Consider increasing memory allocation",
                    "Review garbage collection settings"
                ])
            
            elif "cpu" in cause.lower():
                recommendations.extend([
                    "Profile application for CPU-intensive operations",
                    "Consider horizontal scaling or load balancing",
                    "Optimize algorithms and data structures"
                ])
            
            elif "network" in cause.lower():
                recommendations.extend([
                    "Check network connectivity and bandwidth",
                    "Review firewall and security group settings",
                    "Investigate network latency and packet loss"
                ])
            
            elif "correlation" in cause.lower():
                recommendations.extend([
                    "Investigate upstream dependencies",
                    "Check for cascading failures",
                    "Review service interaction patterns"
                ])
        
        return recommendations
    
    async def _get_severity_recommendations(self, alert: Alert) -> List[str]:
        """Get recommendations based on alert severity"""
        recommendations = []
        
        if alert.severity == AlertSeverity.CRITICAL:
            recommendations.extend([
                "Immediate investigation required",
                "Consider activating incident response team",
                "Prepare rollback procedures if needed"
            ])
        
        elif alert.severity == AlertSeverity.HIGH:
            recommendations.extend([
                "Prioritize investigation within 30 minutes",
                "Monitor for escalation to critical level",
                "Prepare mitigation strategies"
            ])
        
        return recommendations
    
    async def _get_metric_recommendations(self, alert: Alert) -> List[str]:
        """Get recommendations based on specific metrics"""
        recommendations = []
        
        if not alert.metric_name:
            return recommendations
        
        metric_name = alert.metric_name.lower()
        
        if "latency" in metric_name:
            recommendations.extend([
                "Check database query performance",
                "Review network connectivity",
                "Analyze application response times"
            ])
        
        elif "error_rate" in metric_name:
            recommendations.extend([
                "Review application logs for error details",
                "Check input data validation",
                "Verify external service dependencies"
            ])
        
        elif "throughput" in metric_name:
            recommendations.extend([
                "Check system capacity and scaling",
                "Review queue depths and processing rates",
                "Analyze resource bottlenecks"
            ])
        
        return recommendations
    
    def _load_recommendation_rules(self) -> Dict[str, List[str]]:
        """Load recommendation rules (placeholder for external configuration)"""
        return {
            "default": [
                "Check system logs for additional context",
                "Verify monitoring system health",
                "Document findings for future reference"
            ]
        }


class IntelligentAlertingSystem:
    """Main intelligent alerting system"""
    
    def __init__(self, 
                 max_alerts_history: int = 10000,
                 correlation_window: timedelta = timedelta(minutes=10)):
        self.logger = logging.getLogger(__name__)
        
        # Components
        self.evaluator = AlertEvaluator()
        self.root_cause_analyzer = RootCauseAnalyzer()
        self.correlator = AlertCorrelator(correlation_window)
        self.recommendation_engine = RecommendationEngine()
        
        # Storage
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=max_alerts_history)
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Configuration
        self.max_alerts_history = max_alerts_history
        self.correlation_window = correlation_window
        
        # Threading
        self._lock = threading.Lock()
        
        # Callbacks
        self.alert_callbacks: List[Callable[[Alert], None]] = []
    
    async def add_alert_rule(self, rule: AlertRule) -> bool:
        """Add or update an alert rule"""
        try:
            with self._lock:
                self.alert_rules[rule.rule_id] = rule
            
            self.logger.info(f"Added alert rule: {rule.name} ({rule.rule_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add alert rule {rule.rule_id}: {e}")
            return False
    
    async def remove_alert_rule(self, rule_id: str) -> bool:
        """Remove an alert rule"""
        try:
            with self._lock:
                if rule_id in self.alert_rules:
                    del self.alert_rules[rule_id]
                    self.logger.info(f"Removed alert rule: {rule_id}")
                    return True
                else:
                    self.logger.warning(f"Alert rule not found: {rule_id}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to remove alert rule {rule_id}: {e}")
            return False
    
    async def ingest_metric(self, metric_data: MetricData):
        """Ingest metric data and evaluate alert rules"""
        try:
            # Store metric data
            with self._lock:
                self.metric_history[metric_data.name].append(metric_data)
            
            # Evaluate all relevant alert rules
            await self._evaluate_alert_rules(metric_data)
            
        except Exception as e:
            self.logger.error(f"Failed to ingest metric {metric_data.name}: {e}")
    
    async def _evaluate_alert_rules(self, metric_data: MetricData):
        """Evaluate alert rules for a metric"""
        relevant_rules = [
            rule for rule in self.alert_rules.values()
            if rule.metric_name == metric_data.name and rule.enabled
        ]
        
        for rule in relevant_rules:
            try:
                # Get recent metric data for evaluation
                recent_data = list(self.metric_history[metric_data.name])
                
                # Evaluate rule
                alert = await self.evaluator.evaluate_rule(rule, recent_data)
                
                if alert:
                    await self._process_new_alert(alert)
                    
            except Exception as e:
                self.logger.error(f"Failed to evaluate rule {rule.rule_id}: {e}")
    
    async def _process_new_alert(self, alert: Alert):
        """Process a new alert"""
        try:
            # Check for deduplication
            existing_alerts = list(self.active_alerts.values())
            should_deduplicate = await self.correlator.deduplicate_alert(alert, existing_alerts)
            
            if should_deduplicate:
                self.logger.debug(f"Alert deduplicated: {alert.alert_id}")
                return
            
            # Find correlated alerts
            correlated_alerts = await self.correlator.correlate_alerts(alert, existing_alerts)
            alert.related_alerts = correlated_alerts
            
            # Perform root cause analysis
            recent_alerts = [a for a in self.alert_history if 
                           (alert.created_at - a.created_at).total_seconds() < 3600]  # Last hour
            
            root_causes = await self.root_cause_analyzer.analyze_root_cause(
                alert, recent_alerts, dict(self.metric_history)
            )
            alert.root_causes = root_causes
            
            # Generate recommendations
            recommendations = await self.recommendation_engine.generate_recommendations(
                alert, root_causes
            )
            alert.recommendations = recommendations
            
            # Store alert
            with self._lock:
                self.active_alerts[alert.alert_id] = alert
                self.alert_history.append(alert)
            
            # Notify callbacks
            await self._notify_alert_callbacks(alert)
            
            self.logger.info(f"New alert created: {alert.title} ({alert.alert_id})")
            
        except Exception as e:
            self.logger.error(f"Failed to process alert {alert.alert_id}: {e}")
    
    async def _notify_alert_callbacks(self, alert: Alert):
        """Notify registered alert callbacks"""
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")
    
    def add_alert_callback(self, callback: Callable[[Alert], None]):
        """Add alert callback function"""
        self.alert_callbacks.append(callback)
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        try:
            with self._lock:
                if alert_id in self.active_alerts:
                    alert = self.active_alerts[alert_id]
                    alert.status = AlertStatus.ACKNOWLEDGED
                    alert.acknowledged_by = acknowledged_by
                    alert.acknowledged_at = datetime.now()
                    alert.updated_at = datetime.now()
                    
                    self.logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
                    return True
                else:
                    self.logger.warning(f"Alert not found for acknowledgment: {alert_id}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
            return False
    
    async def resolve_alert(self, alert_id: str, resolved_by: str = None) -> bool:
        """Resolve an alert"""
        try:
            with self._lock:
                if alert_id in self.active_alerts:
                    alert = self.active_alerts[alert_id]
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = datetime.now()
                    alert.updated_at = datetime.now()
                    
                    # Move from active to history
                    del self.active_alerts[alert_id]
                    
                    self.logger.info(f"Alert resolved: {alert_id}")
                    return True
                else:
                    self.logger.warning(f"Alert not found for resolution: {alert_id}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to resolve alert {alert_id}: {e}")
            return False
    
    async def get_active_alerts(self, 
                              severity: Optional[AlertSeverity] = None,
                              category: Optional[AlertCategory] = None) -> List[Alert]:
        """Get active alerts with optional filtering"""
        with self._lock:
            alerts = list(self.active_alerts.values())
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if category:
            alerts = [a for a in alerts if a.category == category]
        
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)
    
    async def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alerting system statistics"""
        with self._lock:
            active_count = len(self.active_alerts)
            total_count = len(self.alert_history)
            
            # Count by severity
            severity_counts = defaultdict(int)
            for alert in self.active_alerts.values():
                severity_counts[alert.severity.value] += 1
            
            # Count by category
            category_counts = defaultdict(int)
            for alert in self.active_alerts.values():
                category_counts[alert.category.value] += 1
            
            # Calculate resolution rate
            resolved_count = sum(1 for a in self.alert_history if a.status == AlertStatus.RESOLVED)
            resolution_rate = resolved_count / total_count if total_count > 0 else 0
        
        return {
            "active_alerts": active_count,
            "total_alerts": total_count,
            "resolution_rate": resolution_rate,
            "severity_breakdown": dict(severity_counts),
            "category_breakdown": dict(category_counts),
            "alert_rules": len(self.alert_rules),
            "metrics_tracked": len(self.metric_history)
        }
    
    async def cleanup_old_data(self, retention_days: int = 7):
        """Clean up old metric data and resolved alerts"""
        try:
            cutoff_time = datetime.now() - timedelta(days=retention_days)
            
            # Clean up metric history
            with self._lock:
                for metric_name, data_deque in self.metric_history.items():
                    # Filter out old data
                    filtered_data = deque(
                        [data for data in data_deque if data.timestamp > cutoff_time],
                        maxlen=data_deque.maxlen
                    )
                    self.metric_history[metric_name] = filtered_data
            
            self.logger.info(f"Cleaned up metric data older than {retention_days} days")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")


# Convenience functions for common alert rules
def create_threshold_rule(rule_id: str, name: str, metric_name: str, 
                         threshold: float, operator: str = ">",
                         severity: AlertSeverity = AlertSeverity.HIGH,
                         category: AlertCategory = AlertCategory.PERFORMANCE) -> AlertRule:
    """Create a simple threshold-based alert rule"""
    return AlertRule(
        rule_id=rule_id,
        name=name,
        description=f"Alert when {metric_name} {operator} {threshold}",
        metric_name=metric_name,
        condition=f"{operator} {threshold}",
        severity=severity,
        category=category,
        threshold_value=threshold
    )


def create_anomaly_rule(rule_id: str, name: str, metric_name: str,
                       severity: AlertSeverity = AlertSeverity.MEDIUM,
                       category: AlertCategory = AlertCategory.PERFORMANCE) -> AlertRule:
    """Create an anomaly detection alert rule"""
    return AlertRule(
        rule_id=rule_id,
        name=name,
        description=f"Alert on statistical anomalies in {metric_name}",
        metric_name=metric_name,
        condition="anomaly",
        severity=severity,
        category=category
    )


# Example usage and testing
async def example_usage():
    """Example usage of the Intelligent Alerting System"""
    
    # Initialize alerting system
    alerting_system = IntelligentAlertingSystem()
    
    # Add alert callback
    def alert_handler(alert: Alert):
        print(f"🚨 ALERT: {alert.title}")
        print(f"   Severity: {alert.severity.value.upper()}")
        print(f"   Description: {alert.description}")
        if alert.root_causes:
            print(f"   Root Causes: {', '.join(alert.root_causes)}")
        if alert.recommendations:
            print(f"   Recommendations: {', '.join(alert.recommendations[:2])}")
        print()
    
    alerting_system.add_alert_callback(alert_handler)
    
    # Create alert rules
    rules = [
        create_threshold_rule(
            "cpu_high", "High CPU Usage", "system.cpu.usage", 
            80.0, ">", AlertSeverity.HIGH, AlertCategory.SYSTEM
        ),
        create_threshold_rule(
            "latency_high", "High Trading Latency", "trading.latency", 
            100.0, ">", AlertSeverity.CRITICAL, AlertCategory.TRADING
        ),
        create_anomaly_rule(
            "volume_anomaly", "Trading Volume Anomaly", "trading.volume",
            AlertSeverity.MEDIUM, AlertCategory.TRADING
        ),
        create_threshold_rule(
            "memory_low", "Low Memory", "system.memory.available", 
            1000.0, "<", AlertSeverity.HIGH, AlertCategory.SYSTEM
        )
    ]
    
    # Add rules to system
    for rule in rules:
        await alerting_system.add_alert_rule(rule)
    
    print("=== Intelligent Alerting System Demo ===")
    print(f"Added {len(rules)} alert rules")
    
    # Simulate metric ingestion
    print("\nSimulating metric data...")
    
    # Normal metrics
    for i in range(20):
        await alerting_system.ingest_metric(MetricData(
            name="system.cpu.usage",
            value=50.0 + i * 0.5,  # Gradually increasing
            timestamp=datetime.now() - timedelta(minutes=20-i)
        ))
        
        await alerting_system.ingest_metric(MetricData(
            name="trading.latency",
            value=30.0 + i * 0.2,  # Gradually increasing
            timestamp=datetime.now() - timedelta(minutes=20-i)
        ))
        
        await alerting_system.ingest_metric(MetricData(
            name="trading.volume",
            value=1000.0 + (i % 5) * 100,  # Regular pattern
            timestamp=datetime.now() - timedelta(minutes=20-i)
        ))
    
    # Trigger alerts with anomalous data
    print("\nTriggering alerts with anomalous data...")
    
    # High CPU alert
    await alerting_system.ingest_metric(MetricData(
        name="system.cpu.usage",
        value=95.0,  # Above threshold
        timestamp=datetime.now()
    ))
    
    # High latency alert
    await alerting_system.ingest_metric(MetricData(
        name="trading.latency",
        value=150.0,  # Above threshold
        timestamp=datetime.now()
    ))
    
    # Volume anomaly
    await alerting_system.ingest_metric(MetricData(
        name="trading.volume",
        value=5000.0,  # Significant anomaly
        timestamp=datetime.now()
    ))
    
    # Low memory alert
    await alerting_system.ingest_metric(MetricData(
        name="system.memory.available",
        value=500.0,  # Below threshold
        timestamp=datetime.now()
    ))
    
    # Wait a moment for processing
    await asyncio.sleep(0.1)
    
    # Get system statistics
    stats = await alerting_system.get_alert_statistics()
    print(f"\n=== Alerting System Statistics ===")
    print(f"Active Alerts: {stats['active_alerts']}")
    print(f"Total Alerts: {stats['total_alerts']}")
    print(f"Resolution Rate: {stats['resolution_rate']:.1%}")
    print(f"Severity Breakdown: {stats['severity_breakdown']}")
    print(f"Category Breakdown: {stats['category_breakdown']}")
    
    # Get active alerts
    active_alerts = await alerting_system.get_active_alerts()
    print(f"\n=== Active Alerts ({len(active_alerts)}) ===")
    for alert in active_alerts:
        print(f"- {alert.title} ({alert.severity.value})")
        print(f"  Created: {alert.created_at.strftime('%H:%M:%S')}")
        if alert.related_alerts:
            print(f"  Related: {len(alert.related_alerts)} alerts")
    
    # Acknowledge and resolve some alerts
    if active_alerts:
        print(f"\nAcknowledging first alert...")
        await alerting_system.acknowledge_alert(active_alerts[0].alert_id, "operator")
        
        print(f"Resolving second alert...")
        if len(active_alerts) > 1:
            await alerting_system.resolve_alert(active_alerts[1].alert_id, "system")
    
    # Final statistics
    final_stats = await alerting_system.get_alert_statistics()
    print(f"\n=== Final Statistics ===")
    print(f"Active Alerts: {final_stats['active_alerts']}")
    print(f"Resolution Rate: {final_stats['resolution_rate']:.1%}")


if __name__ == "__main__":
    asyncio.run(example_usage())