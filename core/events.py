"""Event system for the algorithmic trading system.

This module provides the core event classes used throughout the system
for event-driven architecture and communication between components.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


class EventType(Enum):
    """Enumeration of event types in the trading system."""
    
    # Market data events
    MARKET_DATA = "market_data"
    TICK = "tick"
    BAR = "bar"
    QUOTE = "quote"
    
    # Order events
    ORDER_SUBMITTED = "order_submitted"
    ORDER_ACCEPTED = "order_accepted"
    ORDER_REJECTED = "order_rejected"
    ORDER_FILLED = "order_filled"
    ORDER_PARTIALLY_FILLED = "order_partially_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_MODIFIED = "order_modified"
    
    # Position events
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    POSITION_MODIFIED = "position_modified"
    
    # Portfolio events
    PORTFOLIO_UPDATED = "portfolio_updated"
    BALANCE_UPDATED = "balance_updated"
    
    # Strategy events
    STRATEGY_STARTED = "strategy_started"
    STRATEGY_STOPPED = "strategy_stopped"
    SIGNAL_GENERATED = "signal_generated"
    
    # Risk events
    RISK_LIMIT_EXCEEDED = "risk_limit_exceeded"
    MARGIN_CALL = "margin_call"
    
    # System events
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Event:
    """Base event class for the trading system.
    
    All events in the system inherit from this base class and contain
    common metadata such as timestamp, event type, and unique identifier.
    """
    
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing."""
        if isinstance(self.event_type, str):
            # Convert string to EventType enum if needed
            try:
                self.event_type = EventType(self.event_type)
            except ValueError:
                raise ValueError(f"Invalid event type: {self.event_type}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": self.data,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary representation."""
        return cls(
            event_type=EventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_id=data["event_id"],
            source=data.get("source"),
            data=data.get("data", {}),
            metadata=data.get("metadata", {})
        )
    
    def __str__(self) -> str:
        """String representation of the event."""
        return f"Event({self.event_type.value}, {self.timestamp}, {self.event_id[:8]}...)"
    
    def __repr__(self) -> str:
        """Detailed string representation of the event."""
        return (f"Event(event_type={self.event_type.value}, "
                f"timestamp={self.timestamp}, "
                f"event_id={self.event_id}, "
                f"source={self.source}, "
                f"data_keys={list(self.data.keys())})")


class MarketDataEvent(Event):
    """Specialized event for market data."""
    
    def __init__(self, symbol: str, price: float, volume: float = 0, 
                 timestamp: Optional[datetime] = None, **kwargs):
        super().__init__(
            event_type=EventType.MARKET_DATA,
            timestamp=timestamp or datetime.utcnow(),
            data={
                "symbol": symbol,
                "price": price,
                "volume": volume,
                **kwargs
            }
        )
    
    @property
    def symbol(self) -> str:
        return self.data["symbol"]
    
    @property
    def price(self) -> float:
        return self.data["price"]
    
    @property
    def volume(self) -> float:
        return self.data["volume"]


class OrderEvent(Event):
    """Specialized event for order-related activities."""
    
    def __init__(self, order_id: str, symbol: str, event_type: EventType,
                 timestamp: Optional[datetime] = None, **kwargs):
        super().__init__(
            event_type=event_type,
            timestamp=timestamp or datetime.utcnow(),
            data={
                "order_id": order_id,
                "symbol": symbol,
                **kwargs
            }
        )
    
    @property
    def order_id(self) -> str:
        return self.data["order_id"]
    
    @property
    def symbol(self) -> str:
        return self.data["symbol"]


class SignalEvent(Event):
    """Specialized event for trading signals."""
    
    def __init__(self, symbol: str, signal_type: str, strength: float = 1.0,
                 timestamp: Optional[datetime] = None, **kwargs):
        super().__init__(
            event_type=EventType.SIGNAL_GENERATED,
            timestamp=timestamp or datetime.utcnow(),
            data={
                "symbol": symbol,
                "signal_type": signal_type,
                "strength": strength,
                **kwargs
            }
        )
    
    @property
    def symbol(self) -> str:
        return self.data["symbol"]
    
    @property
    def signal_type(self) -> str:
        return self.data["signal_type"]
    
    @property
    def strength(self) -> float:
        return self.data["strength"]