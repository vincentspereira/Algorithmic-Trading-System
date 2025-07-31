# Distributed Tracing System Documentation

## Overview

The Distributed Tracing System provides comprehensive end-to-end request tracking, performance bottleneck identification, and trace-based debugging capabilities for the Nautilus Trader Engine. It supports both OpenTelemetry integration and a custom tracing implementation for environments where OpenTelemetry is not available.

## Key Features

- **End-to-End Request Tracing**: Complete request lifecycle tracking across services
- **Performance Bottleneck Identification**: Automated detection of slow operations
- **Trace-Based Debugging**: Advanced debugging tools with trace tree analysis
- **OpenTelemetry Integration**: Industry-standard tracing with Jaeger support
- **Custom Tracer Fallback**: Built-in tracer when OpenTelemetry is unavailable
- **Async/Sync Support**: Full support for both synchronous and asynchronous operations

## Architecture

### Core Components

1. **DistributedTracer**: Main tracing orchestrator with OpenTelemetry integration
2. **CustomTracer**: Fallback tracer implementation for standalone operation
3. **PerformanceAnalyzer**: Performance analysis and bottleneck detection
4. **TraceDebugger**: Advanced debugging and trace analysis tools
5. **Global Tracing Functions**: Convenient global access and decorators

### Tracing Hierarchy

```
Trace (Request/Transaction)
├── Root Span (Entry Point)
│   ├── Child Span (Database Query)
│   ├── Child Span (Business Logic)
│   │   └── Grandchild Span (Validation)
│   └── Child Span (Response Generation)
```

## Usage Examples

### Basic Setup

```python
from nautilus_trader_engine.monitoring.distributed_tracing import (
    initialize_tracing, get_tracer, trace
)

# Initialize global tracing
tracer = initialize_tracing(
    service_name="nautilus-trader",
    jaeger_endpoint="http://localhost:14268/api/traces",  # Optional
    sampling_rate=1.0
)
```

### Function Decorators

```python
# Using global decorator
@trace("database_query")
async def fetch_user_data(user_id: str):
    """Fetch user data from database"""
    await asyncio.sleep(0.1)  # Simulate DB latency
    return f"user_data_{user_id}"

@trace("business_logic", tags={"version": "1.0"})
def process_data(data: str):
    """Process business logic"""
    return data.upper()

# Using tracer instance decorator
@tracer.trace_function("cache_lookup", span_kind=SpanKind.CLIENT)
async def check_cache(key: str):
    """Check cache for data"""
    await asyncio.sleep(0.01)
    return None  # Cache miss
```

### Context Managers

```python
async def complex_workflow():
    """Complex workflow with nested tracing"""
    
    # Async context manager
    async with tracer.trace_async("user_workflow", tags={"user_id": "12345"}) as span:
        
        # Nested operation
        async with tracer.trace_async("data_validation"):
            if not validate_input():
                raise ValueError("Invalid input")
        
        # Another nested operation
        async with tracer.trace_async("data_processing"):
            result = await process_user_data()
        
        return result

def sync_operation():
    """Synchronous operation tracing"""
    with tracer.trace_sync("file_processing") as span:
        # Add custom tags
        tracer.custom_tracer.add_span_tag(span, "file_size", "1024")
        
        # Add logs
        tracer.custom_tracer.add_span_log(span, "Starting file processing")
        
        # Process file
        process_file()
        
        tracer.custom_tracer.add_span_log(span, "File processing completed")
```

### Manual Span Management

```python
from nautilus_trader_engine.monitoring.distributed_tracing import (
    CustomTracer, SpanContext, SpanKind, TraceLevel
)

# Create custom tracer
custom_tracer = CustomTracer("my-service")

# Start parent span
parent_span = custom_tracer.start_span("parent_operation")

# Create child span context
child_context = SpanContext(
    trace_id=parent_span.trace_id,
    span_id=parent_span.span_id
)

# Start child span
child_span = custom_tracer.start_span(
    "child_operation", 
    parent_context=child_context,
    span_kind=SpanKind.CLIENT,
    tags={"operation_type": "database"}
)

# Add tags and logs
custom_tracer.add_span_tag(child_span, "query", "SELECT * FROM users")
custom_tracer.add_span_log(child_span, "Executing query", TraceLevel.INFO)

# Finish spans
custom_tracer.finish_span(child_span)
custom_tracer.finish_span(parent_span)
```

## Performance Analysis

### Bottleneck Detection

```python
from nautilus_trader_engine.monitoring.distributed_tracing import PerformanceAnalyzer

# Create analyzer
analyzer = PerformanceAnalyzer(tracer)

# Identify bottlenecks
bottlenecks = analyzer.identify_bottlenecks(threshold_ms=1000.0)

for bottleneck in bottlenecks:
    print(f"Bottleneck: {bottleneck['operation']}")
    print(f"  Average Duration: {bottleneck['avg_duration_ms']:.2f}ms")
    print(f"  P95 Duration: {bottleneck['p95_duration_ms']:.2f}ms")
    print(f"  Severity: {bottleneck['severity']}")
    print(f"  Sample Count: {bottleneck['sample_count']}")
```

### Operation Statistics

```python
# Get detailed statistics for an operation
stats = analyzer.get_operation_stats("database_query")

print(f"Operation: {stats['operation']}")
print(f"Sample Count: {stats['sample_count']}")
print(f"Average Duration: {stats['avg_duration_ms']:.2f}ms")
print(f"Median Duration: {stats['median_duration_ms']:.2f}ms")
print(f"P95 Duration: {stats['p95_duration_ms']:.2f}ms")
print(f"P99 Duration: {stats['p99_duration_ms']:.2f}ms")
print(f"Performance Trend: {stats['recent_trend']}")
```

## Trace Debugging

### Finding Slow Traces

```python
from nautilus_trader_engine.monitoring.distributed_tracing import TraceDebugger

# Create debugger
debugger = TraceDebugger(tracer)

# Find traces that exceed threshold
slow_traces = debugger.find_slow_traces(threshold_ms=5000.0)

for trace in slow_traces:
    print(f"Slow Trace: {trace['trace_id']}")
    print(f"  Total Duration: {trace['total_duration_ms']:.2f}ms")
    print(f"  Span Count: {trace['span_count']}")
    print(f"  Operations: {', '.join(trace['operations'])}")
    print(f"  Slowest Operation: {trace['slowest_operation']}")
```

### Trace Tree Analysis

```python
# Analyze the structure of a specific trace
trace_tree = debugger.analyze_trace_tree("trace-id-12345")

print(f"Trace ID: {trace_tree['trace_id']}")
print(f"Total Spans: {trace_tree['total_spans']}")
print(f"Total Duration: {trace_tree['total_duration_ms']:.2f}ms")

def print_span_tree(spans, indent=0):
    for span in spans:
        prefix = "  " * indent
        print(f"{prefix}- {span['operation']}: {span['duration_ms']:.2f}ms")
        if span['children']:
            print_span_tree(span['children'], indent + 1)

print("Trace Structure:")
print_span_tree(trace_tree['root_spans'])
```

## Configuration Options

### Tracer Configuration

```python
# Basic configuration
tracer = DistributedTracer(
    service_name="nautilus-trader",
    sampling_rate=0.1,  # Sample 10% of traces
)

# With Jaeger integration
tracer = DistributedTracer(
    service_name="nautilus-trader",
    jaeger_endpoint="http://jaeger:14268/api/traces",
    sampling_rate=1.0  # Sample all traces
)
```

### Global Tracing Setup

```python
# Initialize with custom configuration
initialize_tracing(
    service_name="nautilus-trader-prod",
    jaeger_endpoint="http://jaeger.monitoring.svc.cluster.local:14268/api/traces",
    sampling_rate=0.05  # 5% sampling for production
)

# Get global tracer
global_tracer = get_tracer()
```

## Data Structures

### SpanData

```python
@dataclass
class SpanData:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: str = "ok"
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    span_kind: SpanKind = SpanKind.INTERNAL
    service_name: str = "nautilus-trader"
```

### SpanContext

```python
@dataclass
class SpanContext:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)
```

## Span Kinds

- **INTERNAL**: Internal operation within a service
- **SERVER**: Server-side operation (handling incoming request)
- **CLIENT**: Client-side operation (outgoing request)
- **PRODUCER**: Message producer operation
- **CONSUMER**: Message consumer operation

## Trace Levels

- **DEBUG**: Detailed debugging information
- **INFO**: General information
- **WARN**: Warning messages
- **ERROR**: Error conditions

## Integration with Trading System

### Order Processing Tracing

```python
@trace("order_processing", tags={"order_type": "market"})
async def process_order(order):
    """Process trading order with full tracing"""
    
    async with tracer.trace_async("order_validation"):
        validate_order(order)
    
    async with tracer.trace_async("risk_check"):
        await check_risk_limits(order)
    
    async with tracer.trace_async("order_execution"):
        result = await execute_order(order)
    
    async with tracer.trace_async("position_update"):
        await update_positions(result)
    
    return result
```

### Market Data Processing

```python
@trace("market_data_processing")
async def process_market_data(data):
    """Process market data with tracing"""
    
    with tracer.trace_sync("data_parsing"):
        parsed_data = parse_market_data(data)
    
    async with tracer.trace_async("data_validation"):
        validated_data = await validate_market_data(parsed_data)
    
    async with tracer.trace_async("strategy_update"):
        await update_strategies(validated_data)
    
    return validated_data
```

## Performance Considerations

- **Sampling**: Use appropriate sampling rates for production (1-10%)
- **Async Operations**: Prefer async context managers for I/O operations
- **Memory Management**: Automatic cleanup of old performance data
- **Thread Safety**: Built-in thread safety for concurrent operations

## Error Handling

The system includes comprehensive error handling:

- **Graceful Degradation**: Continues operation if tracing fails
- **Exception Tracking**: Automatic error status setting for failed spans
- **Fallback Tracing**: Custom tracer when OpenTelemetry unavailable
- **Resource Cleanup**: Automatic span cleanup and memory management

## Testing

Run the comprehensive test suite:

```bash
# Run all distributed tracing tests
python -m pytest tests/test_distributed_tracing.py -v

# Run specific test categories
python -m pytest tests/test_distributed_tracing.py::TestCustomTracer -v
python -m pytest tests/test_distributed_tracing.py::TestDistributedTracer -v
python -m pytest tests/test_distributed_tracing.py::TestPerformanceAnalyzer -v

# Run integration test
python -m pytest tests/test_distributed_tracing.py::test_integration_scenario -v
```

## OpenTelemetry Integration

### Installation

```bash
# Install OpenTelemetry packages
pip install opentelemetry-api
pip install opentelemetry-sdk
pip install opentelemetry-instrumentation-requests
pip install opentelemetry-instrumentation-asyncio
pip install opentelemetry-exporter-jaeger
```

### Jaeger Setup

```bash
# Run Jaeger with Docker
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 14268:14268 \
  jaegertracing/all-in-one:latest
```

### Custom Exporters

```python
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

# Configure Jaeger exporter
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)

# Add to tracer provider
span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)
```

## Monitoring and Alerting

### Performance Alerts

```python
def check_performance_alerts(analyzer):
    """Check for performance degradation"""
    bottlenecks = analyzer.identify_bottlenecks(threshold_ms=1000.0)
    
    for bottleneck in bottlenecks:
        if bottleneck['severity'] == 'high':
            send_alert(f"High latency detected in {bottleneck['operation']}")
        
        if bottleneck['avg_duration_ms'] > 5000.0:
            send_critical_alert(f"Critical latency in {bottleneck['operation']}")
```

### Trace Monitoring

```python
def monitor_trace_health(debugger):
    """Monitor overall trace health"""
    slow_traces = debugger.find_slow_traces(threshold_ms=10000.0)
    
    if len(slow_traces) > 10:  # More than 10 slow traces
        send_alert("High number of slow traces detected")
    
    for trace in slow_traces[:5]:  # Check top 5 slowest
        if trace['total_duration_ms'] > 30000.0:  # 30 seconds
            send_critical_alert(f"Extremely slow trace: {trace['trace_id']}")
```

## Best Practices

1. **Use Meaningful Operation Names**: Choose descriptive names for operations
2. **Add Relevant Tags**: Include context-specific tags for filtering
3. **Implement Sampling**: Use appropriate sampling rates for production
4. **Monitor Performance**: Regularly analyze bottlenecks and trends
5. **Handle Errors Gracefully**: Ensure tracing doesn't break application flow
6. **Clean Up Resources**: Let the system handle automatic cleanup
7. **Use Async Patterns**: Prefer async context managers for I/O operations

## Troubleshooting

### Common Issues

1. **OpenTelemetry Import Errors**: Install required packages or use custom tracer
2. **High Memory Usage**: Reduce sampling rate or check for span leaks
3. **Performance Impact**: Lower sampling rate or optimize traced operations
4. **Missing Traces**: Check tracer initialization and span finishing

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger('nautilus_trader_engine.monitoring.distributed_tracing').setLevel(logging.DEBUG)

# Check tracer status
tracer = get_tracer()
print(f"Tracer available: {tracer is not None}")
print(f"OpenTelemetry available: {tracer.tracer is not None if tracer else False}")
print(f"Custom tracer available: {tracer.custom_tracer is not None if tracer else False}")
```

## Future Enhancements

Planned improvements:

- **Distributed Context Propagation**: Cross-service trace correlation
- **Advanced Sampling Strategies**: Intelligent sampling based on operation type
- **Real-Time Dashboards**: Live performance monitoring dashboards
- **Machine Learning Integration**: AI-powered anomaly detection
- **Custom Metrics Integration**: Correlation with business metrics

## API Reference

### DistributedTracer

Main tracing class with OpenTelemetry integration.

#### Methods

- `trace_async(operation_name, span_kind, tags)`: Async context manager
- `trace_sync(operation_name, span_kind, tags)`: Sync context manager
- `trace_function(operation_name, span_kind, tags)`: Function decorator

### CustomTracer

Fallback tracer implementation.

#### Methods

- `start_span(operation_name, parent_context, span_kind, tags)`: Start new span
- `finish_span(span, status)`: Finish span
- `add_span_tag(span, key, value)`: Add tag to span
- `add_span_log(span, message, level)`: Add log to span

### PerformanceAnalyzer

Performance analysis and bottleneck detection.

#### Methods

- `identify_bottlenecks(threshold_ms)`: Find performance bottlenecks
- `get_operation_stats(operation_name)`: Get detailed operation statistics

### TraceDebugger

Advanced debugging and trace analysis.

#### Methods

- `find_slow_traces(threshold_ms)`: Find traces exceeding threshold
- `analyze_trace_tree(trace_id)`: Analyze trace structure

## Examples

See `nautilus_trader_engine/monitoring/distributed_tracing.py` for the complete example in the `example_usage()` function, which demonstrates:

- Function decorators for automatic tracing
- Nested operations with context managers
- Performance analysis and bottleneck detection
- Trace debugging and analysis
- Integration with async workflows