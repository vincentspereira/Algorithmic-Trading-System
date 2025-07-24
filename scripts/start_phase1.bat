@echo off
REM Phase 1 Infrastructure Startup Script - Windows Version
REM Algorithmic Trading System

echo ==========================================
echo Algorithmic Trading System - Phase 1
echo Foundational Infrastructure Startup
echo ==========================================

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker and try again.
    pause
    exit /b 1
)

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] docker-compose is not installed. Please install it and try again.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo [WARNING] .env file not found. Creating from .env.example...
    if exist .env.example (
        copy .env.example .env >nul
        echo [SUCCESS] .env file created from .env.example
        echo [WARNING] Please review and update the .env file with your preferred settings
        echo [WARNING] Especially update the PostgreSQL password for security
    ) else (
        echo [ERROR] .env.example file not found. Cannot create .env file.
        pause
        exit /b 1
    )
)

REM Create necessary directories
echo [INFO] Creating necessary directories...
if not exist config\postgres mkdir config\postgres
if not exist config\jmx-exporter mkdir config\jmx-exporter
if not exist nautilus_trader_engine mkdir nautilus_trader_engine
if not exist scripts mkdir scripts

REM Stop any existing containers
echo [INFO] Stopping any existing containers...
docker-compose down >nul 2>&1

REM Pull latest images
echo [INFO] Pulling latest Docker images...
docker-compose pull

REM Build custom images
echo [INFO] Building custom images...
docker-compose build

REM Start services
echo [INFO] Starting Phase 1 services...
echo [INFO] This may take a few minutes on first run...

REM Start services in dependency order
echo [INFO] Starting Zookeeper...
docker-compose up -d zookeeper
timeout /t 10 /nobreak >nul

echo [INFO] Starting Kafka...
docker-compose up -d kafka
timeout /t 15 /nobreak >nul

echo [INFO] Starting Schema Registry...
docker-compose up -d schema-registry
timeout /t 10 /nobreak >nul

echo [INFO] Starting databases...
docker-compose up -d postgres clickhouse duckdb
timeout /t 20 /nobreak >nul

echo [INFO] Starting monitoring services...
docker-compose up -d prometheus grafana jmx-exporter
timeout /t 10 /nobreak >nul

echo [INFO] Starting management interfaces...
docker-compose up -d pgadmin
timeout /t 5 /nobreak >nul

echo [INFO] Starting Nautilus Trader Engine...
docker-compose up -d nautilus_trader_engine
timeout /t 15 /nobreak >nul

REM Check service status
echo [INFO] Checking service status...
docker-compose ps

REM Wait for services to be ready
echo [INFO] Waiting for services to be ready...
timeout /t 30 /nobreak >nul

REM Display service URLs
echo.
echo [SUCCESS] Phase 1 infrastructure started successfully!
echo.
echo ==========================================
echo SERVICE ENDPOINTS
echo ==========================================
echo 🚀 Nautilus Trader Engine:  http://localhost:8000
echo 📊 Grafana Dashboard:       http://localhost:3000 (admin/admin)
echo 📈 Prometheus:              http://localhost:9090
echo 🗄️  pgAdmin:                 http://localhost:5433 (admin@trading.com/admin)
echo 📋 Schema Registry:         http://localhost:8081
echo 📊 ClickHouse:              http://localhost:8123
echo 📊 JMX Exporter:            http://localhost:5556
echo.
echo ==========================================
echo NEXT STEPS
echo ==========================================
echo 1. Validate the infrastructure:
echo    python scripts/validate_phase1.py
echo.
echo 2. Check service health:
echo    curl http://localhost:8000/health
echo.
echo 3. View service logs:
echo    docker-compose logs -f
echo.
echo 4. Access Grafana dashboards at http://localhost:3000
echo.
echo 5. Review the Phase 1 documentation:
echo    type README_PHASE1.md
echo.
echo [SUCCESS] Phase 1 infrastructure is ready for development!
echo.

REM Optional: Ask to run validation script
if exist scripts\validate_phase1.py (
    echo ==========================================
    set /p choice="Would you like to run the validation script now? (y/n): "
    if /i "%choice%"=="y" (
        echo [INFO] Running infrastructure validation...
        python scripts/validate_phase1.py
    )
)

echo [SUCCESS] Startup complete! Happy trading! 🚀
pause