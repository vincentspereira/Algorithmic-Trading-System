# Performance Benchmarks

This directory contains performance benchmarks and baseline metrics for the Nautilus Trader Engine.

## Overview

Performance benchmarks establish measurable performance standards and help detect performance regressions during development. The benchmarking system provides:

- **Automated Benchmark Execution**: Run standardized performance tests
- **Baseline Management**: Establish and maintain performance baselines
- **Regression Detection**: Automatically detect performance degradation
- **Historical Tracking**: Monitor performance trends over time
- **CI/CD Integration**: Fail builds on performance regressions

## Benchmark Categories

### Core Benchmarks
- **Dependency Injection**: Service registration and resolution performance
- **Event System**: Event publishing and handling throughput
- **Configuration Management**: Settings loading and validation

### Analysis Benchmarks
- **Adaptive Parameters**: Parameter adaptation and market condition processing
- **Ensemble Methods**: Signal combination and weighting algorithms
- **Technical Indicators**: Indicator calculation performance

### Trading Benchmarks
- **Order Processing**: Order validation and routing performance
- **Risk Management**: Position sizing and risk calculation
- **Portfolio Optimization**: Optimization algorithm performance

### Infrastructure Benchmarks
- **Database Operations**: Query performance and connection pooling
- **Caching**: Cache hit rates and retrieval times
- **Streaming**: Real-time data processing throughput

## Running Benchmarks

### Quick Start

```bash
# Run all benchmarks
python scripts/run_benchmarks.py

# Run specific category
python scripts/run_benchmarks.py --category core

# Run specific benchmark
python scripts/run_benchmarks.py --benchmark dependency_injection

# Establish new baseline
python scripts/run_benchmarks.py --baseline

# Compare with baseline
python scripts/run_benchmarks.py --compare

# Generate detailed report
python scripts/run_benchmarks.py --report --export-json
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Run Performance Benchmarks
  run: python scripts/run_benchmarks.py --compare --ci

- name: Update Baseline (on main branch)
  if: github.ref == 'refs/heads/main'
  run: python scripts/run_benchmarks.py --baseline
```

## Baseline Management

### Establishing Baselines

Baselines should be established when:

- Major architectural changes are made
- New features significantly impact performance
- Performance optimizations are implemented
- After major version releases

```bash
# Establish new baseline
python scripts/run_benchmarks.py --baseline --iterations 1000
```

### Baseline Files

- `baseline.json`: Current performance baseline
- `results/`: Historical benchmark results
- `reports/`: Generated performance reports

## Performance Metrics

### Timing Metrics
- **Mean Execution Time**: Average time per operation
- **95th/99th Percentile**: Worst-case performance
- **Standard Deviation**: Performance consistency

### Resource Metrics
- **Memory Usage**: Peak and average memory consumption
- **CPU Usage**: Processor utilization during benchmarks
- **I/O Operations**: Disk and network I/O performance

### Throughput Metrics
- **Operations/Second**: Transaction processing rate
- **Requests/Second**: API and service throughput
- **Messages/Second**: Event and streaming throughput

## Regression Detection

### Thresholds

Performance regressions are detected when:

- Execution time increases by >10% from baseline
- Memory usage increases by >20% from baseline
- Throughput decreases by >5% from baseline

### Handling Regressions

1. **Verify Regression**: Run benchmarks multiple times to confirm
2. **Identify Cause**: Use profiling tools to find performance bottlenecks
3. **Optimize Code**: Implement performance improvements
4. **Update Baseline**: Establish new baseline after fixes

## Benchmark Development

### Creating New Benchmarks

1. **Extend PerformanceBenchmark**: Create a subclass with specific test logic
2. **Implement setup/teardown**: Initialize and clean up test environment
3. **Define measurements**: Specify what to measure (time, memory, throughput)
4. **Register benchmark**: Add to BenchmarkRunner registry

```python
class MyBenchmark(PerformanceBenchmark):
    def __init__(self):
        super().__init__("my_benchmark", "category", "Description")

    def setup(self):
        # Initialize test environment
        pass

    def run(self, iterations=100):
        result = BenchmarkResult(self.name, self.category, iterations)

        for i in range(iterations):
            start_time = time.time()
            # Run test operation
            operation()
            execution_time = time.time() - start_time

            result.add_measurement(execution_time)

        return result
```

### Benchmark Best Practices

- **Warm-up runs**: Include warm-up iterations before measurement
- **Statistical significance**: Run enough iterations for reliable results
- **Isolated testing**: Minimize external dependencies and interference
- **Realistic data**: Use production-like data and scenarios
- **Resource monitoring**: Track memory, CPU, and I/O usage

## Performance Monitoring

### Continuous Monitoring

- **Daily Benchmarks**: Run benchmarks on main branch daily
- **PR Validation**: Run benchmarks on pull requests
- **Release Validation**: Full benchmark suite before releases

### Alerting

Set up alerts for:
- Performance regressions >5%
- Memory leaks >10%
- Throughput degradation >3%

### Trending

Monitor performance trends:
- Weekly performance reports
- Monthly trend analysis
- Quarterly optimization reviews

## Troubleshooting

### Common Issues

**Inconsistent Results**
- Ensure isolated test environment
- Check for background processes
- Use statistical analysis for significance

**Memory Issues**
- Monitor garbage collection
- Check for memory leaks
- Use memory profiling tools

**High Variance**
- Increase iteration count
- Stabilize test environment
- Remove external dependencies

### Debugging Tools

- **cProfile**: Python code profiler
- **memory_profiler**: Memory usage analysis
- **line_profiler**: Line-by-line performance analysis
- **py-spy**: Sampling profiler

## Contributing

When adding benchmarks:

1. **Follow naming conventions**: Use descriptive, consistent names
2. **Document benchmarks**: Include clear descriptions and purposes
3. **Set realistic targets**: Base thresholds on actual performance needs
4. **Test thoroughly**: Validate benchmarks work across environments
5. **Update documentation**: Add new benchmarks to this README

## Performance Standards

### Response Time Targets
- API calls: <100ms (95th percentile)
- Indicator calculations: <10ms
- Order processing: <50ms
- Report generation: <5 seconds

### Throughput Targets
- Event processing: >1000 events/second
- Signal validation: >500 signals/second
- Order routing: >100 orders/second
- Data ingestion: >1000 records/second

### Resource Targets
- Memory usage: <500MB per process
- CPU usage: <70% sustained load
- Disk I/O: <10MB/s sustained
- Network I/O: <50MB/s sustained

## References

- [Python Performance Benchmarking](https://docs.python.org/3/library/timeit.html)
- [Performance Testing Best Practices](https://martinfowler.com/articles/practical-test-pyramid.html)
- [Continuous Performance Testing](https://www.thoughtworks.com/insights/blog/how-continuous-performance-testing-helps)