#!/bin/bash

echo "========================================"
echo "Python Package Quick Audit - Linux/Mac"
echo "========================================"
echo

# Create backup directory
echo "Creating backup directory..."
mkdir -p backups

echo
echo "[1/5] Creating package backup..."
python3 -m pip freeze > "backups/backup_requirements_$(date +%Y%m%d_%H%M%S).txt"
echo "✅ Requirements backup created"

echo
echo "[2/5] Listing all installed packages..."
python3 -m pip list

echo
echo "[3/5] Checking for outdated packages..."
python3 -m pip list --outdated

echo
echo "[4/5] Checking package dependencies..."
python3 -m pip check

echo
echo "[5/5] Showing Python installation info..."
python3 -c "
import sys, platform
print(f'Python: {sys.version}')
print(f'Platform: {platform.system()} {platform.release()}')
print(f'Executable: {sys.executable}')
"

echo
echo "========================================"
echo "Audit Complete!"
echo "========================================"
echo
echo "Next steps:"
echo "1. Review the package lists above"
echo "2. Run: python3 scripts/cleanup_global_packages.py"
echo "3. Or manually remove packages: python3 -m pip uninstall package_name"
echo
echo "Your backup is saved in: backups/backup_requirements_$(date +%Y%m%d_%H%M%S).txt"
echo

read -p "Press Enter to continue..."