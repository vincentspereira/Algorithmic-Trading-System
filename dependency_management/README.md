# Dependency Management System

## Overview

The Dependency Management System is a comprehensive framework for managing over 60 best-of-breed open-source components used in the Algorithmic Trading System. It provides automated monitoring, update management, security scanning, and integration testing for all external dependencies.

## Quick Start

### Prerequisites
- Python 3.12+
- Docker and Docker Compose
- GitHub Personal Access Token
- Teams/Discord webhooks (optional)

### Setup
```bash
# Clone the repository
git clone <repository-url>
cd algorithmic-trading-system

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Start the dependency monitoring service
cd services/dependency_management_service
docker-compose up -d
```

### Basic Usage
```bash
# Check all dependencies
python monitoring/check_dependencies.py

# Generate weekly report
python scripts/weekly_report_generator.py

# Run system tests
python test_dependency_system.py
```

## System Architecture

### Tier Classification
- **Tier 1**: Critical dependencies (daily monitoring)
- **Tier 2**: Important dependencies (daily monitoring)  
- **Tier 3**: Supporting dependencies (weekly monitoring)
- **Tier 4**: Infrastructure dependencies (weekly monitoring)

### Components
- **Repository Manager**: Automated forking and management
- **Dependency Monitor**: Version and security monitoring
- **Notification Service**: Multi-channel alerts
- **Health Dashboard**: Real-time status visualization
- **Integration Testing**: Automated validation

## Configuration

### Tier Files
- `tiers/tier1_critical.json` - Core trading components
- `tiers/tier2_important.json` - Portfolio and ML components
- `tiers/tier3_supporting.json` - UI and frontend components
- `tiers/tier4_infrastructure.json` - Databases and monitoring

### Monitoring Schedule
- **Tier 1 & 2**: Daily at 06:00 UTC
- **Tier 3 & 4**: Weekly on Monday at 06:00 UTC
- **Security Scans**: Continuous
- **Health Checks**: Every 15 minutes

### Notifications
- **Critical Alerts**: Teams, Discord, GitHub Issues
- **Standard Updates**: Teams, weekly reports
- **Security Issues**: Immediate multi-channel alerts

## Security

### Vulnerability Management
- Continuous security scanning with Bandit
- CVE monitoring and risk assessment
- Automated patch management for non-breaking fixes
- Incident response procedures

### Access Control
- Private repository forks with restricted access
- Token-based authentication for all integrations
- Complete audit trails for compliance

## Testing

### Automated Testing
```bash
# Run unit tests
pytest tests/

# Run integration tests
docker-compose -f testing/docker-compose.test.yml up

# Validate configuration
python scripts/validate_config.py
```

### Manual Testing
```bash
# Test specific tier
python monitoring/check_dependencies.py --tier tier1

# Test notification system
python notification_service/test_notifications.py

# Test dashboard
docker-compose up dashboard
# Open http://localhost:8080
```

## Monitoring Dashboard

Access the health dashboard at:
- **Main Dashboard**: http://localhost:8080/dashboard
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090

## Troubleshooting

### Common Issues
1. **GitHub API rate limits**: Check token permissions
2. **Notification failures**: Verify webhook URLs
3. **Docker issues**: Ensure sufficient resources
4. **Test failures**: Check network connectivity

### Log Locations
- **Service logs**: `docker-compose logs dependency-monitor`
- **Test results**: `./test-results/`
- **Reports**: `./reports/`

## Support

- Create GitHub issue with 'dependency-management' label
- Check monitoring dashboard for system status
- Review documentation in `/docs/DEPENDENCY_MANAGEMENT.md`

## License

Part of the Algorithmic Trading System project.