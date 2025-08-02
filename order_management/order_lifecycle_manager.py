#!/usr/bin/env python3
"""
Enhanced Order Lifecycle Management System for Nautilus Trader Engine
Implements parent-child order relationships, comprehensive modification/cancellation handling,
real-time order status tracking with WebSocket notifications, and TCA (Transaction Cost Analysis).
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import websockets
import threading
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    SUSPENDED = "suspended"

class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    ICEBERG = "iceberg"
    TWAP = "twap"
    VWAP = "vwap"
    IMPLEMENTATION_SHORTFALL = "implementation_shortfall"

class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"

class TimeInForce(Enum):
    """Time in force enumeration"""
    DAY = "day"
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill
    GTD = "gtd"  # Good Till Date

@dataclass
class OrderExecution:
    """Represents an order execution/fill"""
    execution_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: datetime
    venue: str
    commission: float = 0.0
    fees: float = 0.0
    liquidity_flag: str = "unknown"  # "maker", "taker", "unknown"

@dataclass
class Order:
    """Enhanced order representation with lifecycle management"""
    order_id: str
    parent_order_id: Optional[str] = None
    child_order_ids: List[str] = field(default_factory=list)
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: float = 0.0
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    status: OrderStatus = OrderStatus.PENDING
    created_time: datetime = field(default_factory=datetime.now)
    updated_time: datetime = field(default_factory=datetime.now)
    submitted_time: Optional[datetime] = None
    filled_time: Optional[datetime] = None
    cancelled_time: Optional[datetime] = None
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    average_fill_price: float = 0.0
    executions: List[OrderExecution] = field(default_factory=list)
    venue: str = ""
    client_order_id: str = ""
    strategy_id: str = ""
    account_id: str = ""
    tags: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.remaining_quantity:
            self.remaining_quantity = self.quantity
        if not self.client_order_id:
            self.client_order_id = f"client_{self.order_id}"

@dataclass
class OrderModification:
    """Represents an order modification request"""
    modification_id: str
    order_id: str
    timestamp: datetime
    modifications: Dict[str, Any]
    status: str = "pending"  # pending, applied, rejected
    reason: str = ""

@dataclass
class TCAMetrics:
    """Transaction Cost Analysis metrics"""
    order_id: str
    symbol: str
    side: OrderSide
    benchmark_price: float
    average_fill_price: float
    quantity: float
    market_impact: float
    timing_cost: float
    spread_cost: float
    commission_cost: float
    total_cost: float
    implementation_shortfall: float
    arrival_price: float
    decision_price: float
    slippage: float
    participation_rate: float
    duration_minutes: float
    venue_breakdown: Dict[str, float]
    timestamp: datetime

class OrderLifecycleManager:
    """Enhanced order lifecycle management system"""
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.order_modifications: Dict[str, List[OrderModification]] = defaultdict(list)
        self.parent_child_map: Dict[str, List[str]] = defaultdict(list)
        self.child_parent_map: Dict[str, str] = {}
        self.order_executions: Dict[str, List[OrderExecution]] = defaultdict(list)
        self.tca_metrics: Dict[str, TCAMetrics] = {}
        self.websocket_clients: List[websockets.WebSocketServerProtocol] = []
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self.websocket_server = None
        self.notification_queue = asyncio.Queue()
        
        # Start background tasks
        asyncio.create_task(self._start_websocket_server())
        asyncio.create_task(self._process_notifications())
    
    async def create_order(self, order_data: Dict[str, Any]) -> Order:
        """Create a new order with lifecycle tracking"""
        order_id = order_data.get('order_id', str(uuid.uuid4()))
        
        order = Order(
            order_id=order_id,
            parent_order_id=order_data.get('parent_order_id'),
            symbol=order_data.get('symbol', ''),
            side=OrderSide(order_data.get('side', 'buy')),
            order_type=OrderType(order_data.get('order_type', 'market')),
            quantity=float(order_data.get('quantity', 0)),
            price=order_data.get('price'),
            stop_price=order_data.get('stop_price'),
            time_in_force=TimeInForce(order_data.get('time_in_force', 'day')),
            venue=order_data.get('venue', ''),
            client_order_id=order_data.get('client_order_id', f"client_{order_id}"),
            strategy_id=order_data.get('strategy_id', ''),
            account_id=order_data.get('account_id', ''),
            tags=order_data.get('tags', {}),
            metadata=order_data.get('metadata', {})
        )
        
        # Handle parent-child relationships
        if order.parent_order_id:
            self.parent_child_map[order.parent_order_id].append(order_id)
            self.child_parent_map[order_id] = order.parent_order_id
            
            # Update parent order with child reference
            if order.parent_order_id in self.orders:
                self.orders[order.parent_order_id].child_order_ids.append(order_id)
        
        self.orders[order_id] = order
        
        # Trigger events
        await self._trigger_event('order_created', order)
        await self._send_notification('order_created', order)
        
        logger.info(f"Created order {order_id} for {order.symbol} {order.side.value} {order.quantity}")
        return order
    
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> OrderModification:
        """Modify an existing order"""
        if order_id not in self.orders:
            raise ValueError(f"Order {order_id} not found")
        
        order = self.orders[order_id]
        
        # Check if order can be modified
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            raise ValueError(f"Cannot modify order {order_id} with status {order.status.value}")
        
        modification_id = str(uuid.uuid4())
        modification = OrderModification(
            modification_id=modification_id,
            order_id=order_id,
            timestamp=datetime.now(),
            modifications=modifications
        )
        
        try:
            # Apply modifications
            original_values = {}
            for field, new_value in modifications.items():
                if hasattr(order, field):
                    original_values[field] = getattr(order, field)
                    setattr(order, field, new_value)
            
            order.updated_time = datetime.now()
            modification.status = "applied"
            
            # Store modification history
            self.order_modifications[order_id].append(modification)
            
            # Trigger events
            await self._trigger_event('order_modified', order, modification)
            await self._send_notification('order_modified', order, modification)
            
            logger.info(f"Modified order {order_id}: {modifications}")
            
        except Exception as e:
            modification.status = "rejected"
            modification.reason = str(e)
            logger.error(f"Failed to modify order {order_id}: {e}")
            raise
        
        return modification
    
    async def cancel_order(self, order_id: str, reason: str = "") -> bool:
        """Cancel an order and handle child orders"""
        if order_id not in self.orders:
            raise ValueError(f"Order {order_id} not found")
        
        order = self.orders[order_id]
        
        # Check if order can be cancelled
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            logger.warning(f"Cannot cancel order {order_id} with status {order.status.value}")
            return False
        
        # Cancel child orders first
        for child_id in order.child_order_ids:
            if child_id in self.orders:
                await self.cancel_order(child_id, f"Parent order {order_id} cancelled")
        
        # Update order status
        order.status = OrderStatus.CANCELLED
        order.cancelled_time = datetime.now()
        order.updated_time = datetime.now()
        
        if reason:
            order.metadata['cancellation_reason'] = reason
        
        # Trigger events
        await self._trigger_event('order_cancelled', order)
        await self._send_notification('order_cancelled', order)
        
        logger.info(f"Cancelled order {order_id}: {reason}")
        return True
    
    async def add_execution(self, execution: OrderExecution) -> None:
        """Add an execution to an order and update status"""
        order_id = execution.order_id
        
        if order_id not in self.orders:
            logger.error(f"Order {order_id} not found for execution {execution.execution_id}")
            return
        
        order = self.orders[order_id]
        order.executions.append(execution)
        self.order_executions[order_id].append(execution)
        
        # Update order fill information
        order.filled_quantity += execution.quantity
        order.remaining_quantity = max(0, order.quantity - order.filled_quantity)
        
        # Calculate average fill price
        total_value = sum(exec.quantity * exec.price for exec in order.executions)
        total_quantity = sum(exec.quantity for exec in order.executions)
        order.average_fill_price = total_value / total_quantity if total_quantity > 0 else 0
        
        # Update order status
        if order.remaining_quantity <= 0:
            order.status = OrderStatus.FILLED
            order.filled_time = datetime.now()
        elif order.filled_quantity > 0:
            order.status = OrderStatus.PARTIALLY_FILLED
        
        order.updated_time = datetime.now()
        
        # Calculate TCA metrics
        await self._calculate_tca_metrics(order)
        
        # Trigger events
        await self._trigger_event('order_executed', order, execution)
        await self._send_notification('order_executed', order, execution)
        
        logger.info(f"Added execution {execution.execution_id} to order {order_id}: "
                   f"{execution.quantity}@{execution.price}")
    
    async def _calculate_tca_metrics(self, order: Order) -> None:
        """Calculate Transaction Cost Analysis metrics"""
        if not order.executions or order.status not in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]:
            return
        
        # Get market data (simulated for this implementation)
        arrival_price = order.metadata.get('arrival_price', order.average_fill_price)
        decision_price = order.metadata.get('decision_price', arrival_price)
        benchmark_price = order.metadata.get('benchmark_price', arrival_price)
        
        # Calculate costs
        total_quantity = sum(exec.quantity for exec in order.executions)
        total_value = sum(exec.quantity * exec.price for exec in order.executions)
        average_price = total_value / total_quantity if total_quantity > 0 else 0
        
        # Market impact (difference from benchmark)
        market_impact = (average_price - benchmark_price) * total_quantity
        if order.side == OrderSide.SELL:
            market_impact = -market_impact
        
        # Timing cost (benchmark vs decision price)
        timing_cost = (benchmark_price - decision_price) * total_quantity
        if order.side == OrderSide.SELL:
            timing_cost = -timing_cost
        
        # Spread cost (estimated)
        spread_cost = total_quantity * 0.01  # Simplified spread cost
        
        # Commission cost
        commission_cost = sum(exec.commission + exec.fees for exec in order.executions)
        
        # Total cost
        total_cost = abs(market_impact) + abs(timing_cost) + spread_cost + commission_cost
        
        # Implementation shortfall
        implementation_shortfall = (average_price - decision_price) * total_quantity
        if order.side == OrderSide.SELL:
            implementation_shortfall = -implementation_shortfall
        
        # Slippage
        slippage = (average_price - arrival_price) / arrival_price if arrival_price != 0 else 0
        
        # Duration
        duration = (datetime.now() - order.created_time).total_seconds() / 60
        
        # Venue breakdown
        venue_breakdown = defaultdict(float)
        for exec in order.executions:
            venue_breakdown[exec.venue] += exec.quantity
        
        # Participation rate (simplified)
        participation_rate = 0.1  # Would be calculated from market volume data
        
        tca_metrics = TCAMetrics(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            benchmark_price=benchmark_price,
            average_fill_price=average_price,
            quantity=total_quantity,
            market_impact=market_impact,
            timing_cost=timing_cost,
            spread_cost=spread_cost,
            commission_cost=commission_cost,
            total_cost=total_cost,
            implementation_shortfall=implementation_shortfall,
            arrival_price=arrival_price,
            decision_price=decision_price,
            slippage=slippage,
            participation_rate=participation_rate,
            duration_minutes=duration,
            venue_breakdown=dict(venue_breakdown),
            timestamp=datetime.now()
        )
        
        self.tca_metrics[order.order_id] = tca_metrics
        
        # Trigger TCA event
        await self._trigger_event('tca_calculated', order, tca_metrics)
        await self._send_notification('tca_calculated', order, tca_metrics)
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_orders_by_parent(self, parent_order_id: str) -> List[Order]:
        """Get all child orders for a parent order"""
        child_ids = self.parent_child_map.get(parent_order_id, [])
        return [self.orders[child_id] for child_id in child_ids if child_id in self.orders]
    
    def get_orders_by_status(self, status: OrderStatus) -> List[Order]:
        """Get all orders with a specific status"""
        return [order for order in self.orders.values() if order.status == status]
    
    def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """Get all orders for a specific symbol"""
        return [order for order in self.orders.values() if order.symbol == symbol]
    
    def get_tca_metrics(self, order_id: str) -> Optional[TCAMetrics]:
        """Get TCA metrics for an order"""
        return self.tca_metrics.get(order_id)
    
    def get_order_modifications(self, order_id: str) -> List[OrderModification]:
        """Get modification history for an order"""
        return self.order_modifications.get(order_id, [])
    
    async def _trigger_event(self, event_type: str, *args) -> None:
        """Trigger event handlers"""
        handlers = self.event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(*args)
                else:
                    handler(*args)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
    
    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """Add an event handler"""
        self.event_handlers[event_type].append(handler)
    
    async def _send_notification(self, event_type: str, *args) -> None:
        """Send notification to WebSocket clients"""
        notification = {
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': {}
        }
        
        # Serialize data
        for i, arg in enumerate(args):
            if hasattr(arg, '__dict__'):
                notification['data'][f'arg_{i}'] = asdict(arg) if hasattr(arg, '__dataclass_fields__') else arg.__dict__
            else:
                notification['data'][f'arg_{i}'] = str(arg)
        
        await self.notification_queue.put(notification)
    
    async def _start_websocket_server(self) -> None:
        """Start WebSocket server for real-time notifications"""
        async def handle_client(websocket, path):
            self.websocket_clients.append(websocket)
            logger.info(f"WebSocket client connected: {websocket.remote_address}")
            
            try:
                await websocket.wait_closed()
            finally:
                if websocket in self.websocket_clients:
                    self.websocket_clients.remove(websocket)
                logger.info(f"WebSocket client disconnected: {websocket.remote_address}")
        
        try:
            self.websocket_server = await websockets.serve(handle_client, "localhost", 8765)
            logger.info("WebSocket server started on ws://localhost:8765")
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
    
    async def _process_notifications(self) -> None:
        """Process notification queue and send to WebSocket clients"""
        while True:
            try:
                notification = await self.notification_queue.get()
                
                if self.websocket_clients:
                    message = json.dumps(notification, default=str)
                    disconnected_clients = []
                    
                    for client in self.websocket_clients:
                        try:
                            await client.send(message)
                        except websockets.exceptions.ConnectionClosed:
                            disconnected_clients.append(client)
                        except Exception as e:
                            logger.error(f"Error sending notification to client: {e}")
                            disconnected_clients.append(client)
                    
                    # Remove disconnected clients
                    for client in disconnected_clients:
                        if client in self.websocket_clients:
                            self.websocket_clients.remove(client)
                
            except Exception as e:
                logger.error(f"Error processing notifications: {e}")
                await asyncio.sleep(1)
    
    def get_order_statistics(self) -> Dict[str, Any]:
        """Get order statistics"""
        total_orders = len(self.orders)
        status_counts = defaultdict(int)
        
        for order in self.orders.values():
            status_counts[order.status.value] += 1
        
        return {
            'total_orders': total_orders,
            'status_breakdown': dict(status_counts),
            'parent_orders': len([o for o in self.orders.values() if not o.parent_order_id]),
            'child_orders': len([o for o in self.orders.values() if o.parent_order_id]),
            'orders_with_executions': len([o for o in self.orders.values() if o.executions]),
            'total_executions': sum(len(o.executions) for o in self.orders.values()),
            'tca_metrics_calculated': len(self.tca_metrics)
        }

# Example usage and testing
async def main():
    """Example usage of the Order Lifecycle Manager"""
    manager = OrderLifecycleManager()
    
    # Create a parent order
    parent_order_data = {
        'symbol': 'AAPL',
        'side': 'buy',
        'order_type': 'limit',
        'quantity': 1000,
        'price': 150.00,
        'strategy_id': 'momentum_strategy',
        'account_id': 'account_001'
    }
    
    parent_order = await manager.create_order(parent_order_data)
    print(f"Created parent order: {parent_order.order_id}")
    
    # Create child orders
    for i in range(3):
        child_order_data = {
            'parent_order_id': parent_order.order_id,
            'symbol': 'AAPL',
            'side': 'buy',
            'order_type': 'limit',
            'quantity': 300 + i * 50,
            'price': 149.50 + i * 0.25,
            'strategy_id': 'momentum_strategy',
            'account_id': 'account_001'
        }
        
        child_order = await manager.create_order(child_order_data)
        print(f"Created child order: {child_order.order_id}")
    
    # Simulate some executions
    for order in manager.orders.values():
        if order.parent_order_id:  # Only execute child orders
            execution = OrderExecution(
                execution_id=str(uuid.uuid4()),
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity * 0.5,  # Partial fill
                price=order.price * 1.001,  # Slight slippage
                timestamp=datetime.now(),
                venue='NYSE',
                commission=2.50,
                fees=0.50,
                liquidity_flag='taker'
            )
            
            await manager.add_execution(execution)
            print(f"Added execution to order {order.order_id}")
    
    # Print statistics
    stats = manager.get_order_statistics()
    print(f"\nOrder Statistics: {json.dumps(stats, indent=2)}")
    
    # Keep the WebSocket server running
    print("\nWebSocket server running on ws://localhost:8765")
    print("Connect to receive real-time order notifications")
    
    # Wait for a bit to allow WebSocket connections
    await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())