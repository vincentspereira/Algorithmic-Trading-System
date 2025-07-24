@echo off
echo ========================================
echo Python Global Package Cleanup - Windows
echo ========================================
echo.
echo This script will guide you through safely cleaning up
echo your global Python environment before Phase 1 setup.
echo.
echo IMPORTANT: This will create backups before any changes!
echo.
pause

echo.
echo Step 1: Running quick audit...
echo ========================================
call scripts\quick_audit.bat

echo.
echo Step 2: Starting interactive cleanup...
echo ========================================
echo.
echo The interactive cleanup tool will now start.
echo Follow the on-screen prompts to safely remove packages.
echo.
echo TIP: Choose option 2 (Select specific packages) for more control
echo.
pause

python scripts\cleanup_global_packages.py

echo.
echo Step 3: Verifying Python functionality...
echo ========================================
echo.
echo Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo ❌ ERROR: Python is not working properly!
    echo Please check the troubleshooting section in the documentation.
    pause
    exit /b 1
)

echo.
echo Checking pip installation...
python -m pip --version
if %errorlevel% neq 0 (
    echo ❌ ERROR: Pip is not working properly!
    echo Attempting to reinstall pip...
    python -m ensurepip --upgrade
)

echo.
echo Testing Python functionality...
python -c "import sys; print('✅ Python is working correctly!')"

echo.
echo Checking for package conflicts...
python -m pip check

echo.
echo ========================================
echo Cleanup Complete!
echo ========================================
echo.
echo ✅ Python global environment has been cleaned up
echo ✅ Backups have been created in the 'backups' folder
echo ✅ Python functionality verified
echo.
echo Next steps:
echo 1. Create virtual environment: python -m venv venv
echo 2. Activate it: venv\Scripts\activate
echo 3. Run Phase 1 setup: scripts\setup_dev_env.bat
echo.
echo For detailed instructions, see: docs\PYTHON_CLEANUP_INSTRUCTIONS.md
echo For quick reference, see: CLEANUP_STEPS.md
echo.
pause