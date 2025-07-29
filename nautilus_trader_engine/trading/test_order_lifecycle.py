"""
Comprehensive tests for Order Lifecycle Management System
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from .order_management import (
    OrderLifecycleManager, Order, OrderFill, OrderModification,
    OrderType, OrderStatus, OrderSide, TimeInForce, OrderPriority,
    OrderExecutionQuality, initialize_order_manager, start_order_manager
)


class TestOrderLifecycleManager:
    """Test cases for OrderLifecycleManager"""
    
    @pytest.fixture
    async def order_manager(self):
        """Create order lifecycle manager for testing"""
        manager = OrderLifecycleManager(
            enable_notifications=True,
            enable_tca=True
        )
        await manager.start()
        yield manager
        await manager.stop()
    
    @pytest.fixture
    def sample_order(self):
        """Create sample order for testing"""
        return Order(
            order_id="test_order_001",
            client_order_id="client_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100.0,
            price=150.0,
            time_in_force=TimeInForce.DAY,
            strategy_id="test_strategy",
            portfolio_id="test_portfolio"
        )
    
    @pytest.mark.asyncio
    async def test_create_order(self, order_manager, sample_order):
        """Test order creation"""
        order_id = await order_manager.create_order(sample_order)
        
        assert order_id == sample_order.order_id
        assert order_manager.get_order(order_id) is not None
        assert order_manager.get_order_by_client_id("client_001") is not None
        
        # Check metrics
        metrics = order_manager.get_metrics()
        assert metrics['orders_created'] == 1
        assert metrics['total_orders'] == 1
    
    @pytest.mark.asyncio
    async def test_order_validation(self, order_manager):
        """Test order validation"""
        # Invalid quantity
        invalid_order = Order(
            order_id="invalid_001",
            client_order_id="invalid_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=-100.0,  # Invalid
            price=150.0
        )
        
        with pytest.raises(ValueError, match="Order quantity must be positive"):
            await order_manager.create_order(invalid_order)
        
        # Limit order without price
        invalid_order2 = Order(
            order_id="invalid_002",
            client_order_id="invalid_002",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100.0
            # Missing price
        )
        
        with pytest.raises(ValueError, match="limit orders require a price"):
            await order_manager.create_order(invalid_order2)
    
    @pytest.mark.asyncio
    async def test_parent_child_relationships(self, order_manager):
        """Test parent-child order relationships"""
        # Create parent order
        parent_order = Order(
            order_id="parent_001",
            client_order_id="parent_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1000.0,
            price=150.0
        )
        
        parent_id = await order_manager.create_order(parent_order)
        
        # Create child orders
        child_order1 = Order(
            order_id="child_001",
            client_order_id="child_001",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=500.0,
            price=149.0,
            parent_order_id=parent_id
        )
        
        child_order2 = Order(
            order_id="child_002",
            client_order_id="child_002",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=500.0,
            price=151.0,
            parent_order_id=parent_id
        )
        
        await order_manager.create_order(child_order1)
        await order_manager.create_order(child_order2)
        
        # Test relationships
        child_orders = order_manager.get_child_orders(parent_id)
        assert len(child_orders) == 2
        assert child_orders[0].parent_order_id == parent_id
        assert child_orders[1].parent_order_id == parent_id
    
    @pytest.mark.asyncio
    async def test_order_modification(self, order_manager, sample_order):
        """Test order modification"""
        order_id = await order_manager.create_order(sample_order)
        
        # Modify quantity
        success = await order_manager.modify_order(
            order_id, "quantity", 200.0, "Increase position size"
        )
        assert success
        
        order = order_manager.get_order(order_id)
        assert order.quantity == 200.0
        assert order.remaining_quantity == 200.0
        assert len(order.modifications) == 1
        
        # Modify price
        success = await order_manager.modify_order(
            order_id, "price", 155.0, "Better price level"
        )
        assert success
        
        order = order_manager.get_order(order_id)
        assert order.price == 155.0
        assert len(order.modifications) == 2
        
        # Check metrics
        metrics = order_manager.get_metrics()
        assert metrics['modifications_processed'] == 2
    
    @pytest.mark.asyncio
    async def test_order_cancellation(self, order_manager, sample_order):
        """Test order cancellation"""
        order_id = await order_manager.create_order(sample_order)
        
        # Cancel order
        success = await order_manager.cancel_order(order_id, "Strategy change")
        assert success
        
        order = order_manager.get_order(order_id)
        assert order.status == OrderStatus.CANCELLED
        assert order.completion_time is not None
        assert len(order.modifications) == 1
        
        # Check metrics
        metrics = order_manager.get_metrics()
        assert metrics['orders_cancelled'] == 1
    
    @pytest.mark.asyncio
    async def test_parent_cancellation_cascades(self, order_manager):
        """Test that cancelling parent order cancels children"""
        # Create parent order
        parent_order = Order(
            order_id="parent_cascade",
            client_order_id="parent_cascade",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1000.0,
            price=150.0
        )
        
        parent_id = await order_manager.create_order(parent_order)
        
        # Create child order
        child_order = Order(
            order_id="child_cascade",
            client_order_id="child_cascade",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=500.0,
            price=149.0,
            parent_order_id=parent_id
        )
        
        child_id = await order_manager.create_order(child_order)
        
        # Cancel parent
        await order_manager.cancel_order(parent_id, "Cancel all")
        
        # Check both are cancelled
        parent = order_manager.get_order(parent_id)
        child = order_manager.get_order(child_id)
        
        assert parent.status == OrderStatus.CANCELLED
        assert child.status == OrderStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_order_fills(self, order_manager, sample_order):
        """Test order fill processing"""
        order_id = await order_manager.create_order(sample_order)
        
        # Add partial fill
        fill1 = OrderFill(
            fill_id="fill_001",
            order_id=order_id,
            quantity=50.0,
            price=149.5,
            timestamp=datetime.now(),
            venue="NASDAQ"
        )
        
        success = await order_manager.add_fill(order_id, fill1)
        assert success
        
        order = order_manager.get_order(order_id)
        assert order.filled_quantity == 50.0
        assert order.remaining_quantity == 50.0
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.average_fill_price == 149.5
        
        # Add completing fill
        fill2 = OrderFill(
            fill_id="fill_002",
            order_id=order_id,
            quantity=50.0,
            price=150.5,
            timestamp=datetime.now(),
            venue="NASDAQ"
        )
        
        success = await order_manager.add_fill(order_id, fill2)
        assert success
        
        order = order_manager.get_order(order_id)
        assert order.filled_quantity == 100.0
        assert order.remaining_quantity == 0.0
        assert order.status == OrderStatus.FILLED
        assert order.average_fill_price == 150.0  # (50*149.5 + 50*150.5) / 100
        assert order.completion_time is not None
        
        # Check fill history
        fills = order_manager.get_order_fills(order_id)
        assert len(fills) == 2
        
        # Check metrics
        metrics = order_manager.get_metrics()
        assert metrics['orders_filled'] == 1
    
    @pytest.mark.asyncio
    async def test_status_updates(self, order_manager, sample_order):
        """Test order status updates"""
        order_id = await order_manager.create_order(sample_order)
        
        # Update to submitted
        success = await order_manager.update_order_status(
            order_id, OrderStatus.SUBMITTED, {"venue": "NASDAQ"}
        )
        assert success
        
        order = order_manager.get_order(order_id)
        assert order.status == OrderStatus.SUBMITTED
        assert order.submission_time is not None
        
        # Update to acknowledged
        success = await order_manager.update_order_status(
            order_id, OrderStatus.ACKNOWLEDGED
        )
        assert success
        
        order = order_manager.get_order(order_id)
        assert order.status == OrderStatus.ACKNOWLEDGED
        assert order.acknowledgment_time is not None
        
        # Check status history
        history = order_manager.get_order_status_history(order_id)
        assert len(history) == 2
        assert history[0]['new_status'] == 'submitted'
        assert history[1]['new_status'] == 'acknowledged'
    
    @pytest.mark.asyncio
    async def test_execution_quality_tracking(self, order_manager, sample_order):
        """Test execution quality measurement"""
        order_id = await order_manager.create_order(sample_order)
        
        # Set arrival price
        order = order_manager.get_order(order_id)
        order.execution_quality.arrival_price = 150.0
        
        # Update status to track timing
        await order_manager.update_order_status(order_id, OrderStatus.SUBMITTED)
        await asyncio.sleep(0.01)  # Small delay
        await order_manager.update_order_status(order_id, OrderStatus.ACKNOWLEDGED)
        
        # Add fill
        fill = OrderFill(
            fill_id="fill_quality",
            order_id=order_id,
            quantity=100.0,
            price=150.2,  # Slight slippage
            timestamp=datetime.now(),
            venue="NASDAQ"
        )
        
        await order_manager.add_fill(order_id, fill)
        
        # Check execution quality
        eq = order_manager.get_execution_quality(order_id)
        assert eq is not None
        assert eq.average_fill_price == 150.2
        assert eq.fill_rate == 1.0
        assert eq.slippage > 0  # Should have positive slippage for buy order
        assert eq.submission_latency_ms > 0
        assert eq.acknowledgment_latency_ms > 0
    
    @pytest.mark.asyncio
    async def test_strategy_order_grouping(self, order_manager):
        """Test grouping orders by strategy"""
        strategy_id = "momentum_strategy"
        
        # Create multiple orders for same strategy
        for i in range(3):
            order = Order(
                order_id=f"strategy_order_{i}",
                client_order_id=f"strategy_client_{i}",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=100.0,
                price=150.0 + i,
                strategy_id=strategy_id
            )
            await order_manager.create_order(order)
        
        # Get orders by strategy
        strategy_orders = order_manager.get_orders_by_strategy(strategy_id)
        assert len(strategy_orders) == 3
        
        for order in strategy_orders:
            assert order.strategy_id == strategy_id
    
    @pytest.mark.asyncio
    async def test_active_orders_filtering(self, order_manager):
        """Test active orders filtering"""
        # Create orders with different statuses
        orders_data = [
            ("active_1", OrderStatus.PENDING),
            ("active_2", OrderStatus.SUBMITTED),
            ("active_3", OrderStatus.PARTIALLY_FILLED),
            ("inactive_1", OrderStatus.FILLED),
            ("inactive_2", OrderStatus.CANCELLED)
        ]
        
        for order_id, status in orders_data:
            order = Order(
                order_id=order_id,
                client_order_id=order_id,
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=100.0,
                price=150.0
            )
            await order_manager.create_order(order)
            
            if status != OrderStatus.PENDING:
                await order_manager.update_order_status(order_id, status)
        
        # Get active orders
        active_orders = order_manager.get_active_orders()
        assert len(active_orders) == 3
        
        active_ids = {order.order_id for order in active_orders}
        assert active_ids == {"active_1", "active_2", "active_3"}
    
    @pytest.mark.asyncio
    async def test_notifications(self, order_manager, sample_order):
        """Test notification system"""
        order_id = await order_manager.create_order(sample_order)
        
        # Set up notification callbacks
        status_notifications = []
        fill_notifications = []
        
        async def status_callback(event):
            status_notifications.append(event)
        
        async def fill_callback(event):
            fill_notifications.append(event)
        
        await order_manager.subscribe_to_status_updates(order_id, status_callback)
        await order_manager.subscribe_to_fills(order_id, fill_callback)
        
        # Trigger status update
        await order_manager.update_order_status(order_id, OrderStatus.SUBMITTED)
        await asyncio.sleep(0.1)  # Allow notification processing
        
        # Trigger fill
        fill = OrderFill(
            fill_id="notification_fill",
            order_id=order_id,
            quantity=50.0,
            price=150.0,
            timestamp=datetime.now(),
            venue="NASDAQ"
        )
        await order_manager.add_fill(order_id, fill)
        await asyncio.sleep(0.1)  # Allow notification processing
        
        # Check notifications were sent
        assert len(status_notifications) > 0
        assert len(fill_notifications) > 0
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self, order_manager):
        """Test metrics collection"""
        # Create and process various orders
        for i in range(5):
            order = Order(
                order_id=f"metrics_order_{i}",
                client_order_id=f"metrics_client_{i}",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=100.0,
                price=150.0
            )
            await order_manager.create_order(order)
        
        # Fill some orders
        for i in range(2):
            fill = OrderFill(
                fill_id=f"metrics_fill_{i}",
                order_id=f"metrics_order_{i}",
                quantity=100.0,
                price=150.0,
                timestamp=datetime.now(),
                venue="NASDAQ"
            )
            await order_manager.add_fill(f"metrics_order_{i}", fill)
        
        # Cancel some orders
        for i in range(2, 4):
            await order_manager.cancel_order(f"metrics_order_{i}", "Test cancellation")
        
        # Get metrics
        metrics = order_manager.get_metrics()
        
        assert metrics['orders_created'] == 5
        assert metrics['orders_filled'] == 2
        assert metrics['orders_cancelled'] == 2
        assert metrics['total_orders'] == 5
        assert metrics['active_orders'] == 1  # One remaining active
        assert 'orders_by_status' in metrics
        assert 'fill_rate' in metrics
        assert 'avg_order_value' in metrics
    
    def test_order_helper_methods(self, sample_order):
        """Test order helper methods"""
        # Test is_active
        assert sample_order.is_active()
        
        sample_order.status = OrderStatus.FILLED
        assert not sample_order.is_active()
        assert sample_order.is_complete()
        
        # Test add_fill
        fill = OrderFill(
            fill_id="helper_fill",
            order_id=sample_order.order_id,
            quantity=50.0,
            price=149.0,
            timestamp=datetime.now(),
            venue="NASDAQ"
        )
        
        sample_order.add_fill(fill)
        assert sample_order.filled_quantity == 50.0
        assert sample_order.remaining_quantity == 50.0
        assert sample_order.average_fill_price == 149.0
        assert len(sample_order.fills) == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, order_manager):
        """Test concurrent order operations"""
        # Create multiple orders concurrently
        tasks = []
        for i in range(10):
            order = Order(
                order_id=f"concurrent_{i}",
                client_order_id=f"concurrent_client_{i}",
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=100.0,
                price=150.0 + i
            )
            tasks.append(order_manager.create_order(order))
        
        # Execute concurrently
        order_ids = await asyncio.gather(*tasks)
        assert len(order_ids) == 10
        
        # Verify all orders were created
        for order_id in order_ids:
            assert order_manager.get_order(order_id) is not None
        
        # Concurrent modifications
        mod_tasks = []
        for i, order_id in enumerate(order_ids[:5]):
            mod_tasks.append(
                order_manager.modify_order(order_id, "quantity", 200.0 + i, "Concurrent mod")
            )
        
        results = await asyncio.gather(*mod_tasks)
        assert all(results)  # All modifications should succeed


@pytest.mark.asyncio
async def test_global_order_manager():
    """Test global order manager functions"""
    # Test initialization
    manager = initialize_order_manager(enable_tca=True)
    assert manager is not None
    
    # Test start/stop
    started_manager = await start_order_manager(enable_notifications=True)
    assert started_manager is not None
    
    # Test global access
    from .order_management import get_order_manager
    global_manager = get_order_manager()
    assert global_manager is started_manager
    
    # Clean up
    from .order_management import stop_order_manager
    await stop_order_manager()


@pytest.mark.asyncio
async def test_order_lifecycle_integration():
    """Integration test for complete order lifecycle"""
    manager = OrderLifecycleManager(enable_tca=True, enable_notifications=True)
    await manager.start()
    
    try:
        # Create bracket order (parent with stop loss and take profit)
        parent_order = Order(
            order_id="bracket_parent",
            client_order_id="bracket_parent",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100.0,
            price=150.0,
            strategy_id="bracket_strategy"
        )
        
        parent_id = await manager.create_order(parent_order)
        
        # Create stop loss child
        stop_loss = Order(
            order_id="bracket_stop",
            client_order_id="bracket_stop",
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.STOP,
            quantity=100.0,
            stop_price=145.0,
            parent_order_id=parent_id
        )
        
        # Create take profit child
        take_profit = Order(
            order_id="bracket_profit",
            client_order_id="bracket_profit",
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=100.0,
            price=155.0,
            parent_order_id=parent_id
        )
        
        await manager.create_order(stop_loss)
        await manager.create_order(take_profit)
        
        # Simulate order lifecycle
        await manager.update_order_status(parent_id, OrderStatus.SUBMITTED)
        await manager.update_order_status(parent_id, OrderStatus.ACKNOWLEDGED)
        
        # Fill parent order
        fill = OrderFill(
            fill_id="bracket_fill",
            order_id=parent_id,
            quantity=100.0,
            price=150.2,
            timestamp=datetime.now(),
            venue="NASDAQ"
        )
        
        await manager.add_fill(parent_id, fill)
        
        # Verify final state
        parent = manager.get_order(parent_id)
        children = manager.get_child_orders(parent_id)
        
        assert parent.status == OrderStatus.FILLED
        assert len(children) == 2
        assert parent.execution_quality is not None
        assert parent.execution_quality.fill_rate == 1.0
        
        # Check strategy grouping
        strategy_orders = manager.get_orders_by_strategy("bracket_strategy")
        assert len(strategy_orders) == 3  # Parent + 2 children
        
    finally:
        await manager.stop()


if __name__ == "__main__":
    # Run basic test
    asyncio.run(test_global_order_manager())
    print("Order Lifecycle Management tests completed successfully!")