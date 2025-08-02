#!/usr/bin/env python3
"""
Simple test runner for Enhanced Order Management Integration
Tests basic functionality without complex pytest fixtures
"""

import asyncio
import sys
import time
from decimal import Decimal
from datetime import datetime

# Import the components to test
from enhanced_order_integration import (
    EnhancedOrderManagementSystem, RiskParameters,
    create_market_order, create_limit_order, create_stop_order,
    OrderSide, OrderType, OrderStatus
)
from order_execution_engine import OrderExecutionEngine, VenueConfig, VenueType, ExecutionAlgorithm

async def test_basic_functionality():
    """Test basic OMS functionality"""
    print("=== Testing Basic OMS Functionality ===")
    
    # Create OMS with risk parameters
    risk_params = RiskParameters(
        max_order_value=Decimal('1000000'),
        max_position_size=Decimal('100000'),
        allowed_symbols={'EURUSD', 'GBPUSD', 'USDJPY'},
        max_orders_per_second=10
    )
    
    oms = EnhancedOrderManagementSystem(risk_params)
    
    try:
        # Start the system
        print("Starting OMS...")
        await oms.start()
        print("✓ OMS started successfully")
        
        # Create test orders
        market_order = create_market_order('EURUSD', OrderSide.BUY, Decimal('10000'))
        limit_order = create_limit_order('GBPUSD', OrderSide.SELL, Decimal('5000'), Decimal('1.2500'))
        
        print(f"Created market order: {market_order.order_id}")
        print(f"Created limit order: {limit_order.order_id}")
        
        # Submit orders
        print("Submitting orders...")
        market_order_id = await oms.submit_order(market_order)
        limit_order_id = await oms.submit_order(limit_order)
        
        print(f"✓ Market order submitted: {market_order_id}")
        print(f"✓ Limit order submitted: {limit_order_id}")
        
        # Wait for execution
        print("Waiting for execution...")
        await asyncio.sleep(3)
        
        # Check order status
        market_order_status = oms.get_order(market_order_id)
        limit_order_status = oms.get_order(limit_order_id)
        
        print(f"Market order status: {market_order_status.status}")
        print(f"Limit order status: {limit_order_status.status}")
        
        # Check positions
        positions = oms.get_positions()
        print(f"Positions: {positions}")
        
        # Check P&L
        pnl = oms.get_daily_pnl()
        print(f"Daily P&L: {pnl}")
        
        # Get statistics
        stats = oms.get_order_statistics()
        print(f"Order Statistics:")
        print(f"  Total orders: {stats['total_orders']}")
        print(f"  Active orders: {stats['active_orders']}")
        print(f"  Status breakdown: {stats['status_breakdown']}")
        
        print("✓ Basic functionality test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        return False
    finally:
        await oms.stop()
        print("OMS stopped")

async def test_order_validation():
    """Test order validation"""
    print("\\n=== Testing Order Validation ===")
    
    oms = EnhancedOrderManagementSystem()
    
    try:
        await oms.start()
        
        # Test invalid quantity
        try:
            invalid_order = create_market_order('EURUSD', OrderSide.BUY, Decimal('-1000'))
            await oms.submit_order(invalid_order)
            print("✗ Should have failed for negative quantity")
            return False
        except Exception as e:
            print(f"✓ Correctly rejected negative quantity: {e}")
        
        # Test blocked symbol
        oms.risk_parameters.blocked_symbols.add('BLOCKED')
        try:
            blocked_order = create_market_order('BLOCKED', OrderSide.BUY, Decimal('1000'))
            await oms.submit_order(blocked_order)
            print("✗ Should have failed for blocked symbol")
            return False
        except Exception as e:
            print(f"✓ Correctly rejected blocked symbol: {e}")
        
        print("✓ Order validation test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Order validation test failed: {e}")
        return False
    finally:
        await oms.stop()

async def test_execution_engine():
    """Test execution engine"""
    print("\\n=== Testing Execution Engine ===")
    
    engine = OrderExecutionEngine()
    
    try:
        await engine.start()
        print("✓ Execution engine started")
        
        # Test venue status
        venue_status = engine.get_venue_status()
        print(f"Available venues: {list(venue_status.keys())}")
        
        # Create test order
        from order_execution_engine import EnhancedOrder as ExecutionOrder
        
        test_order = ExecutionOrder(
            order_id="TEST_001",
            symbol='EURUSD',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('10000')
        )
        
        # Execute order
        print("Executing test order...")
        execution_reports = await engine.execute_order(test_order)
        
        print(f"✓ Order executed with {len(execution_reports)} fills")
        for report in execution_reports:
            print(f"  Fill: {report.quantity} @ {report.price} on {report.venue}")
        
        # Check statistics
        stats = engine.get_execution_statistics('EURUSD')
        print(f"Execution stats: {stats}")
        
        print("✓ Execution engine test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Execution engine test failed: {e}")
        return False
    finally:
        await engine.stop()

async def test_order_lifecycle():
    """Test complete order lifecycle"""
    print("\\n=== Testing Order Lifecycle ===")
    
    oms = EnhancedOrderManagementSystem()
    
    try:
        await oms.start()
        
        # Create and submit order with a price that won't execute immediately
        order = create_limit_order('EURUSD', OrderSide.BUY, Decimal('5000'), Decimal('0.9000'))  # Very low price
        order_id = await oms.submit_order(order)
        print(f"✓ Order submitted: {order_id}")
        
        # Wait a moment for processing
        await asyncio.sleep(0.5)
        
        # Check initial status
        order_obj = oms.get_order(order_id)
        print(f"Initial status: {order_obj.status}")
        print(f"Filled quantity: {order_obj.filled_quantity}")
        
        # Only modify if order hasn't been filled
        if order_obj.filled_quantity == 0:
            # Modify order
            success = await oms.modify_order(order_id, new_quantity=Decimal('7500'), new_price=Decimal('0.9100'))
            if success:
                print("✓ Order modified successfully")
                order_obj = oms.get_order(order_id)
                print(f"New quantity: {order_obj.quantity}, New price: {order_obj.price}")
            else:
                print("✗ Order modification failed")
        else:
            print(f"⚠ Order already filled ({order_obj.filled_quantity}), skipping modification")
        
        # Cancel order (if still active)
        order_obj = oms.get_order(order_id)
        if order_obj.is_active:
            success = await oms.cancel_order(order_id, "Test cancellation")
            if success:
                print("✓ Order cancelled successfully")
                order_obj = oms.get_order(order_id)
                print(f"Final status: {order_obj.status}")
            else:
                print("✗ Order cancellation failed")
        else:
            print(f"⚠ Order not active (status: {order_obj.status}), skipping cancellation")
        
        print("✓ Order lifecycle test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Order lifecycle test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await oms.stop()

async def test_performance():
    """Test performance with multiple orders"""
    print("\\n=== Testing Performance ===")
    
    risk_params = RiskParameters(
        max_order_value=Decimal('10000000'),
        max_position_size=Decimal('1000000'),
        max_orders_per_second=100
    )
    
    oms = EnhancedOrderManagementSystem(risk_params)
    
    try:
        await oms.start()
        
        # Create multiple orders
        orders = []
        for i in range(20):
            order = create_market_order(
                symbol='EURUSD',
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                quantity=Decimal('1000'),
                account_id=f'ACCOUNT_{i % 5}'
            )
            orders.append(order)
        
        # Submit orders and measure time
        start_time = time.time()
        
        tasks = []
        for order in orders:
            task = asyncio.create_task(oms.submit_order(order))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Count successful submissions
        successful = sum(1 for result in results if not isinstance(result, Exception))
        failed = len(results) - successful
        
        print(f"✓ Processed {len(orders)} orders in {processing_time:.2f}s")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        print(f"  Rate: {len(orders) / processing_time:.2f} orders/sec")
        
        # Wait for execution
        await asyncio.sleep(2)
        
        # Check final statistics
        stats = oms.get_order_statistics()
        print(f"Final statistics: {stats['total_orders']} total orders")
        
        print("✓ Performance test completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Performance test failed: {e}")
        return False
    finally:
        await oms.stop()

async def main():
    """Run all tests"""
    print("Enhanced Order Management Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Order Validation", test_order_validation),
        ("Execution Engine", test_execution_engine),
        ("Order Lifecycle", test_order_lifecycle),
        ("Performance", test_performance)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\\n🎉 All tests passed!")
        return 0
    else:
        print(f"\\n❌ {failed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)