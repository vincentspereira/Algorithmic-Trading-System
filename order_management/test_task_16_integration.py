#!/usr/bin/env python3
"""
Integration Test for Task 16 Components
Tests WebSocket notifications, TCA, and Order Flow Analytics integration
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

# Import components to test
from websocket_notifications import (
    WebSocketNotificationServer, OrderNotificationManager,
    NotificationType, SubscriptionType
)
from transaction_cost_analysis import (
    TransactionCostAnalyzer, MarketDataPoint, ExecutionData, OrderData,
    BenchmarkType, ExecutionQuality
)
from order_flow_analytics import (
    OrderFlowAnalyzer, OrderFlowData, AnalyticsTimeframe, ReportType
)

class TestTask16Integration:
    """Integration tests for Task 16 components"""
    
    @pytest.mark.asyncio
    async def test_websocket_notification_system(self):
        """Test WebSocket notification system"""
        # Create WebSocket server
        websocket_server = WebSocketNotificationServer(host="localhost", port=8766)
        notification_manager = OrderNotificationManager(websocket_server)
        
        try:
            # Start server
            await websocket_server.start()
            
            # Test server stats
            stats = websocket_server.get_server_stats()
            assert stats['active_clients'] == 0
            assert stats['total_subscriptions'] == 0
            
            # Test notification creation and sending
            order_data = {
                'order_id': 'TEST_001',
                'symbol': 'EURUSD',
                'side': 'BUY',
                'quantity': '10000',
                'price': '1.1000',
                'account_id': 'ACCOUNT_001',
                'strategy_id': 'STRATEGY_001'
            }
            
            # Send various notifications
            await notification_manager.notify_order_submitted(order_data)
            await notification_manager.notify_order_accepted(order_data)
            
            execution_data = {
                'execution_id': 'EXEC_001',
                'quantity': '10000',
                'price': '1.1001',
                'venue': 'ECN_PRIMARY'
            }
            
            await notification_manager.notify_order_filled(order_data, execution_data)
            
            # Check notification history
            history = notification_manager.get_notification_history(limit=10)
            assert len(history) == 3
            assert history[0]['type'] == 'ORDER_SUBMITTED'
            assert history[1]['type'] == 'ORDER_ACCEPTED'
            assert history[2]['type'] == 'ORDER_FILLED'
            
            print("✓ WebSocket notification system test passed")
            
        finally:
            await websocket_server.stop()
    
    @pytest.mark.asyncio
    async def test_transaction_cost_analysis(self):
        """Test Transaction Cost Analysis system"""
        tca = TransactionCostAnalyzer()
        
        # Add market data
        market_data = MarketDataPoint(
            timestamp=datetime.now() - timedelta(minutes=5),
            symbol='EURUSD',
            bid_price=Decimal('1.0999'),
            ask_price=Decimal('1.1001'),
            mid_price=Decimal('1.1000'),
            volume=Decimal('1000000')
        )
        tca.add_market_data(market_data)
        
        # Add order data
        order_data = OrderData(
            order_id='TEST_001',
            symbol='EURUSD',
            side='BUY',
            original_quantity=Decimal('100000'),
            order_type='MARKET',
            arrival_time=datetime.now() - timedelta(minutes=5),
            decision_time=datetime.now() - timedelta(minutes=6)
        )
        tca.add_order_data(order_data)
        
        # Add execution data
        execution_data = ExecutionData(
            execution_id='EXEC_001',
            order_id='TEST_001',
            timestamp=datetime.now(),
            symbol='EURUSD',
            side='BUY',
            quantity=Decimal('100000'),
            price=Decimal('1.1002'),
            venue='ECN_PRIMARY',
            commission=Decimal('20.0')
        )
        tca.add_execution_data(execution_data)
        
        # Perform TCA analysis
        tca_result = await tca.analyze_order('TEST_001')
        
        assert tca_result is not None
        assert tca_result.order_id == 'TEST_001'
        assert tca_result.symbol == 'EURUSD'
        assert tca_result.total_quantity == Decimal('100000')
        assert tca_result.average_price == Decimal('1.1002')
        assert tca_result.total_commission == Decimal('20.0')
        assert tca_result.execution_quality in [q for q in ExecutionQuality]
        
        # Test aggregate statistics
        stats = tca.get_aggregate_statistics()
        assert stats['total_orders_analyzed'] == 1
        assert 'average_total_cost_bps' in stats
        
        # Test export report
        report = tca.export_tca_report(['TEST_001'])
        assert 'report_timestamp' in report
        assert 'individual_results' in report
        assert 'TEST_001' in report['individual_results']
        
        print("✓ Transaction Cost Analysis test passed")
    
    @pytest.mark.asyncio
    async def test_order_flow_analytics(self):
        """Test Order Flow Analytics system"""
        analyzer = OrderFlowAnalyzer()
        
        # Add sample order flow data
        order_flow_data = OrderFlowData(
            timestamp=datetime.now(),
            order_id='TEST_001',
            symbol='EURUSD',
            side='BUY',
            order_type='MARKET',
            quantity=Decimal('100000'),
            price=Decimal('1.1000'),
            filled_quantity=Decimal('100000'),
            average_fill_price=Decimal('1.1001'),
            venue='ECN_PRIMARY',
            algorithm='DIRECT',
            execution_time=timedelta(seconds=0.5),
            commission=Decimal('20.0'),
            market_impact_bps=Decimal('2.5'),
            account_id='ACCOUNT_001',
            strategy_id='STRATEGY_001',
            status='FILLED'
        )
        
        analyzer.add_order_flow_data(order_flow_data)
        
        # Add more sample data for better analytics
        for i in range(5):
            data = OrderFlowData(
                timestamp=datetime.now() - timedelta(minutes=i),
                order_id=f'TEST_{i+2:03d}',
                symbol='EURUSD',
                side='SELL' if i % 2 else 'BUY',
                order_type='LIMIT',
                quantity=Decimal('50000'),
                price=Decimal('1.1000'),
                filled_quantity=Decimal('50000'),
                average_fill_price=Decimal('1.0999'),
                venue='ECN_SECONDARY' if i % 2 else 'ECN_PRIMARY',
                algorithm='TWAP' if i % 2 else 'DIRECT',
                execution_time=timedelta(seconds=1.0 + i * 0.1),
                commission=Decimal('10.0'),
                market_impact_bps=Decimal('1.5'),
                account_id='ACCOUNT_001',
                strategy_id='STRATEGY_001',
                status='FILLED'
            )
            analyzer.add_order_flow_data(data)
        
        # Calculate analytics
        analytics = await analyzer.calculate_analytics(AnalyticsTimeframe.HOUR)
        
        assert analytics.total_orders == 6
        assert analytics.total_volume == Decimal('350000')  # 100k + 5*50k
        assert analytics.fill_rate > 0
        assert analytics.execution_quality_score > 0
        assert len(analytics.venue_distribution) == 2
        assert len(analytics.algorithm_distribution) == 2
        
        # Test different report types
        executive_report = await analyzer.generate_report(ReportType.EXECUTIVE_SUMMARY)
        assert executive_report['report_type'] == 'Executive Summary'
        assert 'key_metrics' in executive_report
        
        detailed_report = await analyzer.generate_report(ReportType.DETAILED_ANALYTICS)
        assert detailed_report['report_type'] == 'Detailed Analytics'
        assert 'volume_metrics' in detailed_report
        assert 'performance_metrics' in detailed_report
        
        venue_report = await analyzer.generate_report(ReportType.VENUE_ANALYSIS)
        assert venue_report['report_type'] == 'Venue Analysis'
        assert 'venue_distribution' in venue_report
        
        # Test real-time dashboard data
        dashboard_data = analyzer.get_real_time_dashboard_data()
        assert dashboard_data['order_count'] == 6
        assert 'total_volume' in dashboard_data
        assert 'active_venues' in dashboard_data
        
        print("✓ Order Flow Analytics test passed")
    
    @pytest.mark.asyncio
    async def test_integrated_workflow(self):
        """Test integrated workflow of all Task 16 components"""
        # Initialize all components
        websocket_server = WebSocketNotificationServer(host="localhost", port=8767)
        notification_manager = OrderNotificationManager(websocket_server)
        tca = TransactionCostAnalyzer()
        analyzer = OrderFlowAnalyzer()
        
        try:
            # Start WebSocket server
            await websocket_server.start()
            
            # Simulate order lifecycle with all components
            order_id = 'INTEGRATED_TEST_001'
            symbol = 'EURUSD'
            
            # 1. Order submission
            order_data = {
                'order_id': order_id,
                'symbol': symbol,
                'side': 'BUY',
                'quantity': '100000',
                'price': '1.1000',
                'account_id': 'ACCOUNT_001',
                'strategy_id': 'STRATEGY_001'
            }
            
            await notification_manager.notify_order_submitted(order_data)
            
            # 2. Add market data for TCA
            market_data = MarketDataPoint(
                timestamp=datetime.now() - timedelta(minutes=1),
                symbol=symbol,
                bid_price=Decimal('1.0999'),
                ask_price=Decimal('1.1001'),
                mid_price=Decimal('1.1000'),
                volume=Decimal('1000000')
            )
            tca.add_market_data(market_data)
            
            # 3. Add order data for TCA
            tca_order_data = OrderData(
                order_id=order_id,
                symbol=symbol,
                side='BUY',
                original_quantity=Decimal('100000'),
                order_type='MARKET',
                arrival_time=datetime.now() - timedelta(minutes=1),
                decision_time=datetime.now() - timedelta(minutes=2)
            )
            tca.add_order_data(tca_order_data)
            
            # 4. Order acceptance
            await notification_manager.notify_order_accepted(order_data)
            
            # 5. Order execution
            execution_data_dict = {
                'execution_id': 'EXEC_001',
                'quantity': '100000',
                'price': '1.1002',
                'venue': 'ECN_PRIMARY'
            }
            
            await notification_manager.notify_order_filled(order_data, execution_data_dict)
            
            # 6. Add execution data for TCA
            tca_execution_data = ExecutionData(
                execution_id='EXEC_001',
                order_id=order_id,
                timestamp=datetime.now(),
                symbol=symbol,
                side='BUY',
                quantity=Decimal('100000'),
                price=Decimal('1.1002'),
                venue='ECN_PRIMARY',
                commission=Decimal('20.0')
            )
            tca.add_execution_data(tca_execution_data)
            
            # 7. Add order flow data for analytics
            flow_data = OrderFlowData(
                timestamp=datetime.now(),
                order_id=order_id,
                symbol=symbol,
                side='BUY',
                order_type='MARKET',
                quantity=Decimal('100000'),
                price=Decimal('1.1000'),
                filled_quantity=Decimal('100000'),
                average_fill_price=Decimal('1.1002'),
                venue='ECN_PRIMARY',
                algorithm='DIRECT',
                execution_time=timedelta(seconds=0.5),
                commission=Decimal('20.0'),
                market_impact_bps=Decimal('2.0'),
                account_id='ACCOUNT_001',
                strategy_id='STRATEGY_001',
                status='FILLED'
            )
            analyzer.add_order_flow_data(flow_data)
            
            # 8. Perform TCA analysis
            tca_result = await tca.analyze_order(order_id)
            assert tca_result is not None
            assert tca_result.order_id == order_id
            
            # 9. Generate analytics report
            analytics_report = await analyzer.generate_report(ReportType.EXECUTIVE_SUMMARY)
            assert analytics_report['key_metrics']['total_orders'] == 1
            
            # 10. Check notification history
            notification_history = notification_manager.get_notification_history()
            assert len(notification_history) >= 3  # submitted, accepted, filled
            
            # 11. Verify all components have consistent data
            assert tca_result.symbol == symbol
            assert analytics_report['key_metrics']['total_orders'] == 1
            
            print("✓ Integrated workflow test passed")
            
        finally:
            await websocket_server.stop()
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self):
        """Test performance of all components under load"""
        # Initialize components
        tca = TransactionCostAnalyzer()
        analyzer = OrderFlowAnalyzer()
        
        # Generate load test data
        num_orders = 100
        start_time = time.time()
        
        # Add market data
        for i in range(10):
            market_data = MarketDataPoint(
                timestamp=datetime.now() - timedelta(minutes=i),
                symbol='EURUSD',
                bid_price=Decimal('1.0999') + Decimal(str(i * 0.0001)),
                ask_price=Decimal('1.1001') + Decimal(str(i * 0.0001)),
                mid_price=Decimal('1.1000') + Decimal(str(i * 0.0001)),
                volume=Decimal('1000000')
            )
            tca.add_market_data(market_data)
        
        # Process multiple orders
        for i in range(num_orders):
            order_id = f'LOAD_TEST_{i:03d}'
            
            # TCA order data
            order_data = OrderData(
                order_id=order_id,
                symbol='EURUSD',
                side='BUY' if i % 2 == 0 else 'SELL',
                original_quantity=Decimal('10000'),
                order_type='MARKET',
                arrival_time=datetime.now() - timedelta(seconds=i),
                decision_time=datetime.now() - timedelta(seconds=i+1)
            )
            tca.add_order_data(order_data)
            
            # TCA execution data
            execution_data = ExecutionData(
                execution_id=f'EXEC_{i:03d}',
                order_id=order_id,
                timestamp=datetime.now() - timedelta(seconds=i),
                symbol='EURUSD',
                side='BUY' if i % 2 == 0 else 'SELL',
                quantity=Decimal('10000'),
                price=Decimal('1.1000') + Decimal(str(i * 0.0001)),
                venue='ECN_PRIMARY' if i % 2 == 0 else 'ECN_SECONDARY',
                commission=Decimal('2.0')
            )
            tca.add_execution_data(execution_data)
            
            # Order flow data
            flow_data = OrderFlowData(
                timestamp=datetime.now() - timedelta(seconds=i),
                order_id=order_id,
                symbol='EURUSD',
                side='BUY' if i % 2 == 0 else 'SELL',
                order_type='MARKET',
                quantity=Decimal('10000'),
                price=Decimal('1.1000'),
                filled_quantity=Decimal('10000'),
                average_fill_price=Decimal('1.1000') + Decimal(str(i * 0.0001)),
                venue='ECN_PRIMARY' if i % 2 == 0 else 'ECN_SECONDARY',
                algorithm='DIRECT',
                execution_time=timedelta(milliseconds=500 + i * 10),
                commission=Decimal('2.0'),
                market_impact_bps=Decimal('1.0'),
                account_id='ACCOUNT_001',
                strategy_id='STRATEGY_001',
                status='FILLED'
            )
            analyzer.add_order_flow_data(flow_data)
        
        data_processing_time = time.time() - start_time
        
        # Perform analysis on all orders
        analysis_start_time = time.time()
        
        # TCA analysis for subset of orders
        tca_results = []
        for i in range(0, min(10, num_orders)):  # Analyze first 10 orders
            order_id = f'LOAD_TEST_{i:03d}'
            result = await tca.analyze_order(order_id)
            if result:
                tca_results.append(result)
        
        # Analytics calculation
        analytics = await analyzer.calculate_analytics(AnalyticsTimeframe.HOUR)
        
        analysis_time = time.time() - analysis_start_time
        total_time = time.time() - start_time
        
        # Performance assertions
        assert data_processing_time < 5.0  # Should process 100 orders in under 5 seconds
        assert analysis_time < 10.0  # Should analyze in under 10 seconds
        assert len(tca_results) > 0
        assert analytics.total_orders == num_orders
        
        # Performance metrics
        orders_per_second = num_orders / total_time
        
        print(f"✓ Performance test passed:")
        print(f"  - Processed {num_orders} orders in {total_time:.2f}s ({orders_per_second:.2f} orders/sec)")
        print(f"  - Data processing: {data_processing_time:.2f}s")
        print(f"  - Analysis time: {analysis_time:.2f}s")
        print(f"  - TCA results: {len(tca_results)} orders analyzed")
        print(f"  - Analytics: {analytics.total_orders} orders in analytics")

async def run_integration_tests():
    """Run all integration tests"""
    test_suite = TestTask16Integration()
    
    print("Running Task 16 Integration Tests...")
    print("=" * 50)
    
    try:
        await test_suite.test_websocket_notification_system()
        await test_suite.test_transaction_cost_analysis()
        await test_suite.test_order_flow_analytics()
        await test_suite.test_integrated_workflow()
        await test_suite.test_performance_under_load()
        
        print("=" * 50)
        print("🎉 All Task 16 integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_integration_tests())
    exit(0 if success else 1)