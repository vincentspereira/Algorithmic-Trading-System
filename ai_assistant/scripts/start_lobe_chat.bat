@echo off
setlocal enabledelayedexpansion

REM Lobe Chat Integration Startup Script for Windows
REM This script starts the AI Assistant, Lobe Chat Adapter, and Lobe Chat Frontend

echo 🚀 Starting Lobe Chat Integration for Algorithmic Trading System
echo ================================================================

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker first.
    pause
    exit /b 1
)

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ docker-compose is not installed. Please install docker-compose first.
    pause
    exit /b 1
)

REM Navigate to project root
cd /d "%~dp0\.."

REM Check if .env file exists
if not exist .env (
    echo ⚠️  .env file not found. Creating from example...
    if exist .env.example (
        copy .env.example .env >nul
        echo ✅ Created .env file from .env.example
        echo 📝 Please edit .env file with your API keys and configuration
    ) else (
        echo ❌ .env.example file not found. Please create .env file manually.
        pause
        exit /b 1
    )
)

REM Start prerequisite services first
echo 📦 Starting prerequisite services...
docker-compose up -d postgres redis kafka feast

REM Wait for services to be ready
echo ⏳ Waiting for prerequisite services to be ready...
timeout /t 10 /nobreak >nul

REM Start AI Assistant services
echo 🤖 Starting AI Assistant services...
docker-compose up -d ai_assistant lobe_chat_adapter lobe_chat

REM Wait for services to start
echo ⏳ Waiting for services to start...
timeout /t 15 /nobreak >nul

REM Check service health
echo 🔍 Checking service health...

REM Function to check service health
call :check_service "AI Assistant" "http://localhost:8002/health"
call :check_service "Lobe Chat Adapter" "http://localhost:8003/health"
call :check_service "Lobe Chat Frontend" "http://localhost:3210"

echo.
echo 🎉 Lobe Chat Integration is ready!
echo ================================================================
echo 📱 Lobe Chat Interface: http://localhost:3210
echo 🤖 AI Assistant API: http://localhost:8002
echo 🔗 Lobe Chat Adapter: http://localhost:8003
echo.
echo 📚 Documentation: ai_assistant\LOBE_CHAT_SETUP.md
echo 🧪 Run tests: python ai_assistant\test_lobe_chat_integration.py
echo.
echo 💡 Tips:
  - Open http://localhost:3210 in your browser to start chatting
  - The AI assistant has access to trading tools and reasoning capabilities
  - Check logs with: docker-compose logs -f lobe_chat
echo.
echo 🛑 To stop services: docker-compose down
echo ================================================================
pause
exit /b 0

:check_service
set service_name=%~1
set url=%~2
set max_attempts=10
set attempt=1

:check_loop
curl -s -f "%url%" >nul 2>&1
if errorlevel 1 (
    if !attempt! leq !max_attempts! (
        echo ⏳ Waiting for %service_name% (attempt !attempt!/!max_attempts!^)...
        timeout /t 3 /nobreak >nul
        set /a attempt+=1
        goto check_loop
    ) else (
        echo ❌ %service_name% failed to start properly
        exit /b 1
    )
) else (
    echo ✅ %service_name% is healthy
    exit /b 0
)
