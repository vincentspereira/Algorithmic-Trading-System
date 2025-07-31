# Performance Analytics Dashboard Documentation

## Overview

The Performance Analytics Dashboard provides comprehensive real-time performance visualization, historical performance analysis, capacity planning and forecasting, and performance optimization recommendations. It's designed to give operators and developers deep insights into system performance across all components of the trading platform.

## Key Features

- **Real-Time Visualization**: Live performance metrics with customizable dashboards
- **Historical Analysis**: Trend analysis and historical performance tracking
- **Capacity Planning**: Predictive capacity forecasting with trend analysis
- **Optimization Recommendations**: AI-powered performance optimization suggestions
- **Multi-Asset Support**: Comprehensive metrics for trading, system, and business performance
- **Flexible Dashboard System**: Customizable widgets and layouts

## Architecture

### Core Components

1. **MetricCollector**: Collects and stores performance metrics with time-series data
2. **CapacityPlanner**: Performs capacity planning and forecasting using trend analysis
3. **OptimizationEngine**: Generates performance optimization recommendations
4. **DashboardRenderer**: Renders dashboard data for visualization
5. **PerformanceAnalyticsDashboard**: Main orchestration system

### Data Flow

```
Metrics → MetricCollector → Dashboard Widgets → Visualization
    ↓
CapacityPlanner → Forecasts
    ↓
OptimizationEngine → Recommendations
```

## Usage Examples

### Basic Setup

```python
from nautilus_trader_engine.monitoring.performance_dashboard import (
    PerformanceAnalyticsDashboard, MetricType, TimeRange
)
import asyncio

# Initialize dashboard
dashboard = PerformanceAnalyticsDashboard()

# Start the dashboard system
await dashboard.start()

# Add custom metrics
dashboard.add_metric(
    "trading.order_rate", 
    150.0,
    metric_type=MetricType.GAUGE,
    unit="orders/sec",
    tags={"exchange": "NYSE", "strategy": "momentum"}
)

# Stop when done
await dashboard.stop()
```

### Creating Custom Dashboards

```python
from nautilus_trader_engine.monitoring.performance_dashboard import (
    Dashboard, DashboardWidget, ChartConfig, ChartType
)

# Create custom widgets
trading_widgets = [
    DashboardWidget(
        widget_id="order_rate_chart",
        title="Order Rate Over Time",
        widget_type="chart",
        config={
            "chart_type": ChartType.LINE.value,
            "metrics": ["trading.order_rate", "trading.fill_rate"],
            "time_range": TimeRange.LAST_HOUR.value,
            "y_axis_label": "Rate"
        },
        position={"x": 0, "y": 0, "width": 8, "height": 4}
    ),
    DashboardWidget(
        widget_id="latency_metric",
        title="Current Latency",
        widget_type="metric",
        config={
            "metric_name": "trading.latency",
            "time_range": TimeRange.LAST_5_MINUTES.value,
            "format": "milliseconds"
        },
        position={"x": 8, "y": 0, "width": 4, "height": 4}
    )
]

# Create dashboard
trading_dashboard = Dashboard(
    dashboard_id="trading_performance",
    name="Trading Performance",
    description="Real-time trading system metrics",
    widgets=trading_widgets,
    auto_refresh=True,
    refresh_interval=30
)

# Add to system
await dashboard.create_dashboard(trading_dashboard)
```

### Metric Collection

```python
# System metrics
dashboard.add_metric("system.cpu.usage", 75.5, unit="%")
dashboard.add_metric("system.memory.usage", 68.2, unit="%")
dashboard.add_metric("system.disk.io", 1024.0, unit="MB/s")

# Application metrics
dashboard.add_metric("app.response_time.avg", 125.0, unit="ms")
dashboard.add_metric("app.response_time.p95", 250.0, unit="ms")
dashboard.add_metric("app.error_rate", 0.5, unit="%")

# Trading metrics
dashboard.add_metric("trading.orders_per_second", 150.0, unit="ops")
dashboard.add_metric("trading.fill_rate", 98.5, unit="%")
dashboard.add_metric("trading.slippage", 0.02, unit="bps")

# Business metrics
dashboard.add_metric("business.pnl.realized", 15000.0, unit="USD")
dashboard.add_metric("business.volume.daily", 2500000.0, unit="USD")
```

## Dashboard Management

### Creating Dashboards

```python
# Create dashboard programmatically
custom_dashboard = Dashboard(
    dashboard_id="risk_monitoring",
    name="Risk Monitoring",
    description="Portfolio risk and exposure metrics",
    widgets=[
        DashboardWidget(
            widget_id="var_chart",
            title="Value at Risk",
            widget_type="chart",
            config={
                "chart_type": ChartType.LINE.value,
                "metrics": ["risk.var.portfolio", "risk.var.limit"],
                "time_range": TimeRange.LAST_24_HOURS.value
            }
        )
    ]
)

await dashboard.create_dashboard(custom_dashboard)
```

### Dashboard Operations

```python
# List all dashboards
dashboards = await dashboard.list_dashboards()
for db in dashboards:
    print(f"Dashboard: {db.name} ({db.dashboard_id})")

# Get specific dashboard
risk_dashboard = await dashboard.get_dashboard("risk_monitoring")

# Get dashboard data for rendering
dashboard_data = await dashboard.get_dashboard_data("risk_monitoring")

# Delete dashboard
await dashboard.delete_dashboard("risk_monitoring")
```

### Configuration Export/Import

```python
# Export dashboard configuration
config = await dashboard.export_dashboard_config("trading_performance")

# Save to file
import json
with open("trading_dashboard.json", "w") as f:
    json.dump(config, f, indent=2, default=str)

# Load and import configuration
with open("trading_dashboard.json", "r") as f:
    imported_config = json.load(f)

# Modify for new dashboard
imported_config["dashboard_id"] = "trading_performance_copy"
imported_config["name"] = "Trading Performance (Copy)"

# Import
await dashboard.import_dashboard_config(imported_config)
```

## Capacity Planning

### Generating Forecasts

```python
# Generate capacity forecast
forecast = await dashboard.get_capacity_forecast(
    metric_name="system.cpu.usage",
    forecast_days=30
)

if forecast:
    print(f"Metric: {forecast.metric_name}")
    print(f"Current Value: {forecast.current_value:.2f}")
    print(f"Trend: {forecast.trend}")
    print(f"Capacity Limit: {forecast.capacity_limit}")
    
    if forecast.time_to_limit:
        print(f"Time to Limit: {forecast.time_to_limit}")
    
    print(f"Recommendation: {forecast.recommendation}")
    
    # Plot predicted values
    for date, value in forecast.predicted_values[:7]:  # Next 7 days
        print(f"  {date.strftime('%Y-%m-%d')}: {value:.2f}")
```

### Capacity Planning with Limits

```python
# Set capacity limits for forecasting
cpu_forecast = await dashboard.get_capacity_forecast(
    "system.cpu.usage",
    forecast_days=60,
    capacity_limit=90.0  # 90% CPU limit
)

memory_forecast = await dashboard.get_capacity_forecast(
    "system.memory.usage",
    forecast_days=60,
    capacity_limit=85.0  # 85% memory limit
)

# Check for capacity issues
if cpu_forecast and cpu_forecast.time_to_limit:
    days_to_limit = (cpu_forecast.time_to_limit - datetime.now()).days
    if days_to_limit < 30:
        print(f"WARNING: CPU capacity limit in {days_to_limit} days")
```

## Performance Optimization

### Getting Recommendations

```python
# Get optimization recommendations
recommendations = await dashboard.get_optimization_recommendations(
    time_range=TimeRange.LAST_24_HOURS
)

print(f"Found {len(recommendations)} optimization opportunities:")

for rec in recommendations:
    print(f"\\n{rec.title}")
    print(f"  Priority: {rec.priority.upper()}")
    print(f"  Impact: {rec.impact}")
    print(f"  Category: {rec.category}")
    print(f"  Effort: {rec.effort}")
    
    if rec.expected_improvement:
        print(f"  Expected Improvements:")
        for metric, improvement in rec.expected_improvement.items():
            print(f"    {metric}: {improvement:+.1f}%")
    
    print(f"  Action Items:")
    for action in rec.action_items[:3]:  # Show first 3
        print(f"    - {action}")
    
    print(f"  Estimated Time: {rec.estimated_time}")
```

## System Overview

### Getting System Health

```python
# Get comprehensive system overview
overview = await dashboard.get_system_overview()

print(f"System Health: {overview['system_health']}")
print(f"Total Metrics: {overview['metrics_count']}")
print(f"Total Dashboards: {overview['dashboards_count']}")

# Key metrics summary
print("\\nKey Metrics:")
for metric_name, data in overview['key_metrics'].items():
    print(f"  {metric_name}: {data['current']:.2f} ({data['trend']})")

# Health status interpretation
if overview['system_health'] == 'critical':
    print("⚠️  CRITICAL: Immediate attention required")
elif overview['system_health'] == 'warning':
    print("⚠️  WARNING: Monitor closely")
else:
    print("✅ HEALTHY: System operating normally")
```

## Data Structures

### MetricPoint

```python
@dataclass
class MetricPoint:
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### MetricSeries

```python
@dataclass
class MetricSeries:
    name: str
    metric_type: MetricType
    points: List[MetricPoint] = field(default_factory=list)
    unit: str = ""
    description: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
```

### Dashboard

```python
@dataclass
class Dashboard:
    dashboard_id: str
    name: str
    description: str
    widgets: List[DashboardWidget] = field(default_factory=list)
    layout: str = "grid"  # "grid", "flex"
    auto_refresh: bool = True
    refresh_interval: int = 30
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
```

### DashboardWidget

```python
@dataclass
class DashboardWidget:
    widget_id: str
    title: str
    widget_type: str  # "chart", "metric", "alert", "table"
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, int] = field(default_factory=lambda: {
        "x": 0, "y": 0, "width": 6, "height": 4
    })
    refresh_interval: int = 30
```

## Metric Types and Time Ranges

### Metric Types

- **COUNTER**: Monotonically increasing values (e.g., total requests)
- **GAUGE**: Point-in-time values (e.g., CPU usage, memory usage)
- **HISTOGRAM**: Distribution of values (e.g., response time distribution)
- **TIMER**: Time-based measurements (e.g., operation duration)
- **RATE**: Rate of change (e.g., requests per second)

### Time Ranges

- **LAST_5_MINUTES**: Recent short-term view
- **LAST_15_MINUTES**: Short-term operational view
- **LAST_HOUR**: Standard operational view
- **LAST_6_HOURS**: Extended operational view
- **LAST_24_HOURS**: Daily performance view
- **LAST_7_DAYS**: Weekly trend analysis
- **LAST_30_DAYS**: Monthly capacity planning

### Chart Types

- **LINE**: Time series line charts
- **BAR**: Bar charts for categorical data
- **AREA**: Area charts for cumulative metrics
- **SCATTER**: Scatter plots for correlation analysis
- **HEATMAP**: Heat maps for multi-dimensional data
- **PIE**: Pie charts for proportional data
- **GAUGE**: Gauge charts for single metrics

## Integration with Trading System

### Trading Metrics

```python
# Order management metrics
dashboard.add_metric("trading.orders.submitted", 1250, MetricType.COUNTER)
dashboard.add_metric("trading.orders.filled", 1230, MetricType.COUNTER)
dashboard.add_metric("trading.orders.cancelled", 15, MetricType.COUNTER)
dashboard.add_metric("trading.orders.rejected", 5, MetricType.COUNTER)

# Execution metrics
dashboard.add_metric("trading.execution.latency.avg", 12.5, unit="ms")
dashboard.add_metric("trading.execution.latency.p95", 25.0, unit="ms")
dashboard.add_metric("trading.execution.slippage", 1.2, unit="bps")

# Risk metrics
dashboard.add_metric("risk.var.portfolio", 50000.0, unit="USD")
dashboard.add_metric("risk.exposure.gross", 2500000.0, unit="USD")
dashboard.add_metric("risk.exposure.net", 150000.0, unit="USD")

# P&L metrics
dashboard.add_metric("pnl.realized.daily", 12500.0, unit="USD")
dashboard.add_metric("pnl.unrealized", 8750.0, unit="USD")
dashboard.add_metric("pnl.fees.total", 450.0, unit="USD")
```

### Market Data Metrics

```python
# Market data feed health
dashboard.add_metric("market_data.latency", 2.5, unit="ms")
dashboard.add_metric("market_data.throughput", 15000, unit="msgs/sec")
dashboard.add_metric("market_data.drops", 0, MetricType.COUNTER)

# Price quality metrics
dashboard.add_metric("market_data.spread.avg", 0.01, unit="USD")
dashboard.add_metric("market_data.depth.bid", 50000, unit="shares")
dashboard.add_metric("market_data.depth.ask", 48000, unit="shares")
```

## Performance Considerations

- **Memory Management**: Configurable limits on metric history
- **Efficient Storage**: Time-series optimized data structures
- **Async Processing**: Non-blocking operations for high throughput
- **Caching**: Intelligent caching of computed statistics
- **Background Tasks**: Automated system metric collection

## Error Handling

The system includes comprehensive error handling:

- **Graceful Degradation**: Continues operation when components fail
- **Data Validation**: Input validation and sanitization
- **Logging**: Detailed logging of all operations
- **Fallback Mechanisms**: Default behaviors when analysis fails

## Testing

Run the comprehensive test suite:

```bash
# Run all dashboard tests
python -m pytest tests/test_performance_dashboard.py -v

# Run specific test categories
python -m pytest tests/test_performance_dashboard.py::TestMetricCollector -v
python -m pytest tests/test_performance_dashboard.py::TestCapacityPlanner -v
python -m pytest tests/test_performance_dashboard.py::TestOptimizationEngine -v

# Run integration test
python -m pytest tests/test_performance_dashboard.py::test_integration_scenario -v
```

## Best Practices

1. **Metric Naming**: Use consistent, hierarchical naming (e.g., `system.cpu.usage`)
2. **Appropriate Granularity**: Balance detail with performance
3. **Dashboard Design**: Focus on actionable metrics
4. **Alert Integration**: Connect dashboards with alerting systems
5. **Regular Review**: Periodically review and optimize dashboards
6. **Documentation**: Document custom metrics and dashboards
7. **Testing**: Test dashboard configurations before deployment

## Future Enhancements

Planned improvements:

- **Real-Time Streaming**: WebSocket-based real-time updates
- **Advanced Analytics**: Machine learning-based anomaly detection
- **Custom Visualizations**: Plugin system for custom chart types
- **Mobile Support**: Mobile-optimized dashboard views
- **Export Capabilities**: PDF and image export functionality
- **Collaboration Features**: Dashboard sharing and commenting

## API Reference

### PerformanceAnalyticsDashboard

Main dashboard system class.

#### Methods

- `start()`: Start the dashboard system
- `stop()`: Stop the dashboard system
- `add_metric(name, value, ...)`: Add metric data point
- `create_dashboard(dashboard)`: Create new dashboard
- `get_dashboard_data(dashboard_id)`: Get dashboard data for rendering
- `get_capacity_forecast(metric_name, days)`: Generate capacity forecast
- `get_optimization_recommendations(time_range)`: Get optimization suggestions
- `get_system_overview()`: Get system health overview

### MetricCollector

Metric collection and storage.

#### Methods

- `add_metric_point(name, value, ...)`: Add metric data point
- `get_metric_series(name, time_range)`: Get metric time series
- `get_metric_statistics(name, time_range)`: Get metric statistics
- `get_available_metrics()`: List available metrics

### CapacityPlanner

Capacity planning and forecasting.

#### Methods

- `generate_capacity_forecast(metric_name, days, limit)`: Generate forecast

### OptimizationEngine

Performance optimization recommendations.

#### Methods

- `generate_recommendations(time_range)`: Generate optimization recommendations

## Examples

See `nautilus_trader_engine/monitoring/performance_dashboard.py` for the complete example in the `example_usage()` function, which demonstrates:

- Dashboard initialization and startup
- Custom metric collection
- Dashboard creation and management
- Capacity forecasting
- Optimization recommendations
- System overview and health monitoring