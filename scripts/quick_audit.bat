@echo off
echo ========================================
echo Python Package Quick Audit - Windows
echo ========================================
echo.

echo Creating backup directory...
if not exist "backups" mkdir backups

echo.
echo [1/5] Creating package backup...
python -m pip freeze > backups\backup_requirements_%date:~-4,4%%date:~-10,2%%date:~-7,2%.txt
echo ✅ Requirements backup created

echo.
echo [2/5] Listing all installed packages...
python -m pip list

echo.
echo [3/5] Checking for outdated packages...
python -m pip list --outdated

echo.
echo [4/5] Checking package dependencies...
python -m pip check

echo.
echo [5/5] Showing Python installation info...
python -c "import sys, platform; print(f'Python: {sys.version}'); print(f'Platform: {platform.system()}'); print(f'Executable: {sys.executable}')"

echo.
echo ========================================
echo Audit Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Review the package lists above
echo 2. Run: python scripts\cleanup_global_packages.py
echo 3. Or manually remove packages: python -m pip uninstall package_name
echo.
echo Your backup is saved in: backups\backup_requirements_%date:~-4,4%%date:~-10,2%%date:~-7,2%.txt
echo.
pause