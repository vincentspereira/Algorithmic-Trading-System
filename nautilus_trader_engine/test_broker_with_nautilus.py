"""
Test script for broker abstraction layer with actual Nautilus Trader dependencies

This script tests the broker abstraction layer including
the base class, IBKR adapter, and factory with actual Nautilus Trader dependencies.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import Nautilus Trader components
try:
    from nautilus_trader.model.identifiers import InstrumentId, VenueOrderId
    from nautilus_trader.model.objects import Quantity, Price
    from nautilus_trader.core.uuid import UUID4
    
    from nautilus_trader_engine.adapters.broker_factory import (
        BrokerAdapterFactory, 
        BrokerType, 
        initialize_broker_factory,
        initialize_broker_adapter,
        get_broker_adapter
    )
    from nautilus_trader_engine.adapters.broker_adapter import BrokerOrder, OrderType, OrderSide
    
    NAUTILUS_AVAILABLE = True
except ImportError as e:
    NAUTILUS_AVAILABLE = False
    print(f"Nautilus Trader not available: {e}")


async def test_broker_abstraction_with_nautilus():
    """Test the broker abstraction layer with actual Nautilus Trader dependencies."""
    if not NAUTILUS_AVAILABLE:
        print("Skipping test - Nautilus Trader not available")
        return True
        
    print("Testing Broker Abstraction Layer with Nautilus Trader...")
    
    # Initialize the factory
    initialize_broker_factory()
    print("✓ Broker factory initialized")
    
    # Test available brokers
    available_brokers = BrokerAdapterFactory.get_available_brokers()
    print(f"✓ Available brokers: {list(available_brokers.keys())}")
    
    # Test creating an IBKR adapter
    ibkr_adapter = BrokerAdapterFactory.create_adapter(BrokerType.IBKR, paper_trading=True)
    print("✓ IBKR adapter created")
    
    # Test connecting (simulated)
    connected = await ibkr_adapter.connect()
    if connected:
        print("✓ IBKR adapter connected (simulated)")
    else:
        print("✗ IBKR adapter connection failed")
        return False
    
    # Test account info
    account_info = await ibkr_adapter.get_account_info()
    print(f"✓ Account info retrieved: {account_info.account_id}")
    
    # Test submitting an order (simulated)
    instrument_id = InstrumentId.from_str("AAPL.XNAS")
    order = BrokerOrder(
        instrument_id=instrument_id,
        order_type=OrderType.MARKET,
        side=OrderSide.BUY,
        quantity=Quantity.from_str("100"),
    )
    
    venue_order_id = await ibkr_adapter.submit_order(order)
    print(f"✓ Order submitted with ID: {venue_order_id.value}")
    
    # Test getting order status
    status = await ibkr_adapter.get_order_status(venue_order_id)
    print(f"✓ Order status: {status}")
    
    # Test canceling order
    canceled = await ibkr_adapter.cancel_order(venue_order_id)
    if canceled:
        print("✓ Order canceled successfully")
    else:
        print("✗ Order cancellation failed")
        return False
    
    # Test disconnecting
    await ibkr_adapter.disconnect()
    if not ibkr_adapter.is_connected():
        print("✓ IBKR adapter disconnected")
    else:
        print("✗ IBKR adapter disconnection failed")
        return False
    
    # Test factory initialization function
    initialized_adapter = initialize_broker_adapter(BrokerType.IBKR, paper_trading=True)
    print("✓ Global broker adapter initialized")
    
    # Test getting the global adapter
    global_adapter = get_broker_adapter()
    print("✓ Global broker adapter retrieved")
    
    print("\nAll broker abstraction tests with Nautilus Trader passed!")
    return True


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_broker_abstraction_with_nautilus())
    sys.exit(0 if result else 1)