@echo off
REM Chaos Engineering Test Runner Script for Windows

echo 🔥 Starting Chaos Engineering Tests
echo ==================================

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker and try again.
    exit /b 1
)

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] docker-compose is not installed. Please install docker-compose and try again.
    exit /b 1
)

REM Create necessary directories
echo [INFO] Creating directories...
if not exist "results" mkdir results
if not exist "reports" mkdir reports
if not exist "game_day_reports" mkdir game_day_reports
if not exist "test-results" mkdir test-results
if not exist "monitoring\grafana\dashboards" mkdir monitoring\grafana\dashboards
if not exist "monitoring\grafana\datasources" mkdir monitoring\grafana\datasources

REM Build the chaos engineering image
echo [INFO] Building chaos engineering Docker image...
docker-compose build chaos-engineering

REM Start the infrastructure services
echo [INFO] Starting infrastructure services...
docker-compose up -d prometheus grafana test-api test-database test-redis

REM Wait for services to be ready
echo [INFO] Waiting for services to be ready...
timeout /t 10 /nobreak >nul

REM Run the chaos engineering tests
echo [INFO] Running chaos engineering tests...
docker-compose --profile testing run --rm chaos-test-runner

if %errorlevel% equ 0 (
    echo [INFO] ✅ All chaos engineering tests passed!
) else (
    echo [ERROR] ❌ Some chaos engineering tests failed!
    exit /b 1
)

REM Run a sample chaos experiment
echo [INFO] Running sample chaos experiment...
docker-compose run --rm chaos-engineering python chaos_engineering_framework.py

echo [INFO] Test run completed successfully!
echo [INFO] Reports available in: .\reports\
echo [INFO] Prometheus UI: http://localhost:9090
echo [INFO] Grafana UI: http://localhost:3000 (admin/chaos123)

REM Ask if user wants to keep services running
set /p keep_running="Keep services running for manual testing? (y/N): "
if /i "%keep_running%"=="y" (
    echo [INFO] Services will continue running. Use 'docker-compose down' to stop them.
) else (
    echo [INFO] Stopping services...
    docker-compose down
)

echo 🎉 Chaos engineering test run completed!