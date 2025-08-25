# Dependency Management System

## Overview
The Dependency Management System is a comprehensive solution for managing, monitoring, and securing dependencies across the Algorithmic Trading System. It provides automated monitoring, security scanning, and notification capabilities for 60+ critical components.

## Architecture
![Architecture Overview](./images/architecture.png)

The system consists of four main services:
1. **API Service** (`api/`) - Core dependency management and version tracking
2. **Dashboard** (`dashboard/`) - Real-time monitoring and management interface
3. **Notification Service** (`notification_service/`) - Multi-channel alerting system
4. **Security Service** (`security_service/`) - Vulnerability scanning and SAST

### Component Details

#### API Service
- REST API for dependency management
- Version tracking and update detection
- Integration with GitHub for repository monitoring
- Automated update pipeline management

#### Dashboard
- React 18/Next.js based interface
- Real-time dependency health monitoring
- Interactive visualization of dependency relationships
- Update approval and rollback management

#### Notification Service
- Multi-channel notifications (Slack, Teams, Email)
- Priority-based alert routing
- Customizable notification templates
- Tier-based notification rules

#### Security Service
- Static Application Security Testing (SAST) with Bandit
- CVE database integration
- Continuous vulnerability monitoring
- Risk scoring and assessment

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Git
- Node.js 18+ (for local development)
- Python 3.12+ (for local development)

### Environment Variables
```bash
# API Service
GITHUB_TOKEN=your_github_token

# Notification Service
SLACK_WEBHOOK_URL=your_slack_webhook
TEAMS_WEBHOOK_URL=your_teams_webhook
EMAIL_SMTP_SERVER=smtp.example.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your_email
EMAIL_PASSWORD=your_password

# Security Service
NVD_API_KEY=your_nvd_api_key
```

### Installation
1. Clone the repository:
```bash
git clone https://github.com/vincentspereira/Algorithmic-Trading-System.git
cd "Algorithmic Trading System/dependency_management"
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start the services:
```bash
docker-compose up -d
```

4. Access the dashboard:
```
http://localhost:3000
```

## Configuration

### Dependency Tiers
Dependencies are organized into four tiers based on criticality:

1. **Tier 1 (Critical)**
   - Core trading engine components (e.g., NautilusTrader)
   - Event bus infrastructure (e.g., Apache Kafka)
   - AI workflow components (e.g., LangGraph)

2. **Tier 2 (Important)**
   - Portfolio optimization (e.g., PyPortfolioOpt)
   - Risk management (e.g., Riskfolio-Lib)
   - Machine learning components (e.g., FinRL)

3. **Tier 3 (Supporting)**
   - UI components (e.g., Blockly)
   - AI interfaces (e.g., Lobe Chat)
   - Visualization tools

4. **Tier 4 (Infrastructure)**
   - Container orchestration (e.g., Kubernetes)
   - Monitoring tools (e.g., Prometheus)
   - Service mesh (e.g., Istio)

### Monitoring Configuration
```json
{
  "monitoring": {
    "tier1": {
      "frequency": "daily",
      "alert_threshold": "immediate"
    },
    "tier2": {
      "frequency": "daily",
      "alert_threshold": "4hours"
    },
    "tier3": {
      "frequency": "weekly",
      "alert_threshold": "24hours"
    },
    "tier4": {
      "frequency": "weekly",
      "alert_threshold": "48hours"
    }
  }
}
```

## Usage

### Managing Dependencies
1. **Adding Dependencies**
   ```json
   {
     "name": "new-dependency",
     "version": "1.0.0",
     "tier": 2,
     "repository": "https://github.com/org/repo"
   }
   ```

2. **Updating Dependencies**
   - Through dashboard UI
   - Via API endpoints
   - Automated updates (configurable per tier)

3. **Security Scanning**
   - Automatic SAST scanning
   - CVE monitoring
   - Custom security rules

### API Endpoints

#### Core API (Port 8000)
- `GET /api/dependencies/health` - Get health status
- `GET /api/dependencies/{name}/details` - Get dependency details
- `POST /api/dependencies/{name}/approve-update` - Approve update

#### Notification API (Port 8001)
- `POST /notify` - Send notification
- `GET /notification-status` - Get notification status

#### Security API (Port 8002)
- `POST /scan` - Trigger security scan
- `GET /vulnerabilities` - Get vulnerability report

## Development

### Local Development Setup
1. Install dependencies:
```bash
# API Service
cd api && pip install -r requirements.txt

# Dashboard
cd dashboard && npm install

# Notification Service
cd notification_service && pip install -r requirements.txt

# Security Service
cd security_service && pip install -r requirements.txt
```

2. Start services in development mode:
```bash
# API Service
uvicorn main:app --reload

# Dashboard
npm run dev

# Notification Service
python -m notification_service

# Security Service
python -m security_service
```

### Testing
```bash
# Run all tests
docker-compose -f docker-compose.test.yml up

# Run specific service tests
docker-compose run api pytest
docker-compose run security pytest
```

## Monitoring and Maintenance

### Health Checks
- All services implement health check endpoints
- Monitored via Docker health checks
- Prometheus metrics available

### Logging
- Centralized logging with ELK stack
- Structured JSON logging
- Log retention policies

### Backup and Recovery
- Automated configuration backups
- State persistence
- Disaster recovery procedures

## Security

### Authentication and Authorization
- API key authentication
- Role-based access control
- JWT token validation

### Secure Communication
- TLS encryption
- Internal service authentication
- Secure credential management

### Vulnerability Management
- Automated security scanning
- CVE database integration
- Risk assessment and scoring

## Troubleshooting

### Common Issues
1. Service Connection Issues
   - Check network connectivity
   - Verify service health status
   - Review Docker logs

2. Update Pipeline Failures
   - Check GitHub API rate limits
   - Verify repository access
   - Review CI/CD logs

3. Notification Issues
   - Verify webhook URLs
   - Check SMTP configuration
   - Review notification logs

### Debug Tools
```bash
# View service logs
docker-compose logs -f [service_name]

# Check service status
docker-compose ps

# Verify network connectivity
docker network inspect dependency_management_default
```

## Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Implement changes
4. Add tests
5. Submit pull request

### Code Style
- Python: Follow PEP 8
- JavaScript: ESLint with Airbnb config
- Documentation: Keep READMEs updated

## License
MIT License - See LICENSE file for details
