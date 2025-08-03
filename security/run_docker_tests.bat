@echo off
REM Fraud Detection Docker Test Runner for Windows
REM This script builds and runs comprehensive tests in Docker environment

echo 🐳 Fraud Detection System - Docker Test Suite
echo ==============================================

REM Check if Docker is available
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not in PATH
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose is not installed or not in PATH
    exit /b 1
)

echo [INFO] Docker and Docker Compose are available

REM Navigate to security directory
cd /d "%~dp0"

REM Clean up any existing containers
echo [INFO] Cleaning up existing containers...
docker-compose down --remove-orphans >nul 2>&1
docker system prune -f >nul 2>&1

REM Build the Docker image
echo [INFO] Building Docker image...
docker-compose build fraud-detection-test
if errorlevel 1 (
    echo [ERROR] Failed to build Docker image
    exit /b 1
)
echo [SUCCESS] Docker image built successfully

REM Run the comprehensive tests
echo [INFO] Running comprehensive fraud detection tests...
echo ================================================

docker-compose run --rm fraud-detection-test
if errorlevel 1 (
    echo [ERROR] Tests failed!
    echo [INFO] Showing container logs for debugging...
    docker-compose logs fraud-detection-test
    exit /b 1
)

echo [SUCCESS] All tests completed successfully!

REM Copy test results from container
echo [INFO] Copying test results...
docker-compose run --rm -v "%cd%:/host" fraud-detection-test cp /app/security/COMPREHENSIVE_TEST_REPORT.json /host/ >nul 2>&1

if exist "COMPREHENSIVE_TEST_REPORT.json" (
    echo [SUCCESS] Test report saved to COMPREHENSIVE_TEST_REPORT.json
    echo.
    echo 📊 TEST SUMMARY
    echo ===============
    echo Check COMPREHENSIVE_TEST_REPORT.json for detailed results
)

REM Optional: Run the server for manual testing
set /p choice="Do you want to start the fraud detection server for manual testing? (y/N): "
if /i "%choice%"=="y" (
    echo [INFO] Starting fraud detection server...
    echo [INFO] Server will be available at http://localhost:8080
    echo [INFO] Press Ctrl+C to stop the server
    
    docker-compose up fraud-detection-server
)

REM Clean up
echo [INFO] Cleaning up...
docker-compose down --remove-orphans

echo [SUCCESS] Docker test suite completed!
echo.
echo 📋 Next Steps:
echo - Review the test report: COMPREHENSIVE_TEST_REPORT.json
echo - Check logs for any warnings or issues
echo - Deploy to production if all tests passed

pause