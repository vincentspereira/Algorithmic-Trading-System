"""
Standalone test for Order Management System
"""

import asyncio
import time
import uuid
import logging
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor


class OrderType(Enum):
    """Order types supported by the system"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    ICEBERG = "iceberg"
    TWAP = "twap"
    VWAP = "vwap"
    BRACKET = "bracket"
    OCO = "oco"  # One-Cancels-Other


class OrderStatus(Enum):
    """Order lifecycle status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class OrderSide(Enum):
    """Order side"""
    BUY = "buy"
    SELL = "sell"


class TimeInForce(Enum):
    """Time in force options"""
    DAY = "day"
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill
    GTD = "gtd"  # Good Till Date


class OrderPriority(Enum):
    """Order priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class OrderFill:
    """Individual order fill information"""
    fill_id: str
    order_id: str
    quantity: float
    price: float
    timestamp: datetime
    venue: str
    commission: float = 0.0
    fees: float = 0.0
    
    def __post_init__(self):
        if not self.fill_id:
            self.fill_id = str(uuid.uuid4())


@dataclass
class OrderModification:
    """Order modification request"""
    modification_id: str
    order_id: str
    timestamp: datetime
    modification_type: str  # "quantity", "price", "tif", etc.
    old_value: Any
    new_value: Any
    reason: str = ""
    
    def __post_init__(self):
        if not self.modification_id:
            self.modification_id = str(uuid.uuid4())


@dataclass
class OrderExecutionQuality:
    """Order execution quality metrics"""
    order_id: str
    
    # Timing metrics
    submission_latency_ms: float = 0.0
    acknowledgment_latency_ms: float = 0.0
    fill_latency_ms: float = 0.0
    total_execution_time_ms: float = 0.0
    
    # Price metrics
    arrival_price: Optional[float] = None
    average_fill_price: Optional[float] = None
    benchmark_price: Optional[float] = None
    price_improvement: float = 0.0
    slippage: float = 0.0
    
    # Market impact
    market_impact_bps: float = 0.0
    temporary_impact_bps: float = 0.0
    permanent_impact_bps: float = 0.0
    
    # Execution efficiency
    fill_rate: float = 0.0  # Percentage filled
    participation_rate: float = 0.0  # % of market volume
    implementation_shortfall: float = 0.0
    
    # Venue performance
    venue_scores: Dict[str, float] = field(default_factory=dict)
    routing_efficiency: float = 0.0


@dataclass
class Order:
    """Comprehensive order representation"""
    order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    
    # Order relationships
    parent_order_id: Optional[str] = None
    child_order_ids: List[str] = field(default_factory=list)
    bracket_orders: Dict[str, str] = field(default_factory=dict)  # "stop_loss", "take_profit"
    
    # Status and lifecycle
    status: OrderStatus = OrderStatus.PENDING
    creation_time: datetime = field(default_factory=datetime.now)
    submission_time: Optional[datetime] = None
    acknowledgment_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
    expiry_time: Optional[datetime] = None
    
    # Execution details
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    average_fill_price: float = 0.0
    fills: List[OrderFill] = field(default_factory=list)
    
    # Routing and venue information
    target_venue: Optional[str] = None
    routed_venues: List[str] = field(default_factory=list)
    
    # Metadata
    strategy_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    account_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    priority: OrderPriority = OrderPriority.NORMAL
    
    # Modification history
    modifications: List[OrderModification] = field(default_factory=list)
    
    # Execution quality
    execution_quality: Optional[OrderExecutionQuality] = None
    
    def __post_init__(self):
        if not self.order_id:
            self.order_id = str(uuid.uuid4())
        if not self.client_order_id:
            self.client_order_id = self.order_id
        if self.remaining_quantity == 0.0:
            self.remaining_quantity = self.quantity
    
    def is_active(self) -> bool:
        """Check if order is in an active state"""
        return self.status in [
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.ACKNOWLEDGED,
            OrderStatus.PARTIALLY_FILLED
        ]
    
    def is_complete(self) -> bool:
        """Check if order is complete"""
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED
        ]
    
    def add_fill(self, fill: OrderFill) -> None:
        """Add a fill to the order"""
        self.fills.append(fill)
        self.filled_quantity += fill.quantity
        self.remaining_quantity = max(0, self.quantity - self.filled_quantity)
        
        # Update average fill price
        total_value = sum(f.quantity * f.price for f in self.fills)
        self.average_fill_price = total_value / self.filled_quantity if self.filled_quantity > 0 else 0
        
        # Update status
        if self.remaining_quantity == 0:
            self.status = OrderStatus.FILLED
            self.completion_time = datetime.now()
        elif self.filled_quantity > 0:
            self.status = OrderStatus.PARTIALLY_FILLED
    
    def add_modification(self, modification: OrderModification) -> None:
        """Add a modification to the order history"""
        self.modifications.append(modification)


class OrderLifecycleManager:
    """
    Comprehensive Order Lifecycle Management System
    
    Features:
    - Parent-child order relationships
    - Real-time order status tracking
    - Order modification and cancellation
    - Execution quality measurement
    - Transaction Cost Analysis (TCA)
    """
    
    def __init__(self, enable_notifications: bool = True, enable_tca: bool = True):
        self.enable_notifications = enable_notifications
        self.enable_tca = enable_tca
        
        # Order storage
        self._orders: Dict[str, Order] = {}
        self._orders_by_client_id: Dict[str, str] = {}
        self._orders_by_parent: Dict[str, List[str]] = defaultdict(list)
        self._orders_by_strategy: Dict[str, List[str]] = defaultdict(list)
        
        # Status tracking
        self._status_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._fill_history: Dict[str, List[OrderFill]] = defaultdict(list)
        
        # Notification subscribers
        self._status_subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._fill_subscribers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Background processing
        self._processing_queue = asyncio.Queue(maxsize=10000)
        self._notification_queue = asyncio.Queue(maxsize=5000)
        self._worker_tasks: List[asyncio.Task] = []
        self._running = False
        
        # Performance metrics
        self._metrics = {
            'orders_created': 0,
            'orders_filled': 0,
            'orders_cancelled': 0,
            'modifications_processed': 0,
            'notifications_sent': 0,
            'avg_fill_latency_ms': 0.0,
            'avg_execution_quality_score': 0.0
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the order lifecycle manager"""
        if self._running:
            return
        
        self._running = True
        
        # Start background workers
        self._worker_tasks = [
            asyncio.create_task(self._order_processor()),
            asyncio.create_task(self._notification_processor()),
            asyncio.create_task(self._metrics_collector())
        ]
        
        self.logger.info("Order Lifecycle Manager started")
    
    async def stop(self):
        """Stop the order lifecycle manager"""
        self._running = False
        
        # Cancel worker tasks
        for task in self._worker_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        
        self.logger.info("Order Lifecycle Manager stopped")
    
    async def create_order(self, order: Order) -> str:
        """Create a new order"""
        try:
            # Validate order
            self._validate_order(order)
            
            # Store order
            self._orders[order.order_id] = order
            self._orders_by_client_id[order.client_order_id] = order.order_id
            
            # Track relationships
            if order.parent_order_id:
                self._orders_by_parent[order.parent_order_id].append(order.order_id)
            
            if order.strategy_id:
                self._orders_by_strategy[order.strategy_id].append(order.order_id)
            
            # Initialize execution quality tracking
            if self.enable_tca:
                order.execution_quality = OrderExecutionQuality(order_id=order.order_id)
            
            # Queue for processing
            await self._processing_queue.put({
                'type': 'order_created',
                'order_id': order.order_id,
                'timestamp': time.time_ns()
            })
            
            self._metrics['orders_created'] += 1
            self.logger.info(f"Order created: {order.order_id}")
            
            return order.order_id
            
        except Exception as e:
            self.logger.error(f"Failed to create order: {e}")
            raise
    
    async def modify_order(self, 
                          order_id: str, 
                          modification_type: str,
                          new_value: Any,
                          reason: str = "") -> bool:
        """Modify an existing order"""
        try:
            order = self._orders.get(order_id)
            if not order:
                raise ValueError(f"Order {order_id} not found")
            
            if not order.is_active():
                raise ValueError(f"Cannot modify order {order_id} in status {order.status}")
            
            # Get old value
            old_value = getattr(order, modification_type, None)
            
            # Create modification record
            modification = OrderModification(
                modification_id=str(uuid.uuid4()),
                order_id=order_id,
                timestamp=datetime.now(),
                modification_type=modification_type,
                old_value=old_value,
                new_value=new_value,
                reason=reason
            )
            
            # Apply modification
            if modification_type == "quantity":
                if new_value <= order.filled_quantity:
                    raise ValueError("New quantity cannot be less than filled quantity")
                order.quantity = new_value
                order.remaining_quantity = new_value - order.filled_quantity
            elif modification_type == "price":
                order.price = new_value
            elif modification_type == "time_in_force":
                order.time_in_force = TimeInForce(new_value)
            else:
                setattr(order, modification_type, new_value)
            
            # Add to modification history
            order.add_modification(modification)
            
            # Queue for processing
            await self._processing_queue.put({
                'type': 'order_modified',
                'order_id': order_id,
                'modification': modification,
                'timestamp': time.time_ns()
            })
            
            self._metrics['modifications_processed'] += 1
            self.logger.info(f"Order modified: {order_id} - {modification_type}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to modify order {order_id}: {e}")
            return False
    
    async def cancel_order(self, order_id: str, reason: str = "") -> bool:
        """Cancel an order"""
        try:
            order = self._orders.get(order_id)
            if not order:
                raise ValueError(f"Order {order_id} not found")
            
            if not order.is_active():
                self.logger.warning(f"Order {order_id} is not active (status: {order.status})")
                return False
            
            # Update order status
            old_status = order.status
            order.status = OrderStatus.CANCELLED
            order.completion_time = datetime.now()
            
            # Create modification record
            modification = OrderModification(
                modification_id=str(uuid.uuid4()),
                order_id=order_id,
                timestamp=datetime.now(),
                modification_type="status",
                old_value=old_status.value,
                new_value=OrderStatus.CANCELLED.value,
                reason=reason
            )
            order.add_modification(modification)
            
            # Cancel child orders if this is a parent
            if order_id in self._orders_by_parent:
                for child_id in self._orders_by_parent[order_id]:
                    await self.cancel_order(child_id, f"Parent order {order_id} cancelled")
            
            # Queue for processing
            await self._processing_queue.put({
                'type': 'order_cancelled',
                'order_id': order_id,
                'reason': reason,
                'timestamp': time.time_ns()
            })
            
            self._metrics['orders_cancelled'] += 1
            self.logger.info(f"Order cancelled: {order_id} - {reason}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    async def update_order_status(self, 
                                 order_id: str, 
                                 new_status: OrderStatus,
                                 metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update order status"""
        try:
            order = self._orders.get(order_id)
            if not order:
                raise ValueError(f"Order {order_id} not found")
            
            old_status = order.status
            order.status = new_status
            
            # Update timestamps
            if new_status == OrderStatus.SUBMITTED and not order.submission_time:
                order.submission_time = datetime.now()
            elif new_status == OrderStatus.ACKNOWLEDGED and not order.acknowledgment_time:
                order.acknowledgment_time = datetime.now()
            elif new_status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                order.completion_time = datetime.now()
            
            # Record status change
            status_change = {
                'timestamp': datetime.now(),
                'old_status': old_status.value,
                'new_status': new_status.value,
                'metadata': metadata or {}
            }
            self._status_history[order_id].append(status_change)
            
            # Queue for processing
            await self._processing_queue.put({
                'type': 'status_updated',
                'order_id': order_id,
                'old_status': old_status.value,
                'new_status': new_status.value,
                'metadata': metadata,
                'timestamp': time.time_ns()
            })
            
            self.logger.info(f"Order status updated: {order_id} {old_status.value} -> {new_status.value}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update order status {order_id}: {e}")
            return False
    
    async def add_fill(self, order_id: str, fill: OrderFill) -> bool:
        """Add a fill to an order"""
        try:
            order = self._orders.get(order_id)
            if not order:
                raise ValueError(f"Order {order_id} not found")
            
            # Add fill to order
            order.add_fill(fill)
            
            # Record fill
            self._fill_history[order_id].append(fill)
            
            # Update execution quality metrics
            if order.execution_quality and self.enable_tca:
                await self._update_execution_quality(order, fill)
            
            # Queue for processing
            await self._processing_queue.put({
                'type': 'order_filled',
                'order_id': order_id,
                'fill': fill,
                'timestamp': time.time_ns()
            })
            
            if order.status == OrderStatus.FILLED:
                self._metrics['orders_filled'] += 1
            
            self.logger.info(f"Fill added to order {order_id}: {fill.quantity}@{fill.price}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add fill to order {order_id}: {e}")
            return False
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self._orders.get(order_id)
    
    def get_order_by_client_id(self, client_order_id: str) -> Optional[Order]:
        """Get order by client ID"""
        order_id = self._orders_by_client_id.get(client_order_id)
        return self._orders.get(order_id) if order_id else None
    
    def get_child_orders(self, parent_order_id: str) -> List[Order]:
        """Get child orders for a parent order"""
        child_ids = self._orders_by_parent.get(parent_order_id, [])
        return [self._orders[child_id] for child_id in child_ids if child_id in self._orders]
    
    def get_orders_by_strategy(self, strategy_id: str) -> List[Order]:
        """Get orders for a strategy"""
        order_ids = self._orders_by_strategy.get(strategy_id, [])
        return [self._orders[order_id] for order_id in order_ids if order_id in self._orders]
    
    def get_active_orders(self) -> List[Order]:
        """Get all active orders"""
        return [order for order in self._orders.values() if order.is_active()]
    
    def get_order_status_history(self, order_id: str) -> List[Dict[str, Any]]:
        """Get status change history for an order"""
        return self._status_history.get(order_id, [])
    
    def get_order_fills(self, order_id: str) -> List[OrderFill]:
        """Get fills for an order"""
        return self._fill_history.get(order_id, [])
    
    def get_execution_quality(self, order_id: str) -> Optional[OrderExecutionQuality]:
        """Get execution quality metrics for an order"""
        order = self._orders.get(order_id)
        return order.execution_quality if order else None
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        return {
            **self._metrics,
            'active_orders': len(self.get_active_orders()),
            'total_orders': len(self._orders),
            'orders_by_status': self._get_orders_by_status(),
            'avg_order_value': self._calculate_avg_order_value(),
            'fill_rate': self._calculate_fill_rate()
        }
    
    # Private methods
    
    def _validate_order(self, order: Order) -> None:
        """Validate order parameters"""
        if order.quantity <= 0:
            raise ValueError("Order quantity must be positive")
        
        if order.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and not order.price:
            raise ValueError(f"{order.order_type.value} orders require a price")
        
        if order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and not order.stop_price:
            raise ValueError(f"{order.order_type.value} orders require a stop price")
        
        if order.parent_order_id and order.parent_order_id not in self._orders:
            raise ValueError(f"Parent order {order.parent_order_id} not found")
    
    async def _order_processor(self):
        """Background worker for order processing"""
        while self._running:
            try:
                # Get processing request from queue
                try:
                    request = await asyncio.wait_for(
                        self._processing_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process the analysis request
                await self._process_order_event(request)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Order processor error: {e}")
                await asyncio.sleep(1)
    
    async def _process_order_event(self, event: Dict[str, Any]):
        """Process order lifecycle events"""
        try:
            event_type = event['type']
            order_id = event['order_id']
            
            # Send notifications
            if self.enable_notifications:
                await self._notification_queue.put(event)
            
            # Update metrics based on event type
            if event_type == 'order_filled':
                fill = event['fill']
                fill_latency = (time.time_ns() - event['timestamp']) / 1_000_000
                
                # Update average fill latency
                current_avg = self._metrics['avg_fill_latency_ms']
                total_fills = sum(len(fills) for fills in self._fill_history.values())
                self._metrics['avg_fill_latency_ms'] = (
                    (current_avg * (total_fills - 1) + fill_latency) / total_fills
                    if total_fills > 0 else fill_latency
                )
            
        except Exception as e:
            self.logger.error(f"Failed to process order event: {e}")
    
    async def _notification_processor(self):
        """Background worker for sending notifications"""
        while self._running:
            try:
                # Get notification request
                try:
                    event = await asyncio.wait_for(
                        self._notification_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Send notifications to subscribers
                await self._send_notifications(event)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Notification processor error: {e}")
                await asyncio.sleep(1)
    
    async def _send_notifications(self, event: Dict[str, Any]):
        """Send notifications to subscribers"""
        try:
            order_id = event['order_id']
            event_type = event['type']
            
            # Send status update notifications
            if event_type in ['status_updated', 'order_created', 'order_cancelled']:
                subscribers = self._status_subscribers.get(order_id, [])
                for callback in subscribers:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        self.logger.error(f"Notification callback error: {e}")
            
            # Send fill notifications
            if event_type == 'order_filled':
                subscribers = self._fill_subscribers.get(order_id, [])
                for callback in subscribers:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        self.logger.error(f"Fill notification callback error: {e}")
            
            self._metrics['notifications_sent'] += 1
            
        except Exception as e:
            self.logger.error(f"Failed to send notifications: {e}")
    
    async def _update_execution_quality(self, order: Order, fill: OrderFill):
        """Update execution quality metrics for a fill"""
        if not order.execution_quality:
            return
        
        eq = order.execution_quality
        
        # Update timing metrics
        if order.submission_time:
            eq.submission_latency_ms = (
                (fill.timestamp - order.creation_time).total_seconds() * 1000
            )
        
        if order.acknowledgment_time:
            eq.acknowledgment_latency_ms = (
                (order.acknowledgment_time - order.submission_time).total_seconds() * 1000
                if order.submission_time else 0
            )
        
        eq.fill_latency_ms = (
            (fill.timestamp - order.acknowledgment_time).total_seconds() * 1000
            if order.acknowledgment_time else 0
        )
        
        # Update price metrics
        eq.average_fill_price = order.average_fill_price
        eq.fill_rate = order.filled_quantity / order.quantity
        
        # Calculate slippage (simplified)
        if eq.arrival_price and eq.average_fill_price:
            if order.side == OrderSide.BUY:
                eq.slippage = (eq.average_fill_price - eq.arrival_price) / eq.arrival_price
            else:
                eq.slippage = (eq.arrival_price - eq.average_fill_price) / eq.arrival_price
    
    async def _metrics_collector(self):
        """Background worker for metrics collection"""
        while self._running:
            try:
                # Update real-time metrics
                active_orders = self.get_active_orders()
                self._metrics['active_orders'] = len(active_orders)
                self._metrics['total_orders'] = len(self._orders)
                
                await asyncio.sleep(10)  # Update every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics collector error: {e}")
                await asyncio.sleep(10)
    
    def _get_orders_by_status(self) -> Dict[str, int]:
        """Get order count by status"""
        status_counts = defaultdict(int)
        for order in self._orders.values():
            status_counts[order.status.value] += 1
        return dict(status_counts)
    
    def _calculate_avg_order_value(self) -> float:
        """Calculate average order value"""
        if not self._orders:
            return 0.0
        
        total_value = sum(
            order.quantity * (order.price or order.average_fill_price or 0)
            for order in self._orders.values()
        )
        return total_value / len(self._orders)
    
    def _calculate_fill_rate(self) -> float:
        """Calculate overall fill rate"""
        if not self._orders:
            return 0.0
        
        total_quantity = sum(order.quantity for order in self._orders.values())
        filled_quantity = sum(order.filled_quantity for order in self._orders.values())
        
        return filled_quantity / total_quantity if total_quantity > 0 else 0.0


# Test the order management system
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
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    asyncio.run(test_order_management())