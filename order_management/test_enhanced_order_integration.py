#!/usr/bin/env python3
"""
Comprehensive Test Suite for Enhanced Order Management Integration
Tests the integration between Enhanced Order Manager and Order Execution Engine
"""

import asyncio
import pytest
import pytest_asyncio
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

# Import the components to test
from enhanced_order_integration import (
    EnhancedOrderManagementSystem, EnhancedOrder, RiskParameters,
    OrderType, OrderSide, OrderStatus, TimeInForce,
    create_market_order, create_limit_order, create_stop_order,
    OrderValidationError, RiskManagementError
)
from order_execution_engine import (
    OrderExecutionEngine, VenueConfig, VenueType, ExecutionAlgorithm,
    MarketData, OrderExecutionReport
)

class TestEnhancedOrderIntegration:
    """Test suite for Enhanced Order Management Integration"""
    
    @pytest_asyncio.fixture
    async def oms_system(self):
        """Create an OMS system for testing"""
        risk_params = RiskParameters(
            max_order_value=Decimal('1000000'),
            max_position_size=Decimal('100000'),
            allowed_symbols={'EURUSD', 'GBPUSD', 'USDJPY'},
            max_orders_per_second=10
        )
        
        oms = EnhancedOrderManagementSystem(risk_params)
        await oms.start()
        
        yield oms
        
        await oms.stop()
    
    @pytest.fixture
    def sample_market_order(self):
        """Create a sample market order"""
        return create_market_order(
            symbol='EURUSD',
            side=OrderSide.BUY,
            quantity=Decimal('10000'),
            account_id='TEST_ACCOUNT',
            strategy_id='TEST_STRATEGY'
        )
    
    @pytest.fixture
    def sample_limit_order(self):
        """Create a sample limit order"""
        return create_limit_order(
            symbol='GBPUSD',
            side=OrderSide.SELL,
            quantity=Decimal('5000'),
            price=Decimal('1.2500'),
            account_id='TEST_ACCOUNT',
            strategy_id='TEST_STRATEGY'
        )
    
    @pytest.mark.asyncio
    async def test_system_startup_shutdown(self):
        """Test system startup and shutdown"""
        risk_params = RiskParameters()
        oms = EnhancedOrderManagementSystem(risk_params)
        
        # Test startup
        await oms.start()
        assert oms._running is True
        assert oms.execution_engine._running is True
        
        # Test shutdown
        await oms.stop()
        assert oms._running is False
        assert oms.execution_engine._running is False
    
    @pytest.mark.asyncio
    async def test_order_submission_success(self, oms_system, sample_market_order):
        """Test successful order submission"""
        order_id = await oms_system.submit_order(sample_market_order)
        
        assert order_id == sample_market_order.order_id
        assert sample_market_order.order_id in oms_system.orders
        assert sample_market_order.risk_checked is True
        assert sample_market_order.status in [OrderStatus.SUBMITTED, OrderStatus.ACCEPTED]
    
    @pytest.mark.asyncio
    async def test_order_validation_errors(self, oms_system):
        """Test order validation errors"""
        # Test negative quantity
        invalid_order = EnhancedOrder(
            order_id=str(uuid.uuid4()),
            client_order_id="TEST_001",
            symbol='EURUSD',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('-1000')  # Invalid negative quantity
        )
        
        with pytest.raises(OrderValidationError, match="Order quantity must be positive"):
            await oms_system.submit_order(invalid_order)
        
        # Test limit order without price
        limit_order_no_price = EnhancedOrder(
            order_id=str(uuid.uuid4()),
            client_order_id="TEST_002",
            symbol='EURUSD',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal('1000')
            # Missing price for limit order
        )
        
        with pytest.raises(OrderValidationError, match="Limit orders require a price"):
            await oms_system.submit_order(limit_order_no_price)
    
    @pytest.mark.asyncio
    async def test_risk_management_checks(self, oms_system):
        """Test risk management checks"""
        # Test order value limit
        large_order = create_limit_order(
            symbol='EURUSD',
            side=OrderSide.BUY,
            quantity=Decimal('10000000'),  # Very large quantity
            price=Decimal('1.1000')
        )
        
        with pytest.raises(RiskManagementError, match="Order value .* exceeds maximum"):
            await oms_system.submit_order(large_order)
        
        # Test blocked symbol
        oms_system.risk_parameters.blocked_symbols.add('BLOCKED_SYMBOL')
        blocked_order = create_market_order(
            symbol='BLOCKED_SYMBOL',
            side=OrderSide.BUY,
            quantity=Decimal('1000')
        )
        
        with pytest.raises(OrderValidationError, match="Symbol BLOCKED_SYMBOL is blocked"):
            await oms_system.submit_order(blocked_order)
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, oms_system):
        """Test rate limiting functionality"""
        # Set low rate limit for testing
        oms_system.risk_parameters.max_orders_per_second = 2
        
        # Submit orders rapidly
        orders = []
        for i in range(5):
            order = create_market_order(
                symbol='EURUSD',
                side=OrderSide.BUY,
                quantity=Decimal('1000'),
                account_id='RATE_TEST_ACCOUNT'
            )
            orders.append(order)
        
        # First two should succeed
        await oms_system.submit_order(orders[0])
        await oms_system.submit_order(orders[1])
        
        # Third should fail due to rate limiting
        with pytest.raises(RiskManagementError, match="Rate limit exceeded"):
            await oms_system.submit_order(orders[2])
    
    @pytest.mark.asyncio
    async def test_order_execution_flow(self, oms_system, sample_market_order):
        """Test complete order execution flow"""
        # Submit order
        order_id = await oms_system.submit_order(sample_market_order)
        
        # Wait for execution
        await asyncio.sleep(2)
        
        # Check order status
        order = oms_system.get_order(order_id)
        assert order is not None
        assert order.status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]
        
        # Check execution reports
        assert len(order.execution_reports) > 0
        
        # Check position tracking
        positions = oms_system.get_positions()
        assert 'EURUSD' in positions
        assert positions['EURUSD'] > 0  # Long position
    
    @pytest.mark.asyncio
    async def test_order_cancellation(self, oms_system, sample_limit_order):
        """Test order cancellation"""
        # Submit order
        order_id = await oms_system.submit_order(sample_limit_order)
        
        # Cancel order
        success = await oms_system.cancel_order(order_id, "Test cancellation")
        assert success is True
        
        # Check order status
        order = oms_system.get_order(order_id)
        assert order.status == OrderStatus.CANCELLED
        assert order.tags.get('cancellation_reason') == "Test cancellation"
    
    @pytest.mark.asyncio
    async def test_order_modification(self, oms_system, sample_limit_order):
        """Test order modification"""
        # Submit order
        order_id = await oms_system.submit_order(sample_limit_order)
        
        # Modify order
        new_quantity = Decimal('7500')
        new_price = Decimal('1.2600')
        
        success = await oms_system.modify_order(order_id, new_quantity, new_price)
        assert success is True
        
        # Check modifications
        order = oms_system.get_order(order_id)
        assert order.quantity == new_quantity
        assert order.price == new_price
        assert order.status == OrderStatus.REPLACED
    
    @pytest.mark.asyncio
    async def test_order_approval_workflow(self, oms_system):
        """Test order approval workflow"""
        # Create large order requiring approval
        large_order = create_limit_order(
            symbol='EURUSD',
            side=OrderSide.BUY,
            quantity=Decimal('500000'),  # Large enough to require approval
            price=Decimal('1.1000')
        )
        
        # Submit order
        order_id = await oms_system.submit_order(large_order)
        
        # Check order is pending approval
        order = oms_system.get_order(order_id)
        assert order.status == OrderStatus.PENDING
        assert order.approval_required is True
        assert order_id in oms_system.pending_approvals
        
        # Approve order
        success = await oms_system.approve_order(order_id, "TEST_APPROVER")
        assert success is True
        
        # Check order is no longer pending
        assert order_id not in oms_system.pending_approvals
        assert order.approved_by == "TEST_APPROVER"
        assert order.approval_required is False
    
    @pytest.mark.asyncio
    async def test_position_tracking(self, oms_system):
        """Test position tracking functionality"""
        # Submit buy order
        buy_order = create_market_order('EURUSD', OrderSide.BUY, Decimal('10000'))
        await oms_system.submit_order(buy_order)
        
        # Wait for execution
        await asyncio.sleep(1)
        
        # Submit sell order
        sell_order = create_market_order('EURUSD', OrderSide.SELL, Decimal('5000'))
        await oms_system.submit_order(sell_order)
        
        # Wait for execution
        await asyncio.sleep(1)
        
        # Check net position
        positions = oms_system.get_positions()
        assert 'EURUSD' in positions
        # Net position should be approximately 5000 (10000 - 5000)
        assert abs(positions['EURUSD'] - Decimal('5000')) < Decimal('100')
    
    @pytest.mark.asyncio
    async def test_pnl_tracking(self, oms_system):
        """Test P&L tracking functionality"""
        # Submit orders to generate P&L
        order1 = create_market_order('EURUSD', OrderSide.BUY, Decimal('10000'))
        order2 = create_market_order('EURUSD', OrderSide.SELL, Decimal('10000'))
        
        await oms_system.submit_order(order1)
        await asyncio.sleep(1)
        await oms_system.submit_order(order2)
        await asyncio.sleep(1)
        
        # Check P&L tracking
        pnl = oms_system.get_daily_pnl()
        assert 'DEFAULT' in pnl  # Default account
        # P&L should be non-zero due to spread
        assert pnl['DEFAULT'] != Decimal('0')
    
    @pytest.mark.asyncio
    async def test_order_queries(self, oms_system):
        """Test order query functionality"""
        # Submit orders with different attributes
        order1 = create_market_order('EURUSD', OrderSide.BUY, Decimal('1000'), 
                                   strategy_id='STRATEGY_A')
        order2 = create_limit_order('GBPUSD', OrderSide.SELL, Decimal('2000'), 
                                  Decimal('1.2500'), strategy_id='STRATEGY_B')
        order3 = create_market_order('EURUSD', OrderSide.SELL, Decimal('1500'), 
                                   strategy_id='STRATEGY_A')
        
        await oms_system.submit_order(order1)
        await oms_system.submit_order(order2)
        await oms_system.submit_order(order3)
        
        # Test get_orders_by_symbol
        eurusd_orders = oms_system.get_orders_by_symbol('EURUSD')
        assert len(eurusd_orders) == 2
        
        gbpusd_orders = oms_system.get_orders_by_symbol('GBPUSD')
        assert len(gbpusd_orders) == 1
        
        # Test get_orders_by_strategy
        strategy_a_orders = oms_system.get_orders_by_strategy('STRATEGY_A')
        assert len(strategy_a_orders) == 2
        
        strategy_b_orders = oms_system.get_orders_by_strategy('STRATEGY_B')
        assert len(strategy_b_orders) == 1
        
        # Test get_active_orders
        active_orders = oms_system.get_active_orders()
        assert len(active_orders) >= 3
    
    @pytest.mark.asyncio
    async def test_order_statistics(self, oms_system, sample_market_order, sample_limit_order):
        """Test order statistics functionality"""
        # Submit orders
        await oms_system.submit_order(sample_market_order)
        await oms_system.submit_order(sample_limit_order)
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # Get statistics
        stats = oms_system.get_order_statistics()
        
        assert stats['total_orders'] >= 2
        assert stats['active_orders'] >= 0
        assert 'status_breakdown' in stats
        assert 'execution_stats' in stats
        assert 'venue_status' in stats
    
    @pytest.mark.asyncio
    async def test_venue_management(self, oms_system):
        """Test venue management functionality"""
        # Add custom venue
        custom_venue = VenueConfig(
            venue_id="CUSTOM_VENUE",
            venue_type=VenueType.ECN,
            symbols={'EURUSD', 'GBPUSD'},
            min_quantity=Decimal('1000'),
            max_quantity=Decimal('1000000'),
            tick_size=Decimal('0.00001'),
            commission_rate=Decimal('0.00001'),
            latency_ms=1.0,
            reliability=0.99,
            market_hours={'MON-FRI': ('00:00', '23:59')},
            supports_algorithms={ExecutionAlgorithm.DIRECT},
            priority=1
        )
        
        oms_system.add_venue(custom_venue)
        
        # Check venue was added
        venue_status = oms_system.get_order_statistics()['venue_status']
        assert 'CUSTOM_VENUE' in venue_status
        
        # Remove venue
        oms_system.remove_venue("CUSTOM_VENUE")
        
        # Check venue was removed
        venue_status = oms_system.get_order_statistics()['venue_status']
        assert 'CUSTOM_VENUE' not in venue_status
    
    @pytest.mark.asyncio
    async def test_market_data_integration(self, oms_system):
        """Test market data integration"""
        # Update market data
        market_data = MarketData(
            symbol='EURUSD',
            timestamp=datetime.now(),
            bid_price=Decimal('1.0999'),
            ask_price=Decimal('1.1001'),
            bid_size=Decimal('1000000'),
            ask_size=Decimal('1000000'),
            last_price=Decimal('1.1000'),
            volume=Decimal('50000000')
        )
        
        oms_system.update_market_data('EURUSD', market_data)
        
        # Check market data was updated
        engine_market_data = oms_system.execution_engine.market_data.get('EURUSD')
        assert engine_market_data is not None
        assert engine_market_data.bid_price == Decimal('1.0999')
        assert engine_market_data.ask_price == Decimal('1.1001')
    
    @pytest.mark.asyncio
    async def test_order_callbacks(self, oms_system, sample_market_order):
        """Test order callback functionality"""
        callback_events = []
        
        async def test_callback(order, event_type):
            callback_events.append((order.order_id, event_type))
        
        # Register callback
        oms_system.register_order_callback(sample_market_order.order_id, test_callback)
        
        # Submit order
        await oms_system.submit_order(sample_market_order)
        
        # Wait for callbacks
        await asyncio.sleep(1)
        
        # Check callbacks were triggered
        assert len(callback_events) > 0
        assert any(event[1] == "submitted" for event in callback_events)
    
    @pytest.mark.asyncio
    async def test_execution_callbacks(self, oms_system, sample_market_order):
        """Test execution callback functionality"""
        execution_events = []
        
        async def execution_callback(order, execution_report):
            execution_events.append((order.order_id, execution_report.execution_id))
        
        # Register callback
        oms_system.register_execution_callback(execution_callback)
        
        # Submit order
        await oms_system.submit_order(sample_market_order)
        
        # Wait for execution
        await asyncio.sleep(2)
        
        # Check execution callbacks were triggered
        assert len(execution_events) > 0
    
    @pytest.mark.asyncio
    async def test_risk_callbacks(self, oms_system, sample_market_order):
        """Test risk callback functionality"""
        risk_events = []
        
        async def risk_callback(order, event_type):
            risk_events.append((order.order_id, event_type))
        
        # Register callback
        oms_system.register_risk_callback(risk_callback)
        
        # Submit order
        await oms_system.submit_order(sample_market_order)
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # Check risk callbacks were triggered
        assert len(risk_events) > 0
        assert any(event[1] == "risk_checked" for event in risk_events)
    
    @pytest.mark.asyncio
    async def test_order_expiry(self, oms_system):
        """Test order expiry functionality"""
        # Create DAY order
        day_order = create_limit_order(
            symbol='EURUSD',
            side=OrderSide.BUY,
            quantity=Decimal('1000'),
            price=Decimal('1.0900'),
            time_in_force=TimeInForce.DAY
        )
        
        # Set created time to yesterday to simulate expiry
        day_order.created_time = datetime.now() - timedelta(days=1)
        
        await oms_system.submit_order(day_order)
        
        # Trigger expiry processing
        await oms_system._process_expired_orders()
        
        # Check order expired
        order = oms_system.get_order(day_order.order_id)
        assert order.status == OrderStatus.EXPIRED
    
    def test_factory_functions(self):
        """Test order factory functions"""
        # Test market order creation
        market_order = create_market_order('EURUSD', OrderSide.BUY, Decimal('10000'))
        assert market_order.order_type == OrderType.MARKET
        assert market_order.symbol == 'EURUSD'
        assert market_order.side == OrderSide.BUY
        assert market_order.quantity == Decimal('10000')
        assert market_order.time_in_force == TimeInForce.IOC
        
        # Test limit order creation
        limit_order = create_limit_order('GBPUSD', OrderSide.SELL, Decimal('5000'), Decimal('1.2500'))
        assert limit_order.order_type == OrderType.LIMIT
        assert limit_order.symbol == 'GBPUSD'
        assert limit_order.side == OrderSide.SELL
        assert limit_order.quantity == Decimal('5000')
        assert limit_order.price == Decimal('1.2500')
        assert limit_order.time_in_force == TimeInForce.GTC
        
        # Test stop order creation
        stop_order = create_stop_order('USDJPY', OrderSide.BUY, Decimal('2000'), Decimal('111.00'))
        assert stop_order.order_type == OrderType.STOP
        assert stop_order.symbol == 'USDJPY'
        assert stop_order.side == OrderSide.BUY
        assert stop_order.quantity == Decimal('2000')
        assert stop_order.stop_price == Decimal('111.00')
    
    def test_order_properties(self):
        """Test order property methods"""
        order = create_limit_order('EURUSD', OrderSide.BUY, Decimal('10000'), Decimal('1.1000'))
        
        # Test is_active property
        order.status = OrderStatus.ACCEPTED
        assert order.is_active is True
        
        order.status = OrderStatus.FILLED
        assert order.is_active is False
        
        # Test is_complete property
        order.status = OrderStatus.FILLED
        assert order.is_complete is True
        
        order.status = OrderStatus.ACCEPTED
        assert order.is_complete is False
        
        # Test fill_percentage property
        order.filled_quantity = Decimal('5000')
        assert order.fill_percentage == 50.0
        
        order.filled_quantity = Decimal('10000')
        assert order.fill_percentage == 100.0

class TestOrderExecutionEngine:
    """Test suite for Order Execution Engine"""
    
    @pytest_asyncio.fixture
    async def execution_engine(self):
        """Create an execution engine for testing"""
        engine = OrderExecutionEngine()
        await engine.start()
        
        yield engine
        
        await engine.stop()
    
    @pytest.mark.asyncio
    async def test_engine_startup_shutdown(self):
        """Test execution engine startup and shutdown"""
        engine = OrderExecutionEngine()
        
        # Test startup
        await engine.start()
        assert engine._running is True
        
        # Test shutdown
        await engine.stop()
        assert engine._running is False
    
    @pytest.mark.asyncio
    async def test_direct_execution(self, execution_engine):
        """Test direct execution algorithm"""
        from order_execution_engine import EnhancedOrder as ExecutionOrder
        
        order = ExecutionOrder(
            order_id="TEST_DIRECT",
            symbol='EURUSD',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('10000')
        )
        
        execution_reports = await execution_engine.execute_order(order)
        
        assert len(execution_reports) > 0
        assert all(report.execution_type == "DIRECT" for report in execution_reports)
        assert sum(report.quantity for report in execution_reports) == order.quantity
    
    @pytest.mark.asyncio
    async def test_venue_routing(self, execution_engine):
        """Test smart venue routing"""
        from order_execution_engine import EnhancedOrder as ExecutionOrder
        
        order = ExecutionOrder(
            order_id="TEST_ROUTING",
            symbol='EURUSD',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('100000')  # Large order for multi-venue routing
        )
        
        routes = await execution_engine._smart_route_order(order)
        
        assert len(routes) > 0
        assert sum(quantity for _, quantity in routes) == order.quantity
    
    @pytest.mark.asyncio
    async def test_execution_statistics(self, execution_engine):
        """Test execution statistics tracking"""
        from order_execution_engine import EnhancedOrder as ExecutionOrder
        
        order = ExecutionOrder(
            order_id="TEST_STATS",
            symbol='EURUSD',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal('10000')
        )
        
        await execution_engine.execute_order(order)
        
        stats = execution_engine.get_execution_statistics('EURUSD')
        assert 'total_orders' in stats
        assert stats['total_orders'] >= 1
    
    @pytest.mark.asyncio
    async def test_venue_management(self, execution_engine):
        """Test venue management functionality"""
        # Test adding venue
        custom_venue = VenueConfig(
            venue_id="TEST_VENUE",
            venue_type=VenueType.ECN,
            symbols={'EURUSD'},
            min_quantity=Decimal('1000'),
            max_quantity=Decimal('1000000'),
            tick_size=Decimal('0.00001'),
            commission_rate=Decimal('0.00001'),
            latency_ms=1.0,
            reliability=0.99,
            market_hours={'MON-FRI': ('00:00', '23:59')},
            supports_algorithms={ExecutionAlgorithm.DIRECT}
        )
        
        execution_engine.add_venue(custom_venue)
        assert "TEST_VENUE" in execution_engine.venues
        
        # Test removing venue
        execution_engine.remove_venue("TEST_VENUE")
        assert "TEST_VENUE" not in execution_engine.venues

# Performance and stress tests
class TestPerformanceAndStress:
    """Performance and stress tests"""
    
    @pytest.mark.asyncio
    async def test_high_volume_order_processing(self):
        """Test processing high volume of orders"""
        risk_params = RiskParameters(
            max_order_value=Decimal('10000000'),
            max_position_size=Decimal('1000000'),
            max_orders_per_second=1000
        )
        
        oms = EnhancedOrderManagementSystem(risk_params)
        await oms.start()
        
        try:
            # Submit many orders concurrently
            orders = []
            for i in range(100):
                order = create_market_order(
                    symbol='EURUSD',
                    side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                    quantity=Decimal('1000'),
                    account_id=f'ACCOUNT_{i % 10}'
                )
                orders.append(order)
            
            # Submit orders concurrently
            start_time = time.time()
            tasks = [oms.submit_order(order) for order in orders]
            await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            processing_time = end_time - start_time
            orders_per_second = len(orders) / processing_time
            
            print(f"Processed {len(orders)} orders in {processing_time:.2f}s ({orders_per_second:.2f} orders/sec)")
            
            # Verify orders were processed
            assert len(oms.orders) >= len(orders) * 0.9  # Allow for some failures
            
        finally:
            await oms.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_order_operations(self):
        """Test concurrent order operations"""
        oms = EnhancedOrderManagementSystem()
        await oms.start()
        
        try:
            # Create orders
            orders = [
                create_limit_order('EURUSD', OrderSide.BUY, Decimal('1000'), Decimal('1.0900'))
                for _ in range(10)
            ]
            
            # Submit orders
            for order in orders:
                await oms.submit_order(order)
            
            # Perform concurrent operations
            tasks = []
            for i, order in enumerate(orders):
                if i % 3 == 0:
                    tasks.append(oms.cancel_order(order.order_id))
                elif i % 3 == 1:
                    tasks.append(oms.modify_order(order.order_id, new_quantity=Decimal('1500')))
                # Leave some orders unchanged
            
            # Execute concurrent operations
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify no exceptions occurred
            for result in results:
                if isinstance(result, Exception):
                    print(f"Operation failed: {result}")
            
            # Verify system state is consistent
            stats = oms.get_order_statistics()
            assert stats['total_orders'] == len(orders)
            
        finally:
            await oms.stop()

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])