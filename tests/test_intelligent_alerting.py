"""
Tests for Intelligent Alerting System
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from nautilus_trader_engine.monitoring.intelligent_alerting import (
    IntelligentAlertingSystem,
    AlertEvaluator,
    RootCauseAnalyzer,
    AlertCorrelator,
    RecommendationEngine,
    ThresholdAnomalyDetector,
    StatisticalAnomalyDetector,
    TrendAnomalyDetector,
    Alert,
    AlertRule,
    MetricData,
    AlertSeverity,
    AlertStatus,
    AlertCategory,
    AnomalyType,
    create_threshold_rule,
    create_anomaly_rule
)


class TestAnomalyDetectors:
    """Test anomaly detection algorithms"""
    
    def test_threshold_detector_greater_than(self):
        """Test threshold detector with greater than condition"""
        detector = ThresholdAnomalyDetector(100.0, ">")
        
        # Test data below threshold
        data_below = [MetricData("test", 50.0, datetime.now())]
        result = asyncio.run(detector.detect_anomaly(data_below))
        assert result[0] is False  # No anomaly
        assert result[1] == 0.0    # No confidence
        
        # Test data above threshold
        data_above = [MetricData("test", 150.0, datetime.now())]
        result = asyncio.run(detector.detect_anomaly(data_above))
        assert result[0] is True   # Anomaly detected
        assert result[1] == 1.0    # Full confidence
    
    def test_threshold_detector_less_than(self):
        """Test threshold detector with less than condition"""
        detector = ThresholdAnomalyDetector(100.0, "<")
        
        # Test data above threshold
        data_above = [MetricData("test", 150.0, datetime.now())]
        result = asyncio.run(detector.detect_anomaly(data_above))
        assert result[0] is False
        
        # Test data below threshold
        data_below = [MetricData("test", 50.0, datetime.now())]
        result = asyncio.run(detector.detect_anomaly(data_below))
        assert result[0] is True
    
    def test_statistical_detector_insufficient_data(self):
        """Test statistical detector with insufficient data"""
        detector = StatisticalAnomalyDetector(z_threshold=2.0, min_samples=10)
        
        # Too few samples
        data = [MetricData("test", float(i), datetime.now()) for i in range(5)]
        result = asyncio.run(detector.detect_anomaly(data))
        assert result[0] is False
        assert "Insufficient data" in result[2]
    
    def test_statistical_detector_normal_data(self):
        """Test statistical detector with normal data"""
        detector = StatisticalAnomalyDetector(z_threshold=2.0, min_samples=10)
        
        # Normal data (mean ~50, std ~5)
        data = [MetricData("test", 50.0 + i * 0.1, datetime.now()) for i in range(20)]
        result = asyncio.run(detector.detect_anomaly(data))
        assert result[0] is False  # Should not detect anomaly
    
    def test_statistical_detector_anomalous_data(self):
        """Test statistical detector with anomalous data"""
        detector = StatisticalAnomalyDetector(z_threshold=2.0, min_samples=10)
        
        # Normal data with one outlier
        data = [MetricData("test", 50.0, datetime.now()) for _ in range(19)]
        data.append(MetricData("test", 200.0, datetime.now()))  # Outlier
        
        result = asyncio.run(detector.detect_anomaly(data))
        assert result[0] is True   # Should detect anomaly
        assert result[1] > 0.5     # Should have confidence
    
    def test_trend_detector_insufficient_data(self):
        """Test trend detector with insufficient data"""
        detector = TrendAnomalyDetector(trend_threshold=0.1, min_samples=5)
        
        data = [MetricData("test", float(i), datetime.now()) for i in range(3)]
        result = asyncio.run(detector.detect_anomaly(data))
        assert result[0] is False
        assert "Insufficient data" in result[2]
    
    def test_trend_detector_strong_trend(self):
        """Test trend detector with strong trend"""
        detector = TrendAnomalyDetector(trend_threshold=0.1, min_samples=5)
        
        # Strong upward trend
        data = [MetricData("test", float(i * 10), datetime.now()) for i in range(10)]
        result = asyncio.run(detector.detect_anomaly(data))
        assert result[0] is True   # Should detect trend anomaly
        assert "trend detected" in result[2]


class TestAlertEvaluator:
    """Test alert rule evaluation"""
    
    @pytest.fixture
    def evaluator(self):
        return AlertEvaluator()
    
    @pytest.fixture
    def threshold_rule(self):
        return AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            description="Test threshold rule",
            metric_name="test_metric",
            condition="> 100",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.PERFORMANCE,
            threshold_value=100.0
        )
    
    @pytest.fixture
    def anomaly_rule(self):
        return AlertRule(
            rule_id="anomaly_rule",
            name="Anomaly Rule",
            description="Test anomaly rule",
            metric_name="test_metric",
            condition="anomaly",
            severity=AlertSeverity.MEDIUM,
            category=AlertCategory.PERFORMANCE
        )
    
    @pytest.mark.asyncio
    async def test_evaluate_threshold_rule_no_violation(self, evaluator, threshold_rule):
        """Test threshold rule evaluation with no violation"""
        data = [MetricData("test_metric", 50.0, datetime.now())]
        
        alert = await evaluator.evaluate_rule(threshold_rule, data)
        assert alert is None
    
    @pytest.mark.asyncio
    async def test_evaluate_threshold_rule_violation(self, evaluator, threshold_rule):
        """Test threshold rule evaluation with violation"""
        data = [MetricData("test_metric", 150.0, datetime.now())]
        
        alert = await evaluator.evaluate_rule(threshold_rule, data)
        assert alert is not None
        assert alert.severity == AlertSeverity.HIGH
        assert alert.category == AlertCategory.PERFORMANCE
        assert alert.metric_name == "test_metric"
        assert alert.metric_value == 150.0
        assert alert.anomaly_type == AnomalyType.THRESHOLD
    
    @pytest.mark.asyncio
    async def test_evaluate_disabled_rule(self, evaluator, threshold_rule):
        """Test evaluation of disabled rule"""
        threshold_rule.enabled = False
        data = [MetricData("test_metric", 150.0, datetime.now())]
        
        alert = await evaluator.evaluate_rule(threshold_rule, data)
        assert alert is None
    
    @pytest.mark.asyncio
    async def test_evaluate_anomaly_rule(self, evaluator, anomaly_rule):
        """Test anomaly rule evaluation"""
        # Create data with anomaly
        data = [MetricData("test_metric", 50.0, datetime.now()) for _ in range(19)]
        data.append(MetricData("test_metric", 200.0, datetime.now()))  # Outlier
        
        alert = await evaluator.evaluate_rule(anomaly_rule, data)
        assert alert is not None
        assert alert.anomaly_type == AnomalyType.STATISTICAL
        assert alert.confidence_score > 0
    
    def test_parse_threshold_condition(self, evaluator):
        """Test threshold condition parsing"""
        # Test different operators
        assert evaluator._parse_threshold_condition("> 100") == (100.0, ">")
        assert evaluator._parse_threshold_condition("< 50.5") == (50.5, "<")
        assert evaluator._parse_threshold_condition(">= 75") == (75.0, ">=")
        assert evaluator._parse_threshold_condition("<= 25.25") == (25.25, "<=")
        
        # Test invalid condition
        with pytest.raises(ValueError):
            evaluator._parse_threshold_condition("invalid condition")


class TestRootCauseAnalyzer:
    """Test root cause analysis"""
    
    @pytest.fixture
    def analyzer(self):
        return RootCauseAnalyzer()
    
    @pytest.fixture
    def sample_alert(self):
        return Alert(
            alert_id="test_alert",
            title="High CPU Usage",
            description="CPU usage is high",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.PERFORMANCE,
            source="test",
            metric_name="cpu.usage",
            metric_value=95.0
        )
    
    @pytest.mark.asyncio
    async def test_analyze_root_cause_empty_data(self, analyzer, sample_alert):
        """Test root cause analysis with empty data"""
        root_causes = await analyzer.analyze_root_cause(sample_alert, [], {})
        assert isinstance(root_causes, list)
    
    @pytest.mark.asyncio
    async def test_analyze_correlated_alerts(self, analyzer, sample_alert):
        """Test correlated alerts analysis"""
        # Create related alerts
        related_alerts = [
            Alert(
                alert_id="related_1",
                title="High Memory Usage",
                description="Memory usage is high",
                severity=AlertSeverity.HIGH,
                category=AlertCategory.PERFORMANCE,  # Same category
                source="test",
                created_at=sample_alert.created_at - timedelta(minutes=2)
            ),
            Alert(
                alert_id="related_2",
                title="Disk Space Low",
                description="Disk space is low",
                severity=AlertSeverity.MEDIUM,
                category=AlertCategory.SYSTEM,  # Different category
                source="test",
                created_at=sample_alert.created_at - timedelta(minutes=1)
            )
        ]
        
        causes = await analyzer._analyze_correlated_alerts(sample_alert, related_alerts)
        assert len(causes) > 0
        assert any("Correlated" in cause for cause in causes)
    
    @pytest.mark.asyncio
    async def test_analyze_known_patterns(self, analyzer):
        """Test known pattern analysis"""
        # Trading latency alert
        trading_alert = Alert(
            alert_id="trading_alert",
            title="High Trading Latency",
            description="Trading latency is high",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.TRADING,
            source="test",
            metric_name="trading.latency"
        )
        
        causes = await analyzer._analyze_known_patterns(trading_alert, {})
        assert len(causes) > 0
        assert any("latency" in cause.lower() for cause in causes)
        
        # Memory alert
        memory_alert = Alert(
            alert_id="memory_alert",
            title="High Memory Usage",
            description="Memory usage is high",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.PERFORMANCE,
            source="test",
            metric_name="system.memory.usage"
        )
        
        causes = await analyzer._analyze_known_patterns(memory_alert, {})
        assert len(causes) > 0
        assert any("memory" in cause.lower() for cause in causes)


class TestAlertCorrelator:
    """Test alert correlation and deduplication"""
    
    @pytest.fixture
    def correlator(self):
        return AlertCorrelator(correlation_window=timedelta(minutes=10))
    
    @pytest.fixture
    def base_alert(self):
        return Alert(
            alert_id="base_alert",
            title="High CPU Usage",
            description="CPU usage is high",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.PERFORMANCE,
            source="test",
            metric_name="cpu.usage",
            tags={"host": "server1", "env": "prod"}
        )
    
    @pytest.mark.asyncio
    async def test_correlate_alerts_same_category(self, correlator, base_alert):
        """Test alert correlation with same category"""
        similar_alert = Alert(
            alert_id="similar_alert",
            title="High Memory Usage",
            description="Memory usage is high",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.PERFORMANCE,  # Same category
            source="test",
            metric_name="memory.usage",
            tags={"host": "server1", "env": "prod"},  # Same tags
            created_at=base_alert.created_at + timedelta(minutes=2)
        )
        
        correlated = await correlator.correlate_alerts(base_alert, [similar_alert])
        assert len(correlated) > 0
        assert similar_alert.alert_id in correlated
    
    @pytest.mark.asyncio
    async def test_correlate_alerts_outside_window(self, correlator, base_alert):
        """Test alert correlation outside time window"""
        old_alert = Alert(
            alert_id="old_alert",
            title="High CPU Usage",
            description="CPU usage is high",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.PERFORMANCE,
            source="test",
            metric_name="cpu.usage",
            created_at=base_alert.created_at - timedelta(hours=1)  # Outside window
        )
        
        correlated = await correlator.correlate_alerts(base_alert, [old_alert])
        assert len(correlated) == 0
    
    @pytest.mark.asyncio
    async def test_deduplicate_alert_exact_match(self, correlator, base_alert):
        """Test alert deduplication with exact match"""
        duplicate_alert = Alert(
            alert_id="duplicate_alert",
            title="High CPU Usage",
            description="CPU usage is high",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.PERFORMANCE,
            source="test",
            metric_name="cpu.usage",  # Same metric
            tags={"host": "server1", "env": "prod"},  # Same tags
            created_at=base_alert.created_at + timedelta(minutes=2)
        )
        
        should_deduplicate = await correlator.deduplicate_alert(duplicate_alert, [base_alert])
        assert should_deduplicate is True
    
    @pytest.mark.asyncio
    async def test_deduplicate_alert_different_metric(self, correlator, base_alert):
        """Test alert deduplication with different metric"""
        different_alert = Alert(
            alert_id="different_alert",
            title="High Memory Usage",
            description="Memory usage is high",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.PERFORMANCE,
            source="test",
            metric_name="memory.usage",  # Different metric
            tags={"host": "server1", "env": "prod"},
            created_at=base_alert.created_at + timedelta(minutes=2)
        )
        
        should_deduplicate = await correlator.deduplicate_alert(different_alert, [base_alert])
        assert should_deduplicate is False


class TestRecommendationEngine:
    """Test recommendation generation"""
    
    @pytest.fixture
    def engine(self):
        return RecommendationEngine()
    
    @pytest.mark.asyncio
    async def test_generate_recommendations_performance_alert(self, engine):
        """Test recommendations for performance alert"""
        alert = Alert(
            alert_id="perf_alert",
            title="High CPU Usage",
            description="CPU usage is high",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.PERFORMANCE,
            source="test"
        )
        
        recommendations = await engine.generate_recommendations(alert, [])
        assert len(recommendations) > 0
        assert any("resource" in rec.lower() for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_generate_recommendations_trading_alert(self, engine):
        """Test recommendations for trading alert"""
        alert = Alert(
            alert_id="trading_alert",
            title="High Trading Latency",
            description="Trading latency is high",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.TRADING,
            source="test"
        )
        
        recommendations = await engine.generate_recommendations(alert, [])
        assert len(recommendations) > 0
        assert any("market data" in rec.lower() or "trading" in rec.lower() for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_generate_recommendations_with_root_causes(self, engine):
        """Test recommendations with root causes"""
        alert = Alert(
            alert_id="alert_with_causes",
            title="System Alert",
            description="System issue detected",
            severity=AlertSeverity.HIGH,
            category=AlertCategory.SYSTEM,
            source="test"
        )
        
        root_causes = ["High memory usage detected", "Network latency increased"]
        recommendations = await engine.generate_recommendations(alert, root_causes)
        
        assert len(recommendations) > 0
        # Should include recommendations for both memory and network issues
        memory_recs = [rec for rec in recommendations if "memory" in rec.lower()]
        network_recs = [rec for rec in recommendations if "network" in rec.lower()]
        
        assert len(memory_recs) > 0
        assert len(network_recs) > 0


class TestIntelligentAlertingSystem:
    """Test the main alerting system"""
    
    @pytest.fixture
    def alerting_system(self):
        return IntelligentAlertingSystem()
    
    @pytest.fixture
    def sample_rule(self):
        return create_threshold_rule(
            "cpu_high", "High CPU Usage", "cpu.usage", 
            80.0, ">", AlertSeverity.HIGH, AlertCategory.SYSTEM
        )
    
    @pytest.mark.asyncio
    async def test_add_alert_rule(self, alerting_system, sample_rule):
        """Test adding alert rule"""
        result = await alerting_system.add_alert_rule(sample_rule)
        assert result is True
        assert sample_rule.rule_id in alerting_system.alert_rules
    
    @pytest.mark.asyncio
    async def test_remove_alert_rule(self, alerting_system, sample_rule):
        """Test removing alert rule"""
        await alerting_system.add_alert_rule(sample_rule)
        
        result = await alerting_system.remove_alert_rule(sample_rule.rule_id)
        assert result is True
        assert sample_rule.rule_id not in alerting_system.alert_rules
    
    @pytest.mark.asyncio
    async def test_ingest_metric_no_alert(self, alerting_system, sample_rule):
        """Test metric ingestion without triggering alert"""
        await alerting_system.add_alert_rule(sample_rule)
        
        # Metric below threshold
        metric = MetricData("cpu.usage", 50.0, datetime.now())
        await alerting_system.ingest_metric(metric)
        
        # Should not create alert
        active_alerts = await alerting_system.get_active_alerts()
        assert len(active_alerts) == 0
    
    @pytest.mark.asyncio
    async def test_ingest_metric_with_alert(self, alerting_system, sample_rule):
        """Test metric ingestion that triggers alert"""
        await alerting_system.add_alert_rule(sample_rule)
        
        # Metric above threshold
        metric = MetricData("cpu.usage", 95.0, datetime.now())
        await alerting_system.ingest_metric(metric)
        
        # Should create alert
        active_alerts = await alerting_system.get_active_alerts()
        assert len(active_alerts) == 1
        assert active_alerts[0].metric_name == "cpu.usage"
        assert active_alerts[0].severity == AlertSeverity.HIGH
    
    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, alerting_system, sample_rule):
        """Test alert acknowledgment"""
        await alerting_system.add_alert_rule(sample_rule)
        
        # Create alert
        metric = MetricData("cpu.usage", 95.0, datetime.now())
        await alerting_system.ingest_metric(metric)
        
        active_alerts = await alerting_system.get_active_alerts()
        alert_id = active_alerts[0].alert_id
        
        # Acknowledge alert
        result = await alerting_system.acknowledge_alert(alert_id, "test_user")
        assert result is True
        
        # Check status
        updated_alert = alerting_system.active_alerts[alert_id]
        assert updated_alert.status == AlertStatus.ACKNOWLEDGED
        assert updated_alert.acknowledged_by == "test_user"
    
    @pytest.mark.asyncio
    async def test_resolve_alert(self, alerting_system, sample_rule):
        """Test alert resolution"""
        await alerting_system.add_alert_rule(sample_rule)
        
        # Create alert
        metric = MetricData("cpu.usage", 95.0, datetime.now())
        await alerting_system.ingest_metric(metric)
        
        active_alerts = await alerting_system.get_active_alerts()
        alert_id = active_alerts[0].alert_id
        
        # Resolve alert
        result = await alerting_system.resolve_alert(alert_id)
        assert result is True
        
        # Should be removed from active alerts
        active_alerts = await alerting_system.get_active_alerts()
        assert len(active_alerts) == 0
    
    @pytest.mark.asyncio
    async def test_get_alert_statistics(self, alerting_system, sample_rule):
        """Test alert statistics"""
        await alerting_system.add_alert_rule(sample_rule)
        
        # Create some alerts
        for i in range(3):
            metric = MetricData("cpu.usage", 95.0 + i, datetime.now())
            await alerting_system.ingest_metric(metric)
        
        stats = await alerting_system.get_alert_statistics()
        
        assert stats["active_alerts"] >= 1  # At least one due to deduplication
        assert stats["total_alerts"] >= 1
        assert stats["alert_rules"] == 1
        assert "severity_breakdown" in stats
        assert "category_breakdown" in stats
    
    @pytest.mark.asyncio
    async def test_alert_callback(self, alerting_system, sample_rule):
        """Test alert callback functionality"""
        callback_called = False
        received_alert = None
        
        def test_callback(alert):
            nonlocal callback_called, received_alert
            callback_called = True
            received_alert = alert
        
        alerting_system.add_alert_callback(test_callback)
        await alerting_system.add_alert_rule(sample_rule)
        
        # Trigger alert
        metric = MetricData("cpu.usage", 95.0, datetime.now())
        await alerting_system.ingest_metric(metric)
        
        # Wait for callback
        await asyncio.sleep(0.01)
        
        assert callback_called is True
        assert received_alert is not None
        assert received_alert.metric_name == "cpu.usage"


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_create_threshold_rule(self):
        """Test threshold rule creation"""
        rule = create_threshold_rule(
            "test_rule", "Test Rule", "test.metric", 
            100.0, ">", AlertSeverity.HIGH, AlertCategory.PERFORMANCE
        )
        
        assert rule.rule_id == "test_rule"
        assert rule.name == "Test Rule"
        assert rule.metric_name == "test.metric"
        assert rule.condition == "> 100.0"
        assert rule.severity == AlertSeverity.HIGH
        assert rule.category == AlertCategory.PERFORMANCE
        assert rule.threshold_value == 100.0
    
    def test_create_anomaly_rule(self):
        """Test anomaly rule creation"""
        rule = create_anomaly_rule(
            "anomaly_rule", "Anomaly Rule", "test.metric",
            AlertSeverity.MEDIUM, AlertCategory.SYSTEM
        )
        
        assert rule.rule_id == "anomaly_rule"
        assert rule.name == "Anomaly Rule"
        assert rule.metric_name == "test.metric"
        assert rule.condition == "anomaly"
        assert rule.severity == AlertSeverity.MEDIUM
        assert rule.category == AlertCategory.SYSTEM


@pytest.mark.asyncio
async def test_integration_scenario():
    """Test complete integration scenario"""
    # Initialize alerting system
    alerting_system = IntelligentAlertingSystem()
    
    # Track alerts received
    alerts_received = []
    
    def alert_handler(alert):
        alerts_received.append(alert)
    
    alerting_system.add_alert_callback(alert_handler)
    
    # Create multiple alert rules
    rules = [
        create_threshold_rule(
            "cpu_high", "High CPU Usage", "system.cpu.usage", 
            80.0, ">", AlertSeverity.HIGH, AlertCategory.SYSTEM
        ),
        create_threshold_rule(
            "memory_low", "Low Memory", "system.memory.available", 
            1000.0, "<", AlertSeverity.CRITICAL, AlertCategory.SYSTEM
        ),
        create_anomaly_rule(
            "latency_anomaly", "Latency Anomaly", "app.latency",
            AlertSeverity.MEDIUM, AlertCategory.PERFORMANCE
        )
    ]
    
    # Add rules
    for rule in rules:
        await alerting_system.add_alert_rule(rule)
    
    # Simulate normal metrics
    for i in range(20):
        await alerting_system.ingest_metric(MetricData(
            "system.cpu.usage", 50.0 + i * 0.5, 
            datetime.now() - timedelta(minutes=20-i)
        ))
        
        await alerting_system.ingest_metric(MetricData(
            "system.memory.available", 2000.0 - i * 10, 
            datetime.now() - timedelta(minutes=20-i)
        ))
        
        await alerting_system.ingest_metric(MetricData(
            "app.latency", 100.0 + (i % 3) * 10, 
            datetime.now() - timedelta(minutes=20-i)
        ))
    
    # Trigger alerts
    await alerting_system.ingest_metric(MetricData(
        "system.cpu.usage", 95.0, datetime.now()
    ))
    
    await alerting_system.ingest_metric(MetricData(
        "system.memory.available", 500.0, datetime.now()
    ))
    
    await alerting_system.ingest_metric(MetricData(
        "app.latency", 500.0, datetime.now()  # Anomaly
    ))
    
    # Wait for processing
    await asyncio.sleep(0.1)
    
    # Verify alerts were created
    assert len(alerts_received) >= 2  # At least CPU and memory alerts
    
    # Check alert properties
    cpu_alert = next((a for a in alerts_received if "cpu" in a.title.lower()), None)
    memory_alert = next((a for a in alerts_received if "memory" in a.title.lower()), None)
    
    assert cpu_alert is not None
    assert cpu_alert.severity == AlertSeverity.HIGH
    assert len(cpu_alert.recommendations) > 0
    
    assert memory_alert is not None
    assert memory_alert.severity == AlertSeverity.CRITICAL
    assert len(memory_alert.recommendations) > 0
    
    # Test alert management
    active_alerts = await alerting_system.get_active_alerts()
    assert len(active_alerts) >= 2
    
    # Acknowledge first alert
    if active_alerts:
        await alerting_system.acknowledge_alert(active_alerts[0].alert_id, "test_operator")
        
        # Verify acknowledgment
        updated_alert = alerting_system.active_alerts[active_alerts[0].alert_id]
        assert updated_alert.status == AlertStatus.ACKNOWLEDGED
    
    # Get statistics
    stats = await alerting_system.get_alert_statistics()
    assert stats["active_alerts"] >= 2
    assert stats["total_alerts"] >= 2
    assert stats["alert_rules"] == 3
    
    print("Integration test completed successfully!")
    print(f"Created {len(alerts_received)} alerts")
    print(f"Active alerts: {stats['active_alerts']}")
    print(f"Alert rules: {stats['alert_rules']}")
    
    # Verify alert content
    for alert in alerts_received[:2]:  # Check first 2 alerts
        assert alert.title is not None
        assert alert.description is not None
        assert alert.severity is not None
        assert alert.category is not None
        assert len(alert.recommendations) > 0


if __name__ == "__main__":
    # Run the integration test
    asyncio.run(test_integration_scenario())