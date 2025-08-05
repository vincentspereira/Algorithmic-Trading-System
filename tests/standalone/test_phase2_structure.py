"""
Test script to validate Phase 2 API structure
"""

import os
import sys

def test_api_structure():
    """Test that all required files and directories exist"""
    
    base_path = "nautilus_trader_engine/api"
    
    required_files = [
        "nautilus_trader_engine/api/__init__.py",
        "nautilus_trader_engine/api/main.py",
        "nautilus_trader_engine/api/core/__init__.py",
        "nautilus_trader_engine/api/core/config.py",
        "nautilus_trader_engine/api/core/security.py",
        "nautilus_trader_engine/api/auth/__init__.py",
        "nautilus_trader_engine/api/auth/dependencies.py",
        "nautilus_trader_engine/api/models/__init__.py",
        "nautilus_trader_engine/api/models/auth.py",
        "nautilus_trader_engine/api/models/backtest.py",
        "nautilus_trader_engine/api/routers/__init__.py",
        "nautilus_trader_engine/api/routers/auth.py",
        "nautilus_trader_engine/api/routers/backtest.py"
    ]
    
    print("Testing Phase 2 API Structure...")
    print("=" * 50)
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} - MISSING")
            all_exist = False
    
    print("\n" + "=" * 50)
    if all_exist:
        print("✓ All required files exist!")
        print("\nPhase 2 API structure is complete.")
        print("\nTo run the API:")
        print("1. Install dependencies: pip install -r nautilus_trader_engine/requirements.txt")
        print("2. Run the API: python -m nautilus_trader_engine.api.main")
        print("3. Access docs at: http://localhost:8001/docs")
        print("\nDemo credentials:")
        print("- Username: demo, Password: demo123")
        print("- Username: admin, Password: admin123")
        return True
    else:
        print("✗ Some files are missing!")
        return False

if __name__ == "__main__":
    success = test_api_structure()
    sys.exit(0 if success else 1)