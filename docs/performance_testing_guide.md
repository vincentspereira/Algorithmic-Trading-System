# Performance Testing and Latency Benchmarking Guide

## Overview

This guide provides comprehensive documentation for the Nautilus Trader performance testing and latency benchmarking systems. These tools are designed to measure, analyze, and optimize system performance with microsecond precision for high-frequency trading applications.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Performance Test Suite](#performance-test-suite)
3. [Latency Benchmarking](#latency-benchmarking)
4. [Installation and Setup](#installation-and-setup)
5. [Usage Examples](#usage-examples)
6. [Test Results Analysis](#test-results-analysis)
7. [Performance Optimization](#performance-optimization)
8. [Troubleshooting](#troubleshooting)

## System Architecture

### Components Overview

The performance testing system consists of two main components:

1. **Comprehensive Test Suite** (`comprehensive_test_suite.py`)
   - Load testing scenarios
   - Stress testing capabilities
   - Endurance testing for long-running operations
   - Performance baseline establishment

2. **Latency Benchmarking** (`latency_benchmarking.py`)
   - Microsecond-precision latency measurement
   - Latency distribution analysis
   - Percentile-based reporting
   - Performance optimization recommendations

### Key Features

- **High-Precision Timing**: Nanosecond-level precision using `perf_counter_ns`
- **Comprehensive Metrics**: Response time, throughput, error rates, resource usage
- **Multiple Test Types**: Load, stress, endurance, and component-specific tests
- **Real-time Analysis**: Automated performance analysis and bottleneck detection
- **Visualization**: Automated chart generation for performance metrics
- **Reporting**: Detailed JSON reports with optimization recommendations

## Performance Test Suite

### TestConfiguration Class

```python
@dataclass
class TestConfiguration:
    base_url: str = "http://localhost:8000"
    websocket_url: str = "ws://localhost:8001"
    database_url: str = "postgresql://nautilus:password@localhost:5432/nautilus_trader"
    redis_url: str = "redis://localhost:6379/0"
    
    # Load test configuration
    load_test_users: int = 100
    load_test_spawn_rate: int = 10
    load_test_duration: int = 300  # 5 minutes
    
    # Stress test configuration
    stress_test_users: int = 500
    stress_test_spawn_rate: int = 50
    stress_test_duration: int = 600  # 10 minutes
    
    # Endurance test configuration
    endurance_test_users: int = 50
    endurance_test_duration: int = 3600  # 1 hour
    
    # Performance thresholds
    max_response_time: float = 2.0  # seconds
    max_error_rate: float = 0.01  # 1%
    min_throughput: int = 1000  # requests per second
```

### PerformanceMetrics Class

```python
@dataclass
class PerformanceMetrics:
    timestamp: datetime
    test_type: str
    duration: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    min_response_time: float
    max_response_time: float
    requests_per_second: float
    error_rate: float
    cpu_usage: float
    memory_usage: float
    network_io: Dict[str, float]
    disk_io: Dict[str, float]
```

### Test Types

#### 1. Load Testing

Tests system behavior under expected load conditions:

- **Light Load**: 50 users, 5 minutes
- **Normal Load**: 100 users, 5 minutes  
- **Heavy Load**: 200 users, 5 minutes

```python
load_scenarios = [
    {"users": 50, "duration": 300, "name": "light_load"},
    {"users": 100, "duration": 300, "name": "normal_load"},
    {"users": 200, "duration": 300, "name": "heavy_load"},
]
```

#### 2. Stress Testing

Tests system breaking points and failure modes:

- **Moderate Stress**: 300 users, 5 minutes
- **High Stress**: 500 users, 5 minutes
- **Extreme Stress**: 1000 users, 3 minutes

#### 3. Endurance Testing

Tests system stability over extended periods:

- **Duration**: 1 hour continuous load
- **Users**: 50 concurrent users
- **Monitoring**: Memory leaks, performance degradation

#### 4. Component Testing

Tests individual system components:

- **API Endpoints**: Individual endpoint performance
- **WebSocket**: Connection and message latency
- **Database**: Query performance and connection pooling
- **Cache**: Redis operation latency

### NautilusTraderUser Class

Locust user class simulating realistic trading operations:

```python
class NautilusTraderUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(10)
    def get_portfolio(self):
        """Get portfolio information"""
        self.client.get("/api/portfolio")
    
    @task(8)
    def get_positions(self):
        """Get current positions"""
        self.client.get("/api/positions")
    
    @task(6)
    def get_orders(self):
        """Get order history"""
        self.client.get("/api/orders")
    
    @task(4)
    def place_order(self):
        """Place a test order"""
        order_data = {
            "symbol": "BTCUSD",
            "side": "buy",
            "quantity": 0.001,
            "order_type": "market"
        }
        self.client.post("/api/orders", json=order_data)
```

## Latency Benchmarking

### HighPrecisionTimer Class

Provides nanosecond-precision timing with overhead compensation:

```python
class HighPrecisionTimer:
    def __init__(self):
        self.start_time = None
        self.overhead_ns = self._measure_timer_overhead()
    
    def start(self):
        """Start timing"""
        self.start_time = high_res_timer()
    
    def stop(self) -> int:
        """Stop timing and return elapsed nanoseconds"""
        end_time = high_res_timer()
        elapsed_ns = end_time - self.start_time
        return max(0, elapsed_ns - self.overhead_ns)
```

### LatencyMeasurement Class

```python
@dataclass
class LatencyMeasurement:
    timestamp: float
    operation: str
    latency_ns: int  # nanoseconds
    success: bool
    metadata: Dict[str, Any]
    
    @property
    def latency_us(self) -> float:
        """Latency in microseconds"""
        return self.latency_ns / 1000.0
    
    @property
    def latency_ms(self) -> float:
        """Latency in milliseconds"""
        return self.latency_ns / 1_000_000.0
```

### LatencyStatistics Class

```python
@dataclass
class LatencyStatistics:
    operation: str
    sample_count: int
    mean_ns: float
    median_ns: float
    std_dev_ns: float
    min_ns: int
    max_ns: int
    p50_ns: float
    p90_ns: float
    p95_ns: float
    p99_ns: float
    p99_9_ns: float
    p99_99_ns: float
    success_rate: float
```

### Benchmark Categories

#### 1. API Endpoints

- Health check endpoint
- Portfolio retrieval
- Position queries
- Order management
- Market data requests

#### 2. WebSocket Operations

- Connection establishment
- Message round-trip time
- Subscription latency
- Concurrent connection handling

#### 3. Database Operations

- Simple SELECT queries
- Complex JOIN operations
- INSERT/UPDATE operations
- Transaction processing

#### 4. Cache Operations

- GET operations
- SET operations
- DELETE operations
- Pipeline operations

#### 5. Network Operations

- TCP connection establishment
- DNS resolution
- HTTP request components
- Network I/O performance

#### 6. Trading Operations

- Order validation
- Risk management checks
- Market data processing
- Position calculations
- P&L calculations

## Installation and Setup

### Prerequisites

```bash
# Python dependencies
pip install asyncio aiohttp websockets locust numpy pandas matplotlib seaborn psutil

# System requirements
- Python 3.8+
- 8GB+ RAM for comprehensive testing
- SSD storage for optimal I/O performance
- Multi-core CPU for concurrent testing
```

### Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd nautilus-trader

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export NAUTILUS_API_URL="http://localhost:8000"
export NAUTILUS_WS_URL="ws://localhost:8001"
export NAUTILUS_DB_URL="postgresql://nautilus:password@localhost:5432/nautilus_trader"
export NAUTILUS_REDIS_URL="redis://localhost:6379/0"
```

### Configuration

Create a custom configuration file:

```python
# performance_config.py
from comprehensive_test_suite import TestConfiguration

config = TestConfiguration(
    base_url="http://your-api-server:8000",
    websocket_url="ws://your-ws-server:8001",
    load_test_users=200,
    load_test_duration=600,  # 10 minutes
    max_response_time=1.0,   # 1 second
    max_error_rate=0.005     # 0.5%
)
```

## Usage Examples

### Running Performance Tests

#### Basic Performance Test Suite

```python
import asyncio
from comprehensive_test_suite import PerformanceTestSuite, TestConfiguration

async def run_basic_tests():
    config = TestConfiguration()
    test_suite = PerformanceTestSuite(config)
    
    # Run all performance tests
    results = await test_suite.run_all_tests()
    
    # Save results
    test_suite.save_results(results)
    
    # Generate charts
    test_suite.generate_charts(results)
    
    return results

# Run tests
results = asyncio.run(run_basic_tests())
```

#### Custom Load Test

```python
from comprehensive_test_suite import PerformanceTestSuite, TestConfiguration

# Custom configuration for high-load testing
config = TestConfiguration(
    load_test_users=500,
    load_test_duration=1800,  # 30 minutes
    stress_test_users=1000,
    max_response_time=0.5,    # 500ms
    max_error_rate=0.001      # 0.1%
)

test_suite = PerformanceTestSuite(config)
results = asyncio.run(test_suite.run_all_tests())
```

### Running Latency Benchmarks

#### Basic Latency Benchmark

```python
import asyncio
from latency_benchmarking import LatencyBenchmark

async def run_latency_tests():
    benchmark = LatencyBenchmark()
    
    # Run comprehensive benchmark
    results = await benchmark.run_comprehensive_benchmark()
    
    # Save results
    benchmark.save_results(results)
    
    # Generate charts
    benchmark.generate_latency_charts(results)
    
    return results

# Run benchmarks
results = asyncio.run(run_latency_tests())
```

#### Custom Endpoint Benchmarking

```python
from latency_benchmarking import LatencyBenchmark

benchmark = LatencyBenchmark(
    base_url="http://production-api:8000",
    websocket_url="ws://production-ws:8001"
)

# Run specific benchmark
api_results = asyncio.run(benchmark._benchmark_api_endpoints())
print(f"API latency results: {api_results}")
```

### Command Line Usage

```bash
# Run performance tests
python performance/comprehensive_test_suite.py

# Run latency benchmarks
python performance/latency_benchmarking.py

# Run with custom configuration
python performance/comprehensive_test_suite.py --config custom_config.json

# Run specific test type
python performance/comprehensive_test_suite.py --test-type load

# Generate reports only
python performance/comprehensive_test_suite.py --report-only --input results.json
```

## Test Results Analysis

### Performance Metrics Interpretation

#### Response Time Metrics

- **Mean Response Time**: Average response time across all requests
- **Median Response Time**: 50th percentile response time
- **P95 Response Time**: 95th percentile (95% of requests faster than this)
- **P99 Response Time**: 99th percentile (99% of requests faster than this)

#### Throughput Metrics

- **Requests per Second (RPS)**: System throughput capacity
- **Concurrent Users**: Number of simultaneous users supported
- **Transaction Rate**: Business transactions processed per second

#### Error Metrics

- **Error Rate**: Percentage of failed requests
- **Success Rate**: Percentage of successful requests
- **Failure Types**: Categorization of different error types

#### Resource Utilization

- **CPU Usage**: Processor utilization percentage
- **Memory Usage**: RAM utilization percentage
- **Network I/O**: Network bandwidth utilization
- **Disk I/O**: Storage I/O performance

### Latency Analysis

#### Latency Classifications

```python
def classify_latency(mean_us: float) -> str:
    if mean_us < 100:      # < 100 microseconds
        return "excellent"
    elif mean_us < 1000:   # < 1 millisecond
        return "good"
    elif mean_us < 10000:  # < 10 milliseconds
        return "acceptable"
    else:
        return "poor"
```

#### Percentile Analysis

- **P50 (Median)**: Typical user experience
- **P90**: Experience of 90% of users
- **P95**: Experience of 95% of users
- **P99**: Experience of 99% of users (tail latency)
- **P99.9**: Extreme tail latency

### Performance Degradation Detection

```python
def calculate_performance_degradation(baseline, current):
    return {
        "response_time_increase": (
            (current.average_response_time - baseline.average_response_time) / 
            baseline.average_response_time * 100
        ),
        "throughput_decrease": (
            (baseline.requests_per_second - current.requests_per_second) / 
            baseline.requests_per_second * 100
        ),
        "error_rate_increase": (current.error_rate - baseline.error_rate) * 100
    }
```

### Breaking Point Detection

```python
def detect_breaking_point(metrics):
    return (
        metrics.error_rate > 0.01 or           # > 1% error rate
        metrics.average_response_time > 2.0 or # > 2 seconds response time
        metrics.requests_per_second < 1000     # < 1000 RPS throughput
    )
```

## Performance Optimization

### Optimization Recommendations

#### Infrastructure Optimizations

1. **Connection Pooling**
   ```python
   # Database connection pooling
   pool_size = 20
   max_overflow = 30
   pool_timeout = 30
   ```

2. **Caching Strategy**
   ```python
   # Multi-level caching
   L1_cache = "in-memory"    # Application cache
   L2_cache = "redis"        # Distributed cache
   L3_cache = "database"     # Persistent cache
   ```

3. **Load Balancing**
   ```yaml
   # Nginx load balancing
   upstream nautilus_api {
       least_conn;
       server api1:8000 weight=3;
       server api2:8000 weight=3;
       server api3:8000 weight=2;
   }
   ```

#### Application Optimizations

1. **Async Processing**
   ```python
   # Use async/await for I/O operations
   async def process_order(order):
       async with aiohttp.ClientSession() as session:
           response = await session.post("/api/orders", json=order)
           return await response.json()
   ```

2. **Database Query Optimization**
   ```sql
   -- Add indexes for frequently queried columns
   CREATE INDEX idx_orders_symbol_timestamp ON orders(symbol, timestamp);
   CREATE INDEX idx_positions_user_id ON positions(user_id);
   ```

3. **Memory Management**
   ```python
   # Use object pooling for frequently created objects
   from queue import Queue
   
   class ObjectPool:
       def __init__(self, factory, max_size=100):
           self.factory = factory
           self.pool = Queue(maxsize=max_size)
   ```

### Performance Tuning Guidelines

#### API Server Tuning

```python
# FastAPI/Uvicorn configuration
uvicorn.run(
    app,
    host="0.0.0.0",
    port=8000,
    workers=4,                    # CPU cores
    worker_class="uvicorn.workers.UvicornWorker",
    max_requests=10000,           # Restart worker after N requests
    max_requests_jitter=1000,     # Add randomness to restart
    timeout_keep_alive=5,         # Keep-alive timeout
    limit_concurrency=1000,       # Max concurrent connections
    limit_max_requests=10000      # Max requests in queue
)
```

#### Database Tuning

```sql
-- PostgreSQL configuration
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
```

#### Redis Tuning

```redis
# Redis configuration
maxmemory 512mb
maxmemory-policy allkeys-lru
tcp-keepalive 300
timeout 0
tcp-backlog 511
```

### Monitoring and Alerting

#### Performance Metrics Monitoring

```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active connections')
```

#### Alert Thresholds

```yaml
alerts:
  - name: HighLatency
    condition: p99_latency > 100ms
    severity: warning
    
  - name: HighErrorRate
    condition: error_rate > 1%
    severity: critical
    
  - name: LowThroughput
    condition: rps < 1000
    severity: warning
```

## Troubleshooting

### Common Performance Issues

#### High Latency

**Symptoms:**
- P99 latency > 100ms
- Slow response times
- User complaints

**Diagnosis:**
```python
# Check latency distribution
results = await benchmark.run_comprehensive_benchmark()
api_latencies = results["benchmarks"]["api_endpoints"]

for endpoint, stats in api_latencies.items():
    if stats["p99_ns"] / 1000000 > 100:  # > 100ms
        print(f"High latency detected in {endpoint}: {stats['p99_ns']/1000000:.2f}ms")
```

**Solutions:**
1. Add caching for frequently accessed data
2. Optimize database queries
3. Implement connection pooling
4. Scale horizontally

#### High Error Rate

**Symptoms:**
- Error rate > 1%
- Failed requests
- Timeout errors

**Diagnosis:**
```python
# Analyze error patterns
for test_type, results in performance_results["tests"].items():
    for scenario, metrics in results.items():
        if metrics.get("error_rate", 0) > 0.01:
            print(f"High error rate in {test_type}/{scenario}: {metrics['error_rate']:.2%}")
```

**Solutions:**
1. Increase timeout values
2. Implement retry logic
3. Add circuit breakers
4. Scale resources

#### Low Throughput

**Symptoms:**
- RPS < expected capacity
- Resource underutilization
- Bottlenecks

**Diagnosis:**
```python
# Check throughput bottlenecks
if metrics.requests_per_second < config.min_throughput:
    print(f"Low throughput detected: {metrics.requests_per_second} RPS")
    print(f"CPU usage: {metrics.cpu_usage}%")
    print(f"Memory usage: {metrics.memory_usage}%")
```

**Solutions:**
1. Optimize application code
2. Increase worker processes
3. Tune database connections
4. Optimize network configuration

### Debug Commands

#### System Resource Monitoring

```bash
# Monitor system resources during tests
htop                    # CPU and memory usage
iotop                   # Disk I/O usage
nethogs                 # Network usage by process
ss -tuln               # Network connections
```

#### Database Performance

```sql
-- PostgreSQL performance queries
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;

-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Check lock waits
SELECT * FROM pg_stat_activity WHERE wait_event IS NOT NULL;
```

#### Application Profiling

```python
# Python profiling
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run your code here
    result = run_performance_test()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions
    
    return result
```

### Performance Testing Best Practices

1. **Establish Baselines**
   - Always establish performance baselines before optimization
   - Use consistent test environments
   - Document system configuration

2. **Test Incrementally**
   - Start with light load and gradually increase
   - Test individual components before full system
   - Monitor resource utilization throughout tests

3. **Use Realistic Data**
   - Use production-like data volumes
   - Simulate realistic user behavior
   - Include edge cases and error scenarios

4. **Monitor Continuously**
   - Set up continuous performance monitoring
   - Alert on performance degradation
   - Track performance trends over time

5. **Document Everything**
   - Document test configurations
   - Record optimization changes
   - Maintain performance history

## Conclusion

The Nautilus Trader performance testing and latency benchmarking systems provide comprehensive tools for measuring, analyzing, and optimizing system performance. By following this guide and using the provided tools, you can ensure your trading system meets the demanding performance requirements of high-frequency trading applications.

For additional support or questions, please refer to the project documentation or contact the development team.

---

*Last updated: $(date '+%Y-%m-%d')*
*Version: 1.0.0*