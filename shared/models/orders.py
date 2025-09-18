"""Order models for the algorithmic trading system.

This module provides data structures for orders, order management,
and order lifecycle tracking.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class Side(Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    ICEBERG = "iceberg"
    TWAP = "twap"
    VWAP = "vwap"
    BRACKET = "bracket"


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    WORKING = "working"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class TimeInForce(Enum):
    """Time in force enumeration."""
    DAY = "day"
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate Or Cancel
    FOK = "fok"  # Fill Or Kill
    GTD = "gtd"  # Good Till Date
    OPG = "opg"  # At The Opening
    CLS = "cls"  # At The Close


class OrderCondition(Enum):
    """Order condition enumeration."""
    NONE = "none"
    ONE_CANCELS_OTHER = "oco"
    BRACKET = "bracket"
    TRAILING_STOP = "trailing_stop"


@dataclass
class OrderFill:
    """Represents an order fill/execution."""
    fill_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = ""
    symbol: str = ""
    side: Side = Side.BUY
    quantity: Decimal = Decimal('0')
    price: Decimal = Decimal('0')
    timestamp: datetime = field(default_factory=datetime.utcnow)
    exchange: Optional[str] = None
    commission: Decimal = Decimal('0')
    fees: Decimal = Decimal('0')
    liquidity: Optional[str] = None  # "maker" or "taker"
    
    @property
    def value(self) -> Decimal:
        """Calculate fill value."""
        return self.quantity * self.price
    
    @property
    def net_value(self) -> Decimal:
        """Calculate net fill value after fees."""
        return self.value - self.commission - self.fees
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "fill_id": self.fill_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": float(self.quantity),
            "price": float(self.price),
            "timestamp": self.timestamp.isoformat(),
            "exchange": self.exchange,
            "commission": float(self.commission),
            "fees": float(self.fees),
            "liquidity": self.liquidity,
            "value": float(self.value),
            "net_value": float(self.net_value)
        }


@dataclass
class Order:
    """Represents a trading order."""
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_order_id: Optional[str] = None
    symbol: str = ""
    side: Side = Side.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: Decimal = Decimal('0')
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Execution details
    filled_quantity: Decimal = Decimal('0')
    remaining_quantity: Optional[Decimal] = None
    average_fill_price: Optional[Decimal] = None
    fills: List[OrderFill] = field(default_factory=list)
    
    # Order conditions and parameters
    condition: OrderCondition = OrderCondition.NONE
    parent_order_id: Optional[str] = None
    child_order_ids: List[str] = field(default_factory=list)
    
    # Fees and commissions
    commission: Decimal = Decimal('0')
    fees: Decimal = Decimal('0')
    
    # Exchange and routing
    exchange: Optional[str] = None
    route: Optional[str] = None
    
    # Metadata
    strategy_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    account_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Error handling
    rejection_reason: Optional[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity
    
    @property
    def is_buy(self) -> bool:
        """Check if order is a buy order."""
        return self.side == Side.BUY
    
    @property
    def is_sell(self) -> bool:
        """Check if order is a sell order."""
        return self.side == Side.SELL
    
    @property
    def is_market_order(self) -> bool:
        """Check if order is a market order."""
        return self.order_type == OrderType.MARKET
    
    @property
    def is_limit_order(self) -> bool:
        """Check if order is a limit order."""
        return self.order_type == OrderType.LIMIT
    
    @property
    def is_stop_order(self) -> bool:
        """Check if order is a stop order."""
        return self.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]
    
    @property
    def is_active(self) -> bool:
        """Check if order is in an active state."""
        return self.status in [
            OrderStatus.SUBMITTED,
            OrderStatus.ACCEPTED,
            OrderStatus.WORKING,
            OrderStatus.PARTIALLY_FILLED
        ]
    
    @property
    def is_terminal(self) -> bool:
        """Check if order is in a terminal state."""
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED
        ]
    
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_partially_filled(self) -> bool:
        """Check if order is partially filled."""
        return self.status == OrderStatus.PARTIALLY_FILLED
    
    @property
    def fill_percentage(self) -> Decimal:
        """Calculate fill percentage."""
        if self.quantity == 0:
            return Decimal('0')
        return (self.filled_quantity / self.quantity) * 100
    
    @property
    def total_value(self) -> Decimal:
        """Calculate total order value."""
        if self.is_market_order or not self.price:
            return Decimal('0')  # Cannot calculate for market orders without fill price
        return self.quantity * self.price
    
    @property
    def filled_value(self) -> Decimal:
        """Calculate filled value."""
        return sum(fill.value for fill in self.fills)
    
    @property
    def net_filled_value(self) -> Decimal:
        """Calculate net filled value after fees."""
        return sum(fill.net_value for fill in self.fills)
    
    def add_fill(self, fill: OrderFill) -> None:
        """Add a fill to the order."""
        fill.order_id = self.order_id
        self.fills.append(fill)
        
        # Update filled quantity
        self.filled_quantity += fill.quantity
        self.remaining_quantity = self.quantity - self.filled_quantity
        
        # Update average fill price
        total_filled_value = sum(f.value for f in self.fills)
        if self.filled_quantity > 0:
            self.average_fill_price = total_filled_value / self.filled_quantity
        
        # Update commission and fees
        self.commission += fill.commission
        self.fees += fill.fees
        
        # Update status
        if self.remaining_quantity <= 0:
            self.status = OrderStatus.FILLED
            self.filled_at = fill.timestamp
        elif self.filled_quantity > 0:
            self.status = OrderStatus.PARTIALLY_FILLED
        
        self.updated_at = fill.timestamp
        
        logger.info(f"Fill added to order {self.order_id}: {fill.quantity}@{fill.price}")
    
    def cancel(self, reason: Optional[str] = None) -> None:
        """Cancel the order."""
        if self.is_terminal:
            raise ValueError(f"Cannot cancel order in terminal state: {self.status}")
        
        self.status = OrderStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()
        self.updated_at = self.cancelled_at
        
        if reason:
            self.metadata["cancellation_reason"] = reason
        
        logger.info(f"Order {self.order_id} cancelled: {reason or 'No reason provided'}")
    
    def reject(self, reason: str) -> None:
        """Reject the order."""
        self.status = OrderStatus.REJECTED
        self.rejection_reason = reason
        self.updated_at = datetime.utcnow()
        
        logger.warning(f"Order {self.order_id} rejected: {reason}")
    
    def expire(self) -> None:
        """Expire the order."""
        if self.is_terminal:
            return
        
        self.status = OrderStatus.EXPIRED
        self.updated_at = datetime.utcnow()
        
        logger.info(f"Order {self.order_id} expired")
    
    def update_status(self, new_status: OrderStatus, timestamp: Optional[datetime] = None) -> None:
        """Update order status."""
        old_status = self.status
        self.status = new_status
        self.updated_at = timestamp or datetime.utcnow()
        
        # Set specific timestamps based on status
        if new_status == OrderStatus.SUBMITTED and not self.submitted_at:
            self.submitted_at = self.updated_at
        elif new_status == OrderStatus.FILLED and not self.filled_at:
            self.filled_at = self.updated_at
        elif new_status == OrderStatus.CANCELLED and not self.cancelled_at:
            self.cancelled_at = self.updated_at
        
        logger.info(f"Order {self.order_id} status changed: {old_status.value} -> {new_status.value}")
    
    def validate(self) -> List[str]:
        """Validate order parameters."""
        errors = []
        
        if not self.symbol:
            errors.append("Symbol is required")
        
        if self.quantity <= 0:
            errors.append("Quantity must be positive")
        
        if self.is_limit_order and (not self.price or self.price <= 0):
            errors.append("Limit orders require a positive price")
        
        if self.is_stop_order and (not self.stop_price or self.stop_price <= 0):
            errors.append("Stop orders require a positive stop price")
        
        if self.order_type == OrderType.STOP_LIMIT:
            if not self.price or self.price <= 0:
                errors.append("Stop limit orders require a positive limit price")
            if not self.stop_price or self.stop_price <= 0:
                errors.append("Stop limit orders require a positive stop price")
        
        if self.time_in_force == TimeInForce.GTD and not self.expires_at:
            errors.append("GTD orders require an expiration date")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if order is valid."""
        return len(self.validate()) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": float(self.quantity),
            "price": float(self.price) if self.price else None,
            "stop_price": float(self.stop_price) if self.stop_price else None,
            "time_in_force": self.time_in_force.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "filled_quantity": float(self.filled_quantity),
            "remaining_quantity": float(self.remaining_quantity) if self.remaining_quantity else None,
            "average_fill_price": float(self.average_fill_price) if self.average_fill_price else None,
            "fills": [fill.to_dict() for fill in self.fills],
            "condition": self.condition.value,
            "parent_order_id": self.parent_order_id,
            "child_order_ids": self.child_order_ids,
            "commission": float(self.commission),
            "fees": float(self.fees),
            "exchange": self.exchange,
            "route": self.route,
            "strategy_id": self.strategy_id,
            "portfolio_id": self.portfolio_id,
            "account_id": self.account_id,
            "tags": self.tags,
            "metadata": self.metadata,
            "rejection_reason": self.rejection_reason,
            "error_message": self.error_message,
            "fill_percentage": float(self.fill_percentage),
            "total_value": float(self.total_value),
            "filled_value": float(self.filled_value),
            "net_filled_value": float(self.net_filled_value)
        }
    
    @classmethod
    def create_market_order(cls, symbol: str, side: Side, quantity: Decimal, **kwargs) -> "Order":
        """Create a market order."""
        return cls(
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            **kwargs
        )
    
    @classmethod
    def create_limit_order(cls, symbol: str, side: Side, quantity: Decimal, price: Decimal, **kwargs) -> "Order":
        """Create a limit order."""
        return cls(
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=price,
            **kwargs
        )
    
    @classmethod
    def create_stop_order(cls, symbol: str, side: Side, quantity: Decimal, stop_price: Decimal, **kwargs) -> "Order":
        """Create a stop order."""
        return cls(
            symbol=symbol,
            side=side,
            order_type=OrderType.STOP,
            quantity=quantity,
            stop_price=stop_price,
            **kwargs
        )
    
    @classmethod
    def create_stop_limit_order(cls, symbol: str, side: Side, quantity: Decimal, 
                               stop_price: Decimal, price: Decimal, **kwargs) -> "Order":
        """Create a stop limit order."""
        return cls(
            symbol=symbol,
            side=side,
            order_type=OrderType.STOP_LIMIT,
            quantity=quantity,
            stop_price=stop_price,
            price=price,
            **kwargs
        )


class OrderManager:
    """Manages order lifecycle and state."""
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.orders_by_symbol: Dict[str, List[str]] = {}
        self.orders_by_status: Dict[OrderStatus, List[str]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def add_order(self, order: Order) -> None:
        """Add an order to management."""
        if not order.is_valid():
            raise ValueError(f"Invalid order: {order.validate()}")
        
        self.orders[order.order_id] = order
        
        # Index by symbol
        if order.symbol not in self.orders_by_symbol:
            self.orders_by_symbol[order.symbol] = []
        self.orders_by_symbol[order.symbol].append(order.order_id)
        
        # Index by status
        if order.status not in self.orders_by_status:
            self.orders_by_status[order.status] = []
        self.orders_by_status[order.status].append(order.order_id)
        
        self.logger.info(f"Order added: {order.order_id} ({order.symbol} {order.side.value} {order.quantity})")
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.orders.get(order_id)
    
    def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """Get all orders for a symbol."""
        order_ids = self.orders_by_symbol.get(symbol, [])
        return [self.orders[order_id] for order_id in order_ids if order_id in self.orders]
    
    def get_orders_by_status(self, status: OrderStatus) -> List[Order]:
        """Get all orders with a specific status."""
        order_ids = self.orders_by_status.get(status, [])
        return [self.orders[order_id] for order_id in order_ids if order_id in self.orders]
    
    def get_active_orders(self) -> List[Order]:
        """Get all active orders."""
        active_orders = []
        for order in self.orders.values():
            if order.is_active:
                active_orders.append(order)
        return active_orders
    
    def update_order_status(self, order_id: str, new_status: OrderStatus) -> None:
        """Update order status."""
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")
        
        old_status = order.status
        order.update_status(new_status)
        
        # Update status index
        if old_status in self.orders_by_status:
            try:
                self.orders_by_status[old_status].remove(order_id)
            except ValueError:
                pass
        
        if new_status not in self.orders_by_status:
            self.orders_by_status[new_status] = []
        self.orders_by_status[new_status].append(order_id)
    
    def cancel_order(self, order_id: str, reason: Optional[str] = None) -> None:
        """Cancel an order."""
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"Order not found: {order_id}")
        
        order.cancel(reason)
        self.update_order_status(order_id, OrderStatus.CANCELLED)
    
    def cancel_all_orders(self, symbol: Optional[str] = None) -> List[str]:
        """Cancel all orders, optionally filtered by symbol."""
        cancelled_orders = []
        
        orders_to_cancel = (
            self.get_orders_by_symbol(symbol) if symbol 
            else self.get_active_orders()
        )
        
        for order in orders_to_cancel:
            if order.is_active:
                self.cancel_order(order.order_id, "Bulk cancellation")
                cancelled_orders.append(order.order_id)
        
        return cancelled_orders
    
    def get_order_summary(self) -> Dict[str, Any]:
        """Get summary of all orders."""
        status_counts = {}
        for status in OrderStatus:
            status_counts[status.value] = len(self.get_orders_by_status(status))
        
        return {
            "total_orders": len(self.orders),
            "status_breakdown": status_counts,
            "active_orders": len(self.get_active_orders()),
            "symbols": list(self.orders_by_symbol.keys())
        }