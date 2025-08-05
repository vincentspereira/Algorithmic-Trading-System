"""
Direct test for Order Management System without imports
"""

import asyncio
import sys
import os
sys.path.append('.')

# Import directly from the module
from nautilus_trader_engine.trading.order_management import (
    OrderLifecycleManager, Order, OrderFill, OrderType, OrderStatus, 
    OrderSide, TimeInForce
)
from datetime import datetime


async def test_order_management():
    """Test basic order management functionality"""
    print("Testing Order Lifecycle Management System...")
    
    # Initialize order manager
    manager = OrderLifecycleManager(enable_tca=True, enable_notifications=True)
    await manager.start()
    
    try:
        # Create a test order
        order = Order(
            order_id="test_001",
            client_order_id="client_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100.0,
            price=150.0,
            time_in_force=TimeInForce.DAY,
            strategy_id="test_strategy"
        )
        
        print(f"Creating order: {order.order_id}")
        order_id = await manager.create_order(order)
        print(f"✓ Order created successfully: {order_id}")
        
        # Update order status
        print("Updating order status to SUBMITTED...")
        await manager.update_order_status(order_id, OrderStatus.SUBMITTED)
        print("✓ Order status updated")
        
        # Add a fill
        print("Adding fill to order...")
        fill = OrderFill(
            fill_id="fill_001",
            order_id=order_id,
            quantity=50.0,
            price=149.5,
            timestamp=datetime.now(),
            venue="NASDAQ"
        )
        
        await manager.add_fill(order_id, fill)
        print("✓ Fill added successfully")
        
        # Check order state
        updated_order = manager.get_order(order_id)
        print(f"Order status: {updated_order.status}")
        print(f"Filled quantity: {updated_order.filled_quantity}")
        print(f"Remaining quantity: {updated_order.remaining_quantity}")
        print(f"Average fill price: {updated_order.average_fill_price}")
        
        # Test order modification
        print("Modifying order quantity...")
        success = await manager.modify_order(order_id, "quantity", 200.0, "Increase size")
        if success:
            print("✓ Order modified successfully")
        
        # Get metrics
        metrics = manager.get_metrics()
        print(f"System metrics: {metrics}")
        
        print("\n✅ Order Lifecycle Management System test completed successfully!")
        
    finally:
        await manager.stop()


if __name__ == "__main__":
    asyncio.run(test_order_management())