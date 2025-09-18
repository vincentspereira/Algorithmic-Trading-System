# Docker Development Environment

This directory contains the Docker configuration for the Algorithmic Trading System development environment. The setup provides a complete, production-like environment that can be run locally with minimal configuration.

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** (Windows/macOS) or **Docker Engine** (Linux)
- **Docker Compose** v2.0 or higher
- **Git** for cloning the repository
- **PowerShell** (Windows) or **Bash** (Linux/macOS)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd algorithmic-trading-system
   ```

2. **Run the setup script:**
   
   **Windows (PowerShell):**
   ```powershell
   .\scripts\setup-dev-environment.ps1
   ```
   
   **Linux/macOS (Bash):**
   ```bash
   chmod +x scripts/setup-dev-environment.sh
   ./scripts/setup-dev-environment.sh
   ```

3. **Access the application:**
   - Frontend: http://localhost:3000
   - API Gateway: http://localhost:8001
   - API Documentation: http://localhost:8001/docs

## 📋 Services Overview

### Core Application Services

| Service | Port | Description |
|---------|------|-------------|
| **Frontend** | 3000 | Next.js React application |
| **API Gateway** | 8001 | FastAPI gateway and main API |
| **Market Data Service** | 8002 | Real-time market data processing |
| **Trading Engine** | 8003 | NautilusTrader-based trading engine |
| **Portfolio Manager** | 8004 | Portfolio management and optimization |
| **Risk Manager** | 8005 | Real-time risk monitoring |
| **AI Assistant** | 8006 | Agentic AI assistant service |

### Infrastructure Services

| Service | Port | Description |
|---------|------|-------------|
| **PostgreSQL** | 5432 | Primary database with pgvector |
| **ClickHouse** | 8123, 9000 | Time-series analytics database |
| **Redis** | 6379 | Caching and session storage |
| **Apache Kafka** | 9092, 29092 | Event streaming platform |
| **Zookeeper** | 2181 | Kafka coordination service |
| **Schema Registry** | 8081 | Kafka schema management |

### Background Services

| Service | Description |
|---------|-------------|
| **Celery Worker** | Background task processing |
| **Celery Beat** | Scheduled task management |

### Monitoring & Observability

| Service | Port | Description |
|---------|------|-------------|
| **Prometheus** | 9090 | Metrics collection |
| **Grafana** | 3001 | Metrics visualization |
| **Jaeger** | 16686 | Distributed tracing |
| **Kafka UI** | 8080 | Kafka cluster management |
| **Elasticsearch** | 9200 | Log aggregation |

### AI & Development Tools

| Service | Port | Description |
|---------|------|-------------|
| **Qdrant** | 6333 | Vector database for AI |
| **Jupyter Lab** | 8888 | Interactive development |
| **MinIO** | 9000, 9001 | S3-compatible object storage |
| **Keycloak** | 8090 | Identity and access management |

## 🔧 Configuration

### Environment Variables

The system uses a comprehensive `.env` file for configuration. Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

**Key Configuration Sections:**

- **Database Settings:** PostgreSQL, ClickHouse, Redis connections
- **Message Broker:** Kafka and Zookeeper configuration
- **Market Data:** API keys for data providers
- **Trading:** Broker configurations (Interactive Brokers)
- **AI Services:** OpenAI, Anthropic API keys
- **Security:** JWT secrets, encryption keys
- **Monitoring:** Service discovery and alerting

### Docker Compose Profiles

The system supports multiple profiles for different use cases:

```bash
# Basic development (default)
docker compose --profile development up

# With monitoring services
docker compose --profile development --profile monitoring up

# Full setup with AI services
docker compose --profile development --profile monitoring --profile ai up

# Testing environment
docker compose --profile testing up
```

## 🛠️ Development Workflow

### Starting the Environment

1. **Full setup with monitoring:**
   ```bash
   ./scripts/setup-dev-environment.sh -m
   ```

2. **With AI services:**
   ```bash
   ./scripts/setup-dev-environment.sh -a -m
   ```

3. **Clean restart:**
   ```bash
   ./scripts/setup-dev-environment.sh -c
   ```

### Common Commands

```bash
# View service status
docker compose ps

# View logs for all services
docker compose logs -f

# View logs for specific service
docker compose logs -f api-gateway

# Restart a service
docker compose restart trading-engine

# Execute commands in a container
docker compose exec api-gateway /bin/bash

# Stop all services
docker compose down

# Stop and remove volumes (⚠️ data loss)
docker compose down --volumes
```

### Hot Reloading

The development environment supports hot reloading:

- **Frontend:** Next.js hot reload on file changes
- **Backend:** FastAPI auto-reload on Python file changes
- **Jupyter:** Notebooks auto-save and reload

### Database Access

**PostgreSQL:**
```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U postgres -d trading_system

# Or use external client
psql postgresql://postgres:trading_password_2024@localhost:5432/trading_system
```

**ClickHouse:**
```bash
# Connect to ClickHouse
docker compose exec clickhouse clickhouse-client

# Or via HTTP
curl "http://localhost:8123/?query=SELECT%20version()"
```

**Redis:**
```bash
# Connect to Redis
docker compose exec redis redis-cli
```

## 📊 Monitoring & Debugging

### Health Checks

All services include health checks. Monitor service health:

```bash
# Check service health
docker compose ps

# View health check logs
docker compose logs [service-name] | grep health
```

### Prometheus Metrics

Access Prometheus at http://localhost:9090 to query metrics:

- **Application metrics:** Custom business metrics
- **Infrastructure metrics:** CPU, memory, disk usage
- **Trading metrics:** Order latency, execution rates
- **Market data metrics:** Feed latency, message rates

### Grafana Dashboards

Access Grafana at http://localhost:3001 (admin/grafana_admin_2024):

- **System Overview:** Infrastructure health
- **Trading Performance:** Trading metrics and KPIs
- **Market Data:** Data feed monitoring
- **Application Performance:** Service response times

### Distributed Tracing

Access Jaeger at http://localhost:16686 for request tracing:

- **End-to-end request tracking**
- **Performance bottleneck identification**
- **Service dependency mapping**

## 🔒 Security Considerations

### Development vs Production

**Development Environment:**
- Simplified authentication
- Exposed ports for debugging
- Relaxed security policies
- Default credentials (change in production)

**Production Deployment:**
- Enable TLS/SSL encryption
- Use secrets management (Vault, AWS Secrets Manager)
- Implement proper network segmentation
- Enable audit logging
- Use production-grade credentials

### Secrets Management

```bash
# Never commit secrets to version control
echo ".env" >> .gitignore

# Use environment-specific .env files
cp .env.example .env.development
cp .env.example .env.production
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
docker compose --profile testing run --rm test-runner pytest

# Run specific test suite
docker compose exec api-gateway pytest tests/unit/

# Run integration tests
docker compose exec api-gateway pytest tests/integration/

# Run with coverage
docker compose exec api-gateway pytest --cov=src tests/
```

### Test Databases

The testing profile includes isolated test databases:

- **Test PostgreSQL:** Separate database for tests
- **Test Redis:** Separate Redis instance
- **Test Kafka:** Isolated Kafka topics

## 📈 Performance Optimization

### Resource Limits

For production, uncomment and adjust resource limits in `.env`:

```bash
# Memory limits
POSTGRES_MEMORY_LIMIT=2g
REDIS_MEMORY_LIMIT=1g
KAFKA_MEMORY_LIMIT=2g

# CPU limits
POSTGRES_CPU_LIMIT=1.0
REDIS_CPU_LIMIT=0.5
```

### Volume Optimization

```bash
# Use named volumes for better performance
docker volume ls

# Backup important volumes
docker run --rm -v postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
```

## 🚨 Troubleshooting

### Common Issues

**Port Conflicts:**
```bash
# Check port usage
netstat -tulpn | grep :3000

# Kill process using port
sudo kill -9 $(lsof -t -i:3000)
```

**Memory Issues:**
```bash
# Check Docker memory usage
docker stats

# Increase Docker Desktop memory limit
# Docker Desktop → Settings → Resources → Memory
```

**Service Won't Start:**
```bash
# Check service logs
docker compose logs [service-name]

# Check service configuration
docker compose config

# Validate compose file
docker compose config --quiet
```

**Database Connection Issues:**
```bash
# Test database connectivity
docker compose exec api-gateway python -c "import psycopg2; print('PostgreSQL OK')"

# Check database logs
docker compose logs postgres
```

### Performance Issues

```bash
# Monitor resource usage
docker stats --no-stream

# Check disk usage
docker system df

# Clean up unused resources
docker system prune -a
```

### Network Issues

```bash
# List Docker networks
docker network ls

# Inspect network configuration
docker network inspect algorithmic-trading-system_trading-network

# Test service connectivity
docker compose exec api-gateway ping postgres
```

## 📚 Additional Resources

- **Docker Documentation:** https://docs.docker.com/
- **Docker Compose Reference:** https://docs.docker.com/compose/
- **FastAPI Documentation:** https://fastapi.tiangolo.com/
- **Next.js Documentation:** https://nextjs.org/docs
- **NautilusTrader Documentation:** https://nautilustrader.io/

## 🤝 Contributing

When contributing to the Docker configuration:

1. **Test changes locally** with different profiles
2. **Update documentation** for new services
3. **Maintain backward compatibility** when possible
4. **Follow security best practices**
5. **Update health checks** for new services

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.