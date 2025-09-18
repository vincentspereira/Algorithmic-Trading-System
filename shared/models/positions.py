"""Position models for the algorithmic trading system.

This module provides data structures for positions, position management,
and position tracking.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class PositionSide(Enum):
    """Position side enumeration."""
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class PositionStatus(Enum):
    """Position status enumeration."""
    OPEN = "open"
    CLOSED = "closed"
    CLOSING = "closing"
    SUSPENDED = "suspended"


@dataclass
class PositionEntry:
    """Represents a position entry (trade that contributes to position)."""
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    position_id: str = ""
    symbol: str = ""
    side: str = ""  # "buy" or "sell"
    quantity: Decimal = Decimal('0')
    price: Decimal = Decimal('0')
    timestamp: datetime = field(default_factory=datetime.utcnow)
    order_id: Optional[str] = None
    fill_id: Optional[str] = None
    commission: Decimal = Decimal('0')
    fees: Decimal = Decimal('0')
    
    @property
    def value(self) -> Decimal:
        """Calculate entry value."""
        return self.quantity * self.price
    
    @property
    def net_value(self) -> Decimal:
        """Calculate net entry value after fees."""
        return self.value - self.commission - self.fees
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "entry_id": self.entry_id,
            "position_id": self.position_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": float(self.quantity),
            "price": float(self.price),
            "timestamp": self.timestamp.isoformat(),
            "order_id": self.order_id,
            "fill_id": self.fill_id,
            "commission": float(self.commission),
            "fees": float(self.fees),
            "value": float(self.value),
            "net_value": float(self.net_value)
        }


@dataclass
class Position:
    """Represents a trading position."""
    position_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    side: PositionSide = PositionSide.FLAT
    quantity: Decimal = Decimal('0')
    average_price: Decimal = Decimal('0')
    market_price: Decimal = Decimal('0')
    status: PositionStatus = PositionStatus.OPEN
    
    # Timestamps
    opened_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    
    # Position entries and exits
    entries: List[PositionEntry] = field(default_factory=list)
    
    # Cost basis and P&L tracking
    cost_basis: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')
    total_commission: Decimal = Decimal('0')
    total_fees: Decimal = Decimal('0')
    
    # Portfolio and account information
    portfolio_id: Optional[str] = None
    account_id: Optional[str] = None
    strategy_id: Optional[str] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
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
    
    @property
    def is_open(self) -> bool:
        """Check if position is open."""
        return self.status == PositionStatus.OPEN and not self.is_flat
    
    @property
    def is_closed(self) -> bool:
        """Check if position is closed."""
        return self.status == PositionStatus.CLOSED or self.is_flat
    
    @property
    def market_value(self) -> Decimal:
        """Calculate current market value of position."""
        if self.is_flat:
            return Decimal('0')
        return abs(self.quantity) * self.market_price
    
    @property
    def unrealized_pnl(self) -> Decimal:
        """Calculate unrealized P&L."""
        if self.is_flat:
            return Decimal('0')
        
        if self.is_long:
            return (self.market_price - self.average_price) * self.quantity
        else:  # short position
            return (self.average_price - self.market_price) * abs(self.quantity)
    
    @property
    def total_pnl(self) -> Decimal:
        """Calculate total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl
    
    @property
    def net_pnl(self) -> Decimal:
        """Calculate net P&L after commissions and fees."""
        return self.total_pnl - self.total_commission - self.total_fees
    
    @property
    def pnl_percentage(self) -> Decimal:
        """Calculate P&L as percentage of cost basis."""
        if self.cost_basis == 0:
            return Decimal('0')
        return (self.total_pnl / self.cost_basis) * 100
    
    @property
    def net_pnl_percentage(self) -> Decimal:
        """Calculate net P&L as percentage of cost basis."""
        if self.cost_basis == 0:
            return Decimal('0')
        return (self.net_pnl / self.cost_basis) * 100
    
    @property
    def exposure(self) -> Decimal:
        """Calculate position exposure (absolute market value)."""
        return abs(self.market_value)
    
    def update_market_price(self, new_price: Decimal, timestamp: Optional[datetime] = None) -> None:
        """Update market price for P&L calculations."""
        self.market_price = new_price
        self.updated_at = timestamp or datetime.utcnow()
        
        logger.debug(f"Position {self.position_id} market price updated to {new_price}")
    
    def add_entry(self, entry: PositionEntry) -> None:
        """Add a position entry (buy/sell that affects position)."""
        entry.position_id = self.position_id
        self.entries.append(entry)
        
        # Update position based on entry
        if entry.side.lower() == "buy":
            self._add_long_entry(entry)
        else:  # sell
            self._add_short_entry(entry)
        
        # Update totals
        self.total_commission += entry.commission
        self.total_fees += entry.fees
        self.updated_at = entry.timestamp
        
        logger.info(f"Entry added to position {self.position_id}: {entry.side} {entry.quantity}@{entry.price}")
    
    def _add_long_entry(self, entry: PositionEntry) -> None:
        """Add a long entry to the position."""
        if self.is_short:
            # Covering short position
            if entry.quantity >= abs(self.quantity):
                # Fully cover short and potentially go long
                cover_quantity = abs(self.quantity)
                remaining_quantity = entry.quantity - cover_quantity
                
                # Realize P&L from covering
                cover_pnl = (self.average_price - entry.price) * cover_quantity
                self.realized_pnl += cover_pnl
                
                if remaining_quantity > 0:
                    # Go long with remaining quantity
                    self.quantity = remaining_quantity
                    self.side = PositionSide.LONG
                    self.average_price = entry.price
                    self.cost_basis = remaining_quantity * entry.price
                else:
                    # Flat position
                    self._flatten_position()
            else:
                # Partially cover short position
                self.quantity += entry.quantity  # quantity becomes less negative
                cover_pnl = (self.average_price - entry.price) * entry.quantity
                self.realized_pnl += cover_pnl
        else:
            # Adding to long position or opening new long
            if self.is_flat:
                # Opening new long position
                self.quantity = entry.quantity
                self.side = PositionSide.LONG
                self.average_price = entry.price
                self.cost_basis = entry.quantity * entry.price
            else:
                # Adding to existing long position
                total_cost = (self.quantity * self.average_price) + (entry.quantity * entry.price)
                self.quantity += entry.quantity
                self.average_price = total_cost / self.quantity
                self.cost_basis = total_cost
    
    def _add_short_entry(self, entry: PositionEntry) -> None:
        """Add a short entry to the position."""
        if self.is_long:
            # Selling long position
            if entry.quantity >= self.quantity:
                # Fully close long and potentially go short
                close_quantity = self.quantity
                remaining_quantity = entry.quantity - close_quantity
                
                # Realize P&L from closing
                close_pnl = (entry.price - self.average_price) * close_quantity
                self.realized_pnl += close_pnl
                
                if remaining_quantity > 0:
                    # Go short with remaining quantity
                    self.quantity = -remaining_quantity
                    self.side = PositionSide.SHORT
                    self.average_price = entry.price
                    self.cost_basis = remaining_quantity * entry.price
                else:
                    # Flat position
                    self._flatten_position()
            else:
                # Partially close long position
                self.quantity -= entry.quantity
                close_pnl = (entry.price - self.average_price) * entry.quantity
                self.realized_pnl += close_pnl
                self.cost_basis = self.quantity * self.average_price
        else:
            # Adding to short position or opening new short
            if self.is_flat:
                # Opening new short position
                self.quantity = -entry.quantity
                self.side = PositionSide.SHORT
                self.average_price = entry.price
                self.cost_basis = entry.quantity * entry.price
            else:
                # Adding to existing short position
                current_quantity = abs(self.quantity)
                total_cost = (current_quantity * self.average_price) + (entry.quantity * entry.price)
                new_quantity = current_quantity + entry.quantity
                self.quantity = -new_quantity
                self.average_price = total_cost / new_quantity
                self.cost_basis = total_cost
    
    def _flatten_position(self) -> None:
        """Flatten the position (set to zero)."""
        self.quantity = Decimal('0')
        self.side = PositionSide.FLAT
        self.average_price = Decimal('0')
        self.cost_basis = Decimal('0')
    
    def close_position(self, close_price: Decimal, timestamp: Optional[datetime] = None) -> Decimal:
        """Close the entire position and return realized P&L."""
        if self.is_flat:
            return Decimal('0')
        
        # Calculate final P&L
        final_pnl = self.unrealized_pnl
        self.realized_pnl += final_pnl
        
        # Create closing entry
        close_side = "sell" if self.is_long else "buy"
        close_entry = PositionEntry(
            position_id=self.position_id,
            symbol=self.symbol,
            side=close_side,
            quantity=abs(self.quantity),
            price=close_price,
            timestamp=timestamp or datetime.utcnow()
        )
        self.entries.append(close_entry)
        
        # Flatten position
        self._flatten_position()
        self.status = PositionStatus.CLOSED
        self.closed_at = close_entry.timestamp
        self.updated_at = close_entry.timestamp
        
        logger.info(f"Position {self.position_id} closed with P&L: {final_pnl}")
        return final_pnl
    
    def get_position_summary(self) -> Dict[str, Any]:
        """Get position summary."""
        return {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": float(self.quantity),
            "average_price": float(self.average_price),
            "market_price": float(self.market_price),
            "market_value": float(self.market_value),
            "cost_basis": float(self.cost_basis),
            "unrealized_pnl": float(self.unrealized_pnl),
            "realized_pnl": float(self.realized_pnl),
            "total_pnl": float(self.total_pnl),
            "net_pnl": float(self.net_pnl),
            "pnl_percentage": float(self.pnl_percentage),
            "net_pnl_percentage": float(self.net_pnl_percentage),
            "exposure": float(self.exposure),
            "status": self.status.value,
            "opened_at": self.opened_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "total_commission": float(self.total_commission),
            "total_fees": float(self.total_fees),
            "entry_count": len(self.entries)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        summary = self.get_position_summary()
        summary.update({
            "entries": [entry.to_dict() for entry in self.entries],
            "portfolio_id": self.portfolio_id,
            "account_id": self.account_id,
            "strategy_id": self.strategy_id,
            "tags": self.tags,
            "metadata": self.metadata
        })
        return summary


class PositionManager:
    """Manages positions and position tracking."""
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.positions_by_symbol: Dict[str, List[str]] = {}
        self.positions_by_status: Dict[PositionStatus, List[str]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get_position(self, position_id: str) -> Optional[Position]:
        """Get position by ID."""
        return self.positions.get(position_id)
    
    def get_position_by_symbol(self, symbol: str) -> Optional[Position]:
        """Get active position for a symbol."""
        position_ids = self.positions_by_symbol.get(symbol, [])
        for position_id in position_ids:
            position = self.positions.get(position_id)
            if position and position.is_open:
                return position
        return None
    
    def get_positions_by_symbol(self, symbol: str) -> List[Position]:
        """Get all positions for a symbol."""
        position_ids = self.positions_by_symbol.get(symbol, [])
        return [self.positions[pid] for pid in position_ids if pid in self.positions]
    
    def get_positions_by_status(self, status: PositionStatus) -> List[Position]:
        """Get all positions with a specific status."""
        position_ids = self.positions_by_status.get(status, [])
        return [self.positions[pid] for pid in position_ids if pid in self.positions]
    
    def get_open_positions(self) -> List[Position]:
        """Get all open positions."""
        return [pos for pos in self.positions.values() if pos.is_open]
    
    def get_closed_positions(self) -> List[Position]:
        """Get all closed positions."""
        return [pos for pos in self.positions.values() if pos.is_closed]
    
    def create_or_update_position(self, symbol: str, entry: PositionEntry) -> Position:
        """Create new position or update existing one."""
        # Try to find existing open position for symbol
        position = self.get_position_by_symbol(symbol)
        
        if not position:
            # Create new position
            position = Position(
                symbol=symbol,
                portfolio_id=entry.metadata.get("portfolio_id") if hasattr(entry, 'metadata') else None,
                account_id=entry.metadata.get("account_id") if hasattr(entry, 'metadata') else None,
                strategy_id=entry.metadata.get("strategy_id") if hasattr(entry, 'metadata') else None
            )
            self._add_position(position)
        
        # Add entry to position
        position.add_entry(entry)
        
        # Update position status if it became flat
        if position.is_flat and position.status == PositionStatus.OPEN:
            self._update_position_status(position.position_id, PositionStatus.CLOSED)
        
        return position
    
    def _add_position(self, position: Position) -> None:
        """Add position to management."""
        self.positions[position.position_id] = position
        
        # Index by symbol
        if position.symbol not in self.positions_by_symbol:
            self.positions_by_symbol[position.symbol] = []
        self.positions_by_symbol[position.symbol].append(position.position_id)
        
        # Index by status
        if position.status not in self.positions_by_status:
            self.positions_by_status[position.status] = []
        self.positions_by_status[position.status].append(position.position_id)
        
        self.logger.info(f"Position added: {position.position_id} ({position.symbol})")
    
    def _update_position_status(self, position_id: str, new_status: PositionStatus) -> None:
        """Update position status and indices."""
        position = self.get_position(position_id)
        if not position:
            return
        
        old_status = position.status
        position.status = new_status
        position.updated_at = datetime.utcnow()
        
        # Update status index
        if old_status in self.positions_by_status:
            try:
                self.positions_by_status[old_status].remove(position_id)
            except ValueError:
                pass
        
        if new_status not in self.positions_by_status:
            self.positions_by_status[new_status] = []
        self.positions_by_status[new_status].append(position_id)
        
        if new_status == PositionStatus.CLOSED:
            position.closed_at = position.updated_at
    
    def close_position(self, position_id: str, close_price: Decimal) -> Optional[Decimal]:
        """Close a position."""
        position = self.get_position(position_id)
        if not position:
            return None
        
        pnl = position.close_position(close_price)
        self._update_position_status(position_id, PositionStatus.CLOSED)
        
        return pnl
    
    def close_all_positions(self, symbol: Optional[str] = None) -> Dict[str, Decimal]:
        """Close all positions, optionally filtered by symbol."""
        closed_positions = {}
        
        positions_to_close = (
            self.get_positions_by_symbol(symbol) if symbol 
            else self.get_open_positions()
        )
        
        for position in positions_to_close:
            if position.is_open:
                # Use current market price for closing
                pnl = self.close_position(position.position_id, position.market_price)
                if pnl is not None:
                    closed_positions[position.position_id] = pnl
        
        return closed_positions
    
    def update_market_prices(self, price_updates: Dict[str, Decimal]) -> None:
        """Update market prices for multiple symbols."""
        timestamp = datetime.utcnow()
        
        for symbol, price in price_updates.items():
            positions = self.get_positions_by_symbol(symbol)
            for position in positions:
                if position.is_open:
                    position.update_market_price(price, timestamp)
    
    def get_portfolio_summary(self, portfolio_id: Optional[str] = None) -> Dict[str, Any]:
        """Get portfolio summary."""
        positions = [
            pos for pos in self.positions.values()
            if not portfolio_id or pos.portfolio_id == portfolio_id
        ]
        
        open_positions = [pos for pos in positions if pos.is_open]
        closed_positions = [pos for pos in positions if pos.is_closed]
        
        total_market_value = sum(pos.market_value for pos in open_positions)
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in open_positions)
        total_realized_pnl = sum(pos.realized_pnl for pos in positions)
        total_pnl = total_unrealized_pnl + total_realized_pnl
        
        total_commission = sum(pos.total_commission for pos in positions)
        total_fees = sum(pos.total_fees for pos in positions)
        net_pnl = total_pnl - total_commission - total_fees
        
        return {
            "portfolio_id": portfolio_id,
            "total_positions": len(positions),
            "open_positions": len(open_positions),
            "closed_positions": len(closed_positions),
            "total_market_value": float(total_market_value),
            "total_unrealized_pnl": float(total_unrealized_pnl),
            "total_realized_pnl": float(total_realized_pnl),
            "total_pnl": float(total_pnl),
            "net_pnl": float(net_pnl),
            "total_commission": float(total_commission),
            "total_fees": float(total_fees),
            "symbols": list(set(pos.symbol for pos in open_positions))
        }
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Calculate risk metrics for all positions."""
        open_positions = self.get_open_positions()
        
        if not open_positions:
            return {
                "total_exposure": 0.0,
                "long_exposure": 0.0,
                "short_exposure": 0.0,
                "net_exposure": 0.0,
                "gross_exposure": 0.0,
                "position_count": 0,
                "largest_position": 0.0,
                "concentration_risk": 0.0
            }
        
        long_exposure = sum(pos.market_value for pos in open_positions if pos.is_long)
        short_exposure = sum(pos.market_value for pos in open_positions if pos.is_short)
        
        total_exposure = long_exposure + short_exposure
        net_exposure = long_exposure - short_exposure
        gross_exposure = abs(long_exposure) + abs(short_exposure)
        
        largest_position = max(pos.exposure for pos in open_positions)
        concentration_risk = (largest_position / total_exposure * 100) if total_exposure > 0 else 0
        
        return {
            "total_exposure": float(total_exposure),
            "long_exposure": float(long_exposure),
            "short_exposure": float(short_exposure),
            "net_exposure": float(net_exposure),
            "gross_exposure": float(gross_exposure),
            "position_count": len(open_positions),
            "largest_position": float(largest_position),
            "concentration_risk": float(concentration_risk)
        }