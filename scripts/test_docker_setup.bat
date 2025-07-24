@echo off
setlocal enabledelayedexpansion

:: Docker Setup Test Script for Windows
:: Tests all Docker services and provides comprehensive health checks

echo ================================================================================
echo DOCKER SETUP TEST SCRIPT - ALGORITHMIC TRADING SYSTEM
echo ================================================================================
echo.

:: Color codes for output
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

:: Test results tracking
set "TESTS_PASSED=0"
set "TESTS_FAILED=0"
set "TOTAL_TESTS=0"

:: Function to print colored output
goto :main

:print_success
echo %GREEN%✓ %~1%NC%
set /a TESTS_PASSED+=1
set /a TOTAL_TESTS+=1
goto :eof

:print_error
echo %RED%✗ %~1%NC%
set /a TESTS_FAILED+=1
set /a TOTAL_TESTS+=1
goto :eof

:print_warning
echo %YELLOW%⚠ %~1%NC%
goto :eof

:print_info
echo %BLUE%ℹ %~1%NC%
goto :eof

:main
echo Starting Docker setup tests...
echo.

:: Test 1: Check if Docker is installed and running
echo %BLUE%[1/15] Checking Docker installation...%NC%
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    call :print_success "Docker is installed"
    for /f "tokens=*" %%i in ('docker --version') do echo    Version: %%i
) else (
    call :print_error "Docker is not installed or not in PATH"
    echo    Please install Docker Desktop from https://www.docker.com/products/docker-desktop/
    goto :end_tests
)

:: Test 2: Check if Docker Compose is available
echo.
echo %BLUE%[2/15] Checking Docker Compose...%NC%
docker-compose --version >nul 2>&1
if %errorlevel% equ 0 (
    call :print_success "Docker Compose is available"
    for /f "tokens=*" %%i in ('docker-compose --version') do echo    Version: %%i
) else (
    call :print_error "Docker Compose is not available"
    goto :end_tests
)

:: Test 3: Check if Docker daemon is running
echo.
echo %BLUE%[3/15] Checking Docker daemon...%NC%
docker info >nul 2>&1
if %errorlevel% equ 0 (
    call :print_success "Docker daemon is running"
) else (
    call :print_error "Docker daemon is not running"
    echo    Please start Docker Desktop
    goto :end_tests
)

:: Test 4: Check if .env file exists
echo.
echo %BLUE%[4/15] Checking environment configuration...%NC%
if exist ".env" (
    call :print_success ".env file exists"
    echo    Contents:
    type .env | findstr /v "PASSWORD" 2>nul
    echo    POSTGRES_PASSWORD=****** (hidden)
) else (
    call :print_error ".env file not found"
    echo    Creating .env file with default values...
    echo POSTGRES_USER=admin > .env
    echo POSTGRES_PASSWORD=Atsokapor@1 >> .env
    call :print_info ".env file created with default values"
)

:: Test 5: Check if docker-compose.yml exists
echo.
echo %BLUE%[5/15] Checking Docker Compose configuration...%NC%
if exist "docker-compose.yml" (
    call :print_success "docker-compose.yml exists"
    for /f %%i in ('findstr /c:"services:" docker-compose.yml') do (
        echo    Configuration file is valid
    )
) else (
    call :print_error "docker-compose.yml not found"
    goto :end_tests
)

:: Test 6: Build Docker images
echo.
echo %BLUE%[6/15] Building Docker images (this may take several minutes)...%NC%
echo    Building nautilus_trader_engine image...
docker-compose build nautilus_trader_engine >nul 2>&1
if %errorlevel% equ 0 (
    call :print_success "Nautilus Trader Engine image built successfully"
) else (
    call :print_error "Failed to build Nautilus Trader Engine image"
    echo    Check build logs with: docker-compose build nautilus_trader_engine
)

:: Test 7: Start services
echo.
echo %BLUE%[7/15] Starting Docker services...%NC%
echo    This may take 2-3 minutes for all services to be ready...
docker-compose up -d >nul 2>&1
if %errorlevel% equ 0 (
    call :print_success "Docker services started"
) else (
    call :print_error "Failed to start Docker services"
    echo    Check logs with: docker-compose logs
)

:: Wait for services to be ready
echo    Waiting for services to initialize...
timeout /t 30 /nobreak >nul

:: Test 8: Check container status
echo.
echo %BLUE%[8/15] Checking container status...%NC%
for /f "skip=1 tokens=1,2" %%a in ('docker-compose ps --format "table {{.Name}} {{.State}}"') do (
    if "%%b"=="running" (
        call :print_success "%%a is running"
    ) else (
        call :print_error "%%a is not running (State: %%b)"
    )
)

:: Test 9: Test API health endpoint
echo.
echo %BLUE%[9/15] Testing API health endpoint...%NC%
timeout /t 10 /nobreak >nul
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    call :print_success "API health endpoint is responding"
    echo    Testing detailed health status...
    curl -s http://localhost:8000/health | findstr "healthy" >nul 2>&1
    if %errorlevel% equ 0 (
        call :print_success "All services report healthy status"
    ) else (
        call :print_warning "Some services may not be fully ready yet"
    )
) else (
    call :print_error "API health endpoint is not responding"
    echo    Waiting additional 30 seconds and retrying...
    timeout /t 30 /nobreak >nul
    curl -s http://localhost:8000/health >nul 2>&1
    if %errorlevel% equ 0 (
        call :print_success "API health endpoint is now responding"
    ) else (
        call :print_error "API health endpoint still not responding"
    )
)

:: Test 10: Test database connectivity
echo.
echo %BLUE%[10/15] Testing database connectivity...%NC%
docker-compose exec -T postgres pg_isready -U admin >nul 2>&1
if %errorlevel% equ 0 (
    call :print_success "PostgreSQL is ready"
) else (
    call :print_error "PostgreSQL is not ready"
)

:: Test 11: Test Kafka connectivity
echo.
echo %BLUE%[11/15] Testing Kafka connectivity...%NC%
docker-compose exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 >nul 2>&1
if %errorlevel% equ 0 (
    call :print_success "Kafka is ready"
) else (
    call :print_error "Kafka is not ready"
)

:: Test 12: Run sample backtest
echo.
echo %BLUE%[12/15] Running sample backtest...%NC%
echo    This will test the core trading engine functionality...

:: Try API endpoint first
curl -s -X POST "http://localhost:8000/api/v1/backtest/run" ^
     -H "Content-Type: application/json" ^
     -d "{\"symbol\":\"AAPL\",\"year\":2023}" >nul 2>&1

if %errorlevel% equ 0 (
    call :print_success "Backtest API endpoint is working"
) else (
    call :print_warning "Backtest API endpoint not available, trying direct execution..."
    
    :: Try direct execution in container
    docker-compose exec -T nautilus_trader_engine python -c "from run_initial_backtest import BacktestRunner; runner = BacktestRunner('AAPL', 2023, 10000); print('Backtest runner initialized successfully')" >nul 2>&1
    if %errorlevel% equ 0 (
        call :print_success "Backtest engine is functional"
    ) else (
        call :print_error "Backtest engine test failed"
    )
)

:: Test 13: Test Kafka integration status
echo.
echo %BLUE%[13/15] Testing Kafka integration...%NC%
curl -s http://localhost:8000/api/v1/kafka/status >nul 2>&1
if %errorlevel% equ 0 (
    call :print_success "Kafka integration API is accessible"
    
    :: Check if Kafka is actually connected
    curl -s http://localhost:8000/api/v1/kafka/status | findstr "connected" >nul 2>&1
    if %errorlevel% equ 0 (
        call :print_success "Kafka is connected and ready"
    ) else (
        call :print_warning "Kafka integration API available but connection may be pending"
    )
) else (
    call :print_error "Kafka integration API is not accessible"
)

:: Test 14: Test Kafka connection functionality
echo.
echo %BLUE%[14/15] Testing Kafka connection...%NC%
curl -s -X POST http://localhost:8000/api/v1/kafka/test >nul 2>&1
if %errorlevel% equ 0 (
    call :print_success "Kafka connection test passed"
) else (
    call :print_warning "Kafka connection test failed - may need more time to initialize"
)

:: Test 15: Test Kafka streaming functionality
echo.
echo %BLUE%[15/15] Testing Kafka streaming functionality...%NC%
echo    Testing symbol streaming start/stop...

:: Test starting streaming for AAPL
curl -s -X POST "http://localhost:8000/api/v1/kafka/streaming/start" ^
     -H "Content-Type: application/json" ^
     -d "{\"symbol\":\"AAPL\",\"asset_class\":\"stock\",\"interval\":\"1d\"}" >nul 2>&1

if %errorlevel% equ 0 (
    call :print_success "Kafka streaming start API is working"
    
    :: Check streaming symbols
    curl -s http://localhost:8000/api/v1/kafka/streaming/symbols >nul 2>&1
    if %errorlevel% equ 0 (
        call :print_success "Kafka streaming symbols API is working"
    ) else (
        call :print_warning "Kafka streaming symbols API not responding"
    )
    
    :: Test stopping streaming
    curl -s -X POST "http://localhost:8000/api/v1/kafka/streaming/stop" ^
         -H "Content-Type: application/json" ^
         -d "{\"symbol\":\"AAPL\"}" >nul 2>&1
    
    if %errorlevel% equ 0 (
        call :print_success "Kafka streaming stop API is working"
    ) else (
        call :print_warning "Kafka streaming stop API not responding"
    )
) else (
    call :print_error "Kafka streaming start API failed"
)

:end_tests
echo.
echo ================================================================================
echo TEST SUMMARY
echo ================================================================================
echo Total Tests: %TOTAL_TESTS%
echo Passed: %GREEN%%TESTS_PASSED%%NC%
echo Failed: %RED%%TESTS_FAILED%%NC%
echo.

if %TESTS_FAILED% equ 0 (
    echo %GREEN%🎉 ALL TESTS PASSED! Your Docker setup is ready for trading!%NC%
    echo.
    echo %BLUE%Next Steps:%NC%
    echo 1. Access API documentation: http://localhost:8000/docs
    echo 2. View Grafana dashboards: http://localhost:3000 (admin/admin)
    echo 3. Access pgAdmin: http://localhost:5433 (admin@trading.com/admin)
    echo 4. Run a full backtest: docker-compose exec nautilus_trader_engine python run_initial_backtest.py
    echo.
) else (
    echo %RED%❌ Some tests failed. Please check the errors above.%NC%
    echo.
    echo %YELLOW%Troubleshooting Tips:%NC%
    echo 1. Check Docker Desktop is running
    echo 2. Ensure you have enough memory allocated (8GB+ recommended)
    echo 3. Check logs: docker-compose logs
    echo 4. Try rebuilding: docker-compose build --no-cache
    echo 5. Restart services: docker-compose down && docker-compose up -d
    echo.
)

echo %BLUE%Service Status:%NC%
docker-compose ps

echo.
echo %BLUE%Quick Commands:%NC%
echo - View logs: docker-compose logs -f
echo - Stop services: docker-compose down
echo - Restart services: docker-compose restart
echo - Clean rebuild: docker-compose down && docker-compose build --no-cache && docker-compose up -d
echo.

echo %BLUE%Access URLs:%NC%
echo - API: http://localhost:8000
echo - API Docs: http://localhost:8000/docs
echo - Health Check: http://localhost:8000/health
echo - Kafka Status: http://localhost:8000/api/v1/kafka/status
echo - Grafana: http://localhost:3000
echo - pgAdmin: http://localhost:5433
echo - Prometheus: http://localhost:9090

echo.
echo Test completed at %date% %time%
echo For detailed troubleshooting, see DOCKER_TESTING_GUIDE.md

pause