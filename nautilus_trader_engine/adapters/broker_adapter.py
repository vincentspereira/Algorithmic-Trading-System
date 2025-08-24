"""
Broker Adapter Abstract Base Class

This module provides the abstract base class for broker adapters,
defining the common interface that all broker adapters must implement.

Author: Vincent S. Pereira
Version: 1.0.0
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Try to import Nautilus Trader components
try:
    from nautilus_trader.model.orders import Order
    from nautilus_trader.model.identifiers import InstrumentId, VenueOrderId
    from nautilus_trader.model.objects import Quantity, Price
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False

# If Nautilus Trader is not available, define simplified versions
if not NAUTILUS_AVAILABLE:
    @dataclass
    class InstrumentId:
        """Simplified instrument identifier."""
        value: str
        
        @classmethod
        def from_str(cls, value: str) -> 'InstrumentId':
            return cls(value)
        
        def __str__(self) -> str:
            return self.value

    @dataclass
    class VenueOrderId:
        """Simplified venue order identifier."""
        value: str

    @dataclass
    class Quantity:
        """Simplified quantity representation."""
        value: str
        
        @classmethod
        def from_str(cls, value: str) -> 'Quantity':
            return cls(value)
        
        def __str__(self) -> str:
            return self.value

    @dataclass
    class Price:
        """Simplified price representation."""
        value: str
        
        @classmethod
        def from_str(cls, value: str) -> 'Price':
            return cls(value)
        
        def __str__(self) -> str:
            return self.value


class OrderType(Enum):
    """Supported order types."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderSide(Enum):
    """Order sides."""
    BUY = "buy"
    SELL = "sell"


@dataclass
class BrokerOrder:
    """Standardized order representation."""
    instrument_id: InstrumentId
    order_type: OrderType
    side: OrderSide
    quantity: Quantity
    price: Optional[Price] = None
    stop_price: Optional[Price] = None
    client_order_id: Optional[str] = None
    venue_order_id: Optional[VenueOrderId] = None


@dataclass
class AccountInfo:
    """Standardized account information."""
    account_id: str
    balance: float
    available_funds: float
    equity: float
    currency: str
    positions: Dict[str, Dict[str, Any]]  # symbol -> position details


@dataclass
class Position:
    """Standardized position representation."""
    symbol: str
    quantity: float
    avg_price: float
    market_price: float
    unrealized_pnl: float
    realized_pnl: float


class BrokerAdapter(ABC):
    """
    Abstract base class for broker adapters.
    
    All broker adapters must implement this interface to ensure
    consistent behavior across different brokers.
    """
    
    def __init__(self, paper_trading: bool = True):
        """
        Initialize the broker adapter.
        
        Args:
            paper_trading: Whether to use paper trading mode
        """
        self.paper_trading = paper_trading
        self.connected = False
    
    @abstractmethod
    async def connect(self, **kwargs) -> bool:
        """
        Connect to the broker.
        
        Args:
            **kwargs: Connection parameters specific to the broker
            
        Returns:
            bool: True if connected successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Disconnect from the broker."""
        pass
    
    @abstractmethod
    async def submit_order(self, order: BrokerOrder) -> VenueOrderId:
        """
        Submit an order to the broker.
        
        Args:
            order: The order to submit
            
        Returns:
            VenueOrderId: The order ID assigned by the broker
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, venue_order_id: VenueOrderId) -> bool:
        """
        Cancel an order.
        
        Args:
            venue_order_id: The order ID to cancel
            
        Returns:
            bool: True if cancellation was successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """
        Get account information.
        
        Returns:
            AccountInfo: Account information
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Get current positions.
        
        Returns:
            List[Position]: List of current positions
        """
        pass
    
    @abstractmethod
    async def get_order_status(self, venue_order_id: VenueOrderId) -> str:
        """
        Get the status of an order.
        
        Args:
            venue_order_id: The order ID
            
        Returns:
            str: Order status
        """
        pass
    
    @abstractmethod
    async def get_market_data(self, instrument_id: InstrumentId) -> Dict[str, Any]:
        """
        Get current market data for an instrument.
        
        Args:
            instrument_id: The instrument ID
            
        Returns:
            Dict[str, Any]: Market data
        """
        pass
    
    def is_connected(self) -> bool:
        """
        Check if connected to the broker.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.connected
    
    def switch_trading_mode(self, paper_trading: bool) -> bool:
        """
        Switch between paper and live trading modes.
        
        Args:
            paper_trading: True for paper trading, False for live trading
            
        Returns:
            bool: True if mode switched successfully, False otherwise
        """
        if self.connected:
            return False
            
        self.paper_trading = paper_trading
        return True