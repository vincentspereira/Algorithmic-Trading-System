#!/usr/bin/env python3
"""
Complete Task 16 Integration Test
Tests the fully integrated Enhanced Order Management System with all Task 16 components
"""

import asyncio
import time
from datetime import datetime, timedelta
from decimal import Decimal

from enhanced_order_integration import (
    EnhancedOrderManagementSystem, RiskParameters,
    create_market_order, create_limit_order, OrderSide
)
from order_flow_analytics import AnalyticsTimeframe, ReportType

async def test_complete_task_16_integration():
    """Test complete Task 16 integration"""
    print("Testing Complete Task 16 Integration")
    print("=" * 50)
    
    # Initialize system with all components
    risk_params = RiskParameters(
        max_order_value=Decimal('1000000'),
        max_position_size=Decimal('100000'),
        allowed_symbols={'EURUSD', 'GBPUSD', 'USDJPY'},
        max_orders_per_second=50  # Higher limit for performance testing
    )
    
    oms = EnhancedOrderManagementSystem(risk_params, websocket_port=8768)
    
    try:
        # Start the complete system
        print("Starting Enhanced OMS with all Task 16 components...")
        await oms.start()
        
        # Check WebSocket server is running
        ws_stats = oms.get_websocket_stats()
        print(f"✓ WebSocket server started: {ws_stats['active_clients']} clients")
        
        # Test 1: Order submission with notifications
        print("\\n1. Testing order submission with notifications...")
        market_order = create_market_order('EURUSD', OrderSide.BUY, Decimal('10000'))
        order_id = await oms.submit_order(market_order)
        print(f"✓ Order submitted: {order_id}")
        
        # Wait for execution
        await asyncio.sleep(2)
        
        # Check order status
        order = oms.get_order(order_id)
        print(f"✓ Order status: {order.status}")
        
        # Test 2: Check notifications were sent
        print("\\n2. Testing notification system...")
        notification_history = oms.get_notification_history(limit=5)
        print(f"✓ Notifications sent: {len(notification_history)}")
        for notification in notification_history:
            print(f"  - {notification['type']}: {notification['data'].get('order_id', 'N/A')}")
        
        # Test 3: TCA Analysis
        print("\\n3. Testing Transaction Cost Analysis...")
        tca_result = await oms.get_tca_analysis(order_id)
        if tca_result:
            print(f"✓ TCA Analysis completed:")
            print(f"  - Total Cost: {tca_result.total_cost_bps:.2f} bps")
            print(f"  - Market Impact: {tca_result.market_impact_bps:.2f} bps")
            print(f"  - Execution Quality: {tca_result.execution_quality.value}")
        else:
            print("⚠ TCA Analysis not available (order may not be fully executed)")
        
        # Test 4: Submit more orders for analytics
        print("\\n4. Submitting additional orders for analytics...")
        orders = []
        for i in range(5):
            if i % 2 == 0:
                order = create_market_order('EURUSD', OrderSide.BUY, Decimal('5000'))
            else:
                order = create_limit_order('GBPUSD', OrderSide.SELL, Decimal('3000'), Decimal('1.2500'))
            
            order_id = await oms.submit_order(order)
            orders.append(order_id)
            await asyncio.sleep(0.5)  # Small delay between orders
        
        print(f"✓ Submitted {len(orders)} additional orders")
        
        # Wait for executions
        await asyncio.sleep(3)
        
        # Test 5: Order Flow Analytics
        print("\\n5. Testing Order Flow Analytics...")
        analytics = await oms.get_flow_analytics(AnalyticsTimeframe.HOUR)
        print(f"✓ Analytics calculated:")
        print(f"  - Total Orders: {analytics.total_orders}")
        print(f"  - Total Volume: {analytics.total_volume}")
        print(f"  - Fill Rate: {analytics.fill_rate:.2%}")
        print(f"  - Execution Quality Score: {analytics.execution_quality_score}")
        print(f"  - Venue Distribution: {len(analytics.venue_distribution)} venues")
        
        # Test 6: Generate Reports
        print("\\n6. Testing Report Generation...")
        
        # Executive Summary
        exec_report = await oms.generate_analytics_report(ReportType.EXECUTIVE_SUMMARY)
        print(f"✓ Executive Summary generated:")
        print(f"  - Period: {exec_report['period']}")
        print(f"  - Total Orders: {exec_report['key_metrics']['total_orders']}")
        print(f"  - Quality Score: {exec_report['key_metrics']['execution_quality_score']}")
        
        # Detailed Analytics
        detailed_report = await oms.generate_analytics_report(ReportType.DETAILED_ANALYTICS)
        print(f"✓ Detailed Analytics generated with {len(detailed_report)} sections")
        
        # Venue Analysis
        venue_report = await oms.generate_analytics_report(ReportType.VENUE_ANALYSIS)
        print(f"✓ Venue Analysis generated")
        
        # Test 7: System Statistics
        print("\\n7. Testing System Statistics...")
        order_stats = oms.get_order_statistics()
        print(f"✓ Order Statistics:")
        print(f"  - Total Orders: {order_stats['total_orders']}")
        print(f"  - Active Orders: {order_stats['active_orders']}")
        print(f"  - Status Breakdown: {order_stats['status_breakdown']}")
        
        ws_stats = oms.get_websocket_stats()
        print(f"✓ WebSocket Statistics:")
        print(f"  - Active Clients: {ws_stats['active_clients']}")
        print(f"  - Message Queue Size: {ws_stats['message_queue_size']}")
        
        # Test 8: Position and P&L Tracking
        print("\\n8. Testing Position and P&L Tracking...")
        positions = oms.get_positions()
        pnl = oms.get_daily_pnl()
        print(f"✓ Positions: {positions}")
        print(f"✓ Daily P&L: {pnl}")
        
        # Test 9: Order Lifecycle Operations
        print("\\n9. Testing Order Lifecycle Operations...")
        
        # Create a limit order for modification/cancellation
        limit_order = create_limit_order('EURUSD', OrderSide.BUY, Decimal('5000'), Decimal('1.0900'))
        limit_order_id = await oms.submit_order(limit_order)
        
        await asyncio.sleep(1)
        
        # Modify order
        modify_success = await oms.modify_order(limit_order_id, new_quantity=Decimal('7500'))
        print(f"✓ Order modification: {'Success' if modify_success else 'Failed'}")
        
        # Cancel order
        cancel_success = await oms.cancel_order(limit_order_id, "Test cancellation")
        print(f"✓ Order cancellation: {'Success' if cancel_success else 'Failed'}")
        
        # Test 10: Performance Validation
        print("\\n10. Testing Performance...")
        start_time = time.time()
        
        # Submit multiple orders quickly
        performance_orders = []
        for i in range(20):
            order = create_market_order('EURUSD', OrderSide.BUY, Decimal('1000'))
            order_id = await oms.submit_order(order)
            performance_orders.append(order_id)
        
        processing_time = time.time() - start_time
        orders_per_second = len(performance_orders) / processing_time
        
        print(f"✓ Performance Test:")
        print(f"  - Processed {len(performance_orders)} orders in {processing_time:.2f}s")
        print(f"  - Rate: {orders_per_second:.2f} orders/sec")
        
        # Final validation
        print("\\n" + "=" * 50)
        print("TASK 16 INTEGRATION VALIDATION")
        print("=" * 50)
        
        # Check all components are working
        final_stats = oms.get_order_statistics()
        final_notifications = oms.get_notification_history(limit=1)
        final_analytics = await oms.get_flow_analytics(AnalyticsTimeframe.HOUR)
        
        validations = [
            ("Order Management", final_stats['total_orders'] > 0),
            ("WebSocket Notifications", len(final_notifications) > 0),
            ("Order Flow Analytics", final_analytics.total_orders > 0),
            ("Position Tracking", len(oms.get_positions()) > 0),
            ("P&L Tracking", len(oms.get_daily_pnl()) > 0),
            ("Venue Integration", len(final_stats.get('venue_status', {})) > 0),
            ("Performance", orders_per_second > 50)  # Should handle 50+ orders/sec
        ]
        
        all_passed = True
        for component, passed in validations:
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{component:.<30} {status}")
            if not passed:
                all_passed = False
        
        print("=" * 50)
        if all_passed:
            print("🎉 ALL TASK 16 COMPONENTS VALIDATED SUCCESSFULLY!")
            print("✅ Task 16.1: Order Lifecycle Management Implementation - COMPLETE")
            print("✅ Task 16.2: Advanced OMS Integration - COMPLETE")
            print("✅ Task 16: Enhanced Order Management Integration - COMPLETE")
        else:
            print("❌ Some components failed validation")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await oms.stop()
        print("\\nSystem stopped successfully")

async def main():
    """Run the complete Task 16 integration test"""
    success = await test_complete_task_16_integration()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)