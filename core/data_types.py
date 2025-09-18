"""Core data types for the algorithmic trading system.

This module provides fundamental data structures used throughout
the trading system for representing market data, orders, trades, and positions.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


class OrderSide(Enum):
    """Order side enumeration."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class PositionSide(Enum):
    """Position side enumeration."""
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


@dataclass
class MarketData:
    """Market data representation.
    
    Contains price and volume information for a financial instrument
    at a specific point in time.
    """
    
    symbol: str
    timestamp: datetime
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    close_price: Optional[float] = None
    volume: Optional[float] = None
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    bid_size: Optional[float] = None
    ask_size: Optional[float] = None
    last_price: Optional[float] = None
    last_size: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def mid_price(self) -> Optional[float]:
        """Calculate mid price from bid/ask."""
        if self.bid_price is not None and self.ask_price is not None:
            return (self.bid_price + self.ask_price) / 2
        return None
    
    @property
    def spread(self) -> Optional[float]:
        """Calculate bid-ask spread."""
        if self.bid_price is not None and self.ask_price is not None:
            return self.ask_price - self.bid_price
        return None
    
    @property
    def typical_price(self) -> Optional[float]:
        """Calculate typical price (HLC/3)."""
        if all(p is not None for p in [self.high_price, self.low_price, self.close_price]):
            return (self.high_price + self.low_price + self.close_price) / 3
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "open_price": self.open_price,
            "high_price": self.high_price,
            "low_price": self.low_price,
            "close_price": self.close_price,
            "volume": self.volume,
            "bid_price": self.bid_price,
            "ask_price": self.ask_price,
            "bid_size": self.bid_size,
            "ask_size": self.ask_size,
            "last_price": self.last_price,
            "last_size": self.last_size,
            "metadata": self.metadata
        }


@dataclass
class Order:
    """Order representation.
    
    Represents a trading order with all necessary details for execution.
    """
    
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "DAY"
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    filled_quantity: float = 0.0
    remaining_quantity: Optional[float] = None
    average_fill_price: Optional[float] = None
    commission: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing."""
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity
    
    @property
    def is_buy(self) -> bool:
        """Check if order is a buy order."""
        return self.side == OrderSide.BUY
    
    @property
    def is_sell(self) -> bool:
        """Check if order is a sell order."""
        return self.side == OrderSide.SELL
    
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_active(self) -> bool:
        """Check if order is active (can be filled)."""
        return self.status in [OrderStatus.SUBMITTED, OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED]
    
    def fill(self, quantity: float, price: float, timestamp: Optional[datetime] = None) -> 'Trade':
        """Fill the order (partially or completely)."""
        if quantity <= 0:
            raise ValueError("Fill quantity must be positive")
        
        if quantity > self.remaining_quantity:
            raise ValueError("Fill quantity exceeds remaining quantity")
        
        # Update order state
        self.filled_quantity += quantity
        self.remaining_quantity -= quantity
        self.updated_at = timestamp or datetime.utcnow()
        
        # Update average fill price
        if self.average_fill_price is None:
            self.average_fill_price = price
        else:
            total_value = (self.filled_quantity - quantity) * self.average_fill_price + quantity * price
            self.average_fill_price = total_value / self.filled_quantity
        
        # Update status
        if self.remaining_quantity == 0:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED
        
        # Create trade
        return Trade(
            symbol=self.symbol,
            side=self.side,
            quantity=quantity,
            price=price,
            order_id=self.order_id,
            timestamp=self.updated_at
        )
    
    def cancel(self, timestamp: Optional[datetime] = None):
        """Cancel the order."""
        self.status = OrderStatus.CANCELLED
        self.updated_at = timestamp or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "price": self.price,
            "stop_price": self.stop_price,
            "time_in_force": self.time_in_force,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "average_fill_price": self.average_fill_price,
            "commission": self.commission,
            "metadata": self.metadata
        }


@dataclass
class Trade:
    """Trade representation.
    
    Represents an executed trade (fill) of an order.
    """
    
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: Optional[str] = None
    commission: float = 0.0
    fees: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def value(self) -> float:
        """Calculate trade value (quantity * price)."""
        return self.quantity * self.price
    
    @property
    def net_value(self) -> float:
        """Calculate net trade value after commission and fees."""
        return self.value - self.commission - self.fees
    
    @property
    def is_buy(self) -> bool:
        """Check if trade is a buy."""
        return self.side == OrderSide.BUY
    
    @property
    def is_sell(self) -> bool:
        """Check if trade is a sell."""
        return self.side == OrderSide.SELL
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "trade_id": self.trade_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "price": self.price,
            "timestamp": self.timestamp.isoformat(),
            "commission": self.commission,
            "fees": self.fees,
            "value": self.value,
            "net_value": self.net_value,
            "metadata": self.metadata
        }


@dataclass
class Position:
    """Position representation.
    
    Represents a current position in a financial instrument.
    """
    
    symbol: str
    side: PositionSide = PositionSide.FLAT
    quantity: float = 0.0
    average_price: float = 0.0
    market_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_commission: float = 0.0
    total_fees: float = 0.0
    opened_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)
    trades: List[Trade] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def market_value(self) -> float:
        """Calculate current market value of position."""
        if self.market_price is None:
            return 0.0
        return abs(self.quantity) * self.market_price
    
    @property
    def cost_basis(self) -> float:
        """Calculate cost basis of position."""
        return abs(self.quantity) * self.average_price
    
    @property
    def is_long(self) -> bool:
        """Check if position is long."""
        return self.side == PositionSide.LONG
    
    @property
    def is_short(self) -> bool:
        """Check if position is short."""
        return self.side == PositionSide.SHORT
    
    @property
    def is_flat(self) -> bool:
        """Check if position is flat (no position)."""
        return self.side == PositionSide.FLAT or self.quantity == 0
    
    def update_market_price(self, price: float, timestamp: Optional[datetime] = None):
        """Update market price and recalculate unrealized PnL."""
        self.market_price = price
        self.updated_at = timestamp or datetime.utcnow()
        
        if not self.is_flat:
            if self.is_long:
                self.unrealized_pnl = (price - self.average_price) * self.quantity
            else:  # short position
                self.unrealized_pnl = (self.average_price - price) * abs(self.quantity)
    
    def add_trade(self, trade: Trade):
        """Add a trade to the position and update position state."""
        self.trades.append(trade)
        
        if self.is_flat:
            # Opening new position
            self.quantity = trade.quantity if trade.is_buy else -trade.quantity
            self.average_price = trade.price
            self.side = PositionSide.LONG if trade.is_buy else PositionSide.SHORT
            self.opened_at = trade.timestamp
        else:
            # Modifying existing position
            old_quantity = self.quantity
            trade_quantity = trade.quantity if trade.is_buy else -trade.quantity
            new_quantity = old_quantity + trade_quantity
            
            if new_quantity == 0:
                # Position closed
                self.realized_pnl += self._calculate_realized_pnl(trade)
                self.quantity = 0
                self.side = PositionSide.FLAT
                self.average_price = 0
            elif (old_quantity > 0 and new_quantity > 0) or (old_quantity < 0 and new_quantity < 0):
                # Adding to position
                total_cost = abs(old_quantity) * self.average_price + trade.quantity * trade.price
                self.quantity = new_quantity
                self.average_price = total_cost / abs(new_quantity)
            else:
                # Reducing position
                self.realized_pnl += self._calculate_realized_pnl(trade)
                self.quantity = new_quantity
                if new_quantity != 0:
                    self.side = PositionSide.LONG if new_quantity > 0 else PositionSide.SHORT
                else:
                    self.side = PositionSide.FLAT
        
        # Update commission and fees
        self.total_commission += trade.commission
        self.total_fees += trade.fees
        self.updated_at = trade.timestamp
    
    def _calculate_realized_pnl(self, trade: Trade) -> float:
        """Calculate realized PnL for a trade."""
        if self.is_long and trade.is_sell:
            return (trade.price - self.average_price) * trade.quantity
        elif self.is_short and trade.is_buy:
            return (self.average_price - trade.price) * trade.quantity
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "average_price": self.average_price,
            "market_price": self.market_price,
            "market_value": self.market_value,
            "cost_basis": self.cost_basis,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "total_commission": self.total_commission,
            "total_fees": self.total_fees,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }