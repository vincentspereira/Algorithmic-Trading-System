@echo off
REM Install Dependencies Without TA-Lib Script (Windows)
REM
REM This batch file runs the Python installation script for Windows users.
REM It installs all required dependencies except TA-Lib.
REM
REM Author: Vincent S. Pereira
REM Version: 1.0.0

echo ======================================================================
echo ALGORITHMIC TRADING SYSTEM - DEPENDENCY INSTALLER (Windows)
echo Installing all dependencies except TA-Lib
echo ======================================================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Run the Python installation script
echo Running Python installation script...
python "%~dp0install_without_talib.py"

if errorlevel 1 (
    echo.
    echo Installation failed. Check the errors above.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo INSTALLATION COMPLETED
echo ======================================================================
echo.
echo You can now test the system with:
echo   python nautilus_trader_engine\run_initial_backtest.py
echo.
echo For TA-Lib installation instructions, see:
echo   nautilus_trader_engine\TALIB_INSTALLATION.md
echo.
pause