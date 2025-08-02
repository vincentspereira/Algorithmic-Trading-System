#!/usr/bin/env python3
"""
Enhanced Order Management Integration Layer
Integrates the Enhanced Order Manager with the Order Execution Engine
and provides a unified interface for order management operations.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Set, Callable, Any, Union
from dataclasses import dataclass, field
from collections import defaultdict

# Import components
from order_execution_engine import (
    OrderExecutionEngine, VenueConfig, MarketData, OrderExecutionReport,
    ExecutionAlgorithm, VenueType, OrderType, OrderSide
)
from websocket_notifications import (
    WebSocketNotificationServer, OrderNotificationManager, NotificationType
)
from transaction_cost_analysis import (
    TransactionCostAnalyzer, MarketDataPoint, ExecutionData, OrderData as TCAOrderData
)
from order_flow_analytics import (
    OrderFlowAnalyzer, OrderFlowData, AnalyticsTimeframe, ReportType
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    """Enhanced order status tracking"""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"
    TRIGGERED = "TRIGGERED"
    REPLACED = "REPLACED"

class TimeInForce(Enum):
    """Time in force options"""
    GTC = "GTC"  # Good Till Cancelled
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill
    DAY = "DAY"  # Day order
    GTD = "GTD"  # Good Till Date

@dataclass
class RiskParameters:
    """Risk management parameters for orders"""
    max_order_value: Decimal = Decimal('1000000')
    max_position_size: Decimal = Decimal('100000')
    max_daily_loss: Decimal = Decimal('50000')
    allowed_symbols: Set[str] = field(default_factory=set)
    blocked_symbols: Set[str] = field(default_factory=set)
    max_orders_per_second: int = 10
    require_approval_above: Decimal = Decimal('100000')

@dataclass
class EnhancedOrder:
    """Enhanced order with comprehensive attributes"""
    order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: TimeInForce = TimeInForce.GTC
    status: OrderStatus = OrderStatus.PENDING
    created_time: datetime = field(default_factory=datetime.now)
    updated_time: datetime = field(default_factory=datetime.now)
    filled_quantity: Decimal = Decimal('0')
    remaining_quantity: Optional[Decimal] = None
    average_price: Optional[Decimal] = None
    commission: Decimal = Decimal('0')
    venue: str = "DEFAULT"
    account_id: str = "DEFAULT"
    strategy_id: Optional[str] = None
    parent_order_id: Optional[str] = None
    child_order_ids: List[str] = field(default_factory=list)
    tags: Dict[str, Any] = field(default_factory=dict)
    risk_checked: bool = False
    approval_required: bool = False
    approved_by: Optional[str] = None
    execution_reports: List[OrderExecutionReport] = field(default_factory=list)
    
    def __post_init__(self):
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity
    
    @property
    def is_active(self) -> bool:
        """Check if order is in active state"""
        return self.status in [
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.ACCEPTED,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.TRIGGERED
        ]
    
    @property
    def is_complete(self) -> bool:
        """Check if order is complete"""
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED
        ]
    
    @property
    def fill_percentage(self) -> float:
        """Calculate fill percentage"""
        if self.quantity == 0:
            return 0.0
        return float(self.filled_quantity / self.quantity * 100)

class OrderValidationError(Exception):
    """Order validation error"""
    pass

class RiskManagementError(Exception):
    """Risk management error"""
    pass

class EnhancedOrderManagementSystem:
    """
    Enhanced Order Management System that integrates order management
    with advanced execution capabilities
    """
    
    def __init__(self, risk_parameters: Optional[RiskParameters] = None, 
                 websocket_port: int = 8765):
        # Core components
        self.execution_engine = OrderExecutionEngine()
        self.risk_parameters = risk_parameters or RiskParameters()
        
        # New Task 16 components
        self.websocket_server = WebSocketNotificationServer(port=websocket_port)
        self.notification_manager = OrderNotificationManager(self.websocket_server)
        self.tca_analyzer = TransactionCostAnalyzer()
        self.flow_analyzer = OrderFlowAnalyzer()
        
        # Order storage and tracking
        self.orders: Dict[str, EnhancedOrder] = {}
        self.orders_by_symbol: Dict[str, Set[str]] = defaultdict(set)
        self.orders_by_strategy: Dict[str, Set[str]] = defaultdict(set)
        self.orders_by_account: Dict[str, Set[str]] = defaultdict(set)
        self.pending_approvals: Set[str] = set()
        
        # Risk management
        self.order_rate_limiter: Dict[str, List[float]] = defaultdict(list)
        self.daily_pnl: Dict[str, Decimal] = defaultdict(lambda: Decimal('0'))
        self.position_tracker: Dict[str, Decimal] = defaultdict(lambda: Decimal('0'))
        
        # Callbacks and monitoring
        self.order_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self.execution_callbacks: List[Callable] = []
        self.risk_callbacks: List[Callable] = []
        
        # System state
        self._running = False
        self._background_tasks: Set[asyncio.Task] = set()
        
        # Register execution engine callbacks
        self.execution_engine.register_execution_callback(self._on_execution_report)
        
        logger.info("Enhanced Order Management System initialized")
    
    async def start(self):
        """Start the order management system"""
        self._running = True
        
        # Start execution engine
        await self.execution_engine.start()
        
        # Start WebSocket server
        await self.websocket_server.start()
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._background_processor()),
            asyncio.create_task(self._risk_monitor()),
            asyncio.create_task(self._order_lifecycle_monitor()),
            asyncio.create_task(self._market_data_processor())
        ]
        
        for task in tasks:
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
        
        logger.info("Enhanced Order Management System started")
    
    async def stop(self):
        """Stop the order management system"""
        self._running = False
        
        # Stop execution engine
        await self.execution_engine.stop()
        
        # Stop WebSocket server
        await self.websocket_server.stop()
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        logger.info("Enhanced Order Management System stopped")
    
    async def submit_order(self, order: EnhancedOrder) -> str:
        """Submit an order with comprehensive validation and risk management"""
        logger.info(f"Submitting order: {order.order_id} for {order.symbol}")
        
        try:
            # Validate order
            await self._validate_order(order)
            
            # Risk management checks
            await self._risk_check_order(order)
            
            # Rate limiting check
            await self._check_rate_limits(order)
            
            # Store order
            self.orders[order.order_id] = order
            self.orders_by_symbol[order.symbol].add(order.order_id)
            if order.strategy_id:
                self.orders_by_strategy[order.strategy_id].add(order.order_id)
            self.orders_by_account[order.account_id].add(order.order_id)
            
            # Check if approval required
            if order.approval_required:
                order.status = OrderStatus.PENDING
                self.pending_approvals.add(order.order_id)
                logger.info(f"Order {order.order_id} requires approval")
            else:
                # Submit to execution engine
                await self._submit_to_execution_engine(order)
            
            # Trigger callbacks
            await self._trigger_order_callbacks(order.order_id, "submitted")
            
            # Send WebSocket notification
            await self._send_order_notification("submitted", order)
            
            # Add to TCA and flow analytics
            await self._add_to_analytics(order)
            
            logger.info(f"Order {order.order_id} submitted successfully")
            return order.order_id
            
        except Exception as e:
            order.status = OrderStatus.REJECTED
            logger.error(f"Order submission failed: {e}")
            await self._trigger_order_callbacks(order.order_id, "rejected")
            raise
    
    async def _validate_order(self, order: EnhancedOrder):
        """Validate order parameters"""
        if order.quantity <= 0:
            raise OrderValidationError("Order quantity must be positive")
        
        if order.order_type == OrderType.LIMIT and order.price is None:
            raise OrderValidationError("Limit orders require a price")
        
        if order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and order.stop_price is None:
            raise OrderValidationError("Stop orders require a stop price")
        
        if order.symbol in self.risk_parameters.blocked_symbols:
            raise OrderValidationError(f"Symbol {order.symbol} is blocked")
        
        if (self.risk_parameters.allowed_symbols and 
            order.symbol not in self.risk_parameters.allowed_symbols):
            raise OrderValidationError(f"Symbol {order.symbol} is not allowed")
    
    async def _risk_check_order(self, order: EnhancedOrder):
        """Perform risk management checks"""
        order_value = order.quantity * (order.price or Decimal('0'))
        
        # Check maximum order value
        if order_value > self.risk_parameters.max_order_value:
            raise RiskManagementError(f"Order value {order_value} exceeds maximum {self.risk_parameters.max_order_value}")
        
        # Check position limits
        current_position = self.position_tracker[order.symbol]
        new_position = current_position + (order.quantity if order.side == OrderSide.BUY else -order.quantity)
        
        if abs(new_position) > self.risk_parameters.max_position_size:
            raise RiskManagementError(f"Position size {new_position} would exceed maximum {self.risk_parameters.max_position_size}")
        
        # Check daily loss limits
        account_pnl = self.daily_pnl[order.account_id]
        if account_pnl < -self.risk_parameters.max_daily_loss:
            raise RiskManagementError(f"Daily loss limit exceeded: {account_pnl}")
        
        # Check if approval required
        if order_value > self.risk_parameters.require_approval_above:
            order.approval_required = True
        
        order.risk_checked = True
        
        # Trigger risk callbacks
        for callback in self.risk_callbacks:
            try:
                await callback(order, "risk_checked")
            except Exception as e:
                logger.error(f"Risk callback error: {e}")
    
    async def _check_rate_limits(self, order: EnhancedOrder):
        """Check rate limiting"""
        current_time = time.time()
        account_rates = self.order_rate_limiter[order.account_id]
        
        # Remove old entries (older than 1 second)
        account_rates[:] = [t for t in account_rates if current_time - t < 1.0]
        
        if len(account_rates) >= self.risk_parameters.max_orders_per_second:
            raise RiskManagementError("Rate limit exceeded")
        
        account_rates.append(current_time)
    
    async def _submit_to_execution_engine(self, order: EnhancedOrder):
        """Submit order to execution engine"""
        # Convert to execution engine order format
        execution_order = self._convert_to_execution_order(order)
        
        # Submit to execution engine
        execution_reports = await self.execution_engine.execute_order(execution_order)
        
        # Process execution reports
        for report in execution_reports:
            await self._process_execution_report(report)
        
        # Set status based on execution results
        if execution_reports:
            # If we got execution reports, order was at least partially executed
            if order.filled_quantity >= order.quantity:
                order.status = OrderStatus.FILLED
            else:
                order.status = OrderStatus.PARTIALLY_FILLED
        else:
            # No execution reports means order is waiting (e.g., limit order waiting for price)
            order.status = OrderStatus.ACCEPTED
        
        order.updated_time = datetime.now()
        
        logger.info(f"Order {order.order_id} submitted to execution engine")
    
    def _convert_to_execution_order(self, order: EnhancedOrder):
        """Convert enhanced order to execution engine order format"""
        from order_execution_engine import EnhancedOrder as ExecutionOrder
        
        return ExecutionOrder(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            price=order.price,
            stop_price=order.stop_price
        )
    
    async def _process_execution_report(self, execution_report: OrderExecutionReport):
        """Process execution report from execution engine"""
        order_id = execution_report.order_id
        
        if order_id not in self.orders:
            logger.warning(f"Received execution report for unknown order: {order_id}")
            return
        
        order = self.orders[order_id]
        
        # Update order with execution
        order.filled_quantity += execution_report.quantity
        order.remaining_quantity = order.quantity - order.filled_quantity
        order.commission += execution_report.commission
        order.execution_reports.append(execution_report)
        order.updated_time = datetime.now()
        
        # Calculate average price
        if order.execution_reports:
            total_value = sum(er.quantity * er.price for er in order.execution_reports)
            total_quantity = sum(er.quantity for er in order.execution_reports)
            order.average_price = total_value / total_quantity if total_quantity > 0 else None
        
        # Update order status
        if order.remaining_quantity <= 0:
            order.status = OrderStatus.FILLED
        else:
            order.status = OrderStatus.PARTIALLY_FILLED
        
        # Update position tracking
        position_change = execution_report.quantity if order.side == OrderSide.BUY else -execution_report.quantity
        self.position_tracker[order.symbol] += position_change
        
        # Update P&L tracking (simplified)
        pnl_impact = position_change * execution_report.price
        if order.side == OrderSide.SELL:
            pnl_impact = -pnl_impact
        self.daily_pnl[order.account_id] += pnl_impact
        
        # Add execution data to TCA
        tca_execution_data = ExecutionData(
            execution_id=execution_report.execution_id,
            order_id=order_id,
            timestamp=execution_report.timestamp,
            symbol=execution_report.symbol,
            side=execution_report.side.value,
            quantity=execution_report.quantity,
            price=execution_report.price,
            venue=execution_report.venue,
            commission=execution_report.commission
        )
        self.tca_analyzer.add_execution_data(tca_execution_data)
        
        # Send execution notification
        execution_data = {
            'execution_id': execution_report.execution_id,
            'quantity': str(execution_report.quantity),
            'price': str(execution_report.price),
            'venue': execution_report.venue,
            'timestamp': execution_report.timestamp.isoformat()
        }
        await self.notification_manager.notify_execution_report(execution_data)
        
        # Update flow analytics
        await self._add_to_analytics(order)
        
        # Trigger callbacks
        await self._trigger_order_callbacks(order_id, "executed")
        for callback in self.execution_callbacks:
            try:
                await callback(order, execution_report)
            except Exception as e:
                logger.error(f"Execution callback error: {e}")
        
        logger.info(f"Order {order_id} executed: {execution_report.quantity} @ {execution_report.price}")
    
    async def _on_execution_report(self, order, execution_reports: List[OrderExecutionReport]):
        """Callback for execution reports from execution engine"""
        for report in execution_reports:
            await self._process_execution_report(report)
    
    async def cancel_order(self, order_id: str, reason: str = "User requested") -> bool:
        """Cancel an order"""
        if order_id not in self.orders:
            logger.warning(f"Order {order_id} not found for cancellation")
            return False
        
        order = self.orders[order_id]
        
        if not order.is_active:
            logger.warning(f"Order {order_id} is not active, cannot cancel")
            return False
        
        # Update order status
        order.status = OrderStatus.CANCELLED
        order.updated_time = datetime.now()
        order.tags['cancellation_reason'] = reason
        
        # Remove from pending approvals if applicable
        self.pending_approvals.discard(order_id)
        
        await self._trigger_order_callbacks(order_id, "cancelled")
        
        logger.info(f"Order {order_id} cancelled: {reason}")
        return True
    
    async def modify_order(self, order_id: str, new_quantity: Optional[Decimal] = None, 
                          new_price: Optional[Decimal] = None) -> bool:
        """Modify an existing order"""
        if order_id not in self.orders:
            logger.warning(f"Order {order_id} not found for modification")
            return False
        
        order = self.orders[order_id]
        
        if not order.is_active:
            logger.warning(f"Order {order_id} is not active, cannot modify")
            return False
        
        # Create modified order
        old_quantity = order.quantity
        old_price = order.price
        
        if new_quantity is not None:
            if new_quantity < order.filled_quantity:
                raise OrderValidationError("New quantity cannot be less than filled quantity")
            order.quantity = new_quantity
            order.remaining_quantity = new_quantity - order.filled_quantity
        
        if new_price is not None:
            order.price = new_price
        
        # Re-validate modified order
        try:
            await self._validate_order(order)
            await self._risk_check_order(order)
        except Exception as e:
            # Revert changes
            order.quantity = old_quantity
            order.price = old_price
            order.remaining_quantity = old_quantity - order.filled_quantity
            raise
        
        order.status = OrderStatus.REPLACED
        order.updated_time = datetime.now()
        
        await self._trigger_order_callbacks(order_id, "modified")
        
        logger.info(f"Order {order_id} modified successfully")
        return True
    
    async def approve_order(self, order_id: str, approver: str) -> bool:
        """Approve a pending order"""
        if order_id not in self.orders:
            logger.warning(f"Order {order_id} not found for approval")
            return False
        
        if order_id not in self.pending_approvals:
            logger.warning(f"Order {order_id} does not require approval")
            return False
        
        order = self.orders[order_id]
        order.approved_by = approver
        order.approval_required = False
        self.pending_approvals.remove(order_id)
        
        # Submit to execution engine
        await self._submit_to_execution_engine(order)
        
        await self._trigger_order_callbacks(order_id, "approved")
        
        logger.info(f"Order {order_id} approved by {approver}")
        return True
    
    async def _background_processor(self):
        """Background processor for order management tasks"""
        while self._running:
            try:
                await self._process_expired_orders()
                await self._process_conditional_orders()
                await self._cleanup_rate_limiters()
                await asyncio.sleep(1)  # Process every second
            except Exception as e:
                logger.error(f"Background processor error: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    async def _risk_monitor(self):
        """Monitor risk parameters and positions"""
        while self._running:
            try:
                # Monitor position limits
                for symbol, position in self.position_tracker.items():
                    if abs(position) > self.risk_parameters.max_position_size * Decimal('0.9'):
                        logger.warning(f"Position for {symbol} approaching limit: {position}")
                
                # Monitor daily P&L
                for account_id, pnl in self.daily_pnl.items():
                    if pnl < -self.risk_parameters.max_daily_loss * Decimal('0.8'):
                        logger.warning(f"Account {account_id} approaching daily loss limit: {pnl}")
                
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Risk monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _order_lifecycle_monitor(self):
        """Monitor order lifecycle and status"""
        while self._running:
            try:
                # Monitor order timeouts and status changes
                current_time = datetime.now()
                
                for order in self.orders.values():
                    if order.is_active:
                        # Check for stale orders
                        if (current_time - order.updated_time).total_seconds() > 3600:  # 1 hour
                            logger.warning(f"Order {order.order_id} has been active for over 1 hour")
                
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Order lifecycle monitor error: {e}")
                await asyncio.sleep(120)
    
    async def _process_expired_orders(self):
        """Process expired orders"""
        current_time = datetime.now()
        
        for order in self.orders.values():
            if not order.is_active:
                continue
            
            # Check DAY orders
            if (order.time_in_force == TimeInForce.DAY and 
                current_time.date() > order.created_time.date()):
                order.status = OrderStatus.EXPIRED
                order.updated_time = current_time
                await self._trigger_order_callbacks(order.order_id, "expired")
                logger.info(f"Order {order.order_id} expired (DAY)")
            
            # Check GTD orders (if expiry date is set in tags)
            elif (order.time_in_force == TimeInForce.GTD and 
                  'expiry_date' in order.tags):
                expiry_date = order.tags['expiry_date']
                if isinstance(expiry_date, str):
                    expiry_date = datetime.fromisoformat(expiry_date)
                if current_time > expiry_date:
                    order.status = OrderStatus.EXPIRED
                    order.updated_time = current_time
                    await self._trigger_order_callbacks(order.order_id, "expired")
                    logger.info(f"Order {order.order_id} expired (GTD)")
    
    async def _process_conditional_orders(self):
        """Process conditional orders (simplified implementation)"""
        # This would integrate with market data to trigger conditional orders
        # For now, just a placeholder
        pass
    
    async def _cleanup_rate_limiters(self):
        """Clean up old rate limiter entries"""
        current_time = time.time()
        for account_id in self.order_rate_limiter:
            rates = self.order_rate_limiter[account_id]
            rates[:] = [t for t in rates if current_time - t < 60]  # Keep last minute
    
    def register_order_callback(self, order_id: str, callback: Callable):
        """Register callback for specific order events"""
        self.order_callbacks[order_id].append(callback)
    
    def register_execution_callback(self, callback: Callable):
        """Register callback for execution events"""
        self.execution_callbacks.append(callback)
    
    def register_risk_callback(self, callback: Callable):
        """Register callback for risk events"""
        self.risk_callbacks.append(callback)
    
    async def _trigger_order_callbacks(self, order_id: str, event_type: str):
        """Trigger callbacks for order events"""
        for callback in self.order_callbacks[order_id]:
            try:
                await callback(self.orders[order_id], event_type)
            except Exception as e:
                logger.error(f"Order callback error: {e}")
    
    # Query methods
    def get_order(self, order_id: str) -> Optional[EnhancedOrder]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_orders_by_symbol(self, symbol: str) -> List[EnhancedOrder]:
        """Get all orders for a symbol"""
        order_ids = self.orders_by_symbol.get(symbol, set())
        return [self.orders[oid] for oid in order_ids if oid in self.orders]
    
    def get_orders_by_strategy(self, strategy_id: str) -> List[EnhancedOrder]:
        """Get all orders for a strategy"""
        order_ids = self.orders_by_strategy.get(strategy_id, set())
        return [self.orders[oid] for oid in order_ids if oid in self.orders]
    
    def get_active_orders(self) -> List[EnhancedOrder]:
        """Get all active orders"""
        return [order for order in self.orders.values() if order.is_active]
    
    def get_pending_approvals(self) -> List[EnhancedOrder]:
        """Get orders pending approval"""
        return [self.orders[oid] for oid in self.pending_approvals if oid in self.orders]
    
    def get_positions(self) -> Dict[str, Decimal]:
        """Get current positions"""
        return dict(self.position_tracker)
    
    def get_daily_pnl(self) -> Dict[str, Decimal]:
        """Get daily P&L by account"""
        return dict(self.daily_pnl)
    
    def get_order_statistics(self) -> Dict[str, Any]:
        """Get order statistics"""
        total_orders = len(self.orders)
        active_orders = len(self.get_active_orders())
        pending_approvals = len(self.pending_approvals)
        
        status_counts = defaultdict(int)
        for order in self.orders.values():
            status_counts[order.status.value] += 1
        
        return {
            "total_orders": total_orders,
            "active_orders": active_orders,
            "pending_approvals": pending_approvals,
            "status_breakdown": dict(status_counts),
            "symbols_traded": len(self.orders_by_symbol),
            "strategies_active": len(self.orders_by_strategy),
            "accounts_active": len(self.orders_by_account),
            "execution_stats": self.execution_engine.get_execution_statistics(),
            "venue_status": self.execution_engine.get_venue_status()
        }
    
    # Venue management
    def add_venue(self, venue_config: VenueConfig):
        """Add a new trading venue"""
        self.execution_engine.add_venue(venue_config)
    
    def remove_venue(self, venue_id: str):
        """Remove a trading venue"""
        self.execution_engine.remove_venue(venue_id)
    
    def update_market_data(self, symbol: str, market_data: MarketData):
        """Update market data for a symbol"""
        self.execution_engine.update_market_data(symbol, market_data)
        
        # Also update TCA analyzer
        tca_market_data = MarketDataPoint(
            timestamp=datetime.now(),
            symbol=symbol,
            bid_price=market_data.bid_price,
            ask_price=market_data.ask_price,
            mid_price=market_data.mid_price,
            volume=market_data.volume
        )
        self.tca_analyzer.add_market_data(tca_market_data)
    
    async def _send_order_notification(self, event_type: str, order: EnhancedOrder):
        """Send WebSocket notification for order event"""
        order_data = {
            'order_id': order.order_id,
            'symbol': order.symbol,
            'side': order.side.value,
            'quantity': str(order.quantity),
            'price': str(order.price) if order.price else None,
            'status': order.status.value,
            'account_id': order.account_id,
            'strategy_id': order.strategy_id,
            'timestamp': order.updated_time.isoformat()
        }
        
        if event_type == "submitted":
            await self.notification_manager.notify_order_submitted(order_data)
        elif event_type == "accepted":
            await self.notification_manager.notify_order_accepted(order_data)
        elif event_type == "rejected":
            await self.notification_manager.notify_order_rejected(order_data, "Risk check failed")
        elif event_type == "filled":
            execution_data = {
                'filled_quantity': str(order.filled_quantity),
                'average_price': str(order.average_price) if order.average_price else None,
                'commission': str(order.commission)
            }
            await self.notification_manager.notify_order_filled(order_data, execution_data)
        elif event_type == "cancelled":
            reason = order.tags.get('cancellation_reason', 'Unknown')
            await self.notification_manager.notify_order_cancelled(order_data, reason)
        elif event_type == "modified":
            changes = {'modified_at': datetime.now().isoformat()}
            await self.notification_manager.notify_order_modified(order_data, changes)
    
    async def _add_to_analytics(self, order: EnhancedOrder):
        """Add order to TCA and flow analytics"""
        # Add to TCA analyzer
        tca_order_data = TCAOrderData(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side.value,
            original_quantity=order.quantity,
            order_type=order.order_type.value,
            limit_price=order.price,
            arrival_time=order.created_time,
            decision_time=order.created_time,
            account_id=order.account_id
        )
        self.tca_analyzer.add_order_data(tca_order_data)
        
        # Add to flow analyzer (when order is filled)
        if order.status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]:
            flow_data = OrderFlowData(
                timestamp=order.updated_time,
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side.value,
                order_type=order.order_type.value,
                quantity=order.quantity,
                price=order.price,
                filled_quantity=order.filled_quantity,
                average_fill_price=order.average_price,
                venue=order.venue,
                algorithm="DIRECT",  # Default algorithm
                execution_time=order.updated_time - order.created_time,
                commission=order.commission,
                market_impact_bps=None,  # Would be calculated
                account_id=order.account_id,
                strategy_id=order.strategy_id,
                status=order.status.value
            )
            self.flow_analyzer.add_order_flow_data(flow_data)
    
    async def _market_data_processor(self):
        """Process market data updates for analytics"""
        while self._running:
            try:
                # This would normally receive real market data
                # For now, just simulate periodic updates
                await asyncio.sleep(60)  # Update every minute
            except Exception as e:
                logger.error(f"Market data processor error: {e}")
                await asyncio.sleep(60)
    
    async def get_tca_analysis(self, order_id: str):
        """Get TCA analysis for an order"""
        return await self.tca_analyzer.analyze_order(order_id)
    
    async def get_flow_analytics(self, timeframe: AnalyticsTimeframe = AnalyticsTimeframe.HOUR):
        """Get order flow analytics"""
        return await self.flow_analyzer.calculate_analytics(timeframe)
    
    async def generate_analytics_report(self, report_type: ReportType = ReportType.EXECUTIVE_SUMMARY):
        """Generate analytics report"""
        return await self.flow_analyzer.generate_report(report_type)
    
    def get_websocket_stats(self):
        """Get WebSocket server statistics"""
        return self.websocket_server.get_server_stats()
    
    def get_notification_history(self, limit: int = 100):
        """Get notification history"""
        return self.notification_manager.get_notification_history(limit)

# Factory functions for common order types
def create_market_order(symbol: str, side: OrderSide, quantity: Decimal, 
                       account_id: str = "DEFAULT", strategy_id: Optional[str] = None) -> EnhancedOrder:
    """Create a market order"""
    return EnhancedOrder(
        order_id=str(uuid.uuid4()),
        client_order_id=f"MKT_{int(time.time() * 1000)}",
        symbol=symbol,
        side=side,
        order_type=OrderType.MARKET,
        quantity=quantity,
        time_in_force=TimeInForce.IOC,
        account_id=account_id,
        strategy_id=strategy_id
    )

def create_limit_order(symbol: str, side: OrderSide, quantity: Decimal, price: Decimal,
                      account_id: str = "DEFAULT", strategy_id: Optional[str] = None,
                      time_in_force: TimeInForce = TimeInForce.GTC) -> EnhancedOrder:
    """Create a limit order"""
    return EnhancedOrder(
        order_id=str(uuid.uuid4()),
        client_order_id=f"LMT_{int(time.time() * 1000)}",
        symbol=symbol,
        side=side,
        order_type=OrderType.LIMIT,
        quantity=quantity,
        price=price,
        time_in_force=time_in_force,
        account_id=account_id,
        strategy_id=strategy_id
    )

def create_stop_order(symbol: str, side: OrderSide, quantity: Decimal, stop_price: Decimal,
                     account_id: str = "DEFAULT", strategy_id: Optional[str] = None) -> EnhancedOrder:
    """Create a stop order"""
    return EnhancedOrder(
        order_id=str(uuid.uuid4()),
        client_order_id=f"STP_{int(time.time() * 1000)}",
        symbol=symbol,
        side=side,
        order_type=OrderType.STOP,
        quantity=quantity,
        stop_price=stop_price,
        account_id=account_id,
        strategy_id=strategy_id
    )

async def main():
    """Example usage of Enhanced Order Management System"""
    # Initialize risk parameters
    risk_params = RiskParameters(
        max_order_value=Decimal('500000'),
        max_position_size=Decimal('50000'),
        allowed_symbols={'EURUSD', 'GBPUSD', 'USDJPY'},
        max_orders_per_second=5
    )
    
    # Create order management system
    oms = EnhancedOrderManagementSystem(risk_params)
    
    try:
        # Start the system
        await oms.start()
        
        # Create and submit orders
        market_order = create_market_order('EURUSD', OrderSide.BUY, Decimal('10000'))
        limit_order = create_limit_order('GBPUSD', OrderSide.SELL, Decimal('5000'), Decimal('1.2500'))
        
        # Submit orders
        await oms.submit_order(market_order)
        await oms.submit_order(limit_order)
        
        # Wait for execution
        await asyncio.sleep(5)
        
        # Print statistics
        stats = oms.get_order_statistics()
        print(f"Order Statistics: {stats}")
        
        # Print positions
        positions = oms.get_positions()
        print(f"Positions: {positions}")
        
        # Print P&L
        pnl = oms.get_daily_pnl()
        print(f"Daily P&L: {pnl}")
        
        # Wait a bit more
        await asyncio.sleep(5)
        
    finally:
        # Stop the system
        await oms.stop()

if __name__ == "__main__":
    asyncio.run(main())