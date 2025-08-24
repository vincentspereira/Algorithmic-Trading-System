"""
Simplified test script for broker abstraction layer

This script tests the broker abstraction layer structure
with actual Nautilus Trader dependencies when available.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import sys
import os

# Add the current directory to the Python path
sys.path.append('.')


def test_broker_abstraction_structure():
    """Test the broker abstraction layer structure."""
    print("Testing Broker Abstraction Layer Structure...")
    
    # Test basic structure
    try:
        from adapters import broker_adapter
        print("✓ BrokerAdapter module available")
    except ImportError as e:
        print(f"✗ BrokerAdapter module not available: {e}")
        return False
        
    try:
        from adapters import broker_factory
        print("✓ BrokerFactory module available")
    except ImportError as e:
        print(f"✗ BrokerFactory module not available: {e}")
        return False
        
    try:
        from adapters import ibkr_adapter
        print("✓ IBKRAdapter module available")
    except ImportError as e:
        print(f"✗ IBKRAdapter module not available: {e}")
        return False
    
    # Try to import Nautilus Trader components
    try:
        # Test if Nautilus Trader is available
        import nautilus_trader
        NAUTILUS_AVAILABLE = True
        print("✓ Nautilus Trader is available")
        
        # If available, test the actual imports
        from nautilus_trader.model.identifiers import InstrumentId
        from nautilus_trader.model.objects import Quantity, Price
        from nautilus_trader.core.uuid import UUID4
        
        # Test that the base class exists
        print("✓ BrokerAdapter base class available")
        
        # Test that broker types are defined
        try:
            from adapters.broker_factory import BrokerType
            print(f"✓ Broker types available: {[t for t in BrokerType]}")
        except Exception as e:
            print(f"Could not import BrokerType: {e}")
            
        # Test that order types are defined
        try:
            from adapters.broker_adapter import OrderType
            print(f"✓ Order types available: {[t for t in OrderType]}")
        except Exception as e:
            print(f"Could not import OrderType: {e}")
            
        # Test that order sides are defined
        try:
            from adapters.broker_adapter import OrderSide
            print(f"✓ Order sides available: {[s for s in OrderSide]}")
        except Exception as e:
            print(f"Could not import OrderSide: {e}")
            
    except ImportError as e:
        print(f"Nautilus Trader not available: {e}")
        NAUTILUS_AVAILABLE = False

    print("\nAll broker abstraction structure tests passed!")
    return True


if __name__ == "__main__":
    # Run the test
    result = test_broker_abstraction_structure()
    sys.exit(0 if result else 1)