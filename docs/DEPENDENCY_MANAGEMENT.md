# Dependency Management Guide

## Overview

The Algorithmic Trading System uses a **containerized approach** to dependency management, ensuring isolated, reproducible, and consistent environments across all services. Each service manages its own dependencies within Docker containers, eliminating the need for global package installations and preventing version conflicts.

## Core Principles

### 1. **Isolated Dependencies**
- Each service has its own dependency stack
- No shared global packages between services
- Complete isolation prevents version conflicts
- Services can use different versions of the same library

### 2. **Containerized Environment**
- All dependencies run within Docker containers
- Consistent environment across development, testing, and production
- No local installation of programming language packages required
- Easy cleanup and environment reset

### 3. **No Global Installations**
- Python packages are NOT installed globally on the host system
- Node.js packages are NOT installed globally on the host system
- All runtime dependencies are containerized
- Only Docker and Docker Compose are required on the host

## Service-Specific Dependency Management

### Python Services

#### Nautilus Trader Engine
- **Location**: [`nautilus_trader_engine/requirements.txt`](../nautilus_trader_engine/requirements.txt)
- **Type**: Production service (Phase 1)
- **Dependencies**: NautilusTrader, data feeds, database connectors
- **Container**: Python 3.11 slim base image

#### AI Assistant Service
- **Location**: [`ai_assistant/requirements.txt`](../ai_assistant/requirements.txt)
- **Type**: Placeholder service (Future phases)
- **Dependencies**: OpenAI, Anthropic, LangChain, FastAPI, ML libraries
- **Container**: Python 3.11 slim base image

**Python Dependency Structure:**
```
service_name/
├── requirements.txt          # Production dependencies
├── Dockerfile               # Container configuration
├── README.md               # Service documentation
└── [source code files]
```

### Node.js Services

#### Frontend Service
- **Location**: [`frontend/package.json`](../frontend/package.json)
- **Type**: Placeholder service (Future phases)
- **Dependencies**: Next.js, React, TypeScript, Tailwind CSS
- **Container**: Node.js 18 Alpine base image

**Node.js Dependency Structure:**
```
frontend/
├── package.json            # Dependencies and scripts
├── package-lock.json       # Locked dependency versions
├── Dockerfile             # Multi-stage container build
├── README.md              # Service documentation
└── [source code files]
```

## Docker Configuration

### Python Services Configuration

```dockerfile
# Example Python service Dockerfile structure
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Security: Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Health check and startup
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "main.py"]
```

### Node.js Services Configuration

```dockerfile
# Example Node.js service Dockerfile structure (Multi-stage)
FROM node:18-alpine AS base

# Dependencies stage
FROM base AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Build stage
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Production stage
FROM base AS runner
WORKDIR /app
ENV NODE_ENV production
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
USER nextjs

EXPOSE 3000
CMD ["node", "server.js"]
```

## Docker Compose Integration

### Service Definitions

The [`docker-compose.yml`](../docker-compose.yml) file defines all services with their dependency relationships:

```yaml
services:
  # Active Service (Phase 1)
  nautilus_trader_engine:
    build:
      context: ./nautilus_trader_engine
      dockerfile: Dockerfile
    # ... configuration

  # Placeholder Services (Future Phases)
  # ai_assistant:
  #   build:
  #     context: ./ai_assistant
  #     dockerfile: Dockerfile
  #   # ... configuration (commented out)

  # frontend:
  #   build:
  #     context: ./frontend
  #     dockerfile: Dockerfile
  #   # ... configuration (commented out)
```

### Service Dependencies

Services are configured with proper dependency chains:

```yaml
depends_on:
  postgres:
    condition: service_healthy
  kafka:
    condition: service_started
  clickhouse:
    condition: service_healthy
```

## Development Workflow

### 1. **Initial Setup**
```bash
# Clone repository
git clone <repository-url>
cd algorithmic-trading-system

# Start Phase 1 services
docker-compose up -d
```

### 2. **Adding Dependencies**

**For Python Services:**
```bash
# Edit requirements.txt
echo "new-package==1.0.0" >> service_name/requirements.txt

# Rebuild container
docker-compose build service_name
docker-compose up -d service_name
```

**For Node.js Services:**
```bash
# Add dependency to package.json
cd frontend
npm install new-package

# Rebuild container
docker-compose build frontend
docker-compose up -d frontend
```

### 3. **Development Mode**

**Python Services:**
```bash
# Mount source code for live development
docker-compose up -d
# Code changes are reflected immediately via volume mounts
```

**Node.js Services:**
```bash
# Development mode with hot reloading
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up frontend
```

## Dependency Management Best Practices

### 1. **Version Pinning**
- **Python**: Use exact versions in `requirements.txt`
  ```
  fastapi==0.100.0
  uvicorn==0.22.0
  ```
- **Node.js**: Use exact versions in `package.json`
  ```json
  {
    "dependencies": {
      "next": "14.0.0",
      "react": "18.2.0"
    }
  }
  ```

### 2. **Security Updates**
- Regularly update base Docker images
- Monitor security advisories for dependencies
- Use automated dependency scanning tools
- Keep lock files (`package-lock.json`) in version control

### 3. **Development vs Production**
- **Python**: Separate `requirements-dev.txt` for development tools
- **Node.js**: Use `devDependencies` for development-only packages
- Use multi-stage Docker builds for optimized production images

### 4. **Dependency Auditing**
```bash
# Python security audit
docker run --rm -v $(pwd):/app python:3.11-slim \
  sh -c "cd /app && pip install safety && safety check -r requirements.txt"

# Node.js security audit
docker run --rm -v $(pwd):/app node:18-alpine \
  sh -c "cd /app && npm audit"
```

## Service Status and Implementation

### Phase 1 (Current)
- ✅ **Nautilus Trader Engine**: Fully implemented with dependencies
- ✅ **Infrastructure**: PostgreSQL, Kafka, ClickHouse, monitoring stack

### Future Phases (Placeholders)
- 🔄 **AI Assistant Service**: Placeholder files created, ready for implementation
- 🔄 **Frontend Service**: Placeholder files created, ready for implementation
- 🔄 **Additional Services**: Can be added following the same pattern

## Troubleshooting

### Common Issues

**1. Container Build Failures**
```bash
# Clear Docker cache and rebuild
docker system prune -f
docker-compose build --no-cache service_name
```

**2. Dependency Conflicts**
```bash
# Check container logs
docker-compose logs service_name

# Interactive debugging
docker-compose exec service_name bash
```

**3. Port Conflicts**
```bash
# Check port usage
docker-compose ps
netstat -tulpn | grep :PORT_NUMBER
```

### Health Checks

All services include health checks for monitoring:
```bash
# Check service health
docker-compose ps
docker inspect container_name | grep -A 10 Health
```

## Migration from Global Dependencies

If you previously had global Python or Node.js packages installed:

### Python Cleanup
```bash
# List global packages
pip list --user

# Remove global packages (optional)
pip freeze --user | xargs pip uninstall -y
```

### Node.js Cleanup
```bash
# List global packages
npm list -g --depth=0

# Remove global packages (optional)
npm uninstall -g package_name
```

**Note**: Global cleanup is optional since containerized services don't use global packages.

## Environment Variables

### Service Configuration
Each service uses environment variables for configuration:

```bash
# .env file (not committed to version control)
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
OPENAI_API_KEY=${OPENAI_API_KEY}
```

### Docker Compose Integration
```yaml
services:
  service_name:
    env_file:
      - .env
    environment:
      SERVICE_SPECIFIC_VAR: value
```

## Monitoring and Logging

### Dependency Health
- Prometheus metrics for service health
- Grafana dashboards for dependency monitoring
- Structured logging for dependency issues

### Container Metrics
```bash
# Monitor container resource usage
docker stats

# View service logs
docker-compose logs -f service_name
```

## Future Enhancements

### Planned Improvements
1. **Automated Dependency Updates**: Dependabot or Renovate integration
2. **Security Scanning**: Automated vulnerability scanning in CI/CD
3. **Performance Monitoring**: Dependency performance impact tracking
4. **Multi-Environment Support**: Development, staging, production configurations

### Scalability Considerations
- Horizontal scaling of services
- Load balancing for frontend services
- Database connection pooling
- Caching strategies for AI services

---

## Quick Reference

### Commands
```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d service_name

# View logs
docker-compose logs -f service_name

# Rebuild service
docker-compose build service_name

# Stop all services
docker-compose down

# Clean up everything
docker-compose down -v --remove-orphans
```

### File Locations
- **Python Dependencies**: `service_name/requirements.txt`
- **Node.js Dependencies**: `service_name/package.json`
- **Docker Configuration**: `service_name/Dockerfile`
- **Service Orchestration**: `docker-compose.yml`
- **Environment Variables**: `.env` (create from `.env.example`)

### Support
- **Documentation**: See individual service README files
- **Issues**: Check Docker logs and health checks
- **Development**: Use volume mounts for live code updates

---

*This guide ensures consistent, isolated, and maintainable dependency management across the entire Algorithmic Trading System.*