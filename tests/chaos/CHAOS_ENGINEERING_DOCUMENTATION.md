# Chaos Engineering Framework Documentation

## Overview

The Chaos Engineering Framework for Nautilus Trader Engine provides comprehensive failure injection testing, resilience validation, and recovery testing capabilities. This framework implements industry-standard chaos engineering practices to ensure system reliability and resilience.

## Architecture

### Core Components

#### 1. Chaos Engineering Framework (`chaos_engineering_framework.py`)
- **FailureInjector**: Injects various types of failures into the system
- **SystemMonitor**: Monitors system metrics during experiments
- **ResilienceValidator**: Validates system resilience based on predefined rules
- **ChaosExperimentRunner**: Orchestrates experiment execution

#### 2. Chaos Automation (`chaos_automation.py`)
- **ChaosAutomation**: Automated experiment scheduling and execution
- **ChaosSchedule**: Scheduled experiment configuration
- **ChaosGameDay**: Comprehensive chaos game day events

#### 3. Docker Infrastructure
- **Containerized Environment**: Isolated testing environment
- **Monitoring Stack**: Prometheus and Grafana for metrics
- **Test Services**: Mock services for chaos experiments

## Features

### Failure Types Supported

1. **Network Latency**: Inject network latency to test system resilience
2. **Network Partition**: Simulate network partitions and connectivity loss
3. **Service Crash**: Simulate service crashes and recovery
4. **Memory Pressure**: Create memory pressure to test resource handling
5. **CPU Spike**: Generate CPU spikes to test performance under load
6. **API Timeout**: Inject API timeouts to test timeout handling

### Experiment Types

#### Individual Experiments
- Network latency resilience testing
- Service crash recovery testing
- Memory pressure handling
- Network partition recovery
- CPU spike performance testing

#### Chaos Game Days
- Comprehensive multi-experiment scenarios
- Team coordination exercises
- Incident response training
- System resilience validation

### Monitoring and Metrics

#### System Metrics
- CPU usage monitoring
- Memory usage tracking
- Network latency measurement
- Response time monitoring
- Error rate tracking
- Throughput measurement

#### Custom Metrics
- Trading-specific metrics
- Business KPI monitoring
- Application performance indicators

### Resilience Validation

#### Default Rules
- CPU usage should remain below 95%
- Memory usage should remain below 90%
- Response time should stay under 5 seconds
- Error rate should remain below 10%

#### Custom Rules
- Configurable validation rules
- Business-specific criteria
- Performance thresholds

## Installation and Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)
- 8GB+ RAM recommended
- Network access for pulling Docker images

### Quick Start

1. **Clone and Navigate**
   ```bash
   cd tests/chaos
   ```

2. **Build Docker Images**
   ```bash
   docker-compose build
   ```

3. **Run Sample Experiment**
   ```bash
   docker-compose run --rm chaos-engineering python chaos_engineering_framework.py
   ```

4. **Run Test Suite**
   ```bash
   docker-compose run --rm chaos-engineering python -m pytest test_chaos_engineering.py -v
   ```

### Full Infrastructure Setup

1. **Start Monitoring Stack**
   ```bash
   docker-compose up -d prometheus grafana
   ```

2. **Start Test Services**
   ```bash
   docker-compose up -d test-api test-database test-redis
   ```

3. **Access Monitoring**
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000 (admin/chaos123)

## Usage Guide

### Running Individual Experiments

#### Network Latency Experiment
```python
from chaos_engineering_framework import ChaosExperimentLibrary, ChaosExperimentRunner
import asyncio

# Create experiment
experiment = ChaosExperimentLibrary.network_latency_experiment()

# Run experiment
runner = ChaosExperimentRunner()
results = await runner.run_experiment(experiment)

# Generate report
report = runner.generate_experiment_report(experiment)
```

#### Service Crash Experiment
```python
experiment = ChaosExperimentLibrary.service_crash_experiment()
results = await runner.run_experiment(experiment)
```

### Automated Scheduling

#### Schedule Daily Experiments
```python
from chaos_automation import ChaosAutomation, ChaosScheduleLibrary

automation = ChaosAutomation()

# Schedule daily resilience check
daily_schedule = ChaosScheduleLibrary.daily_resilience_check()
automation.schedule_experiment(daily_schedule)

# Run scheduler
await automation.run_scheduler()
```

#### Chaos Game Day
```python
# Create game day
game_day = ChaosScheduleLibrary.monthly_game_day()
automation.create_game_day(game_day)

# Execute game day
results = await automation.execute_game_day(game_day.game_day_id)
```

### Custom Experiments

#### Creating Custom Experiments
```python
from chaos_engineering_framework import ChaosExperiment, FailureType

custom_experiment = ChaosExperiment(
    experiment_id="custom_001",
    name="Custom Network Test",
    description="Custom chaos experiment",
    failure_type=FailureType.NETWORK_LATENCY,
    target_component="trading_service",
    duration=120,  # 2 minutes
    intensity=0.7,
    parameters={'latency_ms': 300},
    hypothesis="Trading service handles 300ms latency gracefully",
    success_criteria=[
        "Orders continue to be processed",
        "Response time stays under 2 seconds",
        "No data loss occurs"
    ],
    rollback_strategy="Restore normal latency immediately"
)
```

#### Custom Resilience Rules
```python
from chaos_engineering_framework import ResilienceValidator

validator = ResilienceValidator()

# Add custom rule
def trading_latency_rule(metrics):
    return metrics.custom_metrics.get('trading_latency', 0) < 100

validator.add_validation_rule(
    "trading_latency_limit",
    trading_latency_rule,
    "Trading latency should be under 100ms"
)
```

## Configuration

### Chaos Configuration (`chaos_config.yaml`)

#### Environment Settings
```yaml
environments:
  production:
    enabled: false  # Safety first
    allowed_failure_types:
      - "network_latency"
    max_intensity: 0.3
  
  staging:
    enabled: true
    allowed_failure_types:
      - "network_latency"
      - "service_crash"
      - "memory_pressure"
    max_intensity: 0.8
```

#### Safety Settings
```yaml
safety:
  circuit_breaker_enabled: true
  max_error_rate: 15.0
  max_response_time: 10000
  abort_on_critical_failure: true
```

#### Notification Settings
```yaml
notifications:
  email:
    enabled: true
    recipients:
      - "devops@company.com"
  
  slack:
    enabled: true
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#chaos-engineering"
```

## Docker Commands

### Basic Operations
```bash
# Build images
docker-compose build

# Start infrastructure
docker-compose up -d prometheus grafana

# Run experiment
docker-compose run --rm chaos-engineering python chaos_engineering_framework.py

# Run tests
docker-compose run --rm chaos-engineering python -m pytest test_chaos_engineering.py -v

# Stop all services
docker-compose down
```

### Advanced Operations
```bash
# Run specific test
docker-compose run --rm chaos-engineering python -m pytest test_chaos_engineering.py::TestFailureInjector -v

# Run with coverage
docker-compose run --rm chaos-engineering python -m pytest test_chaos_engineering.py --cov=. --cov-report=html

# Interactive shell
docker-compose run --rm chaos-engineering bash

# View logs
docker-compose logs chaos-engineering
```

## Monitoring and Observability

### Prometheus Metrics

#### Experiment Metrics
- `chaos_experiments_started_total`: Total experiments started
- `chaos_experiments_completed_total`: Total experiments completed
- `chaos_experiment_duration_seconds`: Experiment duration
- `chaos_active_experiments_count`: Active experiments count

#### System Metrics
- `chaos_system_cpu_usage`: CPU usage during experiments
- `chaos_system_memory_usage`: Memory usage during experiments
- `chaos_network_latency_ms`: Network latency measurements
- `chaos_response_time_ms`: Response time measurements

#### Resilience Metrics
- `chaos_resilience_rules_passed_total`: Resilience rules passed
- `chaos_resilience_rules_failed_total`: Resilience rules failed
- `chaos_resilience_score`: Overall resilience score

### Grafana Dashboards

#### Chaos Engineering Overview
- Experiment success rate
- Active experiments
- System health during experiments
- Resilience score trends

#### System Performance
- CPU and memory usage
- Network latency trends
- Response time distribution
- Error rate monitoring

### Alerting Rules

#### Critical Alerts
- System resilience compromised (< 70%)
- High experiment failure rate (> 20%)
- Too many concurrent experiments (> 5)

#### Warning Alerts
- Long experiment duration (> 30 minutes)
- High resource usage during experiments
- Network connectivity issues

## Best Practices

### Experiment Design

#### Start Small
- Begin with low-intensity experiments
- Test in non-production environments first
- Gradually increase complexity

#### Clear Hypotheses
- Define clear, testable hypotheses
- Establish measurable success criteria
- Document expected system behavior

#### Safety First
- Always have rollback strategies
- Monitor system health continuously
- Set appropriate abort conditions

### Scheduling and Automation

#### Regular Testing
- Schedule regular resilience checks
- Automate routine experiments
- Track trends over time

#### Game Days
- Organize monthly chaos game days
- Include cross-functional teams
- Practice incident response procedures

### Monitoring and Analysis

#### Comprehensive Metrics
- Monitor both system and business metrics
- Track long-term trends
- Analyze failure patterns

#### Continuous Improvement
- Learn from each experiment
- Update resilience rules based on findings
- Improve system design based on results

## Troubleshooting

### Common Issues

#### Docker Issues
```bash
# Check Docker status
docker info

# Rebuild images
docker-compose build --no-cache

# Clean up containers
docker-compose down -v
docker system prune -f
```

#### Network Issues
```bash
# Check network connectivity
docker-compose exec chaos-engineering ping test-api

# Check port availability
netstat -an | grep 9090  # Prometheus
netstat -an | grep 3000  # Grafana
```

#### Permission Issues
```bash
# Fix volume permissions
sudo chown -R $USER:$USER ./results ./reports ./game_day_reports
```

### Debugging Experiments

#### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Check Experiment Status
```python
# Check active failures
print(failure_injector.active_failures)

# Check metrics history
print(len(system_monitor.metrics_history))

# Check validation results
print(resilience_validator.validation_results)
```

#### Manual Cleanup
```python
# Cleanup all failures
await failure_injector.cleanup_all_failures()

# Stop monitoring
system_monitor.stop_monitoring()
```

## API Reference

### Core Classes

#### ChaosExperiment
```python
@dataclass
class ChaosExperiment:
    experiment_id: str
    name: str
    description: str
    failure_type: FailureType
    target_component: str
    duration: int
    intensity: float
    parameters: Dict[str, Any]
    hypothesis: str
    success_criteria: List[str]
    rollback_strategy: str
```

#### FailureInjector
```python
class FailureInjector:
    async def inject_network_latency(target: str, latency_ms: int, duration: int)
    async def inject_network_partition(target: str, duration: int)
    async def inject_service_crash(service_name: str, duration: int)
    async def inject_memory_pressure(target_usage: float, duration: int)
    async def inject_cpu_spike(target_usage: float, duration: int)
    async def cleanup_all_failures()
```

#### SystemMonitor
```python
class SystemMonitor:
    async def start_monitoring(interval: float = 1.0)
    def stop_monitoring()
    async def collect_metrics() -> SystemMetrics
    def get_metrics_summary() -> Dict[str, Any]
    def add_custom_metric_collector(name: str, collector: Callable)
```

#### ResilienceValidator
```python
class ResilienceValidator:
    def add_validation_rule(name: str, condition: Callable, description: str)
    async def validate_resilience(metrics_history: List[SystemMetrics]) -> Dict[str, Any]
```

### Utility Functions

#### Experiment Libraries
```python
# Predefined experiments
ChaosExperimentLibrary.network_latency_experiment()
ChaosExperimentLibrary.service_crash_experiment()
ChaosExperimentLibrary.memory_pressure_experiment()
ChaosExperimentLibrary.network_partition_experiment()

# Predefined schedules
ChaosScheduleLibrary.daily_resilience_check()
ChaosScheduleLibrary.weekly_stress_test()
ChaosScheduleLibrary.monthly_game_day()
```

## Contributing

### Development Setup
1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Run test suite
5. Submit pull request

### Testing Guidelines
- Write tests for new failure types
- Include integration tests
- Test with Docker environment
- Validate monitoring metrics

### Documentation
- Update API documentation
- Include usage examples
- Document configuration options
- Update troubleshooting guide

## License and Support

This chaos engineering framework is part of the Nautilus Trader Engine system enhancement project. For support, please refer to the main project documentation or contact the development team.

---

*Last updated: January 2, 2025*
*Version: 1.0.0*