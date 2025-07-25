# Docker Testing Guide - Algorithmic Trading System

This guide provides comprehensive instructions for testing the Algorithmic Trading System using Docker on Windows.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Step-by-Step Setup](#step-by-step-setup)
4. [Service Access](#service-access)
5. [Running Backtests](#running-backtests)
6. [Health Checks](#health-checks)
7. [Troubleshooting](#troubleshooting)
8. [Cleanup](#cleanup)

## Prerequisites

### Required Software
- **Docker Desktop for Windows** (version 4.0 or higher)
- **Windows 10/11** with WSL2 enabled
- **Git** for cloning the repository
- **PowerShell** or **Command Prompt**

### System Requirements
- **RAM**: Minimum 8GB (16GB recommended)
- **Storage**: At least 10GB free space
- **CPU**: Multi-core processor recommended

### Docker Desktop Setup
1. Download Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop/)
2. Install with WSL2 backend enabled
3. Ensure Docker Desktop is running (check system tray)
4. Verify installation:
   ```cmd
   docker --version
   docker-compose --version
   ```

## Quick Start

For immediate testing, run this single command:

```cmd
# Clone, build, and start all services
git clone <repository-url>
cd "Algorithmic Trading System"
docker-compose up --build -d
```

Then run the automated test script:
```cmd
scripts\test_docker_setup.bat
```

## Step-by-Step Setup

### 1. Environment Preparation

```cmd
# Navigate to project directory
cd "c:\Users\Vincent_Pereira\Projects\Algo_Trading_Projects\Kilo Code\Algorithmic Trading System"

# Verify .env file exists
type .env
```

Expected `.env` content:
```
POSTGRES_USER=your_postgres_user
POSTGRES_PASSWORD=your_postgres_password
```

### 2. Build Docker Images

```cmd
# Build all services (this may take 10-15 minutes on first run)
docker-compose build

# Check built images
docker images
```

### 3. Start Services

```cmd
# Start all services in detached mode
docker-compose up -d

# View startup logs
docker-compose logs -f
```

### 4. Verify Service Status

```cmd
# Check running containers
docker-compose ps

# Check individual service logs
docker-compose logs nautilus_trader_engine
docker-compose logs postgres
docker-compose logs kafka
```

## Service Access

Once all services are running, you can access:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Nautilus Trader API** | http://localhost:8000 | N/A |
| **API Documentation** | http://localhost:8000/docs | N/A |
| **Grafana Dashboard** | http://localhost:3000 | admin/admin |
| **pgAdmin** | http://localhost:5433 | admin@trading.com/admin |
| **Prometheus** | http://localhost:9090 | N/A |
| **ClickHouse** | http://localhost:8123 | N/A |

### Key Endpoints

- **Health Check**: http://localhost:8000/health
- **System Status**: http://localhost:8000/status
- **Metrics**: http://localhost:8000/metrics
- **Run Backtest**: http://localhost:8000/api/v1/backtest/run

## Running Backtests

### Method 1: Via API Endpoint (Recommended)

```cmd
# Run backtest via API
curl -X POST "http://localhost:8000/api/v1/backtest/run" ^
     -H "Content-Type: application/json" ^
     -d "{\"symbol\":\"AAPL\",\"year\":2023}"
```

### Method 2: Direct Container Execution

```cmd
# Execute backtest inside container
docker-compose exec nautilus_trader_engine python run_initial_backtest.py
```

### Method 3: Using PowerShell

```powershell
# PowerShell version
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/backtest/run" `
                  -Method POST `
                  -ContentType "application/json" `
                  -Body '{"symbol":"AAPL","year":2023}'
```

## Health Checks

### Automated Health Check Script

Run the comprehensive health check:
```cmd
scripts\test_docker_setup.bat
```

### Manual Health Checks

```cmd
# Check all container health
docker-compose ps

# Test API health
curl http://localhost:8000/health

# Test database connectivity
docker-compose exec postgres pg_isready -U admin

# Test Kafka connectivity
docker-compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Check ClickHouse
curl http://localhost:8123/ping
```

### Expected Health Check Results

✅ **Healthy System Output:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:00Z",
  "services": {
    "kafka_connected": true,
    "postgres_connected": true,
    "clickhouse_connected": true,
    "duckdb_connected": true
  }
}
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Port Conflicts
**Error**: `Port already in use`
```cmd
# Find processes using ports
netstat -ano | findstr :8000
netstat -ano | findstr :5432
netstat -ano | findstr :9092

# Kill conflicting processes
taskkill /PID <process_id> /F

# Or use different ports in docker-compose.yml
```

#### 2. Memory Issues
**Error**: `Container killed (OOMKilled)`
```cmd
# Increase Docker Desktop memory allocation
# Docker Desktop → Settings → Resources → Memory → 8GB+

# Check current memory usage
docker stats
```

#### 3. Build Failures
**Error**: `Failed to build nautilus_trader_engine`
```cmd
# Clean build cache
docker system prune -a

# Rebuild with no cache
docker-compose build --no-cache nautilus_trader_engine

# Check build logs
docker-compose build nautilus_trader_engine 2>&1 | tee build.log
```

#### 4. Database Connection Issues
**Error**: `Connection refused to postgres`
```cmd
# Check PostgreSQL logs
docker-compose logs postgres

# Verify environment variables
docker-compose exec nautilus_trader_engine env | grep POSTGRES

# Test connection manually
docker-compose exec postgres psql -U admin -d trading_system -c "\l"
```

#### 5. Kafka Issues
**Error**: `Kafka broker not available`
```cmd
# Check Kafka logs
docker-compose logs kafka

# Verify Kafka is ready
docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Create test topic
docker-compose exec kafka kafka-topics --create --topic test --bootstrap-server localhost:9092
```

#### 6. TA-Lib Installation Issues
**Error**: `TA-Lib not found`
```cmd
# Check TA-Lib installation in container
docker-compose exec nautilus_trader_engine python -c "import talib; print('TA-Lib OK')"

# If failed, rebuild with verbose output
docker-compose build --no-cache nautilus_trader_engine
```

### Windows-Specific Issues

#### WSL2 Integration
```cmd
# Enable WSL2 integration in Docker Desktop
# Settings → Resources → WSL Integration → Enable integration

# Restart Docker Desktop after changes
```

#### File Path Issues
```cmd
# Use forward slashes in volume mounts
# Ensure line endings are LF, not CRLF
git config core.autocrlf false
```

#### Firewall Issues
```cmd
# Allow Docker through Windows Firewall
# Windows Security → Firewall → Allow an app → Docker Desktop
```

### Performance Optimization

#### 1. Resource Allocation
```yaml
# Add to docker-compose.yml services
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '1.0'
```

#### 2. Volume Optimization
```cmd
# Use named volumes instead of bind mounts for better performance
# Already configured in docker-compose.yml
```

## Cleanup

### Stop Services
```cmd
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v

# Stop and remove images
docker-compose down --rmi all
```

### Complete Cleanup
```cmd
# Remove all containers, networks, and images
docker system prune -a

# Remove all volumes
docker volume prune

# Check remaining Docker objects
docker system df
```

## Testing Checklist

Use this checklist to verify your Docker setup:

- [ ] Docker Desktop is running
- [ ] All containers start successfully (`docker-compose ps`)
- [ ] Health check returns "healthy" status
- [ ] API documentation accessible at http://localhost:8000/docs
- [ ] Grafana dashboard loads at http://localhost:3000
- [ ] pgAdmin connects to PostgreSQL
- [ ] Backtest runs successfully
- [ ] Metrics are collected and visible
- [ ] Logs are generated without errors

## Advanced Testing

### Load Testing
```cmd
# Test API under load
for /l %i in (1,1,10) do curl http://localhost:8000/health
```

### Data Persistence Testing
```cmd
# Stop services
docker-compose down

# Restart services
docker-compose up -d

# Verify data persists
curl http://localhost:8000/status
```

### Network Testing
```cmd
# Test inter-service communication
docker-compose exec nautilus_trader_engine ping postgres
docker-compose exec nautilus_trader_engine ping kafka
```

## Support

If you encounter issues not covered in this guide:

1. Check the logs: `docker-compose logs <service_name>`
2. Verify system requirements are met
3. Ensure Docker Desktop is updated to the latest version
4. Try rebuilding with `--no-cache` flag
5. Check Windows Event Viewer for system-level issues

## Next Steps

After successful Docker testing:

1. Explore the API documentation at http://localhost:8000/docs
2. Run different backtest scenarios
3. Monitor system performance via Grafana
4. Experiment with different trading strategies
5. Scale services as needed for production use

---

**Last Updated**: January 2024  
**Version**: 1.0.0  
**Tested On**: Windows 11, Docker Desktop 4.25+