# Algorithmic Trading System - Phase 1: Foundational Setup

## Overview

This document provides setup instructions for Phase 1 of the Algorithmic Trading System. Phase 1 establishes the core infrastructure with Kafka as the event-driven backbone, multi-database support, and observability stack.

## Architecture

Phase 1 implements the following services:

- **Apache Kafka + Zookeeper**: Event streaming backbone
- **Schema Registry**: Kafka schema management
- **PostgreSQL 17 + pgvector**: Relational database with vector search
- **ClickHouse**: Time-series analytics database
- **DuckDB**: Fast OLAP queries for research
- **Nautilus Trader Engine**: Core trading engine (Python-based)
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboards
- **JMX Exporter**: JVM metrics for Kafka
- **pgAdmin**: PostgreSQL management interface

## Prerequisites

- Docker and Docker Compose installed
- At least 8GB RAM available
- 20GB free disk space
- Git for version control
- **Python 3.11+** (for local development only)

⚠️ **IMPORTANT**: This project uses Docker containers for production deployment. For local development, you can choose between:
- **Docker containers** (recommended for production-like environment)
- **Python virtual environments** (recommended for development)

**NEVER install Python packages globally** - always use virtual environments or Docker containers.

## Development Environment Setup

Choose your preferred development approach:

### Option A: Docker Development (Recommended for Production-like Environment)

This approach uses Docker containers for everything, providing complete isolation:

```bash
# Start all services including the trading engine
docker-compose up -d

# View logs
docker-compose logs -f nautilus_trader_engine

# Access the container for development
docker-compose exec nautilus_trader_engine bash
```

### Option B: Local Python Development (Recommended for Active Development)

This approach uses Docker for infrastructure (databases, Kafka) but runs Python locally in a virtual environment:

#### Step 1: Set up Python Virtual Environment

```bash
# Linux/Mac - Use the provided setup script
./scripts/setup_dev_env.sh

# Windows - Use the provided setup script
.\scripts\setup_dev_env.bat

# OR manually create virtual environment:
python -m venv venv

# Activate virtual environment:
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate.bat

# Install dependencies:
pip install -r nautilus_trader_engine/requirements.txt
```

#### Step 2: Start Infrastructure Services Only

```bash
# Start only the infrastructure (databases, Kafka, monitoring)
docker-compose up -d postgres clickhouse kafka zookeeper schema-registry prometheus grafana pgadmin

# Verify services are running
docker-compose ps
```

#### Step 3: Run Python Application Locally

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate.bat  # Windows

# Run the trading engine locally
cd nautilus_trader_engine
python main.py
```

### Environment Verification

Verify your setup is working correctly:

```bash
# Check virtual environment (for local development)
echo $VIRTUAL_ENV  # Linux/Mac
echo %VIRTUAL_ENV%  # Windows

# Test application endpoints
curl http://localhost:8000/health
curl http://localhost:8000/status
```

## Quick Start (Docker-only)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd algorithmic-trading-system
```

### 2. Environment Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your preferred settings
# At minimum, update the PostgreSQL password
nano .env
```

### 3. Start the Infrastructure

```bash
# Start all Phase 1 services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Verify Services

Once all services are running, verify they're accessible:

- **Nautilus Trader Engine**: http://localhost:8000
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **pgAdmin**: http://localhost:5433 (admin@trading.com/admin)
- **Schema Registry**: http://localhost:8081

## Service Details

### Nautilus Trader Engine

The core trading engine provides:
- Health check endpoint: `/health`
- Service status: `/status`
- API information: `/api/v1/info`
- Prometheus metrics: `/metrics`

### PostgreSQL with pgvector

Pre-configured with:
- Vector similarity search capability
- Trading-specific schemas (trading, market_data, ai_embeddings, risk_management, audit)
- Sample data for testing
- Proper indexing for performance

### Kafka Configuration

- **Bootstrap servers**: kafka:9092
- **Zookeeper**: zookeeper:2181
- **Schema Registry**: schema-registry:8081
- **JMX metrics**: Available via JMX Exporter on port 5556

### DuckDB

- **Database path**: `/app/data/duckdb/trading_research.duckdb`
- **Purpose**: Fast OLAP queries for research and analysis
- **Access**: Via Python applications in the nautilus_trader_engine

## Monitoring and Observability

### Prometheus Metrics

Prometheus is configured to scrape metrics from:
- Nautilus Trader Engine (port 8000)
- Kafka JMX Exporter (port 5556)
- PostgreSQL (when postgres_exporter is added)
- ClickHouse (port 8123)
- Schema Registry (port 8081)

### Grafana Dashboards

Access Grafana at http://localhost:3000 with admin/admin credentials.

Pre-configured data sources:
- Prometheus (for metrics)
- PostgreSQL (for trading data)
- ClickHouse (for time-series data)

## Data Flow

```
Market Data → Kafka Topics → NautilusTrader Engine
                ↓
         PostgreSQL (Structured Data)
                ↓
         ClickHouse (Time-Series)
                ↓
         DuckDB (Research Queries)
```

## Development Workflow

### Adding New Services

1. Update `docker-compose.yml`
2. Add configuration files in `/config`
3. Update Prometheus scraping configuration
4. Add health checks and monitoring

### Database Migrations

PostgreSQL initialization scripts are in `/config/postgres/init.sql`. For schema changes:

1. Create migration scripts
2. Update the init.sql file
3. Restart the postgres service

### Configuration Management

All configuration files are in the `/config` directory:
- `/config/prometheus.yml` - Prometheus configuration
- `/config/postgres/init.sql` - PostgreSQL initialization
- `/config/jmx-exporter/config.yaml` - JMX Exporter rules

## Troubleshooting

### Common Issues

1. **Services not starting**: Check Docker resources and port conflicts
2. **Database connection errors**: Verify .env file configuration
3. **Kafka connection issues**: Ensure Zookeeper is healthy first
4. **Memory issues**: Increase Docker memory allocation

### Health Checks

```bash
# Check all service health
docker-compose ps

# Check specific service logs
docker-compose logs nautilus_trader_engine
docker-compose logs kafka
docker-compose logs postgres

# Test service endpoints
curl http://localhost:8000/health
curl http://localhost:9090/-/healthy
```

### Useful Commands

```bash
# Restart specific service
docker-compose restart nautilus_trader_engine

# Rebuild service after code changes
docker-compose build nautilus_trader_engine
docker-compose up -d nautilus_trader_engine

# Access service shell
docker-compose exec nautilus_trader_engine bash
docker-compose exec postgres psql -U trading_admin -d trading_system

# View resource usage
docker stats

# Clean up (WARNING: removes all data)
docker-compose down -v
docker system prune -a
```

## Python Environment Management

### Important Notes

⚠️ **CRITICAL**: The configuration files in this project (`requirements.txt`, `Dockerfile`) do NOT automatically install packages globally. They are specification files that define what should be installed when you run installation commands.

### Best Practices

1. **Always use virtual environments** for local Python development
2. **Use Docker containers** for production deployments
3. **Never install packages globally** unless they are system tools
4. **Verify your environment** before running any Python code

### Cleanup Global Packages

If you need to clean up any globally installed Python packages, see [`docs/PYTHON_CLEANUP_GUIDE.md`](docs/PYTHON_CLEANUP_GUIDE.md) for detailed instructions.

### Environment Troubleshooting

```bash
# Check if you're in a virtual environment
echo $VIRTUAL_ENV  # Linux/Mac (should show venv path)
echo %VIRTUAL_ENV%  # Windows (should show venv path)

# Check Python location
which python  # Linux/Mac (should point to venv/bin/python)
where python  # Windows (should point to venv\Scripts\python.exe)

# List installed packages
pip list  # Should only show project dependencies if in venv
```

## Security Considerations

Phase 1 is configured for development. For production:

1. Change all default passwords in `.env`
2. Configure proper network security
3. Enable SSL/TLS for all services
4. Implement proper authentication
5. Review and restrict service ports
6. **Use Docker containers** for complete isolation

## Next Steps - Phase 2

Phase 2 will add:
- FastAPI bridge with backtesting endpoints
- VectorBT integration for GPU-accelerated backtesting
- Optuna for hyperparameter optimization
- gRPC for low-latency data streaming
- Technical indicator libraries (TA-Lib)

## Support

For issues and questions:
1. Check the logs: `docker-compose logs -f`
2. Verify service health: `curl http://localhost:8000/health`
3. Review configuration files in `/config`
4. Check Docker resources and system requirements

## Performance Tuning

For optimal performance:

1. **Memory allocation**: Increase Docker memory to 16GB+ for production
2. **Kafka**: Tune `KAFKA_HEAP_OPTS` for your workload
3. **PostgreSQL**: Adjust `shared_buffers` and `work_mem`
4. **ClickHouse**: Configure memory limits appropriately
5. **Monitoring**: Use Grafana dashboards to identify bottlenecks

---

**Phase 1 Status**: ✅ Infrastructure Complete
**Next Phase**: Phase 2 - API Bridge & Initial Analytics