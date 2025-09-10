@echo off
REM Development Environment Setup Script using Docker
REM This script sets up a Python development environment using Docker for isolation

setlocal enabledelayedexpansion

echo 🐳 Algorithmic Trading System - Docker Development Environment Setup
echo ====================================================================

REM Check if Docker is available
:check_docker
echo 🔍 Checking Docker installation...

docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Docker is not installed or not in PATH
    echo Please install Docker Desktop from https://docker.com and try again.
    pause
    exit /b 1
)

echo ✅ Found Docker: 
docker --version

REM Build the development container
:build_container
echo.
echo 🏗️  Building development container...

docker-compose -f docker-compose.dev.yml build
if errorlevel 1 (
    echo ❌ Error: Failed to build development container
    pause
    exit /b 1
)
echo ✅ Development container built successfully

REM Create convenience scripts
:create_scripts
echo.
echo 🛠️  Creating convenience scripts...

echo @echo off > run_dev_container.bat
echo REM Quick script to run the development container >> run_dev_container.bat
echo. >> run_dev_container.bat
echo echo 🐳 Starting development container... >> run_dev_container.bat
echo docker-compose -f docker-compose.dev.yml run --rm algo-trading-dev >> run_dev_container.bat
echo echo. >> run_dev_container.bat
echo echo 💡 Inside the container, you can: >> run_dev_container.bat
echo echo    - Install dependencies with pip >> run_dev_container.bat
echo echo    - Run tests >> run_dev_container.bat
echo echo    - Develop and test your code >> run_dev_container.bat
echo echo. >> run_dev_container.bat
echo echo 🔚 Type 'exit' to leave the container >> run_dev_container.bat

echo ✅ Created container script: .\run_dev_container.bat

echo @echo off > start_dev_services.bat
echo REM Quick script to start development services >> start_dev_services.bat
echo. >> start_dev_services.bat
echo echo 🚀 Starting development services... >> start_dev_services.bat
echo docker-compose -f docker-compose.dev.yml up >> start_dev_services.bat

echo ✅ Created services script: .\start_dev_services.bat

REM Display usage instructions
:show_instructions
echo.
echo 🎉 Docker development environment setup complete!
echo.
echo 📋 Next steps:
echo 1. Run the development container:
echo    .\run_dev_container.bat
echo.
echo 2. Or start development services:
echo    .\start_dev_services.bat
echo.
echo 3. Inside the container, all dependencies will be properly isolated
echo    and won't affect your global Python environment.
echo.
echo ⚠️  IMPORTANT: All development should be done inside the Docker container
echo 🔒 This ensures packages are installed only in the container, not globally
echo.
pause