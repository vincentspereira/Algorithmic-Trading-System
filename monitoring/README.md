# Trading System Monitoring Infrastructure

This directory contains the complete monitoring and observability stack for the algorithmic trading system. The monitoring infrastructure provides comprehensive visibility into system health, performance, and business metrics across all components.

## 🏗️ Architecture Overview

The monitoring stack follows a modern observability architecture with:

- **Metrics Collection**: Prometheus with multiple exporters
- **Visualization**: Grafana with pre-built dashboards
- **Alerting**: Alertmanager with multi-channel notifications
- **Distributed Tracing**: Jaeger for request tracing
- **Log Aggregation**: ELK stack (Elasticsearch, Logstash, Kibana)
- **Health Monitoring**: Custom health checkers and blackbox probing

## 📁 Directory Structure

```
monitoring/
├── docker-compose.yml              # Main monitoring stack orchestration
├── prometheus.yml                   # Prometheus configuration
├── alert_rules.yml                 # Prometheus alerting rules
├── recording_rules.yml             # Prometheus recording rules
├── alertmanager.yml                # Alertmanager configuration
├── blackbox.yml                    # Blackbox exporter configuration
├── postgres-queries.yaml           # PostgreSQL custom queries
├── grafana.ini                     # Grafana server configuration
├── grafana-datasources.yml         # Grafana datasource provisioning
├── grafana-dashboard-provisioning.yml # Dashboard provisioning config
├── grafana_dashboards.json         # Pre-built dashboard definitions
└── README.md                       # This documentation
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- At least 8GB RAM available for monitoring stack
- Ports 3001, 9090, 9093, 9115, 16686 available

### 1. Environment Setup

```bash
# Copy environment template
cp ../database/.env.example .env

# Edit environment variables
nano .env
```

### 2. Start Monitoring Stack

```bash
# Start all monitoring services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f prometheus grafana alertmanager
```

### 3. Access Interfaces

- **Grafana**: http://localhost:3001 (admin/trading_system_2024)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093
- **Jaeger**: http://localhost:16686

## 📊 Monitoring Components

### Core Services

#### Prometheus (Port 9090)
- **Purpose**: Metrics collection and storage
- **Retention**: 15 days
- **Scrape Interval**: 15 seconds
- **Storage**: Local with optional remote write

#### Grafana (Port 3001)
- **Purpose**: Visualization and dashboards
- **Authentication**: Admin user with configurable password
- **Datasources**: Auto-provisioned (Prometheus, PostgreSQL, etc.)
- **Dashboards**: Auto-loaded from JSON definitions

#### Alertmanager (Port 9093)
- **Purpose**: Alert routing and notification
- **Channels**: Email, Slack, PagerDuty, Webhook
- **Grouping**: By service and severity
- **Inhibition**: Prevents alert spam

### Exporters and Collectors

#### Node Exporter
- **Metrics**: System-level metrics (CPU, memory, disk, network)
- **Deployment**: On each monitored host
- **Port**: 9100

#### cAdvisor
- **Metrics**: Container resource usage and performance
- **Scope**: All Docker containers
- **Port**: 8080

#### Database Exporters
- **PostgreSQL Exporter**: Database performance and health
- **Redis Exporter**: Cache performance and memory usage
- **Custom Queries**: Business-specific metrics

#### Blackbox Exporter
- **Purpose**: External service monitoring
- **Protocols**: HTTP, HTTPS, TCP, ICMP
- **Endpoints**: Trading APIs, databases, external services

## 📈 Dashboard Categories

### 1. Database Health Overview
- Connection status for all 9 databases
- Query performance and latency
- Resource utilization (CPU, memory, connections)
- Error rates and availability

### 2. Trading Performance
- Order processing metrics
- Execution latency and slippage
- Portfolio performance and P&L
- Strategy performance comparison

### 3. System Resources
- Host-level metrics (CPU, memory, disk, network)
- Container resource usage
- Service availability and health
- Capacity planning metrics

### 4. Kafka Monitoring
- Message throughput and latency
- Consumer lag and partition health
- Broker performance and availability
- Topic-level metrics

### 5. Application Performance
- Request rates and response times
- Error rates and success ratios
- Business transaction metrics
- User experience metrics

### 6. Security and Compliance
- Authentication and authorization events
- Audit trail metrics
- Compliance monitoring
- Security incident detection

## Legacy Components (Preserved)

### Core Components

1. **Monitoring Infrastructure** (`monitoring_infrastructure.py`)
   - Metrics collection using Prometheus client
   - System performance monitoring
   - Health checks and status reporting
   - Alert management

2. **Advanced Alerting & Analytics** (`advanced_alerting_analytics.py`)
   - Anomaly detection using statistical models
   - Predictive analytics for trend analysis
   - Alert correlation engine
   - Performance analysis and recommendations

3. **Monitoring Server** (`monitoring_server.py`)
   - HTTP API for monitoring data
   - Real-time WebSocket updates
   - Web-based dashboards
   - Integration with external monitoring tools

### External Services

1. **Prometheus** - Time series database and metrics collection
2. **Grafana** - Visualization and dashboards
3. **Redis** - Caching and temporary data storage

## Features

### Metrics Collection
- System metrics (CPU, memory, disk, network)
- Application metrics (HTTP requests, trading orders, security events)
- Custom business metrics
- Real-time metric updates

### Health Monitoring
- Component health checks
- System resource monitoring
- Automated health status reporting
- Configurable health thresholds

### Alerting
- Multi-level alert severity (INFO, WARNING, ERROR, CRITICAL)
- Alert correlation and grouping
- Anomaly detection alerts
- Predictive alerts based on trends

### Analytics
- Performance trend analysis
- Anomaly detection using statistical models
- Predictive analytics for capacity planning
- Alert correlation and root cause analysis

### Dashboards
- Real-time system overview
- Interactive web dashboards
- Grafana integration for advanced visualization
- Mobile-responsive design

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- 8GB+ RAM recommended

### Starting the Monitoring Stack

1. **Build and start all services:**
   ```bash
   cd monitoring
   docker-compose up -d
   ```

2. **Verify services are running:**
   ```bash
   docker-compose ps
   ```

3. **Check health status:**
   ```bash
   curl http://localhost:8090/health
   ```

### Accessing Services

- **Monitoring Dashboard**: http://localhost:8090
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Metrics Endpoint**: http://localhost:8090/metrics

## API Endpoints

### Health and Status
- `GET /health` - System health check
- `GET /status` - Detailed system status
- `GET /metrics` - Prometheus metrics

### Monitoring API
- `GET /api/v1/alerts` - Get all alerts
- `POST /api/v1/alerts/{id}/resolve` - Resolve an alert
- `GET /api/v1/health-checks` - Get health check results
- `GET /api/v1/system-metrics` - Get current system metrics

### WebSocket
- `WS /ws` - Real-time monitoring updates

## Configuration

### Environment Variables
- `MONITORING_MODE` - Set to 'production' for production mode
- `LOG_LEVEL` - Logging level (INFO, DEBUG, WARNING, ERROR)
- `METRICS_RETENTION_DAYS` - How long to retain metrics (default: 30)

### Prometheus Configuration
Edit `config/prometheus.yml` to add new scrape targets:

```yaml
scrape_configs:
  - job_name: 'your-service'
    static_configs:
      - targets: ['your-service:port']
```

### Grafana Dashboards
- Pre-configured dashboards are in `config/grafana/dashboards/`
- Access Grafana at http://localhost:3000 to create custom dashboards

## Monitoring Metrics

### System Metrics
- `trading_system_system_cpu_percent` - CPU usage percentage
- `trading_system_system_memory_percent` - Memory usage percentage
- `trading_system_system_disk_percent` - Disk usage percentage

### Application Metrics
- `trading_system_http_requests_total` - Total HTTP requests
- `trading_system_http_request_duration_seconds` - HTTP request duration
- `trading_system_trading_orders_total` - Total trading orders
- `trading_system_security_events_total` - Security events

### Custom Metrics
You can add custom metrics using the MetricsCollector:

```python
from monitoring_infrastructure import MetricsCollector

collector = MetricsCollector()
collector.increment_counter('custom_metric', {'label': 'value'})
collector.set_gauge('custom_gauge', 42.0)
collector.observe_histogram('custom_duration', 0.123)
```

## Alerting Rules

### Default Alert Conditions
- CPU usage > 90% (CRITICAL)
- Memory usage > 90% (CRITICAL)
- Disk usage > 95% (CRITICAL)
- High error rates (WARNING/ERROR)
- Anomalous behavior detected (WARNING)

### Custom Alerts
Add custom alert rules in `config/alert_rules.yml`:

```yaml
groups:
  - name: custom_alerts
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: High request latency detected
```

## Testing

### Basic Functionality Test
```bash
docker-compose exec monitoring-infrastructure python monitoring/test_basic_functionality.py
```

### Comprehensive Test Suite
```bash
docker-compose exec monitoring-infrastructure python monitoring/test_comprehensive_monitoring.py
```

### Load Testing
```bash
# Generate test metrics
curl -X POST http://localhost:8090/api/v1/test/generate-metrics
```

## Troubleshooting

### Common Issues

1. **Container won't start**
   - Check logs: `docker-compose logs monitoring-infrastructure`
   - Verify port availability: `netstat -tulpn | grep 8090`

2. **Metrics not appearing**
   - Check Prometheus targets: http://localhost:9090/targets
   - Verify metrics endpoint: `curl http://localhost:8090/metrics`

3. **Grafana connection issues**
   - Check Grafana logs: `docker-compose logs grafana`
   - Verify datasource configuration in Grafana UI

### Performance Tuning

1. **High Memory Usage**
   - Reduce metrics retention period
   - Increase scrape intervals
   - Limit number of metric labels

2. **High CPU Usage**
   - Reduce monitoring frequency
   - Optimize alert rules
   - Use metric aggregation

## Development

### Adding New Metrics
1. Define metric in `monitoring_infrastructure.py`
2. Add collection logic in appropriate component
3. Update Grafana dashboards if needed
4. Add tests for new metrics

### Adding New Health Checks
1. Implement check function in `HealthChecker`
2. Register the check in `_register_default_checks`
3. Add tests for the new check

### Extending Alerting
1. Add alert logic in `advanced_alerting_analytics.py`
2. Update alert correlation rules
3. Add notification channels if needed

## Security Considerations

- Change default Grafana password in production
- Use HTTPS for external access
- Implement authentication for monitoring APIs
- Regularly update container images
- Monitor access logs

## Backup and Recovery

### Data Backup
```bash
# Backup Prometheus data
docker-compose exec prometheus tar -czf /tmp/prometheus-backup.tar.gz /prometheus

# Backup Grafana dashboards
docker-compose exec grafana tar -czf /tmp/grafana-backup.tar.gz /var/lib/grafana
```

### Recovery
```bash
# Restore from backup
docker-compose down
# Restore data volumes
docker-compose up -d
```

## Scaling

### Horizontal Scaling
- Use Prometheus federation for multiple instances
- Load balance monitoring APIs
- Distribute alert processing

### Vertical Scaling
- Increase container resource limits
- Optimize database queries
- Use metric sampling for high-volume metrics

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review container logs
3. Verify configuration files
4. Test with minimal setup

## License

This monitoring infrastructure is part of the trading system project.