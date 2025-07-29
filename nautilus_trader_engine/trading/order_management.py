"""
Advanced Order Management System
Comprehensive order lifecycle management with parent-child relationships, 
real-time tracking, and execution quality measurement
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

# Import core components
from ..core.messaging.message_bus import MessageBus
from ..core.caching.cache_manager import CacheManager


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
    - WebSocket notifications
    - Transaction Cost Analysis (TCA)
    """
    
    def __init__(self,
                 message_bus: Optional[MessageBus] = None,
                 cache_manager: Optional[CacheManager] = None,
                 enable_notifications: bool = True,
                 enable_tca: bool = True):
        
        self.message_bus = message_bus
        self.cache_manager = cache_manager
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
        
        # Thread pool for intensive calculations
        self._thread_pool = ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="order-lifecycle"
        )
        
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
            asyncio.create_task(self._tca_processor()),
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
        
        # Shutdown thread pool
        self._thread_pool.shutdown(wait=True)
        
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
            
            # Cache order
            if self.cache_manager:
                await self.cache_manager.set(f"order:{order.order_id}", order, ttl=3600)
            
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
            
            # Update cache
            if self.cache_manager:
                await self.cache_manager.set(f"order:{order_id}", order, ttl=3600)
            
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
            
            # Update cache
            if self.cache_manager:
                await self.cache_manager.set(f"order:{order_id}", order, ttl=3600)
            
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
            
            # Update cache
            if self.cache_manager:
                await self.cache_manager.set(f"order:{order_id}", order, ttl=3600)
            
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
            
            # Update cache
            if self.cache_manager:
                await self.cache_manager.set(f"order:{order_id}", order, ttl=3600)
            
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
    
    async def subscribe_to_status_updates(self, order_id: str, callback: Callable):
        """Subscribe to status updates for an order"""
        self._status_subscribers[order_id].append(callback)
    
    async def subscribe_to_fills(self, order_id: str, callback: Callable):
        """Subscribe to fill updates for an order"""
        self._fill_subscribers[order_id].append(callback)
    
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
                # Get processing request
                try:
                    request = await asyncio.wait_for(
                        self._processing_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process request
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
            
            # Publish to message bus
            if self.message_bus:
                await self.message_bus.publish(f"orders.{event_type}", event)
            
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
    
    async def _tca_processor(self):
        """Background worker for Transaction Cost Analysis"""
        if not self.enable_tca:
            return
        
        while self._running:
            try:
                # Process TCA for completed orders
                completed_orders = [
                    order for order in self._orders.values()
                    if order.is_complete() and order.execution_quality
                    and not hasattr(order.execution_quality, '_tca_processed')
                ]
                
                for order in completed_orders:
                    await self._calculate_comprehensive_tca(order)
                    order.execution_quality._tca_processed = True
                
                await asyncio.sleep(5)  # Run every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"TCA processor error: {e}")
                await asyncio.sleep(5)
    
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
    
    async def _calculate_comprehensive_tca(self, order: Order):
        """Calculate comprehensive Transaction Cost Analysis"""
        if not order.execution_quality or not order.fills:
            return
        
        eq = order.execution_quality
        
        # Calculate implementation shortfall
        if eq.arrival_price and eq.average_fill_price:
            if order.side == OrderSide.BUY:
                eq.implementation_shortfall = (
                    (eq.average_fill_price - eq.arrival_price) * order.filled_quantity
                )
            else:
                eq.implementation_shortfall = (
                    (eq.arrival_price - eq.average_fill_price) * order.filled_quantity
                )
        
        # Calculate market impact (simplified)
        eq.market_impact_bps = abs(eq.slippage) * 10000 if eq.slippage else 0
        
        # Update average execution quality score
        quality_score = self._calculate_execution_quality_score(eq)
        current_avg = self._metrics['avg_execution_quality_score']
        total_completed = len([o for o in self._orders.values() if o.is_complete()])
        self._metrics['avg_execution_quality_score'] = (
            (current_avg * (total_completed - 1) + quality_score) / total_completed
            if total_completed > 0 else quality_score
        )
    
    def _calculate_execution_quality_score(self, eq: OrderExecutionQuality) -> float:
        """Calculate overall execution quality score (0-1)"""
        score = 1.0
        
        # Penalize high latency
        if eq.fill_latency_ms > 1000:  # > 1 second
            score -= 0.2
        elif eq.fill_latency_ms > 500:  # > 500ms
            score -= 0.1
        
        # Penalize high slippage
        if abs(eq.slippage) > 0.01:  # > 1%
            score -= 0.3
        elif abs(eq.slippage) > 0.005:  # > 0.5%
            score -= 0.15
        
        # Reward high fill rate
        score += (eq.fill_rate - 0.5) * 0.2  # Bonus for >50% fill rate
        
        return max(0.0, min(1.0, score))
    
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


# Global order lifecycle manager instance
_order_manager_instance: Optional[OrderLifecycleManager] = None


def get_order_manager() -> OrderLifecycleManager:
    """Get global order lifecycle manager instance"""
    global _order_manager_instance
    if _order_manager_instance is None:
        raise RuntimeError("Order manager not initialized. Call initialize_order_manager() first.")
    return _order_manager_instance


def initialize_order_manager(
    message_bus: Optional[MessageBus] = None,
    cache_manager: Optional[CacheManager] = None,
    enable_notifications: bool = True,
    enable_tca: bool = True
) -> OrderLifecycleManager:
    """Initialize global order lifecycle manager instance"""
    global _order_manager_instance
    _order_manager_instance = OrderLifecycleManager(
        message_bus=message_bus,
        cache_manager=cache_manager,
        enable_notifications=enable_notifications,
        enable_tca=enable_tca
    )
    return _order_manager_instance


async def start_order_manager(**kwargs) -> OrderLifecycleManager:
    """Start order manager with configuration"""
    manager = initialize_order_manager(**kwargs)
    await manager.start()
    return manager


async def stop_order_manager():
    """Stop global order manager"""
    global _order_manager_instance
    if _order_manager_instance:
        await _order_manager_instance.stop()
        _order_manager_instance = None