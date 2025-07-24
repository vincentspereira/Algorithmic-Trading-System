# Python Global Package Cleanup Guide

This guide helps you identify and clean up any Python packages that may have been installed globally on your system, ensuring a clean development environment.

## Overview

**IMPORTANT**: The configuration files in this project (`requirements.txt`, `Dockerfile`) do NOT automatically install packages globally. They are just specification files that define what should be installed when you run installation commands.

However, if you've previously installed Python packages globally or want to ensure a clean system, this guide will help you.

## Checking for Global Packages

### 1. List All Globally Installed Packages

```bash
# On Linux/Mac/Windows
pip list --user  # User-installed packages
pip list         # All packages (including system packages)

# To see only packages you've installed (not system packages)
pip freeze --user
```

### 2. Check Specific Trading-Related Packages

Run this command to check if any of our project's packages are installed globally:

```bash
# Check for specific packages from our requirements.txt
pip show nautilus_trader kafka-python psycopg2-binary clickhouse-driver pandas numpy scipy scikit-learn fastapi uvicorn
```

If any of these show information, they are installed globally.

## Cleanup Methods

### Method 1: Selective Removal (Recommended)

Remove only the packages related to our trading system:

```bash
# Remove trading-specific packages if they exist globally
pip uninstall -y nautilus_trader
pip uninstall -y kafka-python
pip uninstall -y psycopg2-binary
pip uninstall -y clickhouse-driver
pip uninstall -y duckdb
pip uninstall -y pandas
pip uninstall -y numpy
pip uninstall -y scipy
pip uninstall -y scikit-learn
pip uninstall -y ta-lib
pip uninstall -y ta
pip uninstall -y yfinance
pip uninstall -y backtrader
pip uninstall -y vectorbt
pip uninstall -y optuna
pip uninstall -y fastapi
pip uninstall -y uvicorn
pip uninstall -y pydantic
pip uninstall -y python-multipart
pip uninstall -y aiofiles
pip uninstall -y asyncpg
pip uninstall -y sqlalchemy
pip uninstall -y alembic
pip uninstall -y redis
pip uninstall -y celery
pip uninstall -y prometheus-client
pip uninstall -y structlog
pip uninstall -y python-json-logger
pip uninstall -y pyportfolioopt
pip uninstall -y riskfolio-lib
pip uninstall -y quantlib
pip uninstall -y arch
pip uninstall -y statsmodels
pip uninstall -y matplotlib
pip uninstall -y seaborn
pip uninstall -y plotly
pip uninstall -y dash
pip uninstall -y jupyter
pip uninstall -y ipykernel
pip uninstall -y bandit
pip uninstall -y pre-commit
pip uninstall -y alpha_vantage
```

### Method 2: Complete User Package Cleanup (Advanced)

⚠️ **WARNING**: This removes ALL user-installed packages. Only do this if you're sure you want to start completely fresh.

```bash
# Create a list of all user-installed packages
pip freeze --user > user_packages.txt

# Remove all user-installed packages
pip uninstall -r user_packages.txt -y

# Clean up the temporary file
rm user_packages.txt  # Linux/Mac
del user_packages.txt  # Windows
```

### Method 3: Using pip-autoremove (Optional)

Install and use pip-autoremove to clean up unused dependencies:

```bash
# Install pip-autoremove
pip install pip-autoremove

# Remove a package and its unused dependencies
pip-autoremove nautilus_trader -y

# Remove pip-autoremove itself when done
pip uninstall pip-autoremove -y
```

## Automated Cleanup Script

### Linux/Mac Script

Create and run this script to check and clean up automatically:

```bash
#!/bin/bash
# cleanup_global_python.sh

echo "🧹 Python Global Package Cleanup"
echo "================================="

# List of packages from our requirements.txt
PACKAGES=(
    "nautilus_trader" "kafka-python" "psycopg2-binary" "clickhouse-driver"
    "duckdb" "pandas" "numpy" "scipy" "scikit-learn" "ta-lib" "ta"
    "yfinance" "backtrader" "vectorbt" "optuna" "fastapi" "uvicorn"
    "pydantic" "python-multipart" "aiofiles" "asyncpg" "sqlalchemy"
    "alembic" "redis" "celery" "prometheus-client" "structlog"
    "python-json-logger" "pyportfolioopt" "riskfolio-lib" "quantlib"
    "arch" "statsmodels" "matplotlib" "seaborn" "plotly" "dash"
    "jupyter" "ipykernel" "bandit" "pre-commit" "alpha_vantage"
)

echo "🔍 Checking for globally installed trading packages..."

FOUND_PACKAGES=()
for package in "${PACKAGES[@]}"; do
    if pip show "$package" &>/dev/null; then
        echo "  ❌ Found: $package"
        FOUND_PACKAGES+=("$package")
    fi
done

if [ ${#FOUND_PACKAGES[@]} -eq 0 ]; then
    echo "✅ No trading-related packages found globally installed"
    exit 0
fi

echo ""
echo "Found ${#FOUND_PACKAGES[@]} packages installed globally."
read -p "Do you want to remove them? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Removing packages..."
    for package in "${FOUND_PACKAGES[@]}"; do
        echo "  Removing $package..."
        pip uninstall "$package" -y
    done
    echo "✅ Cleanup complete!"
else
    echo "ℹ️  Cleanup cancelled. Packages remain installed."
fi
```

### Windows Script

```batch
@echo off
REM cleanup_global_python.bat

echo 🧹 Python Global Package Cleanup
echo =================================

echo 🔍 Checking for globally installed trading packages...

set PACKAGES=nautilus_trader kafka-python psycopg2-binary clickhouse-driver duckdb pandas numpy scipy scikit-learn ta-lib ta yfinance backtrader vectorbt optuna fastapi uvicorn pydantic python-multipart aiofiles asyncpg sqlalchemy alembic redis celery prometheus-client structlog python-json-logger pyportfolioopt riskfolio-lib quantlib arch statsmodels matplotlib seaborn plotly dash jupyter ipykernel bandit pre-commit alpha_vantage

set FOUND_COUNT=0
for %%p in (%PACKAGES%) do (
    pip show %%p >nul 2>&1
    if not errorlevel 1 (
        echo   ❌ Found: %%p
        set /a FOUND_COUNT+=1
    )
)

if %FOUND_COUNT%==0 (
    echo ✅ No trading-related packages found globally installed
    pause
    exit /b 0
)

echo.
echo Found %FOUND_COUNT% packages installed globally.
set /p REMOVE="Do you want to remove them? (y/N): "

if /i "%REMOVE%"=="y" (
    echo 🗑️  Removing packages...
    for %%p in (%PACKAGES%) do (
        pip show %%p >nul 2>&1
        if not errorlevel 1 (
            echo   Removing %%p...
            pip uninstall %%p -y
        )
    )
    echo ✅ Cleanup complete!
) else (
    echo ℹ️  Cleanup cancelled. Packages remain installed.
)

pause
```

## Verification

After cleanup, verify that packages are removed:

```bash
# Check that no trading packages are installed globally
pip list | grep -E "(nautilus|kafka|pandas|numpy|fastapi)"

# Should return no results if cleanup was successful
```

## Best Practices Going Forward

1. **Always use virtual environments** for Python development
2. **Never install packages globally** unless they are system tools (like pip, virtualenv)
3. **Use the provided setup scripts** in this project:
   - Linux/Mac: `./scripts/setup_dev_env.sh`
   - Windows: `.\scripts\setup_dev_env.bat`
4. **Use Docker containers** for production deployments (already configured)

## Troubleshooting

### Permission Errors

If you get permission errors during cleanup:

```bash
# Linux/Mac - use sudo only if necessary
sudo pip uninstall package_name

# Windows - run Command Prompt as Administrator
```

### Package Not Found Errors

If pip says a package is not installed but you think it is:

```bash
# Check different Python installations
python -m pip list
python3 -m pip list
py -m pip list  # Windows

# Check conda environments if you use Anaconda
conda list
```

### Virtual Environment Confusion

If you're unsure whether you're in a virtual environment:

```bash
# Check if virtual environment is active
echo $VIRTUAL_ENV  # Linux/Mac (should be empty if not in venv)
echo %VIRTUAL_ENV%  # Windows (should be empty if not in venv)

# Check Python location
which python  # Linux/Mac
where python  # Windows
```

## Summary

- ✅ Configuration files in this project don't install packages automatically
- ✅ Use virtual environments for all development work
- ✅ Use Docker containers for production
- ✅ Clean up global packages if needed using this guide
- ✅ Always activate your virtual environment before working on the project

For questions or issues, refer to the main project documentation or create an issue in the project repository.