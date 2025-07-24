@echo off
REM Development Environment Setup Script for Windows
REM This script creates a Python virtual environment and installs dependencies safely

setlocal enabledelayedexpansion

echo 🐍 Algorithmic Trading System - Development Environment Setup
echo ============================================================

REM Check if Python 3.11+ is available
:check_python
echo 🔍 Checking Python installation...

python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://python.org and try again.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Found Python: %PYTHON_VERSION%

REM Extract major and minor version numbers
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

if %MAJOR% LSS 3 (
    echo ❌ Error: Python 3.11+ is required. Found Python %PYTHON_VERSION%
    echo Please install Python 3.11 or higher and try again.
    pause
    exit /b 1
)

if %MAJOR% EQU 3 if %MINOR% LSS 11 (
    echo ❌ Error: Python 3.11+ is required. Found Python %PYTHON_VERSION%
    echo Please install Python 3.11 or higher and try again.
    pause
    exit /b 1
)

REM Create virtual environment
:create_venv
echo.
echo 🏗️  Setting up virtual environment...

set VENV_DIR=venv

if exist "%VENV_DIR%" (
    echo ⚠️  Virtual environment already exists at .\%VENV_DIR%
    set /p RECREATE="Do you want to recreate it? (y/N): "
    if /i "!RECREATE!"=="y" (
        echo 🗑️  Removing existing virtual environment...
        rmdir /s /q "%VENV_DIR%"
    ) else (
        echo 📁 Using existing virtual environment
        goto install_dependencies
    )
)

echo 🔨 Creating Python virtual environment...
python -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo ❌ Error: Failed to create virtual environment
    pause
    exit /b 1
)
echo ✅ Virtual environment created at .\%VENV_DIR%

REM Activate virtual environment and install dependencies
:install_dependencies
echo.
echo 📦 Installing dependencies...
echo 🔄 Activating virtual environment...

call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo ❌ Error: Failed to activate virtual environment
    pause
    exit /b 1
)

echo 📦 Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo ❌ Error: Failed to upgrade pip
    pause
    exit /b 1
)

echo 📚 Installing project dependencies...
if exist "nautilus_trader_engine\requirements.txt" (
    pip install -r nautilus_trader_engine\requirements.txt
    if errorlevel 1 (
        echo ❌ Error: Failed to install dependencies
        pause
        exit /b 1
    )
    echo ✅ Dependencies installed successfully
) else (
    echo ❌ Error: requirements.txt not found at nautilus_trader_engine\requirements.txt
    pause
    exit /b 1
)

REM Create activation script
:create_activation_script
echo.
echo 🛠️  Creating convenience scripts...

echo @echo off > activate_dev_env.bat
echo REM Quick activation script for development environment >> activate_dev_env.bat
echo. >> activate_dev_env.bat
echo if not exist "venv" ^( >> activate_dev_env.bat
echo     echo ❌ Virtual environment not found. Run .\scripts\setup_dev_env.bat first >> activate_dev_env.bat
echo     pause >> activate_dev_env.bat
echo     exit /b 1 >> activate_dev_env.bat
echo ^) >> activate_dev_env.bat
echo. >> activate_dev_env.bat
echo echo 🐍 Activating development environment... >> activate_dev_env.bat
echo call venv\Scripts\activate.bat >> activate_dev_env.bat
echo echo ✅ Development environment activated >> activate_dev_env.bat
echo echo 💡 To deactivate, run: deactivate >> activate_dev_env.bat
echo echo 📁 Current Python: >> activate_dev_env.bat
echo where python >> activate_dev_env.bat
echo echo 📦 To see installed packages, run: pip list >> activate_dev_env.bat

echo ✅ Created activation script: .\activate_dev_env.bat

REM Display usage instructions
:show_instructions
echo.
echo 🎉 Development environment setup complete!
echo.
echo 📋 Next steps:
echo 1. Activate the environment:
echo    venv\Scripts\activate.bat
echo    # OR use the convenience script:
echo    .\activate_dev_env.bat
echo.
echo 2. Verify installation:
echo    python --version
echo    pip list
echo.
echo 3. Run the application:
echo    cd nautilus_trader_engine
echo    python main.py
echo.
echo 4. To deactivate when done:
echo    deactivate
echo.
echo ⚠️  IMPORTANT: Always activate the virtual environment before working on the project!
echo 🔒 This ensures packages are installed locally, not globally on your system.
echo.
pause