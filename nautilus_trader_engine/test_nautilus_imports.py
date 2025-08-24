"""
Test script to verify Nautilus Trader imports

This script tests that all required Nautilus Trader components
can be imported correctly.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_nautilus_imports():
    """Test that all required Nautilus Trader components can be imported."""
    print("Testing Nautilus Trader imports...")
    
    # Test core imports
    try:
        from nautilus_trader.model.orders import Order
        print("✓ nautilus_trader.model.orders.Order imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import nautilus_trader.model.orders.Order: {e}")
        return False
    
    # Test identifiers imports
    try:
        from nautilus_trader.model.identifiers import InstrumentId, VenueOrderId, AccountId
        print("✓ nautilus_trader.model.identifiers imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import nautilus_trader.model.identifiers: {e}")
        return False
    
    # Test objects imports
    try:
        from nautilus_trader.model.objects import Quantity, Price
        print("✓ nautilus_trader.model.objects imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import nautilus_trader.model.objects: {e}")
        return False
    
    # Test UUID imports
    try:
        from nautilus_trader.core.uuid import UUID4
        print("✓ nautilus_trader.core.uuid imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import nautilus_trader.core.uuid: {e}")
        return False
    
    print("\nAll Nautilus Trader imports successful!")
    return True

if __name__ == "__main__":
    # Run the test
    result = test_nautilus_imports()
    sys.exit(0 if result else 1)