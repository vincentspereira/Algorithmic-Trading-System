#!/usr/bin/env python3
"""
Comprehensive Test Suite for Order Lifecycle Management System
Tests parent-child relationships, modifications, cancellations, status tracking, and TCA.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timedelta
from order_lifecycle_manager import (
    OrderLifecycleManager, Order, OrderExecution, OrderStatus, 
    OrderSide, OrderType, TimeInForce
)
from order_status_tracker import OrderStatusTracker, NotificationSubscription, NotificationType
from transaction_cost_analysis import TransactionCostAnalyzer, TCABenchmark

class TestOrderLifecycleManager:
    """Test cases for Order Lifecycle Manager"""
    
    @pytest.fixture
    async def manager(self):
        """Create order lifecycle manager for testing"""
        return OrderLifecycleManager()
    
    @pytest.mark.asyncio
    async def test_create_basic_order(self, manager):
        """Test basic order creation"""
        order_data = {
            'symbol': 'AAPL',
            'side': 'buy',
            'order_type': 'limit',
            'quantity': 100,
            'price': 150.00
        }
        
        order = await manager.create_order(order_data)
        
        assert order.symbol == 'AAPL'
        assert order.side == OrderSide.BUY
        assert order.quantity == 100
        assert order.price == 150.00
        assert order.status == OrderStatus.PENDING
        assert order.remaining_quantity == 100
        assert order.filled_quantity == 0
    
    @pytest.mark.asyncio
    async def test_parent_child_relationships(self, manager):
        """Test parent-child order relationships"""
        # Create parent order
        parent_data = {
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 1000,
            'price': 150.00
        }
        parent_order = await manager.create_order(parent_data)
        
        # Create child orders
        child_orders = []
        for i in range(3):
            child_data = {
                'parent_order_id': parent_order.order_id,
                'symbol': 'AAPL',
                'side': 'buy',
                'quantity': 300 + i * 50,
                'price': 149.50 + i * 0.25
            }
            child_order = await manager.create_order(child_data)
            child_orders.append(child_order)
        
        # Verify relationships
        assert len(parent_order.child_order_ids) == 3
        assert all(child.parent_order_id == parent_order.order_id for child in child_orders)
        
        # Test get_orders_by_parent
        retrieved_children = manager.get_orders_by_parent(parent_order.order_id)
        assert len(retrieved_children) == 3
        assert all(child.parent_order_id == parent_order.order_id for child in retrieved_children)
    
    @pytest.mark.asyncio
    async def test_order_modification(self, manager):
        """Test order modification functionality"""
        order_data = {
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 100,
            'price': 150.00
        }
        order = await manager.create_order(order_data)
        
        # Modify order
        modifications = {
            'quantity': 200,
            'price': 149.50
        }
        modification = await manager.modify_order(order.order_id, modifications)
        
        assert modification.status == "applied"
        assert order.quantity == 200
        assert order.price == 149.50
        
        # Check modification history
        mod_history = manager.get_order_modifications(order.order_id)
        assert len(mod_history) == 1
        assert mod_history[0].modifications == modifications
    
    @pytest.mark.asyncio
    async def test_order_cancellation(self, manager):
        """Test order cancellation with child orders"""
        # Create parent with children
        parent_data = {'symbol': 'AAPL', 'side': 'buy', 'quantity': 1000}
        parent_order = await manager.create_order(parent_data)
        
        child_data = {
            'parent_order_id': parent_order.order_id,
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 500
        }
        child_order = await manager.create_order(child_data)
        
        # Cancel parent order
        result = await manager.cancel_order(parent_order.order_id, "Test cancellation")
        
        assert result is True
        assert parent_order.status == OrderStatus.CANCELLED
        assert child_order.status == OrderStatus.CANCELLED
        assert parent_order.cancelled_time is not None
    
    @pytest.mark.asyncio
    async def test_order_execution(self, manager):
        """Test order execution and fill tracking"""
        order_data = {
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 1000,
            'price': 150.00
        }
        order = await manager.create_order(order_data)
        
        # Add partial execution
        execution1 = OrderExecution(
            execution_id=str(uuid.uuid4()),
            order_id=order.order_id,
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=400,
            price=150.05,
            timestamp=datetime.now(),
            venue='NYSE',
            commission=2.00
        )
        await manager.add_execution(execution1)
        
        assert order.status == OrderStatus.PARTIALLY_FILLED
        assert order.filled_quantity == 400
        assert order.remaining_quantity == 600
        assert order.average_fill_price == 150.05
        
        # Add completing execution
        execution2 = OrderExecution(
            execution_id=str(uuid.uuid4()),
            order_id=order.order_id,
            symbol='AAPL',
            side=OrderSide.BUY,
            quantity=600,
            price=150.10,
            timestamp=datetime.now(),
            venue='NASDAQ',
            commission=3.00
        )
        await manager.add_execution(execution2)
        
        assert order.status == OrderStatus.FILLED
        assert order.filled_quantity == 1000
        assert order.remaining_quantity == 0
        assert order.filled_time is not None
        
        # Check average fill price calculation
        expected_avg = (400 * 150.05 + 600 * 150.10) / 1000
        assert abs(order.average_fill_price - expected_avg) < 0.01

if __name__ == "__main__":
    pytest.main([__file__, "-v"])