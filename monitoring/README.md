# Production Monitoring and Observability Infrastructure

## Overview

This comprehensive monitoring infrastructure provides enterprise-grade monitoring, metrics collection, alerting, and observability for the trading system. It includes real-time dashboards, predictive analytics, and advanced alerting capabilities.

## Architecture

The monitoring system consists of several key components:

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