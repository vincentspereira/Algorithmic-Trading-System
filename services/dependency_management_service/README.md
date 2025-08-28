# Dependency Management System

## Overview

The Dependency Management System is a comprehensive framework for managing over 60 best-of-breed open-source components used in the Algorithmic Trading System. It provides automated monitoring, update management, security scanning, and integration testing for all external dependencies.

## Architecture

The system is organized into four tiers based on criticality:

- **Tier 1 (Critical)**: Core trading, AI, and API components
- **Tier 2 (Important)**: Portfolio, risk, ML, and quantitative analysis components  
- **Tier 3 (Supporting)**: UI, no-code, and interface components
- **Tier 4 (Infrastructure)**: Databases, monitoring, and deployment tools

## Components

### 1. Repository Manager (`repository_manager.py`)
- Manages forking and branch protection for all 60+ repositories
- Handles customization tracking and conflict detection
- Automated repository setup and configuration

### 2. Dependency Monitor (`monitoring/check_dependencies.py`)
- Daily monitoring for Tier 1 & 2 dependencies
- Weekly monitoring for Tier 3 & 4 dependencies
- Security vulnerability scanning
- Version update detection

### 3. Notification Service (`notification_service/`)
- Multi-channel notifications (Teams, Discord, Email)
- Critical alerts for security issues
- Weekly consolidated reports
- Escalation procedures

### 4. Health Dashboard (`dashboard/`)
- Real-time dependency status visualization
- Grafana integration for metrics
- Interactive health monitoring
- Manual override controls

### 5. Integration Testing (`testing/`)
- Docker-based isolated test environments
- Automated CI/CD integration
- Rollback mechanisms on failures
- Performance benchmarking

## Configuration Files

### Dependencies Configuration (`dependencies.json`)
Master configuration file containing all 60+ dependencies organized by tier:

```json
{
  "version": "1.1.0",
  "tiers": {
    "tier1": {
      "description": "Critical components",
      "dependencies": [...]
    }
  }
}
```

### Tier-Specific Files (`tiers/`)
- `tier1_critical.json` - Trading engine, Kafka, LangChain, etc.
- `tier2_important.json` - Portfolio optimization, technical analysis, ML
- `tier3_supporting.json` - Frontend, UI components, visualization
- `tier4_infrastructure.json` - Databases, monitoring, deployment

### Customization Tracking (`customization_tracking.json`)
Tracks all customizations made to forked repositories:

```json
{
  "customizations": [
    {
      "dependency": "TA-Lib",
      "customizations": [
        {
          "name": "Volume-Weighted Indicators",
          "files": ["indicators/volume_weighted_sma.py"],
          "tracking_tags": ["// @PLACEHOLDER: VW indicator implementation"]
        }
      ]
    }
  ]
}
```

## Monitoring Schedule

| Tier | Frequency | Notification |
|------|-----------|-------------|
| Tier 1 | Daily | Immediate for critical issues |
| Tier 2 | Daily | Standard notifications |
| Tier 3 | Weekly | Batch notifications |
| Tier 4 | Weekly | Summary notifications |

## Security Features

### 1. Vulnerability Scanning
- Automated security scans using Bandit and Safety
- CVE database integration
- Risk assessment and prioritization

### 2. Zero-Trust Architecture
- All dependencies verified and scanned
- Controlled update processes
- Isolated testing environments

### 3. Audit Trail
- Complete change tracking
- Immutable audit logs
- Compliance reporting

## Usage

### Starting the System
```bash
# Start dependency monitoring service
cd services/dependency_management_service
docker-compose up -d

# Run manual dependency check
python monitoring/check_dependencies.py

# Generate weekly report
python scripts/weekly_report_generator.py
```

### Managing Dependencies
```bash
# Add new dependency
python repository_manager.py --add-dependency <repo_url> --tier <tier>

# Update dependency configuration
python scripts/update_dependency.py --name <dep_name> --version <version>

# Check for updates
python monitoring/check_dependencies.py --tier <tier>
```

### Dashboard Access
- **Health Dashboard**: http://localhost:8080/dashboard
- **Grafana Metrics**: http://localhost:3000
- **Prometheus**: http://localhost:9090

## Integration with CI/CD

The system integrates with GitHub Actions for:

### 1. Automated Monitoring (`.github/workflows/dependency-monitoring.yml`)
- Daily scans for critical dependencies
- Security vulnerability detection
- Automated issue creation

### 2. Integration Testing (`.github/workflows/dependency-integration-testing.yml`)
- Docker-based testing environments
- Compatibility validation
- Performance benchmarking

### 3. Placeholder Scanning (`.github/workflows/placeholder-scanning.yml`)
- Automated detection of @PLACEHOLDER tags
- GitHub issue creation for technical debt
- Build gates for quality control

## Customizations

### Volume-Weighted Indicators
Custom technical indicators added to TA-Lib:
- Volume-Weighted SMA/EMA
- Volume-Weighted MACD/MFI
- Normalized ATR
- Choppy Market Index

### Event-Driven Enhancements
Kafka customizations for:
- Hierarchical topic naming
- Schema evolution support
- Event sourcing patterns

### AI Integration
LangChain/LangGraph customizations for:
- Trading-specific tools
- Model Context Protocols (MCPs)
- RAG pipeline integration

## Troubleshooting

### Common Issues
1. **Fork creation failures**: Check GitHub token permissions
2. **Monitoring timeouts**: Verify network connectivity to PyPI/npm
3. **Dashboard not loading**: Check Docker service status
4. **Notification failures**: Verify webhook URLs in environment

### Error Recovery
```bash
# Reset dependency state
python scripts/reset_dependency_state.py

# Force update check
python monitoring/check_dependencies.py --force

# Restart monitoring service
docker-compose restart dependency-monitor
```

## Development

### Adding New Dependencies
1. Update `dependencies.json` with new entry
2. Add to appropriate tier file
3. Configure monitoring rules
4. Update integration tests
5. Document customizations if any

### Testing
```bash
# Run unit tests
pytest tests/

# Run integration tests
python test_dependency_system.py

# Validate configuration
python scripts/validate_config.py
```

## Security Considerations

- All forks are private repositories with controlled access
- Automated security scanning on all dependencies
- Regular vulnerability assessments
- Incident response procedures for critical issues

## Compliance

The system maintains compliance with:
- SOX requirements for financial systems
- GDPR for data protection
- PCI DSS for payment processing
- Industry best practices for security

## Support

For issues or questions:
- Create GitHub issue with 'dependency-management' label
- Contact the DevOps team via Teams
- Check the monitoring dashboard for system status

## License

This dependency management system is part of the Algorithmic Trading System and follows the same licensing terms.