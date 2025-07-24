@echo off
setlocal enabledelayedexpansion

:: Quick Start Docker Script for Algorithmic Trading System
:: This script provides a single command to build and run the entire system

echo ================================================================================
echo QUICK START - ALGORITHMIC TRADING SYSTEM
echo ================================================================================
echo.

:: Color codes for output
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

echo %BLUE%Starting Docker-based Algorithmic Trading System...%NC%
echo.

:: Check if Docker is running
echo %BLUE%[1/6] Checking Docker status...%NC%
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%✗ Docker is not running. Please start Docker Desktop.%NC%
    pause
    exit /b 1
)
echo %GREEN%✓ Docker is running%NC%

:: Check if .env file exists, create if not
echo.
echo %BLUE%[2/6] Checking environment configuration...%NC%
if not exist ".env" (
    echo %YELLOW%⚠ Creating .env file with default values...%NC%
    echo POSTGRES_USER=admin > .env
    echo POSTGRES_PASSWORD=Atsokapor@1 >> .env
    echo %GREEN%✓ .env file created%NC%
) else (
    echo %GREEN%✓ .env file exists%NC%
)

:: Stop any existing containers
echo.
echo %BLUE%[3/6] Stopping existing containers...%NC%
docker-compose down >nul 2>&1
echo %GREEN%✓ Existing containers stopped%NC%

:: Build images
echo.
echo %BLUE%[4/6] Building Docker images (this may take 10-15 minutes on first run)...%NC%
echo %YELLOW%Please wait while we build the trading engine...%NC%
docker-compose build --parallel
if %errorlevel% neq 0 (
    echo %RED%✗ Build failed. Check the output above for errors.%NC%
    pause
    exit /b 1
)
echo %GREEN%✓ Images built successfully%NC%

:: Start services
echo.
echo %BLUE%[5/6] Starting all services...%NC%
docker-compose up -d
if %errorlevel% neq 0 (
    echo %RED%✗ Failed to start services. Check the output above for errors.%NC%
    pause
    exit /b 1
)
echo %GREEN%✓ Services started%NC%

:: Wait for services to be ready
echo.
echo %BLUE%[6/6] Waiting for services to initialize...%NC%
echo %YELLOW%This may take 2-3 minutes for all services to be ready...%NC%

:: Wait and check health
set "RETRY_COUNT=0"
set "MAX_RETRIES=12"

:health_check_loop
timeout /t 15 /nobreak >nul
set /a RETRY_COUNT+=1

curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo %GREEN%✓ API is responding%NC%
    goto :services_ready
)

if %RETRY_COUNT% geq %MAX_RETRIES% (
    echo %RED%✗ Services did not start within expected time%NC%
    goto :show_status
)

echo %YELLOW%⏳ Still waiting... (attempt %RETRY_COUNT%/%MAX_RETRIES%)%NC%
goto :health_check_loop

:services_ready
echo.
echo %GREEN%🎉 SYSTEM IS READY!%NC%
echo.

:show_status
echo ================================================================================
echo SYSTEM STATUS
echo ================================================================================
docker-compose ps

echo.
echo ================================================================================
echo ACCESS INFORMATION
echo ================================================================================
echo %BLUE%🌐 Web Interfaces:%NC%
echo   • API Documentation:  http://localhost:8000/docs
echo   • Health Check:       http://localhost:8000/health
echo   • System Status:      http://localhost:8000/status
echo   • Grafana Dashboard:  http://localhost:3000 (admin/admin)
echo   • pgAdmin:           http://localhost:5433 (admin@trading.com/admin)
echo   • Prometheus:        http://localhost:9090
echo.

echo %BLUE%🔧 Management Commands:%NC%
echo   • View logs:         docker-compose logs -f
echo   • Stop system:       docker-compose down
echo   • Restart system:    docker-compose restart
echo   • Run backtest:      curl -X POST http://localhost:8000/api/v1/backtest/run
echo.

echo %BLUE%🧪 Testing:%NC%
echo   • Run full test:     scripts\test_docker_setup.bat
echo   • Manual backtest:   docker-compose exec nautilus_trader_engine python run_initial_backtest.py
echo.

:: Test API if it's responding
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo %BLUE%📊 Quick System Test:%NC%
    echo Running a quick health check...
    
    for /f "delims=" %%i in ('curl -s http://localhost:8000/health') do set "health_response=%%i"
    echo !health_response! | findstr "healthy" >nul 2>&1
    if %errorlevel% equ 0 (
        echo %GREEN%✓ All services are healthy and ready for trading!%NC%
        
        echo.
        echo %BLUE%🚀 Ready to run your first backtest?%NC%
        set /p "run_backtest=Run a sample AAPL backtest now? (y/n): "
        if /i "!run_backtest!"=="y" (
            echo.
            echo %YELLOW%Running sample backtest...%NC%
            curl -s -X POST "http://localhost:8000/api/v1/backtest/run" ^
                 -H "Content-Type: application/json" ^
                 -d "{\"symbol\":\"AAPL\",\"year\":2023,\"initial_capital\":100000}"
            echo.
            echo %GREEN%✓ Backtest completed! Check the API response above.%NC%
        )
    ) else (
        echo %YELLOW%⚠ Services are starting but not all are healthy yet%NC%
        echo   Wait a few more minutes and check: http://localhost:8000/health
    )
) else (
    echo %RED%✗ API is not responding yet%NC%
    echo   Check logs with: docker-compose logs nautilus_trader_engine
    echo   Or wait a few more minutes for services to fully start
)

echo.
echo ================================================================================
echo %GREEN%QUICK START COMPLETED%NC%
echo ================================================================================
echo.
echo %BLUE%Next Steps:%NC%
echo 1. Explore the API at http://localhost:8000/docs
echo 2. View system metrics in Grafana at http://localhost:3000
echo 3. Run comprehensive tests with: scripts\test_docker_setup.bat
echo 4. Check the DOCKER_TESTING_GUIDE.md for detailed information
echo.

echo %YELLOW%Need help?%NC%
echo • Check logs: docker-compose logs -f
echo • Troubleshooting: See DOCKER_TESTING_GUIDE.md
echo • Stop system: docker-compose down
echo.

pause