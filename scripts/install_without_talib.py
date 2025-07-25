#!/usr/bin/env python3
"""
Install Dependencies Without TA-Lib Script

This script installs all required dependencies except TA-Lib, allowing users
to proceed with testing while addressing the TA-Lib installation issue separately.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    print(f"Running: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed")
        print(f"Error: {e.stderr.strip()}")
        return False

def read_requirements():
    """Read and filter requirements.txt"""
    script_dir = Path(__file__).parent
    req_file = script_dir.parent / "nautilus_trader_engine" / "requirements.txt"
    
    if not req_file.exists():
        print(f"Error: requirements.txt not found at {req_file}")
        return []
    
    requirements = []
    with open(req_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines, comments, and ta-lib
            if line and not line.startswith('#') and 'ta-lib' not in line.lower():
                requirements.append(line)
    
    return requirements

def install_requirements():
    """Install filtered requirements"""
    requirements = read_requirements()
    
    if not requirements:
        print("No requirements to install")
        return False
    
    print(f"Found {len(requirements)} packages to install (excluding TA-Lib)")
    print("Packages to install:")
    for req in requirements:
        print(f"  - {req}")
    
    # Create temporary requirements file
    temp_req_file = "temp_requirements_no_talib.txt"
    
    try:
        with open(temp_req_file, 'w') as f:
            f.write('\n'.join(requirements))
        
        # Install packages
        success = run_command(
            f"pip install -r {temp_req_file}",
            "Installing packages"
        )
        
        return success
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_req_file):
            os.remove(temp_req_file)

def test_imports():
    """Test critical imports"""
    print("\nTesting critical imports...")
    
    critical_imports = [
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('yfinance', 'yfinance'),
        ('backtrader', 'backtrader'),
        ('fastapi', 'FastAPI'),
        ('ta', 'ta library (TA-Lib alternative)')
    ]
    
    failed_imports = []
    
    for module, description in critical_imports:
        try:
            __import__(module)
            print(f"✓ {description}")
        except ImportError as e:
            print(f"✗ {description}: {e}")
            failed_imports.append(description)
    
    return len(failed_imports) == 0

def main():
    """Main installation function"""
    print("=" * 70)
    print("ALGORITHMIC TRADING SYSTEM - DEPENDENCY INSTALLER")
    print("Installing all dependencies except TA-Lib")
    print("=" * 70)
    
    # Check Python version
    python_version = sys.version_info
    print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 8):
        print("Warning: Python 3.8+ is recommended")
    
    # Upgrade pip first
    print("\nUpgrading pip...")
    run_command("python -m pip install --upgrade pip", "Pip upgrade")
    
    # Install requirements
    if install_requirements():
        print("\n" + "=" * 50)
        print("INSTALLATION COMPLETED SUCCESSFULLY")
        print("=" * 50)
        
        # Test imports
        if test_imports():
            print("\n✓ All critical packages imported successfully")
            print("\nYou can now run the backtesting scripts:")
            print("  python nautilus_trader_engine/run_initial_backtest.py")
            print("\nFor TA-Lib installation, see:")
            print("  nautilus_trader_engine/TALIB_INSTALLATION.md")
        else:
            print("\n⚠️  Some imports failed. Check the errors above.")
            
    else:
        print("\n" + "=" * 50)
        print("INSTALLATION FAILED")
        print("=" * 50)
        print("Some packages failed to install. Check the errors above.")
        return 1
    
    print("\n" + "=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print("1. Test the system: python nautilus_trader_engine/run_initial_backtest.py")
    print("2. Install TA-Lib (optional): See TALIB_INSTALLATION.md")
    print("3. Use Docker for full setup: docker-compose up --build")
    print("4. The system will use 'ta' library as TA-Lib fallback")
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInstallation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)