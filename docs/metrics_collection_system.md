# Metrics Collection System Documentation

## Overview

The Metrics Collection System provides comprehensive metrics collection for business-level KPIs, system performance metrics, custom metric definitions, and metrics aggregation and storage. It's designed to monitor all aspects of the trading system with real-time collection, aggregation, and analysis capabilities.

## Key Features

- **Business-Level KPI Tracking**: Trading volume, P&L, order metrics, portfolio values
- **System Performance Metrics**: CPU, memory, latency, throughput, error rates
- **Custom Metric Definitions**: Flexible framework for application-specific metrics
- **Real-Time Aggregation**: Automatic metric aggregation with configurable windows
- **Thread-Safe Collection**: Concurrent metric collection with proper synchronization
- **Retention Management**: Automatic cleanup of old metrics based on retention policies

## Architecture

### Core Components

1. **MetricCollector**: Core engine for metric collection and storage
2. **BusinessMetricsCollector**: Specialized collector for trading and portfolio metrics
3. **SystemMetricsCollector**: System resource and performance metrics
4. **CustomMetricsRegistry**: Registry for application-specific metrics
5. **MetricsAggregator**: Aggregation engine with configurable windows
6. **MetricsCollectionSystem**: Main orchestrator and management interface

### Data Flow

```
Raw Metrics → MetricCollector → Buffer → Aggregator → Storage
                    ↓
            Real-time Access ← Query Interface
```

## Usage Examples

### Basic Setup

```python
import asyncio
from nautilus_trader_engine.monitoring.metrics_collection import (
    MetricsCollectionSystem, MetricType, MetricCategory
)

# Initialize the metrics system
metrics_system = MetricsCollectionSystem(max_buffer_size=10000)

# Start the system
await metrics_system.start()
```

### Business Metrics Collection

```python
async def collect_trading_data():
    # Collect business metrics
    business_data = {
        "trading": {
            "total_orders": 250,
            "filled_orders": 240,
            "daily_volume": 2500000.0
        },
        "portfolio": {
            "total_value": 10000000.0,
            "realized_pnl": 75000.0,
            "unrealized_pnl": -15000.0
        },
        "risk": {
            "daily_var": 150000.0,
            "total_exposure": 9500000.0
        }
    }
    
    await metrics_system.collect_business_metrics(business_data)
    
    print("Business metrics collected successfully")

# Run collection
asyncio.run(collect_trading_data())
```

### Custom Metrics Registration

```python
# Register custom metrics with calculators
def calculate_sharpe_ratio(returns, risk_free_rate=0.02):
    if len(returns) < 2:
        return 0
    excess_returns = [r - risk_free_rate/252 for r in returns]
    mean_excess = statistics.mean(excess_returns)
    std_excess = statistics.stdev(excess_returns)
    return (mean_excess / std_excess) * math.sqrt(252) if std_excess > 0 else 0

# Register the custom metric
metrics_system.register_custom_metric(
    name="strategy.sharpe_ratio",
    metric_type=MetricType.GAUGE,
    description="Strategy Sharpe ratio",
    unit="ratio",
    calculator=calculate_sharpe_ratio
)

# Collect custom metric
daily_returns = [0.01, 0.02, -0.005, 0.015, 0.008, -0.003, 0.012]
metrics_system.custom_registry.collect_custom_metric(
    "strategy.sharpe_ratio", 
    daily_returns
)
```

### Direct Metric Collection

```python
# Collect individual metrics
metrics_system.collect_metric("orders.executed", 45, tags={"strategy": "momentum"})
metrics_system.collect_metric("latency.order_processing", 2.5, tags={"venue": "NYSE"})
metrics_system.collect_metric("portfolio.drawdown", -0.03)

# Collect with metadata
metrics_system.collector.collect_metric(
    "trade.execution_quality", 
    0.95, 
    tags={"asset_class": "equity"},
    metadata={"calculation_method": "implementation_shortfall"}
)
```

### Metric Aggregation

```python
# Get aggregated metrics
aggregated = metrics_system.collector.aggregate_metrics("trading.orders.total", window_seconds=300)

if aggregated:
    print(f"Orders in last 5 minutes:")
    print(f"  Count: {aggregated.count}")
    print(f"  Average: {aggregated.avg_value:.2f}")
    print(f"  Min: {aggregated.min_value}")
    print(f"  Max: {aggregated.max_value}")
    print(f"  Sum: {aggregated.sum_value}")
    
    if aggregated.percentiles:
        print(f"  P95: {aggregated.percentiles['p95']:.2f}")
        print(f"  P99: {aggregated.percentiles['p99']:.2f}")
```

### System Monitoring

```python
# Get system metrics summary
summary = metrics_system.get_metrics_summary()

print(f"System Status: {summary['system_status']}")
print(f"Total Metrics Collected: {summary['collection_stats']['total_metrics_collected']}")
print(f"Registered Metrics: {summary['registered_metrics']}")
print(f"Buffer Utilization: {summary['collection_stats']['buffer_utilization']:.1%}")

# Recent metric values
if summary.get("recent_values"):
    for metric_name, data in summary["recent_values"].items():
        print(f"{metric_name}: {data['latest_value']} (at {data['latest_timestamp']})")
```

### Time-Range Queries

```python
from datetime import datetime, timedelta

# Get metrics for specific time range
end_time = datetime.now()
start_time = end_time - timedelta(hours=1)

# Get raw metric values
values = metrics_system.collector.get_metric_values(
    "portfolio.value.total", 
    start_time, 
    end_time
)

print(f"Portfolio values in last hour: {len(values)} data points")
for value in values[-5:]:  # Last 5 values
    print(f"  {value.timestamp}: ${value.value:,.2f}")

# Get aggregated metrics for time range
aggregated_list = metrics_system.aggregator.get_aggregated_metrics(
    "trading.volume.daily",
    start_time,
    end_time
)

print(f"Aggregated trading volume: {len(aggregated_list)} windows")
```

## Metric Types and Categories

### Metric Types

- **COUNTER**: Monotonically increasing values (e.g., total orders)
- **GAUGE**: Point-in-time values (e.g., portfolio value, CPU usage)
- **HISTOGRAM**: Distribution of values (e.g., latency distribution)
- **TIMER**: Duration measurements (e.g., execution time)
- **RATE**: Rate of change (e.g., orders per second)
- **PERCENTAGE**: Percentage values (e.g., fill rate, success rate)

### Metric Categories

- **BUSINESS**: Trading, portfolio, and financial metrics
- **SYSTEM**: Infrastructure and resource metrics
- **PERFORMANCE**: Latency, throughput, and efficiency metrics
- **TRADING**: Order execution and market data metrics
- **RISK**: Risk management and exposure metrics
- **CUSTOM**: Application-specific metrics

## Built-in Metrics

### Business Metrics

- `trading.orders.total`: Total number of orders placed
- `trading.orders.filled`: Number of filled orders
- `trading.volume.daily`: Daily trading volume in USD
- `trading.pnl.realized`: Realized profit and loss
- `trading.pnl.unrealized`: Unrealized profit and loss
- `portfolio.value.total`: Total portfolio value
- `risk.var.daily`: Daily Value at Risk
- `risk.exposure.total`: Total risk exposure

### System Metrics

- `system.cpu.usage`: CPU usage percentage
- `system.memory.usage`: Memory usage percentage
- `system.latency.api`: API response latency
- `system.throughput.requests`: Request throughput
- `system.errors.total`: Total system errors
- `system.uptime`: System uptime in seconds

## Configuration Options

### System Configuration

```python
# Configure collection system
metrics_system = MetricsCollectionSystem(
    max_buffer_size=50000  # Maximum metrics in memory buffer
)

# Configure metric definitions
from nautilus_trader_engine.monitoring.metrics_collection import MetricDefinition

custom_metric = MetricDefinition(
    name="custom.metric.name",
    metric_type=MetricType.GAUGE,
    category=MetricCategory.CUSTOM,
    description="Custom metric description",
    unit="units",
    aggregation_window=300,  # 5 minutes
    retention_period=604800,  # 7 days
    alert_thresholds={"warning": 100, "critical": 200}
)
```

### Aggregation Configuration

```python
# Start custom aggregation tasks
metrics_system.aggregator.start_aggregation_task(
    metric_name="custom.important.metric",
    interval_seconds=30  # Aggregate every 30 seconds
)

# Stop aggregation
metrics_system.aggregator.stop_aggregation_task("custom.important.metric")
```

## Data Structures

### MetricDefinition

```python
@dataclass
class MetricDefinition:
    name: str
    metric_type: MetricType
    category: MetricCategory
    description: str
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    aggregation_window: int = 60  # seconds
    retention_period: int = 86400  # seconds
    alert_thresholds: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
```

### MetricValue

```python
@dataclass
class MetricValue:
    value: Union[float, int]
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### AggregatedMetric

```python
@dataclass
class AggregatedMetric:
    name: str
    start_time: datetime
    end_time: datetime
    count: int
    sum_value: float
    min_value: float
    max_value: float
    avg_value: float
    percentiles: Dict[str, float] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
```

## Performance Considerations

- **Thread Safety**: All operations are thread-safe with proper locking
- **Memory Management**: Automatic buffer size management and cleanup
- **Efficient Storage**: Deque-based storage for O(1) append/pop operations
- **Lazy Aggregation**: Aggregation computed on-demand to reduce overhead
- **Configurable Retention**: Automatic cleanup based on retention policies

## Error Handling

The system includes comprehensive error handling:

- **Collection Failures**: Graceful handling of metric collection errors
- **Invalid Metrics**: Validation and rejection of invalid metric data
- **Resource Limits**: Protection against memory exhaustion
- **Recovery**: Automatic recovery from transient failures

## Integration Points

### With Trading System

```python
# Integration with order management
async def on_order_filled(order):
    await metrics_system.collect_business_metrics({
        "trading": {
            "total_orders": order_manager.total_orders,
            "filled_orders": order_manager.filled_orders,
            "daily_volume": order_manager.daily_volume
        }
    })

# Integration with portfolio management
async def on_portfolio_update(portfolio):
    await metrics_system.collect_business_metrics({
        "portfolio": {
            "total_value": portfolio.total_value,
            "realized_pnl": portfolio.realized_pnl,
            "unrealized_pnl": portfolio.unrealized_pnl
        }
    })
```

### With Alerting System

```python
# Check thresholds and trigger alerts
def check_metric_thresholds(metric_name, value):
    definition = metrics_system.collector.metric_definitions.get(metric_name)
    if definition and definition.alert_thresholds:
        if value > definition.alert_thresholds.get("critical", float('inf')):
            # Trigger critical alert
            pass
        elif value > definition.alert_thresholds.get("warning", float('inf')):
            # Trigger warning alert
            pass
```

## Testing

Run the comprehensive test suite:

```bash
# Run all metrics tests
python -m pytest tests/test_metrics_collection.py -v

# Run specific test categories
python -m pytest tests/test_metrics_collection.py::TestMetricCollector -v
python -m pytest tests/test_metrics_collection.py::TestBusinessMetricsCollector -v
python -m pytest tests/test_metrics_collection.py::TestSystemMetricsCollector -v

# Run integration test
python -m pytest tests/test_metrics_collection.py::test_integration_scenario -v
```

## Future Enhancements

Planned improvements:

- **Storage Backends**: Integration with time-series databases (InfluxDB, Prometheus)
- **Real-Time Streaming**: WebSocket-based real-time metric streaming
- **Advanced Aggregations**: Moving averages, exponential smoothing
- **Metric Correlation**: Automatic correlation analysis between metrics
- **Predictive Analytics**: ML-based metric forecasting and anomaly detection

## API Reference

### MetricsCollectionSystem

Main system class for comprehensive metrics management.

#### Methods

- `start()`: Start the metrics collection system
- `stop()`: Stop the metrics collection system
- `collect_business_metrics(metric_data)`: Collect business metrics
- `register_custom_metric(name, type, description, ...)`: Register custom metric
- `collect_metric(name, value, tags)`: Collect individual metric
- `get_metrics_summary()`: Get comprehensive system summary

### Component Classes

- `MetricCollector`: Core metric collection and storage
- `BusinessMetricsCollector`: Business and trading metrics
- `SystemMetricsCollector`: System performance metrics
- `CustomMetricsRegistry`: Custom metric management
- `MetricsAggregator`: Metric aggregation and analysis

## Examples

See `nautilus_trader_engine/monitoring/metrics_collection.py` for the complete example in the `example_usage()` function, which demonstrates:

- System startup and configuration
- Business metrics collection
- Custom metric registration
- Real-time aggregation
- System monitoring and summary generation