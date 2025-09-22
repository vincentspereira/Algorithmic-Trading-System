# Comprehensive Monitoring for Nautilus Trader Engine

This directory contains the complete monitoring, logging, and observability stack for the Nautilus Trader Engine, providing institutional-grade visibility into system performance, health, and behavior.

## Overview

The monitoring system provides:

- **Real-time Metrics**: Performance and business metrics collection
- **Distributed Tracing**: Request tracing across microservices
- **Log Aggregation**: Centralized logging with advanced search
- **Alerting**: Intelligent alerting with escalation policies
- **Dashboards**: Comprehensive visualization and reporting
- **Health Checks**: Automated system health validation
- **Performance Monitoring**: Detailed performance analysis and profiling

## Architecture

### Monitoring Stack

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │    │   Prometheus    │    │     Grafana     │
│   (Metrics)     │───▶│   (Collection)  │───▶│  (Dashboards)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Jaeger        │    │     Loki        │    │   AlertManager  │
│   (Tracing)     │    │   (Logging)     │───▶│   (Alerts)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Node Exporter │    │  Promtail       │    │   Slack/Email   │
│  (System)       │    │  (Log Shipping) │    │  (Notifications)|
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Metrics Collection

### Application Metrics

#### Business Metrics

```python
from monitoring.metrics import BusinessMetrics

# Trading performance metrics
metrics = BusinessMetrics()

# Record trade execution
metrics.record_trade(
    symbol="AAPL",
    side="BUY",
    quantity=100,
    price=150.25,
    strategy="momentum"
)

# Record P&L
metrics.record_pnl(
    account_id="account_123",
    realized_pnl=1250.50,
    unrealized_pnl=-320.75
)

# Record signal accuracy
metrics.record_signal_accuracy(
    strategy="rsi_divergence",
    accuracy=0.78,
    total_signals=150
)
```

#### Performance Metrics

```python
from monitoring.metrics import PerformanceMetrics

perf_metrics = PerformanceMetrics()

# Record API response times
@perf_metrics.timed("api_response_time")
async def get_portfolio(request):
    # API logic here
    return portfolio_data

# Record database query performance
with perf_metrics.timed("database_query"):
    result = db.execute("SELECT * FROM trades")

# Record memory usage
perf_metrics.record_memory_usage()

# Record error rates
perf_metrics.record_error("database_connection_failed")
```

#### System Metrics

```python
from monitoring.metrics import SystemMetrics

sys_metrics = SystemMetrics()

# Record resource usage
sys_metrics.record_cpu_usage()
sys_metrics.record_memory_usage()
sys_metrics.record_disk_usage()
sys_metrics.record_network_io()

# Record queue depths
sys_metrics.record_queue_depth("order_queue", 45)
sys_metrics.record_queue_depth("signal_queue", 12)
```

### Custom Metrics

#### Counter Metrics

```python
from prometheus_client import Counter

# Trade counter
trades_total = Counter(
    'trades_total',
    'Total number of trades executed',
    ['strategy', 'symbol', 'side']
)

# Increment counter
trades_total.labels(
    strategy='momentum',
    symbol='AAPL',
    side='BUY'
).inc()
```

#### Gauge Metrics

```python
from prometheus_client import Gauge

# Account balance gauge
account_balance = Gauge(
    'account_balance',
    'Current account balance',
    ['account_id', 'currency']
)

# Set gauge value
account_balance.labels(
    account_id='acc_123',
    currency='USD'
).set(100000.50)
```

#### Histogram Metrics

```python
from prometheus_client import Histogram

# Request duration histogram
request_duration = Histogram(
    'request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

# Time function execution
with request_duration.labels(
    method='GET',
    endpoint='/api/portfolio'
).time():
    result = get_portfolio()
```

## Distributed Tracing

### Setting up Tracing

```python
from monitoring.tracing import setup_tracing, create_span

# Initialize tracing
setup_tracing(
    service_name="nautilus-trader-engine",
    jaeger_host="jaeger:14268"
)

# Create spans for operations
with create_span("execute_trade") as span:
    span.set_attribute("symbol", "AAPL")
    span.set_attribute("quantity", 100)

    # Trade execution logic
    result = execute_trade_logic()

    span.set_attribute("success", result.success)
    if not result.success:
        span.record_exception(result.error)
```

### Custom Spans

```python
from monitoring.tracing import tracer

# Manual span creation
with tracer.start_as_current_span("complex_calculation") as span:
    span.set_attribute("algorithm", "rsi_calculation")
    span.set_attribute("period", 14)

    # Complex calculation
    rsi_values = calculate_rsi(prices, 14)

    span.set_attribute("data_points", len(rsi_values))
    span.add_event("calculation_completed")
```

## Logging

### Structured Logging

```python
import structlog
from monitoring.logging import setup_logging

# Configure structured logging
setup_logging(
    level="INFO",
    format="json",
    loki_url="http://loki:3100"
)

# Structured log entries
logger = structlog.get_logger()

# Business logic logging
logger.info(
    "trade_executed",
    symbol="AAPL",
    side="BUY",
    quantity=100,
    price=150.25,
    strategy="momentum",
    account_id="acc_123"
)

# Error logging with context
try:
    result = risky_operation()
except Exception as e:
    logger.error(
        "operation_failed",
        operation="risky_operation",
        error=str(e),
        error_type=type(e).__name__,
        stack_trace=traceback.format_exc()
    )
```

### Log Levels and Context

```python
# Debug logging for development
logger.debug(
    "indicator_calculation",
    indicator="RSI",
    period=14,
    data_points=len(prices),
    execution_time=0.023
)

# Warning for potential issues
logger.warning(
    "high_volatility_detected",
    symbol="TSLA",
    volatility=0.45,
    threshold=0.30,
    timestamp=datetime.now().iso()
)

# Error for failures
logger.error(
    "broker_connection_lost",
    broker="interactive_brokers",
    error="connection_timeout",
    retry_count=3
)

# Critical for system issues
logger.critical(
    "database_unavailable",
    database="postgresql",
    impact="trading_halted",
    affected_accounts=150
)
```

## Alerting

### Alert Rules

```yaml
# alerting_rules.yml
groups:
  - name: trading_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }}% which is above 5%"

      - alert: LowTradeVolume
        expr: rate(trades_total[1h]) < 10
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Low trading volume"
          description: "Only {{ $value }} trades in the last hour"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API latency"
          description: "95th percentile latency is {{ $value }}s"
```

### Alert Manager Configuration

```yaml
# alertmanager.yml
global:
  smtp_smtp:
    host: smtp.gmail.com
    port: 587
    username: alerts@nautilus-trader.com
    password: ${SMTP_PASSWORD}

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'team-notifications'
  routes:
    - match:
        severity: critical
      receiver: 'critical-notifications'

receivers:
  - name: 'team-notifications'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK}'
        channel: '#trading-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ .CommonAnnotations.description }}'

  - name: 'critical-notifications'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK}'
        channel: '#critical-alerts'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_KEY}'
```

## Dashboards

### Grafana Dashboards

#### Trading Performance Dashboard

- **Real-time P&L**: Current profit/loss across accounts
- **Trade Volume**: Number of trades executed over time
- **Strategy Performance**: Win rate and returns by strategy
- **Risk Metrics**: VaR, Sharpe ratio, max drawdown

#### System Performance Dashboard

- **API Response Times**: Latency percentiles and trends
- **Resource Usage**: CPU, memory, disk, network utilization
- **Error Rates**: Application and infrastructure errors
- **Queue Depths**: Processing queue lengths

#### Business Metrics Dashboard

- **Account Balances**: Real-time account equity
- **Position Sizes**: Current exposure by asset
- **Market Data**: Feed health and latency
- **Compliance**: Regulatory metric tracking

### Custom Dashboard Creation

```python
from monitoring.dashboards import create_dashboard, Panel, Row

# Create trading dashboard
dashboard = create_dashboard("Trading Performance")

# Add P&L row
pnl_row = Row("Profit & Loss")
pnl_row.add_panel(
    Panel(
        title="Real-time P&L",
        type="graph",
        targets=[{
            "expr": "sum(realized_pnl + unrealized_pnl) by (account)",
            "legend": "{{account}}"
        }]
    )
)

dashboard.add_row(pnl_row)

# Save dashboard
dashboard.save_to_grafana(grafana_url, api_key)
```

## Health Checks

### Application Health Checks

```python
from monitoring.health import HealthChecker, HealthCheck

# Create health checker
health_checker = HealthChecker()

# Add database health check
@health_checker.add_check("database")
async def check_database():
    try:
        # Test database connection
        await db.execute("SELECT 1")
        return HealthCheck.healthy("Database connection OK")
    except Exception as e:
        return HealthCheck.unhealthy(f"Database error: {e}")

# Add broker connectivity check
@health_checker.add_check("broker")
async def check_broker():
    try:
        # Test broker connection
        connected = await broker.ping()
        if connected:
            return HealthCheck.healthy("Broker connection OK")
        else:
            return HealthCheck.unhealthy("Broker not responding")
    except Exception as e:
        return HealthCheck.unhealthy(f"Broker error: {e}")

# Add external API checks
@health_checker.add_check("market_data")
async def check_market_data():
    try:
        # Test market data feed
        data = await market_data.get_quote("AAPL")
        if data:
            return HealthCheck.healthy("Market data feed OK")
        else:
            return HealthCheck.unhealthy("No market data received")
    except Exception as e:
        return HealthCheck.unhealthy(f"Market data error: {e}")

# Expose health endpoint
@app.get("/health")
async def health_endpoint():
    return await health_checker.run_all_checks()
```

### Dependency Health Checks

```python
# Comprehensive dependency checks
health_checks = {
    "redis": check_redis_connection,
    "postgres": check_postgres_connection,
    "rabbitmq": check_rabbitmq_connection,
    "external_api": check_external_api,
    "disk_space": check_disk_space,
    "memory_usage": check_memory_usage
}

# Run all checks
results = await health_checker.run_checks(health_checks)

# Return detailed health status
return {
    "status": "healthy" if all(r.healthy for r in results.values()) else "unhealthy",
    "checks": {name: check.to_dict() for name, check in results.items()},
    "timestamp": datetime.now().isoformat()
}
```

## Performance Profiling

### Code Profiling

```python
from monitoring.profiling import Profiler

profiler = Profiler()

# Profile function execution
@profiler.profile
def calculate_indicators(prices, volumes):
    # Complex indicator calculations
    rsi = calculate_rsi(prices)
    macd = calculate_macd(prices)
    bollinger = calculate_bollinger_bands(prices)

    return {
        'rsi': rsi,
        'macd': macd,
        'bollinger': bollinger
    }

# Profile async functions
@profiler.profile_async
async def execute_trading_strategy(signals):
    # Trading logic
    trades = []
    for signal in signals:
        trade = await execute_trade(signal)
        trades.append(trade)

    return trades

# Get profiling results
profile_data = profiler.get_results()
print(f"Total execution time: {profile_data['total_time']}")
print(f"Most expensive function: {profile_data['bottlenecks'][0]}")
```

### Memory Profiling

```python
from monitoring.profiling import MemoryProfiler

memory_profiler = MemoryProfiler()

# Profile memory usage
@memory_profiler.profile_memory
def process_large_dataset(data):
    # Memory-intensive operations
    processed_data = heavy_processing(data)
    results = complex_calculations(processed_data)

    return results

# Get memory statistics
memory_stats = memory_profiler.get_memory_stats()
print(f"Peak memory usage: {memory_stats['peak_memory']} MB")
print(f"Memory growth: {memory_stats['memory_growth']} MB")
```

## Integration Examples

### Prometheus Integration

```python
from prometheus_client import start_http_server, Counter, Histogram
from monitoring.metrics import MetricsCollector

# Start metrics server
start_http_server(8001)

# Create metrics collector
metrics = MetricsCollector()

# Business metrics
trades_executed = Counter(
    'trades_executed_total',
    'Total number of trades executed',
    ['strategy', 'symbol']
)

trade_value = Histogram(
    'trade_value_dollars',
    'Value of executed trades',
    ['strategy'],
    buckets=[100, 1000, 10000, 100000, 1000000]
)

# Record metrics
def record_trade(trade):
    trades_executed.labels(
        strategy=trade.strategy,
        symbol=trade.symbol
    ).inc()

    trade_value.labels(
        strategy=trade.strategy
    ).observe(trade.value)
```

### Jaeger Tracing Integration

```python
from jaeger_client import Config
from monitoring.tracing import TracingManager

# Configure Jaeger
config = Config(
    config={
        'sampler': {
            'type': 'const',
            'param': 1,
        },
        'local_agent': {
            'reporting_host': 'jaeger',
            'reporting_port': 14268,
        },
        'logging': True,
    },
    service_name='nautilus-trader-engine',
)

# Initialize tracing
tracer = config.initialize_tracer()

# Create tracing manager
tracing_manager = TracingManager(tracer)

# Trace operations
@tracing_manager.trace
async def process_trade_request(request):
    with tracer.start_active_span('validate_request') as scope:
        # Validation logic
        is_valid = validate_request(request)
        scope.span.set_tag('valid', is_valid)

    if is_valid:
        with tracer.start_active_span('execute_trade') as scope:
            # Trade execution
            result = await execute_trade(request)
            scope.span.set_tag('success', result.success)

    return result
```

### ELK Stack Integration

```python
import logging
from elasticsearch import Elasticsearch
from monitoring.logging import ELKHandler

# Configure ELK logging
es = Elasticsearch(['elasticsearch:9200'])
elk_handler = ELKHandler(es, index='nautilus-logs')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    handlers=[elk_handler]
)

logger = logging.getLogger('nautilus')

# Structured logging to ELK
logger.info('Trade executed', extra={
    'trade_id': '12345',
    'symbol': 'AAPL',
    'quantity': 100,
    'price': 150.25,
    'strategy': 'momentum',
    'pnl': 125.50
})
```

## Alerting Examples

### Custom Alert Rules

```python
from monitoring.alerting import AlertManager, AlertRule

alert_manager = AlertManager()

# Define custom alert rules
rules = [
    AlertRule(
        name="HighSlippage",
        condition=lambda: get_average_slippage() > 0.005,
        severity="warning",
        message="Average slippage exceeded 0.5%",
        cooldown_minutes=15
    ),

    AlertRule(
        name="StrategyDivergence",
        condition=lambda: detect_strategy_divergence() > 0.1,
        severity="critical",
        message="Strategy performance diverged significantly",
        cooldown_minutes=5
    ),

    AlertRule(
        name="DataFeedDelay",
        condition=lambda: get_data_feed_delay() > 30,
        severity="warning",
        message="Market data feed delay exceeded 30 seconds",
        cooldown_minutes=10
    )
]

# Register rules
for rule in rules:
    alert_manager.add_rule(rule)

# Start monitoring
alert_manager.start_monitoring(interval_seconds=60)
```

## Best Practices

### Metrics Collection

1. **Use appropriate metric types**: Counters for events, gauges for states, histograms for distributions
2. **Add relevant labels**: Include dimensions for filtering and aggregation
3. **Avoid high cardinality**: Don't create metrics with unbounded label values
4. **Use meaningful names**: Follow naming conventions (e.g., `http_requests_total`)

### Logging Practices

1. **Structured logging**: Use key-value pairs instead of free-form text
2. **Appropriate log levels**: DEBUG for development, INFO for normal operations, WARN/ERROR for issues
3. **Include context**: Add relevant IDs, timestamps, and metadata
4. **Performance aware**: Avoid expensive operations in logging code

### Alerting Guidelines

1. **Alert on symptoms, not causes**: Alert when user experience is impacted
2. **Set appropriate thresholds**: Use statistical analysis to determine normal ranges
3. **Avoid alert fatigue**: Use appropriate cooldown periods and escalation
4. **Include actionable information**: Alerts should contain enough context to investigate

### Dashboard Design

1. **Focus on key metrics**: Show the most important information prominently
2. **Use consistent layouts**: Standardize dashboard layouts across teams
3. **Include time ranges**: Allow users to view data across different time periods
4. **Add documentation**: Include descriptions and links to runbooks

## Troubleshooting

### Common Monitoring Issues

#### Metrics Not Appearing

```bash
# Check Prometheus targets
curl http://prometheus:9090/api/v1/targets

# Verify metrics endpoint
curl http://localhost:8001/metrics

# Check service discovery
docker-compose logs prometheus
```

#### Tracing Not Working

```bash
# Check Jaeger UI
open http://localhost:16686

# Verify tracing configuration
docker-compose logs jaeger

# Test tracing manually
curl -X POST http://localhost:14268/api/traces \
  -H "Content-Type: application/json" \
  -d @test_trace.json
```

#### Logs Not Appearing

```bash
# Check Loki logs
curl "http://loki:3100/loki/api/v1/query?query={job=\"nautilus\"}"

# Verify Promtail configuration
docker-compose logs promtail

# Test log shipping
docker-compose exec promtail logcli query "{job=\"nautilus\"}"
```

### Performance Issues

#### High Memory Usage

```bash
# Check memory metrics
curl http://prometheus:9090/api/v1/query?query=process_resident_memory_bytes

# Profile memory usage
python -m memory_profiler script.py

# Check for memory leaks
python -c "
import tracemalloc
tracemalloc.start()
# Run code
snapshot = tracemalloc.take_snapshot()
for stat in snapshot.statistics('lineno')[:10]:
    print(stat)
"
```

#### High CPU Usage

```bash
# Profile CPU usage
python -m cProfile -s time script.py

# Check system metrics
curl http://prometheus:9090/api/v1/query?query=rate(process_cpu_user_seconds_total[5m])

# Use py-spy for live profiling
py-spy top --pid $(pgrep python)
```

## Security Considerations

### Monitoring Security

1. **Access control**: Restrict access to monitoring dashboards and APIs
2. **Data encryption**: Encrypt sensitive monitoring data at rest and in transit
3. **Audit logging**: Log all access to monitoring systems
4. **Network security**: Isolate monitoring traffic on private networks

### Metrics Security

1. **Sensitive data**: Avoid logging or metrics containing sensitive information
2. **PII protection**: Anonymize or exclude personally identifiable information
3. **Access logging**: Log all queries to metrics and logs
4. **Rate limiting**: Implement rate limiting on monitoring endpoints

## Scaling Considerations

### Horizontal Scaling

```yaml
# Docker Compose scaling
services:
  nautilus-trader-engine:
    deploy:
      replicas: 3
    labels:
      - "prometheus-job=nautilus"
      - "prometheus-port=8001"
```

### Monitoring at Scale

1. **Federated Prometheus**: Use federation for multi-region setups
2. **Thanos**: Long-term storage and global querying
3. **Cortex**: Horizontally scalable Prometheus backend
4. **Loki scaling**: Use object storage for log scaling

## Integration with CI/CD

### Automated Testing

```yaml
# CI pipeline with monitoring validation
- name: Run integration tests
  run: |
    docker-compose up -d
    sleep 30
    python -m pytest tests/integration/ -v

- name: Validate monitoring
  run: |
    # Check metrics are being collected
    curl -f http://prometheus:9090/api/v1/query?query=up

    # Check health endpoints
    curl -f http://localhost:8000/health

    # Validate dashboards
    curl -f http://grafana:3000/api/health
```

### Deployment Monitoring

```yaml
# Deployment with monitoring
- name: Deploy application
  run: |
    docker-compose up -d --scale nautilus-trader-engine=2

- name: Wait for healthy deployment
  run: |
    for i in {1..30}; do
      if curl -f http://localhost:8000/health; then
        echo "Application is healthy"
        break
      fi
      sleep 10
    done

- name: Validate metrics collection
  run: |
    # Ensure new instances are being monitored
    instances=$(curl -s http://prometheus:9090/api/v1/query?query=up | jq '.data.result | length')
    if [ "$instances" -lt 2 ]; then
      echo "Not all instances are being monitored"
      exit 1
    fi
```

This comprehensive monitoring setup ensures the Nautilus Trader Engine maintains high availability, performance, and observability in production environments.