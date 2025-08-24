"""
Broker Adapter Factory

This module provides a factory for creating broker adapters,
allowing for easy switching between different brokers.

Author: Vincent S. Pereira
Version: 1.0.0
"""

from typing import Dict, Optional, Type
from enum import Enum

# Try to import Nautilus Trader components
try:
    from nautilus_trader.model.orders import Order
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False

from .broker_adapter import BrokerAdapter
from .ibkr_adapter import IBKRAdapter

# Try to import other adapters if available
try:
    from .alpaca_adapter import AlpacaAdapter
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

try:
    from .oanda_adapter import OandaAdapter
    OANDA_AVAILABLE = True
except ImportError:
    OANDA_AVAILABLE = False


class BrokerType(Enum):
    """Supported broker types."""
    IBKR = "ibkr"
    ALPACA = "alpaca"
    OANDA = "oanda"


class BrokerAdapterFactory:
    """Factory for creating broker adapters."""
    
    # Registry of available broker adapters
    _adapters: Dict[BrokerType, Type[BrokerAdapter]] = {
        BrokerType.IBKR: IBKRAdapter,
    }
    
    @classmethod
    def register_adapter(cls, broker_type: BrokerType, adapter_class: Type[BrokerAdapter]):
        """
        Register a new broker adapter.
        
        Args:
            broker_type: The broker type
            adapter_class: The adapter class
        """
        cls._adapters[broker_type] = adapter_class
    
    @classmethod
    def create_adapter(cls, broker_type: BrokerType, paper_trading: bool = True, **kwargs) -> BrokerAdapter:
        """
        Create a broker adapter instance.
        
        Args:
            broker_type: The broker type
            paper_trading: Whether to use paper trading mode
            **kwargs: Additional arguments for adapter initialization
            
        Returns:
            BrokerAdapter: The created adapter instance
        """
        if broker_type not in cls._adapters:
            raise ValueError(f"Unsupported broker type: {broker_type}")
            
        adapter_class = cls._adapters[broker_type]
        return adapter_class(paper_trading=paper_trading, **kwargs)
    
    @classmethod
    def get_available_brokers(cls) -> Dict[BrokerType, str]:
        """
        Get available broker types and their descriptions.
        
        Returns:
            Dict[BrokerType, str]: Available broker types and descriptions
        """
        brokers = {
            BrokerType.IBKR: "Interactive Brokers",
        }
        
        if ALPACA_AVAILABLE:
            brokers[BrokerType.ALPACA] = "Alpaca"
            
        if OANDA_AVAILABLE:
            brokers[BrokerType.OANDA] = "Oanda"
            
        return brokers


# Initialize the factory with available adapters
def initialize_broker_factory():
    """Initialize the broker factory with available adapters."""
    if ALPACA_AVAILABLE:
        BrokerAdapterFactory.register_adapter(BrokerType.ALPACA, AlpacaAdapter)
        
    if OANDA_AVAILABLE:
        BrokerAdapterFactory.register_adapter(BrokerType.OANDA, OandaAdapter)


# Global broker adapter instance
_current_adapter: Optional[BrokerAdapter] = None
_current_broker_type: Optional[BrokerType] = None


def get_broker_adapter() -> BrokerAdapter:
    """
    Get the current broker adapter instance.
    
    Returns:
        BrokerAdapter: The current broker adapter
    """
    global _current_adapter
    if _current_adapter is None:
        _current_adapter = BrokerAdapterFactory.create_adapter(BrokerType.IBKR)
    return _current_adapter


def initialize_broker_adapter(broker_type: BrokerType, paper_trading: bool = True, **kwargs) -> BrokerAdapter:
    """
    Initialize the global broker adapter instance.
    
    Args:
        broker_type: The broker type
        paper_trading: Whether to use paper trading mode
        **kwargs: Additional arguments for adapter initialization
        
    Returns:
        BrokerAdapter: The initialized adapter
    """
    global _current_adapter, _current_broker_type
    _current_adapter = BrokerAdapterFactory.create_adapter(broker_type, paper_trading=paper_trading, **kwargs)
    _current_broker_type = broker_type
    return _current_adapter


def get_current_broker_type() -> Optional[BrokerType]:
    """
    Get the current broker type.
    
    Returns:
        Optional[BrokerType]: The current broker type
    """
    global _current_broker_type
    return _current_broker_type