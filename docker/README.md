# Docker Containerization for Nautilus Trader Engine

This directory contains the complete Docker containerization setup for the Nautilus Trader Engine, providing production-ready containerized deployment with development, testing, and monitoring capabilities.

## Overview

The Docker setup includes:

- **Multi-stage Dockerfile** with optimized production builds
- **Docker Compose** orchestration for complete stack deployment
- **Development environment** with hot reloading
- **GPU support** for machine learning workloads
- **Monitoring stack** with Prometheus, Grafana, and ELK
- **Database integration** with PostgreSQL and Redis
- **Security hardening** with non-root users and minimal images

## Quick Start

### Prerequisites

```bash
# Install Docker and Docker Compose
# Linux/macOS
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Windows (using Chocolatey)
choco install docker-desktop

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.18.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Basic Deployment

```bash
# Clone the repository
git clone https://github.com/your-org/nautilus-trader-engine.git
cd nautilus-trader-engine

# Start the complete stack
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f nautilus-trader-engine
```

### Development Environment

```bash
# Start development environment with hot reloading
docker-compose --profile dev up -d

# Run tests in container
docker-compose exec nautilus-dev python -m pytest

# Access development API
curl http://localhost:8002/docs
```

## Architecture

### Container Stages

The Dockerfile uses multi-stage builds for optimization:

1. **base**: Common dependencies and system packages
2. **development**: Full development environment with all tools
3. **testing**: Runs automated tests and quality checks
4. **builder**: Builds Python dependencies for production
5. **production**: Minimal runtime image for production deployment
6. **gpu**: GPU-enabled image for ML workloads
7. **debug**: Troubleshooting image with debugging tools
8. **minimal**: Ultra-lightweight image for specific use cases

### Service Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │     API Gateway │
│     (nginx)     │    │   (traefik)     │
└─────────────────┘    └─────────────────┘
          │                       │
          └───────────────────────┘
                  │
        ┌─────────────────┐
        │ Nautilus Engine │
        │   (main app)    │
        └─────────────────┘
          │         │
          │         │
┌─────────────────┐   ┌─────────────────┐
│     Redis       │   │   PostgreSQL    │
│     (cache)     │   │   (database)    │
└─────────────────┘   └─────────────────┘
          │
          │
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   Prometheus    │   │     Grafana     │   │   Node Exporter │
│  (metrics)      │   │   (dashboards)  │   │   (system)      │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

## Configuration

### Environment Variables

Create a `.env` file for configuration:

```bash
# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
MAX_WORKERS=4
CACHE_SIZE_MB=512

# Database
POSTGRES_URL=postgresql://nautilus:password@postgres:5432/nautilus_trader
REDIS_URL=redis://redis:6379/0

# External APIs
ALPHA_VANTAGE_API_KEY=your_key_here
FINNHUB_API_KEY=your_key_here

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here

# GPU (optional)
GPU_ENABLED=0
CUDA_VISIBLE_DEVICES=0
```

### Docker Compose Profiles

Use profiles to run different service combinations:

```bash
# Production stack
docker-compose up -d

# Development with monitoring
docker-compose --profile dev --profile monitoring up -d

# GPU-enabled deployment
docker-compose --profile gpu up -d

# Full observability stack
docker-compose --profile monitoring --profile logging up -d
```

## Usage Examples

### Basic Trading Operations

```bash
# Start the engine
docker-compose up -d nautilus-trader-engine

# Check health
curl http://localhost:8000/health

# Get system status
curl http://localhost:8000/api/v1/status

# Run a backtest
curl -X POST http://localhost:8000/api/v1/backtest \
  -H "Content-Type: application/json" \
  -d @backtest_config.json
```

### Development Workflow

```bash
# Start development environment
docker-compose --profile dev up -d

# Run tests
docker-compose exec nautilus-dev python -m pytest tests/unit/

# Run linting
docker-compose exec nautilus-dev flake8 nautilus_trader_engine/

# Generate documentation
docker-compose exec nautilus-dev python scripts/generate_docs.py
```

### Database Operations

```bash
# Access PostgreSQL
docker-compose exec postgres psql -U nautilus -d nautilus_trader

# Access Redis CLI
docker-compose exec redis redis-cli

# Backup database
docker-compose exec postgres pg_dump -U nautilus nautilus_trader > backup.sql

# Restore database
docker-compose exec -T postgres psql -U nautilus nautilus_trader < backup.sql
```

### Monitoring

```bash
# Access Grafana dashboards
open http://localhost:3000  # admin/admin

# Access Prometheus metrics
open http://localhost:9090

# Query metrics
curl "http://localhost:9090/api/v1/query?query=up"
```

## Advanced Configuration

### Custom Docker Images

Build custom images for specific requirements:

```dockerfile
# Dockerfile.custom
FROM nautilus-trader-engine:latest

# Add custom dependencies
RUN pip install custom-package==1.0.0

# Add custom configuration
COPY custom-config.yml /app/config/

# Set custom entrypoint
CMD ["python", "-m", "my_custom_entrypoint"]
```

### Kubernetes Deployment

Use the Docker images in Kubernetes:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nautilus-trader
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nautilus-trader
  template:
    metadata:
      labels:
        app: nautilus-trader
    spec:
      containers:
      - name: nautilus
        image: nautilus-trader-engine:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
```

### GPU Support

For GPU workloads:

```bash
# Ensure NVIDIA Docker is installed
# https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

# Run GPU-enabled container
docker run --gpus all -p 8000:8000 nautilus-trader-engine:gpu

# Or with docker-compose
docker-compose --profile gpu up -d
```

## Security

### Container Security

- **Non-root user**: All containers run as non-root user
- **Minimal base images**: Use slim/alpine images where possible
- **No privileged containers**: No privileged mode or host mounts
- **Read-only filesystems**: Use read-only root filesystems where possible

### Network Security

- **Internal networks**: Services communicate on private networks
- **No exposed ports**: Only necessary ports are exposed
- **Environment variables**: Sensitive data passed via environment variables
- **Secrets management**: Use Docker secrets or external secret managers

### Image Security

```bash
# Scan images for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image nautilus-trader-engine:latest

# Sign images
docker trust sign nautilus-trader-engine:latest

# Use trusted base images
FROM python:3.11-slim@sha256:...
```

## Performance Optimization

### Image Optimization

```dockerfile
# Use multi-stage builds
FROM python:3.11-slim as builder
# Build dependencies
FROM python:3.11-slim as production
# Copy only necessary files

# Use .dockerignore
# Exclude unnecessary files

# Optimize layer caching
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

### Runtime Optimization

```bash
# Set appropriate resource limits
docker run --memory=2g --cpus=2 nautilus-trader-engine:latest

# Use health checks
docker run --health-cmd="curl -f http://localhost:8000/health" \
  --health-interval=30s nautilus-trader-engine:latest

# Optimize for specific workloads
docker run --read-only --tmpfs /tmp nautilus-trader-engine:latest
```

## Troubleshooting

### Common Issues

**Container won't start**
```bash
# Check logs
docker-compose logs nautilus-trader-engine

# Check resource usage
docker stats

# Verify configuration
docker-compose config
```

**Database connection issues**
```bash
# Check database logs
docker-compose logs postgres

# Test connection
docker-compose exec nautilus-trader-engine python -c "
import psycopg2
conn = psycopg2.connect('postgresql://nautilus:password@postgres:5432/nautilus_trader')
print('Database connection successful')
"
```

**Memory issues**
```bash
# Monitor memory usage
docker stats

# Adjust memory limits
docker-compose up -d --scale nautilus-trader-engine=1
```

**GPU issues**
```bash
# Check GPU availability
docker run --rm --gpus all nvidia/cuda:11.8-base nvidia-smi

# Verify GPU support in container
docker run --rm --gpus all nautilus-trader-engine:gpu python -c "
import torch
print('CUDA available:', torch.cuda.is_available())
"
```

### Debugging

```bash
# Access container shell
docker-compose exec nautilus-trader-engine bash

# Run debug container
docker run -it --entrypoint bash nautilus-trader-engine:debug

# View container logs
docker logs nautilus-trader-engine

# Follow logs in real-time
docker logs -f nautilus-trader-engine
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Docker CI/CD

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Build Docker image
      run: docker build -t nautilus-trader-engine:test .
    - name: Run tests
      run: docker run nautilus-trader-engine:test python -m pytest

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - uses: actions/checkout@v3
    - name: Build and push Docker image
      run: |
        docker build -t nautilus-trader-engine:latest .
        docker tag nautilus-trader-engine:latest ghcr.io/${{ github.repository }}/nautilus-trader-engine:latest
        docker push ghcr.io/${{ github.repository }}/nautilus-trader-engine:latest
```

## Contributing

When contributing to the Docker setup:

1. **Test changes locally** before committing
2. **Update documentation** for any configuration changes
3. **Follow security best practices** for container images
4. **Optimize for performance** and minimal image sizes
5. **Add health checks** for new services
6. **Update CI/CD pipelines** for deployment changes

## Support

For Docker-related issues:

- Check the [Docker Documentation](https://docs.docker.com/)
- Review [Docker Compose Documentation](https://docs.docker.com/compose/)
- Create an issue in the main repository
- Check existing issues for similar problems

## License

This Docker setup is part of the Nautilus Trader Engine project and follows the same license terms.