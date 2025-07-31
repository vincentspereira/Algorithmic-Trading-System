"""
Tests for Metrics Collection System
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta

from nautilus_trader_engine.monitoring.metrics_collection import (
    MetricsCollectionSystem,
    MetricCollector,
    BusinessMetricsCollector,
    SystemMetricsCollector,
    CustomMetricsRegistry,
    MetricsAggregator,
    MetricDefinition,
    MetricValue,
    AggregatedMetric,
    MetricType,
    MetricCategory
)


class TestMetricDefinition:
    """Test MetricDefinition data class"""
    
    def test_metric_definition_creation(self):
        """Test metric definition creation"""
        definition = MetricDefinition(
            name="test.metric",
            metric_type=MetricType.COUNTER,
            category=MetricCategory.BUSINESS,
            description="Test metric",
            unit="count"
        )
        
        assert definition.name == "test.metric"
        assert definition.metric_type == MetricType.COUNTER
        assert definition.category == MetricCategory.BUSINESS
        assert definition.description == "Test metric"
        assert definition.unit == "count"
        assert definition.aggregation_window == 60
        assert definition.retention_period == 86400


class TestMetricCollector:
    """Test core metric collector"""
    
    @pytest.fixture
    def collector(self):
        return MetricCollector(max_buffer_size=100)
    
    @pytest.fixture
    def sample_metric_definition(self):
        return MetricDefinition(
            name="test.counter",
            metric_type=MetricType.COUNTER,
            category=MetricCategory.CUSTOM,
            description="Test counter metric"
        )
    
    def test_register_metric(self, collector, sample_metric_definition):
        """Test metric registration"""
        result = collector.register_metric(sample_metric_definition)
        
        assert result is True
        assert "test.counter" in collector.metric_definitions
        assert collector.metric_definitions["test.counter"] == sample_metric_definition
    
    def test_collect_metric(self, collector, sample_metric_definition):
        """Test metric collection"""
        # Register metric first
        collector.register_metric(sample_metric_definition)
        
        # Collect metric value
        result = collector.collect_metric("test.counter", 42, tags={"env": "test"})
        
        assert result is True
        assert len(collector.metrics_buffer["test.counter"]) == 1
        
        metric_value = collector.metrics_buffer["test.counter"][0]
        assert metric_value.value == 42
        assert metric_value.tags == {"env": "test"}
        assert isinstance(metric_value.timestamp, datetime)
    
    def test_collect_unregistered_metric(self, collector):
        """Test collecting unregistered metric"""
        result = collector.collect_metric("unregistered.metric", 100)
        
        assert result is False
        assert "unregistered.metric" not in collector.metrics_buffer
    
    def test_buffer_size_limit(self, collector, sample_metric_definition):
        """Test buffer size limit enforcement"""
        collector.register_metric(sample_metric_definition)
        
        # Fill buffer beyond limit
        for i in range(150):  # Buffer size is 100
            collector.collect_metric("test.counter", i)
        
        # Should maintain buffer size limit
        assert len(collector.metrics_buffer["test.counter"]) == 100
        
        # Should contain most recent values
        values = list(collector.metrics_buffer["test.counter"])
        assert values[-1].value == 149  # Last value
        assert values[0].value == 50   # First value after eviction
    
    def test_get_metric_values(self, collector, sample_metric_definition):
        """Test retrieving metric values"""
        collector.register_metric(sample_metric_definition)
        
        # Collect some values
        for i in range(5):
            collector.collect_metric("test.counter", i)
            time.sleep(0.01)  # Small delay for timestamp differences
        
        # Get all values
        values = collector.get_metric_values("test.counter")
        assert len(values) == 5
        assert [v.value for v in values] == [0, 1, 2, 3, 4]
    
    def test_get_metric_values_with_time_range(self, collector, sample_metric_definition):
        """Test retrieving metric values with time filtering"""
        collector.register_metric(sample_metric_definition)
        
        start_time = datetime.now()
        
        # Collect values with delays
        for i in range(3):
            collector.collect_metric("test.counter", i)
            time.sleep(0.1)
        
        mid_time = datetime.now()
        
        for i in range(3, 6):
            collector.collect_metric("test.counter", i)
            time.sleep(0.1)
        
        end_time = datetime.now()
        
        # Test time range filtering
        values = collector.get_metric_values("test.counter", mid_time, end_time)
        assert len(values) >= 3  # Should get values from mid_time onwards
    
    def test_aggregate_metrics(self, collector, sample_metric_definition):
        """Test metric aggregation"""
        collector.register_metric(sample_metric_definition)
        
        # Collect some values
        values = [10, 20, 30, 40, 50]
        for value in values:
            collector.collect_metric("test.counter", value)
        
        # Aggregate metrics
        aggregated = collector.aggregate_metrics("test.counter", 60)
        
        assert aggregated is not None
        assert aggregated.name == "test.counter"
        assert aggregated.count == 5
        assert aggregated.sum_value == 150
        assert aggregated.min_value == 10
        assert aggregated.max_value == 50
        assert aggregated.avg_value == 30
    
    def test_collection_stats(self, collector, sample_metric_definition):
        """Test collection statistics"""
        collector.register_metric(sample_metric_definition)
        
        # Collect some metrics
        for i in range(10):
            collector.collect_metric("test.counter", i)
        
        stats = collector.get_collection_stats()
        
        assert stats["total_metrics_collected"] == 10
        assert stats["registered_metrics"] == 1
        assert "test.counter" in stats["buffer_sizes"]
        assert stats["buffer_sizes"]["test.counter"] == 10
        assert stats["last_collection_time"] is not None


class TestBusinessMetricsCollector:
    """Test business metrics collector"""
    
    @pytest.fixture
    def collector(self):
        return MetricCollector()
    
    @pytest.fixture
    def business_collector(self, collector):
        return BusinessMetricsCollector(collector)
    
    @pytest.mark.asyncio
    async def test_collect_trading_metrics(self, business_collector):
        """Test trading metrics collection"""
        orders_data = {
            "total_orders": 100,
            "filled_orders": 95,
            "daily_volume": 1000000.0
        }
        
        await business_collector.collect_trading_metrics(orders_data)
        
        # Check that metrics were collected
        collector = business_collector.collector
        
        assert len(collector.metrics_buffer["trading.orders.total"]) == 1
        assert len(collector.metrics_buffer["trading.orders.filled"]) == 1
        assert len(collector.metrics_buffer["trading.volume.daily"]) == 1
        
        # Check values
        assert collector.metrics_buffer["trading.orders.total"][0].value == 100
        assert collector.metrics_buffer["trading.orders.filled"][0].value == 95
        assert collector.metrics_buffer["trading.volume.daily"][0].value == 1000000.0
    
    @pytest.mark.asyncio
    async def test_collect_portfolio_metrics(self, business_collector):
        """Test portfolio metrics collection"""
        portfolio_data = {
            "total_value": 5000000.0,
            "realized_pnl": 25000.0,
            "unrealized_pnl": -5000.0
        }
        
        await business_collector.collect_portfolio_metrics(portfolio_data)
        
        collector = business_collector.collector
        
        assert len(collector.metrics_buffer["portfolio.value.total"]) == 1
        assert len(collector.metrics_buffer["trading.pnl.realized"]) == 1
        assert len(collector.metrics_buffer["trading.pnl.unrealized"]) == 1
        
        # Check calculated total P&L
        assert len(collector.metrics_buffer["trading.pnl.total"]) == 1
        assert collector.metrics_buffer["trading.pnl.total"][0].value == 20000.0
    
    @pytest.mark.asyncio
    async def test_collect_risk_metrics(self, business_collector):
        """Test risk metrics collection"""
        risk_data = {
            "daily_var": 50000.0,
            "total_exposure": 4800000.0
        }
        
        await business_collector.collect_risk_metrics(risk_data)
        
        collector = business_collector.collector
        
        assert len(collector.metrics_buffer["risk.var.daily"]) == 1
        assert len(collector.metrics_buffer["risk.exposure.total"]) == 1
        
        assert collector.metrics_buffer["risk.var.daily"][0].value == 50000.0
        assert collector.metrics_buffer["risk.exposure.total"][0].value == 4800000.0


class TestSystemMetricsCollector:
    """Test system metrics collector"""
    
    @pytest.fixture
    def collector(self):
        return MetricCollector()
    
    @pytest.fixture
    def system_collector(self, collector):
        return SystemMetricsCollector(collector)
    
    @pytest.mark.asyncio
    async def test_collect_system_resources(self, system_collector):
        """Test system resource metrics collection"""
        await system_collector.collect_system_resources()
        
        collector = system_collector.collector
        
        # Should have collected CPU and memory metrics
        assert len(collector.metrics_buffer["system.cpu.usage"]) == 1
        assert len(collector.metrics_buffer["system.memory.usage"]) == 1
        
        # Values should be reasonable percentages
        cpu_value = collector.metrics_buffer["system.cpu.usage"][0].value
        memory_value = collector.metrics_buffer["system.memory.usage"][0].value
        
        assert 0 <= cpu_value <= 100
        assert 0 <= memory_value <= 100
    
    @pytest.mark.asyncio
    async def test_collect_performance_metrics(self, system_collector):
        """Test performance metrics collection"""
        await system_collector.collect_performance_metrics(latency_ms=25.5, request_count=100)
        
        collector = system_collector.collector
        
        assert len(collector.metrics_buffer["system.latency.api"]) == 1
        assert len(collector.metrics_buffer["system.throughput.requests"]) == 1
        
        assert collector.metrics_buffer["system.latency.api"][0].value == 25.5
        assert collector.metrics_buffer["system.throughput.requests"][0].value == 100
    
    @pytest.mark.asyncio
    async def test_collect_error_metrics(self, system_collector):
        """Test error metrics collection"""
        await system_collector.collect_error_metrics(error_count=5, error_type="validation")
        
        collector = system_collector.collector
        
        assert len(collector.metrics_buffer["system.errors.total"]) == 1
        
        error_metric = collector.metrics_buffer["system.errors.total"][0]
        assert error_metric.value == 5
        assert error_metric.tags["error_type"] == "validation"


class TestCustomMetricsRegistry:
    """Test custom metrics registry"""
    
    @pytest.fixture
    def collector(self):
        return MetricCollector()
    
    @pytest.fixture
    def registry(self, collector):
        return CustomMetricsRegistry(collector)
    
    def test_register_custom_metric(self, registry):
        """Test custom metric registration"""
        definition = MetricDefinition(
            name="custom.test.metric",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.CUSTOM,
            description="Custom test metric"
        )
        
        result = registry.register_custom_metric(definition)
        
        assert result is True
        assert "custom.test.metric" in registry.custom_metrics
        assert "custom.test.metric" in registry.collector.metric_definitions
    
    def test_register_custom_metric_with_calculator(self, registry):
        """Test custom metric registration with calculator"""
        def calculate_ratio(numerator, denominator):
            return numerator / denominator if denominator != 0 else 0
        
        definition = MetricDefinition(
            name="custom.ratio",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.CUSTOM,
            description="Custom ratio metric"
        )
        
        result = registry.register_custom_metric(definition, calculate_ratio)
        
        assert result is True
        assert "custom.ratio" in registry.metric_calculators
    
    def test_collect_custom_metric_with_calculator(self, registry):
        """Test collecting custom metric with calculator"""
        def calculate_percentage(value, total):
            return (value / total * 100) if total > 0 else 0
        
        definition = MetricDefinition(
            name="custom.percentage",
            metric_type=MetricType.PERCENTAGE,
            category=MetricCategory.CUSTOM,
            description="Custom percentage metric"
        )
        
        registry.register_custom_metric(definition, calculate_percentage)
        
        # Collect metric using calculator
        result = registry.collect_custom_metric("custom.percentage", 75, 100)
        
        assert result is True
        
        # Check collected value
        values = registry.collector.get_metric_values("custom.percentage")
        assert len(values) == 1
        assert values[0].value == 75.0  # 75/100 * 100 = 75%
    
    def test_collect_custom_metric_direct_value(self, registry):
        """Test collecting custom metric with direct value"""
        definition = MetricDefinition(
            name="custom.direct",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.CUSTOM,
            description="Custom direct metric"
        )
        
        registry.register_custom_metric(definition)
        
        # Collect metric with direct value
        result = registry.collect_custom_metric("custom.direct", value=42)
        
        assert result is True
        
        values = registry.collector.get_metric_values("custom.direct")
        assert len(values) == 1
        assert values[0].value == 42


class TestMetricsAggregator:
    """Test metrics aggregator"""
    
    @pytest.fixture
    def collector(self):
        return MetricCollector()
    
    @pytest.fixture
    def aggregator(self, collector):
        return MetricsAggregator(collector)
    
    @pytest.fixture
    def sample_metric(self, collector):
        definition = MetricDefinition(
            name="test.aggregation",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.CUSTOM,
            description="Test aggregation metric"
        )
        collector.register_metric(definition)
        
        # Add some sample data
        for i in range(10):
            collector.collect_metric("test.aggregation", i * 10)
        
        return "test.aggregation"
    
    def test_get_aggregated_metrics(self, aggregator, sample_metric):
        """Test getting aggregated metrics"""
        # First aggregate some metrics
        aggregated = aggregator.collector.aggregate_metrics(sample_metric, 60)
        assert aggregated is not None
        
        # Get aggregated metrics
        aggregated_list = aggregator.get_aggregated_metrics(sample_metric)
        
        assert len(aggregated_list) >= 1
        assert all(isinstance(agg, AggregatedMetric) for agg in aggregated_list)
    
    def test_get_aggregated_metrics_with_time_range(self, aggregator, sample_metric):
        """Test getting aggregated metrics with time filtering"""
        # Aggregate metrics
        aggregated = aggregator.collector.aggregate_metrics(sample_metric, 60)
        assert aggregated is not None
        
        # Get with time range
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=5)
        
        aggregated_list = aggregator.get_aggregated_metrics(sample_metric, start_time, end_time)
        
        # Should get recent aggregations
        assert isinstance(aggregated_list, list)
        for agg in aggregated_list:
            assert start_time <= agg.end_time <= end_time


class TestMetricsCollectionSystem:
    """Test the main metrics collection system"""
    
    @pytest.fixture
    def metrics_system(self):
        return MetricsCollectionSystem(max_buffer_size=100)
    
    @pytest.mark.asyncio
    async def test_system_start_stop(self, metrics_system):
        """Test system start and stop"""
        assert not metrics_system.is_running
        
        await metrics_system.start()
        assert metrics_system.is_running
        
        await metrics_system.stop()
        assert not metrics_system.is_running
    
    @pytest.mark.asyncio
    async def test_collect_business_metrics(self, metrics_system):
        """Test collecting business metrics through system"""
        await metrics_system.start()
        
        business_data = {
            "trading": {
                "total_orders": 50,
                "filled_orders": 48,
                "daily_volume": 500000.0
            },
            "portfolio": {
                "total_value": 2000000.0,
                "realized_pnl": 10000.0,
                "unrealized_pnl": 2000.0
            }
        }
        
        await metrics_system.collect_business_metrics(business_data)
        
        # Check that metrics were collected
        collector = metrics_system.collector
        assert len(collector.metrics_buffer["trading.orders.total"]) == 1
        assert len(collector.metrics_buffer["portfolio.value.total"]) == 1
        
        await metrics_system.stop()
    
    def test_register_custom_metric(self, metrics_system):
        """Test registering custom metric through system"""
        result = metrics_system.register_custom_metric(
            name="system.custom.test",
            metric_type=MetricType.COUNTER,
            description="System custom test metric",
            unit="count"
        )
        
        assert result is True
        assert "system.custom.test" in metrics_system.custom_registry.custom_metrics
    
    def test_collect_metric(self, metrics_system):
        """Test collecting metric through system"""
        # Register metric first
        metrics_system.register_custom_metric(
            name="system.test.metric",
            metric_type=MetricType.GAUGE,
            description="System test metric"
        )
        
        # Collect metric
        result = metrics_system.collect_metric("system.test.metric", 123.45)
        
        assert result is True
        
        values = metrics_system.collector.get_metric_values("system.test.metric")
        assert len(values) == 1
        assert values[0].value == 123.45
    
    def test_get_metrics_summary(self, metrics_system):
        """Test getting metrics summary"""
        # Register and collect some metrics
        metrics_system.register_custom_metric(
            name="summary.test",
            metric_type=MetricType.COUNTER,
            description="Summary test metric"
        )
        
        metrics_system.collect_metric("summary.test", 42)
        
        summary = metrics_system.get_metrics_summary()
        
        assert isinstance(summary, dict)
        assert "collection_stats" in summary
        assert "registered_metrics" in summary
        assert "custom_metrics" in summary
        assert "system_status" in summary
        assert "timestamp" in summary
        
        assert summary["registered_metrics"] > 0
        assert summary["custom_metrics"] >= 1


@pytest.mark.asyncio
async def test_integration_scenario():
    """Test complete integration scenario"""
    metrics_system = MetricsCollectionSystem()
    
    # Start the system
    await metrics_system.start()
    
    # Register custom metrics
    metrics_system.register_custom_metric(
        name="integration.test.counter",
        metric_type=MetricType.COUNTER,
        description="Integration test counter"
    )
    
    # Collect various metrics
    business_data = {
        "trading": {
            "total_orders": 200,
            "filled_orders": 190,
            "daily_volume": 2500000.0
        },
        "portfolio": {
            "total_value": 10000000.0,
            "realized_pnl": 50000.0,
            "unrealized_pnl": -10000.0
        },
        "risk": {
            "daily_var": 100000.0,
            "total_exposure": 9500000.0
        }
    }
    
    await metrics_system.collect_business_metrics(business_data)
    
    # Collect custom metric
    metrics_system.collect_metric("integration.test.counter", 1)
    
    # Wait a bit for processing
    await asyncio.sleep(0.1)
    
    # Get summary
    summary = metrics_system.get_metrics_summary()
    
    # Verify results
    assert summary["system_status"] == "running"
    assert summary["collection_stats"]["total_metrics_collected"] > 0
    assert summary["registered_metrics"] > 0
    
    # Check that business metrics were collected
    collector = metrics_system.collector
    assert len(collector.metrics_buffer["trading.orders.total"]) == 1
    assert len(collector.metrics_buffer["portfolio.value.total"]) == 1
    assert len(collector.metrics_buffer["risk.var.daily"]) == 1
    
    # Test aggregation
    aggregated = collector.aggregate_metrics("trading.orders.total", 60)
    assert aggregated is not None
    assert aggregated.count == 1
    assert aggregated.avg_value == 200
    
    # Stop the system
    await metrics_system.stop()
    
    print("Integration test completed successfully!")
    print(f"Total metrics collected: {summary['collection_stats']['total_metrics_collected']}")
    print(f"Registered metrics: {summary['registered_metrics']}")
    print(f"Trading orders: {collector.metrics_buffer['trading.orders.total'][0].value}")
    print(f"Portfolio value: ${collector.metrics_buffer['portfolio.value.total'][0].value:,.2f}")


if __name__ == "__main__":
    # Run the integration test
    asyncio.run(test_integration_scenario())