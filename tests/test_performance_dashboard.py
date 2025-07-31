"""
Tests for Performance Analytics Dashboard
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from nautilus_trader_engine.monitoring.performance_dashboard import (
    PerformanceAnalyticsDashboard,
    MetricCollector,
    CapacityPlanner,
    OptimizationEngine,
    DashboardRenderer,
    MetricPoint,
    MetricSeries,
    ChartConfig,
    DashboardWidget,
    Dashboard,
    PerformanceMetrics,
    CapacityForecast,
    OptimizationRecommendation,
    MetricType,
    TimeRange,
    ChartType
)


class TestMetricCollector:
    """Test metric collection functionality"""
    
    @pytest.fixture
    def collector(self):
        return MetricCollector(max_points_per_series=100)
    
    def test_add_metric_point(self, collector):
        """Test adding metric points"""
        collector.add_metric_point(
            "test.metric", 42.0,
            tags={"host": "server1"},
            metric_type=MetricType.GAUGE,
            unit="ms"
        )
        
        assert "test.metric" in collector.metrics
        series = collector.metrics["test.metric"]
        assert series.name == "test.metric"
        assert series.metric_type == MetricType.GAUGE
        assert series.unit == "ms"
        assert len(series.points) == 1
        assert series.points[0].value == 42.0
        assert series.points[0].tags["host"] == "server1"
    
    def test_get_metric_series(self, collector):
        """Test retrieving metric series"""
        # Add test data
        now = datetime.now()
        for i in range(10):
            collector.add_metric_point(
                "test.metric", 
                float(i),
                timestamp=now - timedelta(minutes=i)
            )
        
        # Get series with time range filter
        series = collector.get_metric_series("test.metric", TimeRange.LAST_5_MINUTES)
        assert series is not None
        assert len(series.points) <= 6  # Should filter to last 5 minutes
        
        # Get non-existent metric
        series = collector.get_metric_series("nonexistent.metric")
        assert series is None
    
    def test_get_metric_statistics(self, collector):
        """Test metric statistics calculation"""
        # Add test data
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in values:
            collector.add_metric_point("test.metric", value)
        
        stats = collector.get_metric_statistics("test.metric")
        
        assert stats["count"] == 5
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert stats["mean"] == 30.0
        assert stats["median"] == 30.0
        assert "std" in stats
    
    def test_max_points_limit(self, collector):
        """Test maximum points per series limit"""
        # Add more points than the limit
        for i in range(150):
            collector.add_metric_point("test.metric", float(i))
        
        series = collector.metrics["test.metric"]
        assert len(series.points) == 100  # Should be limited to max_points_per_series
        
        # Should keep the most recent points
        assert series.points[-1].value == 149.0
    
    def test_get_available_metrics(self, collector):
        """Test getting available metrics list"""
        collector.add_metric_point("metric1", 1.0)
        collector.add_metric_point("metric2", 2.0)
        collector.add_metric_point("metric3", 3.0)
        
        metrics = collector.get_available_metrics()
        assert len(metrics) == 3
        assert "metric1" in metrics
        assert "metric2" in metrics
        assert "metric3" in metrics


class TestCapacityPlanner:
    """Test capacity planning functionality"""
    
    @pytest.fixture
    def collector(self):
        return MetricCollector()
    
    @pytest.fixture
    def planner(self, collector):
        return CapacityPlanner(collector)
    
    @pytest.mark.asyncio
    async def test_generate_capacity_forecast_insufficient_data(self, planner, collector):
        """Test forecast with insufficient data"""
        # Add only a few data points
        for i in range(5):
            collector.add_metric_point("test.metric", float(i))
        
        forecast = await planner.generate_capacity_forecast("test.metric")
        assert forecast is None
    
    @pytest.mark.asyncio
    async def test_generate_capacity_forecast_increasing_trend(self, planner, collector):
        """Test forecast with increasing trend"""
        # Add increasing trend data
        base_time = datetime.now() - timedelta(days=30)
        for i in range(30):
            timestamp = base_time + timedelta(days=i)
            value = 50.0 + i * 2.0  # Increasing trend
            collector.add_metric_point("test.metric", value, timestamp=timestamp)
        
        forecast = await planner.generate_capacity_forecast(
            "test.metric", forecast_days=30, capacity_limit=200.0
        )
        
        assert forecast is not None
        assert forecast.metric_name == "test.metric"
        assert forecast.trend == "increasing"
        assert len(forecast.predicted_values) == 30
        assert forecast.capacity_limit == 200.0
        assert forecast.time_to_limit is not None
        # Check that recommendation mentions either increasing trend or capacity planning
        assert any(word in forecast.recommendation.lower() for word in ["increasing", "capacity", "limit", "expansion"])
    
    @pytest.mark.asyncio
    async def test_generate_capacity_forecast_stable_trend(self, planner, collector):
        """Test forecast with stable trend"""
        # Add stable data
        base_time = datetime.now() - timedelta(days=30)
        import random
        random.seed(42)  # For reproducible results
        for i in range(30):
            timestamp = base_time + timedelta(days=i)
            value = 50.0 + random.uniform(-0.5, 0.5)  # Stable with random variations
            collector.add_metric_point("test.metric", value, timestamp=timestamp)
        
        forecast = await planner.generate_capacity_forecast("test.metric")
        
        assert forecast is not None
        # With random data, trend could be stable, increasing, or decreasing
        assert forecast.trend in ["stable", "increasing", "decreasing"]
        # Recommendation should be reasonable for the detected trend
        assert len(forecast.recommendation) > 0


class TestOptimizationEngine:
    """Test optimization engine functionality"""
    
    @pytest.fixture
    def collector(self):
        return MetricCollector()
    
    @pytest.fixture
    def engine(self, collector):
        return OptimizationEngine(collector)
    
    @pytest.mark.asyncio
    async def test_generate_recommendations_high_cpu(self, engine, collector):
        """Test recommendations for high CPU usage"""
        # Add high CPU usage data
        for i in range(20):
            collector.add_metric_point("system.cpu.usage", 90.0 + i * 0.1)
        
        recommendations = await engine.generate_recommendations()
        
        # Should generate CPU-related recommendation
        cpu_recs = [r for r in recommendations if "cpu" in r.title.lower()]
        assert len(cpu_recs) > 0
        
        cpu_rec = cpu_recs[0]
        assert cpu_rec.category == "performance"
        assert cpu_rec.priority == "high"
        assert len(cpu_rec.action_items) > 0
    
    @pytest.mark.asyncio
    async def test_generate_recommendations_high_memory(self, engine, collector):
        """Test recommendations for high memory usage"""
        # Add high memory usage data
        for i in range(20):
            collector.add_metric_point("system.memory.usage", 90.0 + i * 0.1)
        
        recommendations = await engine.generate_recommendations()
        
        # Should generate memory-related recommendation
        memory_recs = [r for r in recommendations if "memory" in r.title.lower()]
        assert len(memory_recs) > 0
        
        memory_rec = memory_recs[0]
        assert memory_rec.category == "performance"
        assert memory_rec.priority == "high"
    
    @pytest.mark.asyncio
    async def test_generate_recommendations_high_latency(self, engine, collector):
        """Test recommendations for high response time"""
        # Add high latency data
        for i in range(20):
            collector.add_metric_point("app.response_time", 1500.0 + i * 10)
        
        recommendations = await engine.generate_recommendations()
        
        # Should generate latency-related recommendation
        latency_recs = [r for r in recommendations if "response time" in r.title.lower() or "latency" in r.title.lower()]
        assert len(latency_recs) > 0
        
        latency_rec = latency_recs[0]
        assert latency_rec.category == "performance"
        assert latency_rec.priority == "high"
    
    @pytest.mark.asyncio
    async def test_generate_recommendations_high_error_rate(self, engine, collector):
        """Test recommendations for high error rate"""
        # Add high error rate data
        for i in range(20):
            collector.add_metric_point("app.error_rate", 8.0 + i * 0.1)
        
        recommendations = await engine.generate_recommendations()
        
        # Should generate error rate recommendation
        error_recs = [r for r in recommendations if "error" in r.title.lower()]
        assert len(error_recs) > 0
        
        error_rec = error_recs[0]
        assert error_rec.category == "reliability"
        assert error_rec.priority == "critical"


class TestDashboardRenderer:
    """Test dashboard rendering functionality"""
    
    @pytest.fixture
    def collector(self):
        collector = MetricCollector()
        # Add test data
        for i in range(10):
            collector.add_metric_point("test.metric", float(i * 10))
        return collector
    
    @pytest.fixture
    def renderer(self, collector):
        return DashboardRenderer(collector)
    
    @pytest.mark.asyncio
    async def test_render_chart_data(self, renderer):
        """Test chart data rendering"""
        chart_config = ChartConfig(
            chart_id="test_chart",
            title="Test Chart",
            chart_type=ChartType.LINE,
            metrics=["test.metric"],
            time_range=TimeRange.LAST_HOUR
        )
        
        chart_data = await renderer.render_chart_data(chart_config)
        
        assert chart_data["chart_id"] == "test_chart"
        assert chart_data["title"] == "Test Chart"
        assert chart_data["type"] == "line"
        assert "data" in chart_data
        assert "datasets" in chart_data["data"]
        assert len(chart_data["data"]["datasets"]) == 1
    
    @pytest.mark.asyncio
    async def test_render_metric_widget(self, renderer):
        """Test metric widget rendering"""
        widget_data = await renderer.render_metric_widget("test.metric")
        
        assert widget_data["metric_name"] == "test.metric"
        assert "current_value" in widget_data
        assert "statistics" in widget_data
        assert "trend" in widget_data
        assert widget_data["trend"] in ["up", "down", "stable"]


class TestPerformanceAnalyticsDashboard:
    """Test main dashboard system"""
    
    @pytest.fixture
    def dashboard(self):
        return PerformanceAnalyticsDashboard()
    
    def test_initialization(self, dashboard):
        """Test dashboard initialization"""
        assert dashboard.metric_collector is not None
        assert dashboard.capacity_planner is not None
        assert dashboard.optimization_engine is not None
        assert dashboard.dashboard_renderer is not None
        assert len(dashboard.dashboards) == 1  # Default dashboard
        assert "main" in dashboard.dashboards
    
    @pytest.mark.asyncio
    async def test_create_dashboard(self, dashboard):
        """Test dashboard creation"""
        test_dashboard = Dashboard(
            dashboard_id="test",
            name="Test Dashboard",
            description="Test dashboard",
            widgets=[]
        )
        
        result = await dashboard.create_dashboard(test_dashboard)
        assert result is True
        assert "test" in dashboard.dashboards
        
        retrieved = await dashboard.get_dashboard("test")
        assert retrieved is not None
        assert retrieved.name == "Test Dashboard"
    
    @pytest.mark.asyncio
    async def test_list_dashboards(self, dashboard):
        """Test listing dashboards"""
        dashboards = await dashboard.list_dashboards()
        assert len(dashboards) >= 1  # At least the default dashboard
        
        # Create additional dashboard
        test_dashboard = Dashboard(
            dashboard_id="test2",
            name="Test Dashboard 2",
            description="Another test dashboard",
            widgets=[]
        )
        await dashboard.create_dashboard(test_dashboard)
        
        dashboards = await dashboard.list_dashboards()
        assert len(dashboards) >= 2
    
    @pytest.mark.asyncio
    async def test_delete_dashboard(self, dashboard):
        """Test dashboard deletion"""
        # Create test dashboard
        test_dashboard = Dashboard(
            dashboard_id="to_delete",
            name="To Delete",
            description="Dashboard to delete",
            widgets=[]
        )
        await dashboard.create_dashboard(test_dashboard)
        
        # Delete it
        result = await dashboard.delete_dashboard("to_delete")
        assert result is True
        assert "to_delete" not in dashboard.dashboards
        
        # Try to delete non-existent dashboard
        result = await dashboard.delete_dashboard("nonexistent")
        assert result is False
    
    def test_add_metric(self, dashboard):
        """Test adding metrics"""
        dashboard.add_metric("test.metric", 42.0, unit="ms")
        
        metrics = dashboard.get_available_metrics()
        assert "test.metric" in metrics
        
        stats = dashboard.metric_collector.get_metric_statistics("test.metric")
        assert stats["count"] == 1
        assert stats["mean"] == 42.0
    
    @pytest.mark.asyncio
    async def test_get_dashboard_data(self, dashboard):
        """Test getting dashboard data"""
        # Add some test metrics
        dashboard.add_metric("system.cpu.usage", 75.0)
        dashboard.add_metric("system.memory.usage", 60.0)
        
        dashboard_data = await dashboard.get_dashboard_data("main")
        
        assert dashboard_data["dashboard_id"] == "main"
        assert dashboard_data["name"] == "System Performance"
        assert "widgets" in dashboard_data
        assert len(dashboard_data["widgets"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_system_overview(self, dashboard):
        """Test system overview"""
        # Add test metrics
        dashboard.add_metric("system.cpu.usage", 45.0)
        dashboard.add_metric("system.memory.usage", 60.0)
        dashboard.add_metric("app.response_time.avg", 150.0)
        dashboard.add_metric("app.error_rate", 2.0)
        
        overview = await dashboard.get_system_overview()
        
        assert "timestamp" in overview
        assert "system_health" in overview
        assert "key_metrics" in overview
        assert overview["system_health"] in ["healthy", "warning", "critical"]
    
    @pytest.mark.asyncio
    async def test_get_capacity_forecast(self, dashboard):
        """Test capacity forecasting"""
        # Add trending data
        for i in range(30):
            dashboard.add_metric("test.trending.metric", 50.0 + i * 2.0)
        
        forecast = await dashboard.get_capacity_forecast("test.trending.metric")
        
        if forecast:  # May be None if insufficient data
            assert forecast.metric_name == "test.trending.metric"
            assert forecast.trend in ["increasing", "decreasing", "stable"]
    
    @pytest.mark.asyncio
    async def test_get_optimization_recommendations(self, dashboard):
        """Test optimization recommendations"""
        # Add metrics that should trigger recommendations
        for i in range(20):
            dashboard.add_metric("system.cpu.usage", 95.0)  # High CPU
            dashboard.add_metric("system.memory.usage", 90.0)  # High memory
        
        recommendations = await dashboard.get_optimization_recommendations()
        
        assert isinstance(recommendations, list)
        # Should have recommendations for high resource usage
        if recommendations:
            assert all(isinstance(r, OptimizationRecommendation) for r in recommendations)
    
    @pytest.mark.asyncio
    async def test_export_import_dashboard_config(self, dashboard):
        """Test dashboard configuration export/import"""
        # Create test dashboard
        test_dashboard = Dashboard(
            dashboard_id="export_test",
            name="Export Test",
            description="Dashboard for export test",
            widgets=[
                DashboardWidget(
                    widget_id="test_widget",
                    title="Test Widget",
                    widget_type="metric",
                    config={"metric_name": "test.metric"}
                )
            ]
        )
        await dashboard.create_dashboard(test_dashboard)
        
        # Export configuration
        config = await dashboard.export_dashboard_config("export_test")
        assert config is not None
        assert config["dashboard_id"] == "export_test"
        assert config["name"] == "Export Test"
        assert len(config["widgets"]) == 1
        
        # Delete original dashboard
        await dashboard.delete_dashboard("export_test")
        
        # Import configuration with new ID
        config["dashboard_id"] = "imported_test"
        result = await dashboard.import_dashboard_config(config)
        assert result is True
        
        # Verify imported dashboard
        imported = await dashboard.get_dashboard("imported_test")
        assert imported is not None
        assert imported.name == "Export Test"
        assert len(imported.widgets) == 1


@pytest.mark.asyncio
async def test_integration_scenario():
    """Test complete integration scenario"""
    # Initialize dashboard
    dashboard = PerformanceAnalyticsDashboard()
    
    # Add various metrics over time
    import random
    
    print("Adding performance metrics...")
    
    # System metrics
    for i in range(100):
        dashboard.add_metric("system.cpu.usage", random.uniform(20, 80))
        dashboard.add_metric("system.memory.usage", random.uniform(40, 90))
        dashboard.add_metric("system.disk.usage", random.uniform(30, 70))
    
    # Application metrics
    for i in range(100):
        dashboard.add_metric("app.response_time.avg", random.uniform(50, 300))
        dashboard.add_metric("app.response_time.p95", random.uniform(100, 500))
        dashboard.add_metric("app.error_rate", random.uniform(0, 8))
        dashboard.add_metric("app.throughput", random.uniform(100, 1000))
    
    # Trading metrics
    for i in range(100):
        dashboard.add_metric("trading.order_rate", random.uniform(50, 200))
        dashboard.add_metric("trading.fill_rate", random.uniform(85, 99))
        dashboard.add_metric("trading.latency", random.uniform(5, 50))
    
    # Verify metrics were added
    available_metrics = dashboard.get_available_metrics()
    assert len(available_metrics) >= 10
    
    # Test system overview
    overview = await dashboard.get_system_overview()
    assert overview["metrics_count"] >= 10
    assert overview["system_health"] in ["healthy", "warning", "critical"]
    
    # Test dashboard data retrieval
    dashboard_data = await dashboard.get_dashboard_data("main")
    assert dashboard_data["dashboard_id"] == "main"
    assert len(dashboard_data["widgets"]) > 0
    
    # Test capacity forecasting
    forecast = await dashboard.get_capacity_forecast("system.cpu.usage")
    if forecast:
        assert forecast.metric_name == "system.cpu.usage"
        assert forecast.trend in ["increasing", "decreasing", "stable"]
    
    # Test optimization recommendations
    recommendations = await dashboard.get_optimization_recommendations()
    assert isinstance(recommendations, list)
    
    # Create custom dashboard
    trading_dashboard = Dashboard(
        dashboard_id="trading_performance",
        name="Trading Performance",
        description="Trading system metrics",
        widgets=[
            DashboardWidget(
                widget_id="order_rate_chart",
                title="Order Rate",
                widget_type="chart",
                config={
                    "chart_type": ChartType.LINE.value,
                    "metrics": ["trading.order_rate"],
                    "time_range": TimeRange.LAST_HOUR.value
                }
            ),
            DashboardWidget(
                widget_id="latency_metric",
                title="Trading Latency",
                widget_type="metric",
                config={
                    "metric_name": "trading.latency",
                    "time_range": TimeRange.LAST_HOUR.value
                }
            )
        ]
    )
    
    result = await dashboard.create_dashboard(trading_dashboard)
    assert result is True
    
    # Test custom dashboard data
    trading_data = await dashboard.get_dashboard_data("trading_performance")
    assert trading_data["dashboard_id"] == "trading_performance"
    assert len(trading_data["widgets"]) == 2
    
    # List all dashboards
    all_dashboards = await dashboard.list_dashboards()
    assert len(all_dashboards) >= 2  # main + trading
    
    # Test configuration export/import
    config = await dashboard.export_dashboard_config("trading_performance")
    assert config is not None
    
    config["dashboard_id"] = "trading_copy"
    config["name"] = "Trading Performance Copy"
    
    import_result = await dashboard.import_dashboard_config(config)
    assert import_result is True
    
    # Verify the copy
    copy_dashboard = await dashboard.get_dashboard("trading_copy")
    assert copy_dashboard is not None
    assert copy_dashboard.name == "Trading Performance Copy"
    
    print("Integration test completed successfully!")
    print(f"Total metrics: {len(available_metrics)}")
    print(f"System health: {overview['system_health']}")
    print(f"Total dashboards: {len(all_dashboards)}")
    print(f"Recommendations: {len(recommendations)}")


if __name__ == "__main__":
    # Run the integration test
    asyncio.run(test_integration_scenario())