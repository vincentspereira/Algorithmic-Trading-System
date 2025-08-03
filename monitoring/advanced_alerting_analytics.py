#!/usr/bin/env python3
"""
Advanced Alerting and Analytics System
Machine learning-based anomaly detection, intelligent alert correlation,
automated root cause analysis, and predictive capacity planning.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import threading
import os
import sys
from pathlib import Path
import statistics
import math
import random

# Data processing and ML
try:
    import numpy as np
    import pandas as pd
    from scipy import stats
    from scipy.signal import find_peaks
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("SciPy/NumPy not available, using fallback implementations")

import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

class AnomalyType(Enum):
    """Types of anomalies"""
    SPIKE = "SPIKE"
    DIP = "DIP"
    TREND_CHANGE = "TREND_CHANGE"
    SEASONAL_DEVIATION = "SEASONAL_DEVIATION"
    OUTLIER = "OUTLIER"
    PATTERN_BREAK = "PATTERN_BREAK"

class AlertCorrelationType(Enum):
    """Types of alert correlations"""
    CAUSAL = "CAUSAL"
    TEMPORAL = "TEMPORAL"
    SPATIAL = "SPATIAL"
    FUNCTIONAL = "FUNCTIONAL"
    STATISTICAL = "STATISTICAL"

class RootCauseCategory(Enum):
    """Root cause categories"""
    INFRASTRUCTURE = "INFRASTRUCTURE"
    APPLICATION = "APPLICATION"
    NETWORK = "NETWORK"
    DATABASE = "DATABASE"
    EXTERNAL_SERVICE = "EXTERNAL_SERVICE"
    USER_BEHAVIOR = "USER_BEHAVIOR"
    CONFIGURATION = "CONFIGURATION"

@dataclass
class TimeSeriesPoint:
    """Time series data point"""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Anomaly:
    """Detected anomaly"""
    anomaly_id: str
    anomaly_type: AnomalyType
    timestamp: datetime
    value: float
    expected_value: float
    confidence: float
    severity: float
    metric_name: str
    component: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AlertCorrelation:
    """Alert correlation result"""
    correlation_id: str
    correlation_type: AlertCorrelationType
    primary_alert_id: str
    related_alert_ids: List[str]
    confidence: float
    time_window: timedelta
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RootCauseAnalysis:
    """Root cause analysis result"""
    analysis_id: str
    alert_ids: List[str]
    root_cause_category: RootCauseCategory
    confidence: float
    description: str
    evidence: List[str]
    recommendations: List[str]
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CapacityForecast:
    """Capacity planning forecast"""
    forecast_id: str
    metric_name: str
    component: str
    forecast_horizon: timedelta
    predicted_values: List[Tuple[datetime, float]]
    confidence_intervals: List[Tuple[float, float]]
    capacity_threshold: float
    predicted_breach_time: Optional[datetime]
    recommendations: List[str]
    timestamp: datetime

class AnomalyDetector:
    """Machine learning-based anomaly detection"""
    
    def __init__(self, window_size: int = 100, sensitivity: float = 2.0):
        self.window_size = window_size
        self.sensitivity = sensitivity
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.baseline_stats: Dict[str, Dict[str, float]] = {}
        self.seasonal_patterns: Dict[str, List[float]] = {}
        
        logger.info("Anomaly detector initialized", window_size=window_size, sensitivity=sensitivity)
    
    def add_data_point(self, metric_name: str, point: TimeSeriesPoint):
        """Add a new data point for analysis"""
        self.metric_history[metric_name].append(point)
        self._update_baseline_stats(metric_name)
        self._update_seasonal_patterns(metric_name)
    
    def detect_anomalies(self, metric_name: str, point: TimeSeriesPoint) -> List[Anomaly]:
        """Detect anomalies in the given data point"""
        anomalies = []
        
        if len(self.metric_history[metric_name]) < 10:
            return anomalies  # Need more data
        
        # Statistical anomaly detection
        stat_anomaly = self._detect_statistical_anomaly(metric_name, point)
        if stat_anomaly:
            anomalies.append(stat_anomaly)
        
        # Trend change detection
        trend_anomaly = self._detect_trend_change(metric_name, point)
        if trend_anomaly:
            anomalies.append(trend_anomaly)
        
        # Seasonal deviation detection
        seasonal_anomaly = self._detect_seasonal_deviation(metric_name, point)
        if seasonal_anomaly:
            anomalies.append(seasonal_anomaly)
        
        # Pattern break detection
        pattern_anomaly = self._detect_pattern_break(metric_name, point)
        if pattern_anomaly:
            anomalies.append(pattern_anomaly)
        
        return anomalies
    
    def _detect_statistical_anomaly(self, metric_name: str, point: TimeSeriesPoint) -> Optional[Anomaly]:
        """Detect statistical anomalies using z-score"""
        if metric_name not in self.baseline_stats:
            return None
        
        stats = self.baseline_stats[metric_name]
        mean = stats['mean']
        std = stats['std']
        
        if std == 0:
            return None
        
        z_score = abs(point.value - mean) / std
        
        if z_score > self.sensitivity:
            anomaly_type = AnomalyType.SPIKE if point.value > mean else AnomalyType.DIP
            confidence = min(z_score / (self.sensitivity * 2), 1.0)
            severity = min(z_score / self.sensitivity, 3.0)
            
            return Anomaly(
                anomaly_id=str(uuid.uuid4()),
                anomaly_type=anomaly_type,
                timestamp=point.timestamp,
                value=point.value,
                expected_value=mean,
                confidence=confidence,
                severity=severity,
                metric_name=metric_name,
                component=point.metadata.get('component', 'unknown'),
                description=f"Statistical anomaly detected: z-score {z_score:.2f}",
                metadata={'z_score': z_score, 'threshold': self.sensitivity}
            )
        
        return None
    
    def _detect_trend_change(self, metric_name: str, point: TimeSeriesPoint) -> Optional[Anomaly]:
        """Detect trend changes using linear regression"""
        history = list(self.metric_history[metric_name])
        if len(history) < 20:
            return None
        
        # Calculate trend for recent window
        recent_values = [p.value for p in history[-10:]]
        older_values = [p.value for p in history[-20:-10]]
        
        if SCIPY_AVAILABLE:
            recent_slope, _, recent_r, _, _ = stats.linregress(range(len(recent_values)), recent_values)
            older_slope, _, older_r, _, _ = stats.linregress(range(len(older_values)), older_values)
        else:
            recent_slope = self._calculate_slope(recent_values)
            older_slope = self._calculate_slope(older_values)
            recent_r = 0.5  # Fallback correlation
            older_r = 0.5
        
        # Check for significant trend change
        slope_change = abs(recent_slope - older_slope)
        if slope_change > statistics.stdev([p.value for p in history]) * 0.1:
            confidence = min(slope_change / statistics.stdev([p.value for p in history]), 1.0)
            
            return Anomaly(
                anomaly_id=str(uuid.uuid4()),
                anomaly_type=AnomalyType.TREND_CHANGE,
                timestamp=point.timestamp,
                value=point.value,
                expected_value=statistics.mean([p.value for p in history[-5:]]),
                confidence=confidence,
                severity=2.0,
                metric_name=metric_name,
                component=point.metadata.get('component', 'unknown'),
                description=f"Trend change detected: slope change {slope_change:.4f}",
                metadata={'recent_slope': recent_slope, 'older_slope': older_slope}
            )
        
        return None
    
    def _detect_seasonal_deviation(self, metric_name: str, point: TimeSeriesPoint) -> Optional[Anomaly]:
        """Detect seasonal pattern deviations"""
        if metric_name not in self.seasonal_patterns:
            return None
        
        pattern = self.seasonal_patterns[metric_name]
        if len(pattern) < 24:  # Need at least 24 hours of data
            return None
        
        # Get expected value based on hour of day
        hour = point.timestamp.hour
        expected_value = pattern[hour % len(pattern)]
        
        deviation = abs(point.value - expected_value)
        threshold = statistics.stdev(pattern) * self.sensitivity
        
        if deviation > threshold:
            confidence = min(deviation / threshold, 1.0)
            
            return Anomaly(
                anomaly_id=str(uuid.uuid4()),
                anomaly_type=AnomalyType.SEASONAL_DEVIATION,
                timestamp=point.timestamp,
                value=point.value,
                expected_value=expected_value,
                confidence=confidence,
                severity=1.5,
                metric_name=metric_name,
                component=point.metadata.get('component', 'unknown'),
                description=f"Seasonal deviation detected: {deviation:.2f} from expected {expected_value:.2f}",
                metadata={'hour': hour, 'seasonal_pattern': pattern}
            )
        
        return None
    
    def _detect_pattern_break(self, metric_name: str, point: TimeSeriesPoint) -> Optional[Anomaly]:
        """Detect pattern breaks using autocorrelation"""
        history = list(self.metric_history[metric_name])
        if len(history) < 50:
            return None
        
        values = [p.value for p in history]
        
        # Simple pattern break detection using moving averages
        short_ma = statistics.mean(values[-5:])
        long_ma = statistics.mean(values[-20:])
        
        deviation = abs(short_ma - long_ma)
        threshold = statistics.stdev(values) * 0.5
        
        if deviation > threshold:
            confidence = min(deviation / threshold, 1.0)
            
            return Anomaly(
                anomaly_id=str(uuid.uuid4()),
                anomaly_type=AnomalyType.PATTERN_BREAK,
                timestamp=point.timestamp,
                value=point.value,
                expected_value=long_ma,
                confidence=confidence,
                severity=1.8,
                metric_name=metric_name,
                component=point.metadata.get('component', 'unknown'),
                description=f"Pattern break detected: short MA {short_ma:.2f} vs long MA {long_ma:.2f}",
                metadata={'short_ma': short_ma, 'long_ma': long_ma}
            )
        
        return None
    
    def _update_baseline_stats(self, metric_name: str):
        """Update baseline statistics for a metric"""
        history = list(self.metric_history[metric_name])
        if len(history) < 5:
            return
        
        values = [p.value for p in history]
        self.baseline_stats[metric_name] = {
            'mean': statistics.mean(values),
            'std': statistics.stdev(values) if len(values) > 1 else 0,
            'median': statistics.median(values),
            'min': min(values),
            'max': max(values)
        }
    
    def _update_seasonal_patterns(self, metric_name: str):
        """Update seasonal patterns for a metric"""
        history = list(self.metric_history[metric_name])
        if len(history) < 24:
            return
        
        # Group by hour of day
        hourly_values = defaultdict(list)
        for point in history:
            hour = point.timestamp.hour
            hourly_values[hour].append(point.value)
        
        # Calculate average for each hour
        pattern = []
        for hour in range(24):
            if hour in hourly_values:
                pattern.append(statistics.mean(hourly_values[hour]))
            else:
                pattern.append(0.0)
        
        self.seasonal_patterns[metric_name] = pattern
    
    def _calculate_slope(self, values: List[float]) -> float:
        """Calculate slope using simple linear regression"""
        n = len(values)
        if n < 2:
            return 0.0
        
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(values)
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        return numerator / denominator if denominator != 0 else 0.0

class AlertCorrelationEngine:
    """Intelligent alert correlation and deduplication"""
    
    def __init__(self, correlation_window: timedelta = timedelta(minutes=5)):
        self.correlation_window = correlation_window
        self.alert_history: deque = deque(maxlen=1000)
        self.correlation_rules: List[Dict[str, Any]] = []
        self.active_correlations: Dict[str, AlertCorrelation] = {}
        
        # Initialize default correlation rules
        self._initialize_correlation_rules()
        
        logger.info("Alert correlation engine initialized", window=correlation_window)
    
    def _initialize_correlation_rules(self):
        """Initialize default correlation rules"""
        self.correlation_rules = [
            {
                'name': 'infrastructure_cascade',
                'type': AlertCorrelationType.CAUSAL,
                'conditions': {
                    'component_hierarchy': ['infrastructure', 'application', 'user'],
                    'time_window': timedelta(minutes=2)
                },
                'confidence_boost': 0.8
            },
            {
                'name': 'service_dependency',
                'type': AlertCorrelationType.FUNCTIONAL,
                'conditions': {
                    'service_dependencies': {
                        'database': ['api', 'web'],
                        'api': ['web', 'mobile'],
                        'cache': ['api', 'web']
                    },
                    'time_window': timedelta(minutes=3)
                },
                'confidence_boost': 0.7
            },
            {
                'name': 'temporal_clustering',
                'type': AlertCorrelationType.TEMPORAL,
                'conditions': {
                    'time_window': timedelta(minutes=1),
                    'min_alerts': 3
                },
                'confidence_boost': 0.6
            }
        ]
    
    def add_alert(self, alert: Dict[str, Any]) -> List[AlertCorrelation]:
        """Add new alert and find correlations"""
        self.alert_history.append({
            **alert,
            'timestamp': datetime.now(),
            'alert_id': alert.get('alert_id', str(uuid.uuid4()))
        })
        
        correlations = self._find_correlations(alert)
        
        # Update active correlations
        for correlation in correlations:
            self.active_correlations[correlation.correlation_id] = correlation
        
        return correlations
    
    def _find_correlations(self, new_alert: Dict[str, Any]) -> List[AlertCorrelation]:
        """Find correlations for a new alert"""
        correlations = []
        current_time = datetime.now()
        
        # Get recent alerts within correlation window
        recent_alerts = [
            alert for alert in self.alert_history
            if current_time - alert['timestamp'] <= self.correlation_window
            and alert['alert_id'] != new_alert.get('alert_id')
        ]
        
        if not recent_alerts:
            return correlations
        
        # Apply correlation rules
        for rule in self.correlation_rules:
            correlation = self._apply_correlation_rule(new_alert, recent_alerts, rule)
            if correlation:
                correlations.append(correlation)
        
        return correlations
    
    def _apply_correlation_rule(self, new_alert: Dict[str, Any], recent_alerts: List[Dict[str, Any]], rule: Dict[str, Any]) -> Optional[AlertCorrelation]:
        """Apply a specific correlation rule"""
        rule_type = rule['type']
        conditions = rule['conditions']
        
        if rule_type == AlertCorrelationType.CAUSAL:
            return self._check_causal_correlation(new_alert, recent_alerts, rule)
        elif rule_type == AlertCorrelationType.FUNCTIONAL:
            return self._check_functional_correlation(new_alert, recent_alerts, rule)
        elif rule_type == AlertCorrelationType.TEMPORAL:
            return self._check_temporal_correlation(new_alert, recent_alerts, rule)
        elif rule_type == AlertCorrelationType.SPATIAL:
            return self._check_spatial_correlation(new_alert, recent_alerts, rule)
        
        return None
    
    def _check_causal_correlation(self, new_alert: Dict[str, Any], recent_alerts: List[Dict[str, Any]], rule: Dict[str, Any]) -> Optional[AlertCorrelation]:
        """Check for causal correlations based on component hierarchy"""
        hierarchy = rule['conditions']['component_hierarchy']
        time_window = rule['conditions']['time_window']
        
        new_component = new_alert.get('component', '')
        new_level = self._get_component_level(new_component, hierarchy)
        
        if new_level == -1:
            return None
        
        # Find alerts from lower levels in hierarchy
        related_alerts = []
        for alert in recent_alerts:
            alert_component = alert.get('component', '')
            alert_level = self._get_component_level(alert_component, hierarchy)
            
            if alert_level != -1 and alert_level < new_level:
                time_diff = new_alert.get('timestamp', datetime.now()) - alert['timestamp']
                if time_diff <= time_window:
                    related_alerts.append(alert['alert_id'])
        
        if related_alerts:
            confidence = rule['confidence_boost'] * (len(related_alerts) / 5.0)  # Max 5 related alerts
            confidence = min(confidence, 1.0)
            
            return AlertCorrelation(
                correlation_id=str(uuid.uuid4()),
                correlation_type=AlertCorrelationType.CAUSAL,
                primary_alert_id=new_alert.get('alert_id', ''),
                related_alert_ids=related_alerts,
                confidence=confidence,
                time_window=time_window,
                description=f"Causal correlation detected: {new_component} affected by {len(related_alerts)} upstream issues",
                metadata={'hierarchy_level': new_level, 'rule': rule['name']}
            )
        
        return None
    
    def _check_functional_correlation(self, new_alert: Dict[str, Any], recent_alerts: List[Dict[str, Any]], rule: Dict[str, Any]) -> Optional[AlertCorrelation]:
        """Check for functional correlations based on service dependencies"""
        dependencies = rule['conditions']['service_dependencies']
        time_window = rule['conditions']['time_window']
        
        new_service = new_alert.get('service', new_alert.get('component', ''))
        
        # Check if new alert's service has dependencies
        dependent_services = []
        for service, deps in dependencies.items():
            if new_service in deps:
                dependent_services.append(service)
        
        if not dependent_services:
            return None
        
        # Find alerts from dependent services
        related_alerts = []
        for alert in recent_alerts:
            alert_service = alert.get('service', alert.get('component', ''))
            if alert_service in dependent_services:
                time_diff = new_alert.get('timestamp', datetime.now()) - alert['timestamp']
                if time_diff <= time_window:
                    related_alerts.append(alert['alert_id'])
        
        if related_alerts:
            confidence = rule['confidence_boost'] * (len(related_alerts) / len(dependent_services))
            confidence = min(confidence, 1.0)
            
            return AlertCorrelation(
                correlation_id=str(uuid.uuid4()),
                correlation_type=AlertCorrelationType.FUNCTIONAL,
                primary_alert_id=new_alert.get('alert_id', ''),
                related_alert_ids=related_alerts,
                confidence=confidence,
                time_window=time_window,
                description=f"Functional correlation detected: {new_service} depends on {len(related_alerts)} affected services",
                metadata={'dependent_services': dependent_services, 'rule': rule['name']}
            )
        
        return None
    
    def _check_temporal_correlation(self, new_alert: Dict[str, Any], recent_alerts: List[Dict[str, Any]], rule: Dict[str, Any]) -> Optional[AlertCorrelation]:
        """Check for temporal correlations (alerts clustered in time)"""
        time_window = rule['conditions']['time_window']
        min_alerts = rule['conditions']['min_alerts']
        
        # Find alerts within tight time window
        clustered_alerts = []
        new_time = new_alert.get('timestamp', datetime.now())
        
        for alert in recent_alerts:
            time_diff = abs(new_time - alert['timestamp'])
            if time_diff <= time_window:
                clustered_alerts.append(alert['alert_id'])
        
        if len(clustered_alerts) >= min_alerts - 1:  # -1 because new alert is not in recent_alerts
            confidence = rule['confidence_boost'] * (len(clustered_alerts) / 10.0)  # Max 10 clustered alerts
            confidence = min(confidence, 1.0)
            
            return AlertCorrelation(
                correlation_id=str(uuid.uuid4()),
                correlation_type=AlertCorrelationType.TEMPORAL,
                primary_alert_id=new_alert.get('alert_id', ''),
                related_alert_ids=clustered_alerts,
                confidence=confidence,
                time_window=time_window,
                description=f"Temporal correlation detected: {len(clustered_alerts) + 1} alerts within {time_window}",
                metadata={'cluster_size': len(clustered_alerts) + 1, 'rule': rule['name']}
            )
        
        return None
    
    def _check_spatial_correlation(self, new_alert: Dict[str, Any], recent_alerts: List[Dict[str, Any]], rule: Dict[str, Any]) -> Optional[AlertCorrelation]:
        """Check for spatial correlations (same location/region)"""
        # This would be implemented based on geographic or logical location data
        # For now, return None as it requires location metadata
        return None
    
    def _get_component_level(self, component: str, hierarchy: List[str]) -> int:
        """Get component level in hierarchy"""
        for i, level in enumerate(hierarchy):
            if level.lower() in component.lower():
                return i
        return -1
    
    def get_active_correlations(self) -> List[AlertCorrelation]:
        """Get currently active correlations"""
        current_time = datetime.now()
        
        # Remove expired correlations
        expired_ids = [
            corr_id for corr_id, correlation in self.active_correlations.items()
            if current_time - correlation.timestamp > self.correlation_window * 2
        ]
        
        for corr_id in expired_ids:
            del self.active_correlations[corr_id]
        
        return list(self.active_correlations.values())

class RootCauseAnalyzer:
    """Automated root cause analysis with decision trees"""
    
    def __init__(self):
        self.analysis_history: List[RootCauseAnalysis] = []
        self.decision_rules: List[Dict[str, Any]] = []
        self.component_dependencies: Dict[str, List[str]] = {}
        
        # Initialize decision rules
        self._initialize_decision_rules()
        
        logger.info("Root cause analyzer initialized")
    
    def _initialize_decision_rules(self):
        """Initialize root cause analysis decision rules"""
        self.decision_rules = [
            {
                'name': 'high_cpu_memory',
                'conditions': {
                    'metrics': ['cpu_percent', 'memory_percent'],
                    'thresholds': {'cpu_percent': 80, 'memory_percent': 80},
                    'operator': 'OR'
                },
                'root_cause': RootCauseCategory.INFRASTRUCTURE,
                'confidence': 0.8,
                'evidence_template': 'High resource utilization detected',
                'recommendations': [
                    'Scale up infrastructure resources',
                    'Optimize resource-intensive processes',
                    'Implement resource monitoring and alerting'
                ]
            },
            {
                'name': 'database_connection_errors',
                'conditions': {
                    'error_patterns': ['connection refused', 'timeout', 'connection pool'],
                    'components': ['database', 'db', 'sql']
                },
                'root_cause': RootCauseCategory.DATABASE,
                'confidence': 0.9,
                'evidence_template': 'Database connectivity issues detected',
                'recommendations': [
                    'Check database server health',
                    'Verify connection pool configuration',
                    'Review database performance metrics'
                ]
            },
            {
                'name': 'network_connectivity',
                'conditions': {
                    'error_patterns': ['network unreachable', 'dns resolution', 'connection timeout'],
                    'metrics': ['network_latency', 'packet_loss']
                },
                'root_cause': RootCauseCategory.NETWORK,
                'confidence': 0.85,
                'evidence_template': 'Network connectivity issues detected',
                'recommendations': [
                    'Check network infrastructure',
                    'Verify DNS configuration',
                    'Review firewall and routing rules'
                ]
            },
            {
                'name': 'application_errors',
                'conditions': {
                    'error_patterns': ['null pointer', 'index out of bounds', 'stack overflow'],
                    'log_levels': ['ERROR', 'FATAL']
                },
                'root_cause': RootCauseCategory.APPLICATION,
                'confidence': 0.75,
                'evidence_template': 'Application errors detected in logs',
                'recommendations': [
                    'Review application logs for detailed error information',
                    'Check recent code deployments',
                    'Verify application configuration'
                ]
            },
            {
                'name': 'external_service_dependency',
                'conditions': {
                    'error_patterns': ['service unavailable', 'api timeout', 'external service'],
                    'response_codes': [502, 503, 504]
                },
                'root_cause': RootCauseCategory.EXTERNAL_SERVICE,
                'confidence': 0.7,
                'evidence_template': 'External service dependency issues detected',
                'recommendations': [
                    'Check external service status',
                    'Implement circuit breaker patterns',
                    'Review service level agreements'
                ]
            }
        ]
    
    async def analyze_root_cause(self, alert_ids: List[str], alert_data: List[Dict[str, Any]]) -> RootCauseAnalysis:
        """Perform root cause analysis for given alerts"""
        analysis_id = str(uuid.uuid4())
        
        # Collect evidence from alerts
        evidence = self._collect_evidence(alert_data)
        
        # Apply decision rules
        root_cause_results = []
        for rule in self.decision_rules:
            result = self._apply_decision_rule(rule, evidence)
            if result:
                root_cause_results.append(result)
        
        # Select best root cause
        if root_cause_results:
            best_result = max(root_cause_results, key=lambda x: x['confidence'])
            root_cause_category = best_result['root_cause']
            confidence = best_result['confidence']
            description = best_result['description']
            recommendations = best_result['recommendations']
            evidence_list = best_result['evidence']
        else:
            # Fallback analysis
            root_cause_category = RootCauseCategory.APPLICATION
            confidence = 0.3
            description = "Unable to determine specific root cause"
            recommendations = ["Manual investigation required", "Review system logs", "Check recent changes"]
            evidence_list = [f"Alert: {alert.get('message', 'Unknown')}" for alert in alert_data[:3]]
        
        analysis = RootCauseAnalysis(
            analysis_id=analysis_id,
            alert_ids=alert_ids,
            root_cause_category=root_cause_category,
            confidence=confidence,
            description=description,
            evidence=evidence_list,
            recommendations=recommendations,
            timestamp=datetime.now(),
            metadata={'rules_applied': len(self.decision_rules), 'evidence_count': len(evidence)}
        )
        
        self.analysis_history.append(analysis)
        
        logger.info("Root cause analysis completed", 
                   analysis_id=analysis_id, 
                   root_cause=root_cause_category.value,
                   confidence=confidence)
        
        return analysis
    
    def _collect_evidence(self, alert_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Collect evidence from alert data"""
        evidence = {
            'error_messages': [],
            'metrics': {},
            'components': set(),
            'log_levels': set(),
            'response_codes': [],
            'timestamps': []
        }
        
        for alert in alert_data:
            # Extract error messages
            message = alert.get('message', '')
            if message:
                evidence['error_messages'].append(message.lower())
            
            # Extract metrics
            if 'metrics' in alert:
                for metric_name, value in alert['metrics'].items():
                    if metric_name not in evidence['metrics']:
                        evidence['metrics'][metric_name] = []
                    evidence['metrics'][metric_name].append(value)
            
            # Extract components
            component = alert.get('component', '')
            if component:
                evidence['components'].add(component.lower())
            
            # Extract log levels
            log_level = alert.get('log_level', alert.get('severity', ''))
            if log_level:
                evidence['log_levels'].add(log_level.upper())
            
            # Extract response codes
            response_code = alert.get('response_code', alert.get('status_code'))
            if response_code:
                evidence['response_codes'].append(int(response_code))
            
            # Extract timestamps
            timestamp = alert.get('timestamp')
            if timestamp:
                evidence['timestamps'].append(timestamp)
        
        return evidence
    
    def _apply_decision_rule(self, rule: Dict[str, Any], evidence: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Apply a decision rule to evidence"""
        conditions = rule['conditions']
        matches = 0
        total_conditions = 0
        evidence_list = []
        
        # Check error patterns
        if 'error_patterns' in conditions:
            total_conditions += 1
            error_messages = ' '.join(evidence['error_messages'])
            for pattern in conditions['error_patterns']:
                if pattern.lower() in error_messages:
                    matches += 1
                    evidence_list.append(f"Error pattern found: {pattern}")
                    break
        
        # Check component patterns
        if 'components' in conditions:
            total_conditions += 1
            for component_pattern in conditions['components']:
                if any(component_pattern in comp for comp in evidence['components']):
                    matches += 1
                    evidence_list.append(f"Component match: {component_pattern}")
                    break
        
        # Check metrics thresholds
        if 'metrics' in conditions and 'thresholds' in conditions:
            total_conditions += 1
            metric_matches = 0
            for metric_name, threshold in conditions['thresholds'].items():
                if metric_name in evidence['metrics']:
                    values = evidence['metrics'][metric_name]
                    if any(value > threshold for value in values):
                        metric_matches += 1
                        evidence_list.append(f"Metric threshold exceeded: {metric_name} > {threshold}")
            
            operator = conditions.get('operator', 'AND')
            if operator == 'OR' and metric_matches > 0:
                matches += 1
            elif operator == 'AND' and metric_matches == len(conditions['thresholds']):
                matches += 1
        
        # Check log levels
        if 'log_levels' in conditions:
            total_conditions += 1
            for log_level in conditions['log_levels']:
                if log_level in evidence['log_levels']:
                    matches += 1
                    evidence_list.append(f"Log level match: {log_level}")
                    break
        
        # Check response codes
        if 'response_codes' in conditions:
            total_conditions += 1
            for code in conditions['response_codes']:
                if code in evidence['response_codes']:
                    matches += 1
                    evidence_list.append(f"Response code match: {code}")
                    break
        
        # Calculate confidence based on matches
        if matches > 0 and total_conditions > 0:
            match_ratio = matches / total_conditions
            confidence = rule['confidence'] * match_ratio
            
            return {
                'root_cause': rule['root_cause'],
                'confidence': confidence,
                'description': rule['evidence_template'],
                'recommendations': rule['recommendations'],
                'evidence': evidence_list,
                'rule_name': rule['name']
            }
        
        return None

class CapacityPlanner:
    """Predictive capacity planning with time-series forecasting"""
    
    def __init__(self, forecast_horizon: timedelta = timedelta(days=7)):
        self.forecast_horizon = forecast_horizon
        self.metric_history: Dict[str, List[TimeSeriesPoint]] = defaultdict(list)
        self.capacity_thresholds: Dict[str, float] = {}
        self.forecasts: Dict[str, CapacityForecast] = {}
        
        # Default capacity thresholds
        self.capacity_thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_percent': 90.0,
            'network_utilization': 75.0,
            'connection_pool_usage': 80.0
        }
        
        logger.info("Capacity planner initialized", forecast_horizon=forecast_horizon)
    
    def add_metric_data(self, metric_name: str, point: TimeSeriesPoint):
        """Add metric data for forecasting"""
        self.metric_history[metric_name].append(point)
        
        # Keep only recent data (last 30 days)
        cutoff_time = datetime.now() - timedelta(days=30)
        self.metric_history[metric_name] = [
            p for p in self.metric_history[metric_name]
            if p.timestamp > cutoff_time
        ]
    
    def set_capacity_threshold(self, metric_name: str, threshold: float):
        """Set capacity threshold for a metric"""
        self.capacity_thresholds[metric_name] = threshold
        logger.info(f"Capacity threshold set: {metric_name} = {threshold}")
    
    async def generate_forecast(self, metric_name: str) -> Optional[CapacityForecast]:
        """Generate capacity forecast for a metric"""
        if metric_name not in self.metric_history:
            return None
        
        history = self.metric_history[metric_name]
        if len(history) < 24:  # Need at least 24 data points
            return None
        
        # Prepare time series data
        timestamps = [p.timestamp for p in history]
        values = [p.value for p in history]
        
        # Generate forecast using simple linear trend + seasonal components
        forecast_points = self._forecast_time_series(timestamps, values)
        
        # Calculate confidence intervals
        confidence_intervals = self._calculate_confidence_intervals(values, len(forecast_points))
        
        # Find capacity threshold breach
        threshold = self.capacity_thresholds.get(metric_name, 100.0)
        breach_time = self._find_threshold_breach(forecast_points, threshold)
        
        # Generate recommendations
        recommendations = self._generate_capacity_recommendations(metric_name, forecast_points, threshold, breach_time)
        
        forecast = CapacityForecast(
            forecast_id=str(uuid.uuid4()),
            metric_name=metric_name,
            component=history[-1].metadata.get('component', 'unknown'),
            forecast_horizon=self.forecast_horizon,
            predicted_values=forecast_points,
            confidence_intervals=confidence_intervals,
            capacity_threshold=threshold,
            predicted_breach_time=breach_time,
            recommendations=recommendations,
            timestamp=datetime.now()
        )
        
        self.forecasts[metric_name] = forecast
        
        logger.info("Capacity forecast generated", 
                   metric=metric_name, 
                   breach_time=breach_time,
                   recommendations_count=len(recommendations))
        
        return forecast
    
    def _forecast_time_series(self, timestamps: List[datetime], values: List[float]) -> List[Tuple[datetime, float]]:
        """Forecast time series using trend and seasonal decomposition"""
        if len(values) < 24:
            return []
        
        # Calculate trend using linear regression
        x_values = [(ts - timestamps[0]).total_seconds() for ts in timestamps]
        
        if SCIPY_AVAILABLE:
            slope, intercept, _, _, _ = stats.linregress(x_values, values)
        else:
            slope = self._calculate_slope_from_xy(x_values, values)
            intercept = statistics.mean(values) - slope * statistics.mean(x_values)
        
        # Extract seasonal component (daily pattern)
        seasonal_pattern = self._extract_seasonal_pattern(timestamps, values)
        
        # Generate forecast points
        forecast_points = []
        last_timestamp = timestamps[-1]
        forecast_interval = timedelta(hours=1)  # Hourly forecasts
        
        forecast_steps = int(self.forecast_horizon.total_seconds() / forecast_interval.total_seconds())
        
        for i in range(1, forecast_steps + 1):
            forecast_time = last_timestamp + (forecast_interval * i)
            
            # Trend component
            x_forecast = (forecast_time - timestamps[0]).total_seconds()
            trend_value = slope * x_forecast + intercept
            
            # Seasonal component
            hour = forecast_time.hour
            seasonal_value = seasonal_pattern.get(hour, 0.0)
            
            # Combine components
            forecast_value = max(0, trend_value + seasonal_value)
            
            forecast_points.append((forecast_time, forecast_value))
        
        return forecast_points
    
    def _extract_seasonal_pattern(self, timestamps: List[datetime], values: List[float]) -> Dict[int, float]:
        """Extract daily seasonal pattern"""
        hourly_values = defaultdict(list)
        
        for timestamp, value in zip(timestamps, values):
            hour = timestamp.hour
            hourly_values[hour].append(value)
        
        # Calculate average for each hour
        seasonal_pattern = {}
        overall_mean = statistics.mean(values)
        
        for hour in range(24):
            if hour in hourly_values:
                hour_mean = statistics.mean(hourly_values[hour])
                seasonal_pattern[hour] = hour_mean - overall_mean
            else:
                seasonal_pattern[hour] = 0.0
        
        return seasonal_pattern
    
    def _calculate_slope_from_xy(self, x_values: List[float], y_values: List[float]) -> float:
        """Calculate slope from x,y values"""
        n = len(x_values)
        if n < 2:
            return 0.0
        
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(y_values)
        
        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def _calculate_confidence_intervals(self, historical_values: List[float], forecast_length: int) -> List[Tuple[float, float]]:
        """Calculate confidence intervals for forecast"""
        if len(historical_values) < 2:
            return [(0.0, 0.0)] * forecast_length
        
        std_dev = statistics.stdev(historical_values)
        
        # Simple confidence intervals (±2 standard deviations)
        confidence_intervals = []
        for i in range(forecast_length):
            # Increase uncertainty over time
            uncertainty = std_dev * (1 + i * 0.1)
            confidence_intervals.append((-uncertainty, uncertainty))
        
        return confidence_intervals
    
    def _find_threshold_breach(self, forecast_points: List[Tuple[datetime, float]], threshold: float) -> Optional[datetime]:
        """Find when threshold will be breached"""
        for timestamp, value in forecast_points:
            if value >= threshold:
                return timestamp
        return None
    
    def _generate_capacity_recommendations(self, metric_name: str, forecast_points: List[Tuple[datetime, float]], threshold: float, breach_time: Optional[datetime]) -> List[str]:
        """Generate capacity planning recommendations"""
        recommendations = []
        
        if not forecast_points:
            return ["Insufficient data for capacity planning"]
        
        max_forecast_value = max(value for _, value in forecast_points)
        current_utilization = forecast_points[0][1] if forecast_points else 0
        
        if breach_time:
            time_to_breach = breach_time - datetime.now()
            recommendations.append(f"Capacity threshold will be breached in {time_to_breach}")
            
            if time_to_breach < timedelta(days=7):
                recommendations.append("URGENT: Scale up resources immediately")
            elif time_to_breach < timedelta(days=30):
                recommendations.append("Plan resource scaling within the next month")
            else:
                recommendations.append("Monitor capacity trends and plan scaling")
        
        # Metric-specific recommendations
        if metric_name == 'cpu_percent':
            if max_forecast_value > threshold:
                recommendations.extend([
                    "Consider adding more CPU cores or upgrading to higher-performance instances",
                    "Optimize CPU-intensive processes and algorithms",
                    "Implement CPU-based auto-scaling policies"
                ])
        elif metric_name == 'memory_percent':
            if max_forecast_value > threshold:
                recommendations.extend([
                    "Increase available memory or upgrade to memory-optimized instances",
                    "Optimize memory usage and implement memory pooling",
                    "Review memory leaks and garbage collection settings"
                ])
        elif metric_name == 'disk_percent':
            if max_forecast_value > threshold:
                recommendations.extend([
                    "Add additional storage capacity or upgrade to larger disks",
                    "Implement data archiving and cleanup policies",
                    "Consider using cloud storage for less frequently accessed data"
                ])
        
        # Growth rate analysis
        if len(forecast_points) > 1:
            growth_rate = (forecast_points[-1][1] - forecast_points[0][1]) / len(forecast_points)
            if growth_rate > 0:
                recommendations.append(f"Metric is growing at {growth_rate:.2f} units per hour")
        
        return recommendations
    
    def get_all_forecasts(self) -> Dict[str, CapacityForecast]:
        """Get all current forecasts"""
        return self.forecasts.copy()

class AdvancedAlertingAnalytics:
    """Main class coordinating all advanced alerting and analytics components"""
    
    def __init__(self):
        self.anomaly_detector = AnomalyDetector()
        self.correlation_engine = AlertCorrelationEngine()
        self.root_cause_analyzer = RootCauseAnalyzer()
        self.capacity_planner = CapacityPlanner()
        
        self.running = False
        self.analytics_thread = None
        
        logger.info("Advanced alerting analytics system initialized")
    
    async def start(self):
        """Start the analytics system"""
        if self.running:
            return
        
        self.running = True
        self.analytics_thread = threading.Thread(target=self._analytics_loop, daemon=True)
        self.analytics_thread.start()
        
        logger.info("Advanced alerting analytics system started")
    
    def stop(self):
        """Stop the analytics system"""
        self.running = False
        if self.analytics_thread:
            self.analytics_thread.join(timeout=5)
        
        logger.info("Advanced alerting analytics system stopped")
    
    def _analytics_loop(self):
        """Main analytics processing loop"""
        while self.running:
            try:
                # This would be replaced with actual metric ingestion
                # For now, just sleep
                time.sleep(10)
            except Exception as e:
                logger.error(f"Error in analytics loop: {e}")
                time.sleep(10)
    
    async def process_metric(self, metric_name: str, value: float, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a new metric value"""
        metadata = metadata or {}
        point = TimeSeriesPoint(
            timestamp=datetime.now(),
            value=value,
            metadata=metadata
        )
        
        # Add to anomaly detector
        self.anomaly_detector.add_data_point(metric_name, point)
        
        # Add to capacity planner
        self.capacity_planner.add_metric_data(metric_name, point)
        
        # Detect anomalies
        anomalies = self.anomaly_detector.detect_anomalies(metric_name, point)
        
        # Generate alerts for anomalies
        alerts = []
        for anomaly in anomalies:
            alert = {
                'alert_id': str(uuid.uuid4()),
                'metric_name': metric_name,
                'anomaly_type': anomaly.anomaly_type.value,
                'value': anomaly.value,
                'expected_value': anomaly.expected_value,
                'confidence': anomaly.confidence,
                'severity': anomaly.severity,
                'component': anomaly.component,
                'message': anomaly.description,
                'timestamp': anomaly.timestamp,
                'metadata': anomaly.metadata
            }
            alerts.append(alert)
            
            # Add to correlation engine
            correlations = self.correlation_engine.add_alert(alert)
        
        return {
            'metric_name': metric_name,
            'value': value,
            'anomalies_detected': len(anomalies),
            'alerts_generated': len(alerts),
            'timestamp': point.timestamp.isoformat()
        }
    
    async def analyze_alert_group(self, alert_ids: List[str], alert_data: List[Dict[str, Any]]) -> RootCauseAnalysis:
        """Perform root cause analysis on a group of alerts"""
        return await self.root_cause_analyzer.analyze_root_cause(alert_ids, alert_data)
    
    async def generate_capacity_forecast(self, metric_name: str) -> Optional[CapacityForecast]:
        """Generate capacity forecast for a metric"""
        return await self.capacity_planner.generate_forecast(metric_name)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        return {
            'running': self.running,
            'anomaly_detector': {
                'metrics_tracked': len(self.anomaly_detector.metric_history),
                'baseline_stats': len(self.anomaly_detector.baseline_stats)
            },
            'correlation_engine': {
                'active_correlations': len(self.correlation_engine.active_correlations),
                'correlation_rules': len(self.correlation_engine.correlation_rules)
            },
            'root_cause_analyzer': {
                'analysis_history': len(self.root_cause_analyzer.analysis_history),
                'decision_rules': len(self.root_cause_analyzer.decision_rules)
            },
            'capacity_planner': {
                'metrics_tracked': len(self.capacity_planner.metric_history),
                'active_forecasts': len(self.capacity_planner.forecasts),
                'capacity_thresholds': len(self.capacity_planner.capacity_thresholds)
            }
        }

# Example usage and testing
if __name__ == "__main__":
    async def main():
        analytics = AdvancedAlertingAnalytics()
        await analytics.start()
        
        # Simulate some metrics
        for i in range(100):
            cpu_value = 50 + 30 * math.sin(i * 0.1) + random.gauss(0, 5)
            result = await analytics.process_metric('cpu_percent', cpu_value, {'component': 'web-server'})
            print(f"Processed metric: {result}")
            
            if i % 20 == 0:
                forecast = await analytics.generate_capacity_forecast('cpu_percent')
                if forecast:
                    print(f"Generated forecast: {forecast.forecast_id}")
            
            await asyncio.sleep(0.1)
        
        status = analytics.get_system_status()
        print(f"System status: {status}")
        
        analytics.stop()
    
    asyncio.run(main())

logger = structlog.get_logger(__name__)

class AnomalyType(Enum):
    """Types of anomalies detected"""
    SPIKE = "SPIKE"
    DIP = "DIP"
    TREND_CHANGE = "TREND_CHANGE"
    SEASONAL_DEVIATION = "SEASONAL_DEVIATION"
    OUTLIER = "OUTLIER"
    PATTERN_BREAK = "PATTERN_BREAK"

class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# RootCauseCategory already defined above

@dataclass
class MetricDataPoint:
    """Single metric data point"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TimeSeries:
    """Time series data structure"""
    metric_name: str
    data_points: List[MetricDataPoint]
    labels: Dict[str, str] = field(default_factory=dict)
    
    def get_values(self) -> List[float]:
        """Get just the values"""
        return [dp.value for dp in self.data_points]
    
    def get_timestamps(self) -> List[float]:
        """Get just the timestamps"""
        return [dp.timestamp for dp in self.data_points]
    
    def get_recent_values(self, duration_seconds: int) -> List[float]:
        """Get values from the last N seconds"""
        cutoff_time = time.time() - duration_seconds
        return [dp.value for dp in self.data_points if dp.timestamp >= cutoff_time]

@dataclass
class Anomaly:
    """Detected anomaly"""
    anomaly_id: str
    metric_name: str
    anomaly_type: AnomalyType
    timestamp: float
    value: float
    expected_value: Optional[float]
    confidence: float
    severity: AlertSeverity
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Alert:
    """Enhanced alert with correlation info"""
    alert_id: str
    name: str
    severity: AlertSeverity
    message: str
    component: str
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Correlation and analysis fields
    correlation_id: Optional[str] = None
    related_alerts: List[str] = field(default_factory=list)
    root_cause: Optional[RootCauseCategory] = None
    root_cause_confidence: float = 0.0
    root_cause_explanation: str = ""
    anomalies: List[str] = field(default_factory=list)

@dataclass
class CapacityForecast:
    """Capacity planning forecast"""
    metric_name: str
    current_value: float
    predicted_values: List[Tuple[float, float]]  # (timestamp, predicted_value)
    capacity_threshold: float
    time_to_threshold: Optional[float]  # seconds until threshold reached
    confidence_interval: Tuple[float, float]
    trend: str  # "increasing", "decreasing", "stable"
    seasonality_detected: bool
    recommendations: List[str]

class AnomalyDetector:
    """Machine learning-based anomaly detection"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.time_series_data: Dict[str, TimeSeries] = {}
        self.anomaly_history: Dict[str, List[Anomaly]] = defaultdict(list)
        
        # Detection parameters
        self.window_size = self.config.get('window_size', 100)
        self.sensitivity = self.config.get('sensitivity', 2.0)  # Standard deviations
        self.min_data_points = self.config.get('min_data_points', 20)
        
        logger.info("Anomaly detector initialized", config=self.config)
    
    def add_metric_data(self, metric_name: str, value: float, 
                       labels: Optional[Dict[str, str]] = None,
                       metadata: Optional[Dict[str, Any]] = None):
        """Add a new metric data point"""
        data_point = MetricDataPoint(
            timestamp=time.time(),
            value=value,
            labels=labels or {},
            metadata=metadata or {}
        )
        
        if metric_name not in self.time_series_data:
            self.time_series_data[metric_name] = TimeSeries(
                metric_name=metric_name,
                data_points=[],
                labels=labels or {}
            )
        
        time_series = self.time_series_data[metric_name]
        time_series.data_points.append(data_point)
        
        # Keep only recent data points
        cutoff_time = time.time() - 3600  # Keep 1 hour of data
        time_series.data_points = [
            dp for dp in time_series.data_points 
            if dp.timestamp >= cutoff_time
        ]
    
    def detect_anomalies(self, metric_name: str) -> List[Anomaly]:
        """Detect anomalies in a metric"""
        if metric_name not in self.time_series_data:
            return []
        
        time_series = self.time_series_data[metric_name]
        if len(time_series.data_points) < self.min_data_points:
            return []
        
        anomalies = []
        values = time_series.get_values()
        timestamps = time_series.get_timestamps()
        
        # Statistical anomaly detection
        anomalies.extend(self._detect_statistical_anomalies(
            metric_name, values, timestamps
        ))
        
        # Trend change detection
        anomalies.extend(self._detect_trend_changes(
            metric_name, values, timestamps
        ))
        
        # Store detected anomalies
        self.anomaly_history[metric_name].extend(anomalies)
        
        return anomalies
    
    def _detect_statistical_anomalies(self, metric_name: str, 
                                    values: List[float], 
                                    timestamps: List[float]) -> List[Anomaly]:
        """Detect statistical outliers"""
        anomalies = []
        
        if len(values) < self.min_data_points:
            return anomalies
        
        # Use recent window for baseline
        window_values = values[-self.window_size:]
        
        if SCIPY_AVAILABLE:
            # Use scipy for more accurate statistics
            mean = np.mean(window_values[:-1])  # Exclude current value
            std = np.std(window_values[:-1])
        else:
            # Fallback implementation
            mean = statistics.mean(window_values[:-1])
            std = statistics.stdev(window_values[:-1]) if len(window_values) > 1 else 0
        
        current_value = values[-1]
        current_timestamp = timestamps[-1]
        
        if std > 0:
            z_score = abs(current_value - mean) / std
            
            if z_score > self.sensitivity:
                anomaly_type = AnomalyType.SPIKE if current_value > mean else AnomalyType.DIP
                confidence = min(z_score / self.sensitivity, 1.0)
                
                severity = AlertSeverity.CRITICAL if z_score > 4 else \
                          AlertSeverity.ERROR if z_score > 3 else \
                          AlertSeverity.WARNING
                
                anomaly = Anomaly(
                    anomaly_id=f"anomaly_{uuid.uuid4().hex[:8]}",
                    metric_name=metric_name,
                    anomaly_type=anomaly_type,
                    timestamp=current_timestamp,
                    value=current_value,
                    expected_value=mean,
                    confidence=confidence,
                    severity=severity,
                    description=f"{anomaly_type.value} detected: {current_value:.2f} (expected ~{mean:.2f}, z-score: {z_score:.2f})",
                    metadata={
                        'z_score': z_score,
                        'mean': mean,
                        'std': std,
                        'window_size': len(window_values)
                    }
                )
                
                anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_trend_changes(self, metric_name: str, 
                            values: List[float], 
                            timestamps: List[float]) -> List[Anomaly]:
        """Detect significant trend changes"""
        anomalies = []
        
        if len(values) < 30:  # Need enough data for trend analysis
            return anomalies
        
        # Split data into two halves
        mid_point = len(values) // 2
        first_half = values[:mid_point]
        second_half = values[mid_point:]
        
        if SCIPY_AVAILABLE:
            # Calculate linear regression slopes
            x1 = np.arange(len(first_half))
            x2 = np.arange(len(second_half))
            
            slope1, _, _, _, _ = stats.linregress(x1, first_half)
            slope2, _, _, _, _ = stats.linregress(x2, second_half)
        else:
            # Simple slope calculation
            def calculate_slope(y_values):
                if len(y_values) < 2:
                    return 0
                x_values = list(range(len(y_values)))
                n = len(y_values)
                sum_x = sum(x_values)
                sum_y = sum(y_values)
                sum_xy = sum(x * y for x, y in zip(x_values, y_values))
                sum_x2 = sum(x * x for x in x_values)
                
                denominator = n * sum_x2 - sum_x * sum_x
                if denominator == 0:
                    return 0
                return (n * sum_xy - sum_x * sum_y) / denominator
            
            slope1 = calculate_slope(first_half)
            slope2 = calculate_slope(second_half)
        
        # Check for significant slope change
        slope_change = abs(slope2 - slope1)
        if slope_change > 0.1:  # Threshold for significant change
            anomaly = Anomaly(
                anomaly_id=f"trend_{uuid.uuid4().hex[:8]}",
                metric_name=metric_name,
                anomaly_type=AnomalyType.TREND_CHANGE,
                timestamp=timestamps[-1],
                value=values[-1],
                expected_value=None,
                confidence=min(slope_change / 0.5, 1.0),
                severity=AlertSeverity.WARNING,
                description=f"Trend change detected: slope changed from {slope1:.4f} to {slope2:.4f}",
                metadata={
                    'slope_before': slope1,
                    'slope_after': slope2,
                    'slope_change': slope_change
                }
            )
            
            anomalies.append(anomaly)
        
        return anomalies
    
    def get_anomaly_summary(self) -> Dict[str, Any]:
        """Get summary of detected anomalies"""
        total_anomalies = sum(len(anomalies) for anomalies in self.anomaly_history.values())
        
        anomaly_types = defaultdict(int)
        severity_counts = defaultdict(int)
        
        for anomalies in self.anomaly_history.values():
            for anomaly in anomalies:
                anomaly_types[anomaly.anomaly_type.value] += 1
                severity_counts[anomaly.severity.value] += 1
        
        return {
            'total_anomalies': total_anomalies,
            'metrics_monitored': len(self.time_series_data),
            'anomaly_types': dict(anomaly_types),
            'severity_distribution': dict(severity_counts),
            'detection_window_size': self.window_size,
            'sensitivity': self.sensitivity
        }

class AlertCorrelationEngine:
    """Intelligent alert correlation and deduplication"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.alerts: Dict[str, Alert] = {}
        self.correlation_groups: Dict[str, List[str]] = {}  # correlation_id -> alert_ids
        self.correlation_rules: List[Dict[str, Any]] = []
        
        # Correlation parameters
        self.time_window = self.config.get('correlation_time_window', 300)  # 5 minutes
        self.similarity_threshold = self.config.get('similarity_threshold', 0.7)
        
        self._load_correlation_rules()
        
        logger.info("Alert correlation engine initialized")
    
    def _load_correlation_rules(self):
        """Load alert correlation rules"""
        # Default correlation rules
        self.correlation_rules = [
            {
                'name': 'service_dependency',
                'conditions': [
                    {'field': 'component', 'operator': 'different'},
                    {'field': 'timestamp', 'operator': 'within', 'value': 60}  # 1 minute
                ],
                'weight': 0.8
            },
            {
                'name': 'same_component',
                'conditions': [
                    {'field': 'component', 'operator': 'equals'},
                    {'field': 'timestamp', 'operator': 'within', 'value': 300}  # 5 minutes
                ],
                'weight': 0.9
            },
            {
                'name': 'similar_message',
                'conditions': [
                    {'field': 'message', 'operator': 'similar', 'threshold': 0.7},
                    {'field': 'timestamp', 'operator': 'within', 'value': 180}  # 3 minutes
                ],
                'weight': 0.6
            }
        ]
    
    def add_alert(self, alert: Alert) -> str:
        """Add an alert and perform correlation"""
        self.alerts[alert.alert_id] = alert
        
        # Find correlations with existing alerts
        correlations = self._find_correlations(alert)
        
        if correlations:
            # Create or update correlation group
            correlation_id = self._create_correlation_group(alert, correlations)
            alert.correlation_id = correlation_id
        
        logger.info("Alert added", alert_id=alert.alert_id, 
                   correlations=len(correlations), 
                   correlation_id=alert.correlation_id)
        
        return alert.alert_id
    
    def _find_correlations(self, new_alert: Alert) -> List[str]:
        """Find correlated alerts"""
        correlations = []
        
        # Get recent alerts within time window
        cutoff_time = new_alert.timestamp - timedelta(seconds=self.time_window)
        recent_alerts = [
            alert for alert in self.alerts.values()
            if alert.timestamp >= cutoff_time and alert.alert_id != new_alert.alert_id
        ]
        
        for alert in recent_alerts:
            similarity_score = self._calculate_similarity(new_alert, alert)
            
            if similarity_score >= self.similarity_threshold:
                correlations.append(alert.alert_id)
        
        return correlations
    
    def _calculate_similarity(self, alert1: Alert, alert2: Alert) -> float:
        """Calculate similarity score between two alerts"""
        total_weight = 0
        weighted_score = 0
        
        for rule in self.correlation_rules:
            rule_score = self._evaluate_correlation_rule(alert1, alert2, rule)
            weight = rule['weight']
            
            weighted_score += rule_score * weight
            total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0
    
    def _evaluate_correlation_rule(self, alert1: Alert, alert2: Alert, 
                                 rule: Dict[str, Any]) -> float:
        """Evaluate a single correlation rule"""
        score = 1.0
        
        for condition in rule['conditions']:
            field = condition['field']
            operator = condition['operator']
            
            if field == 'component':
                if operator == 'equals':
                    if alert1.component != alert2.component:
                        score = 0
                elif operator == 'different':
                    if alert1.component == alert2.component:
                        score *= 0.5  # Reduce score but don't eliminate
            
            elif field == 'timestamp':
                if operator == 'within':
                    time_diff = abs((alert1.timestamp - alert2.timestamp).total_seconds())
                    max_diff = condition['value']
                    if time_diff > max_diff:
                        score = 0
                    else:
                        # Closer in time = higher score
                        score *= (max_diff - time_diff) / max_diff
            
            elif field == 'message':
                if operator == 'similar':
                    similarity = self._calculate_text_similarity(alert1.message, alert2.message)
                    threshold = condition.get('threshold', 0.7)
                    if similarity < threshold:
                        score = 0
                    else:
                        score *= similarity
        
        return score
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using simple word overlap"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _create_correlation_group(self, new_alert: Alert, 
                                correlated_alert_ids: List[str]) -> str:
        """Create or update a correlation group"""
        # Check if any correlated alerts already have a correlation ID
        existing_correlation_id = None
        for alert_id in correlated_alert_ids:
            alert = self.alerts[alert_id]
            if alert.correlation_id:
                existing_correlation_id = alert.correlation_id
                break
        
        if existing_correlation_id:
            # Add to existing group
            correlation_id = existing_correlation_id
            self.correlation_groups[correlation_id].append(new_alert.alert_id)
        else:
            # Create new group
            correlation_id = f"corr_{uuid.uuid4().hex[:8]}"
            self.correlation_groups[correlation_id] = [new_alert.alert_id] + correlated_alert_ids
            
            # Update correlation IDs for all alerts in the group
            for alert_id in correlated_alert_ids:
                self.alerts[alert_id].correlation_id = correlation_id
        
        # Update related alerts lists
        for alert_id in self.correlation_groups[correlation_id]:
            alert = self.alerts[alert_id]
            alert.related_alerts = [
                aid for aid in self.correlation_groups[correlation_id] 
                if aid != alert_id
            ]
        
        return correlation_id
    
    def get_correlation_summary(self) -> Dict[str, Any]:
        """Get correlation summary"""
        total_alerts = len(self.alerts)
        correlated_alerts = len([a for a in self.alerts.values() if a.correlation_id])
        correlation_groups = len(self.correlation_groups)
        
        return {
            'total_alerts': total_alerts,
            'correlated_alerts': correlated_alerts,
            'correlation_groups': correlation_groups,
            'correlation_rate': correlated_alerts / total_alerts if total_alerts > 0 else 0,
            'time_window': self.time_window,
            'similarity_threshold': self.similarity_threshold
        }