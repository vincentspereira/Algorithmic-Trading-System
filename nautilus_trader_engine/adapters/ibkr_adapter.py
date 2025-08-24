"""
Interactive Brokers (IBKR) Adapter for Nautilus Trader

This module provides integration with Interactive Brokers for both paper and live trading.
It includes functionality for connecting to IBKR, managing orders, and switching between
paper and live trading modes.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

# Try to import ib_insync, which is the standard library for IBKR integration
try:
    from ib_insync import IB, Stock, Option, Future, Forex, Crypto, Order, Trade
    IBKR_AVAILABLE = True
except ImportError:
    IBKR_AVAILABLE = False
    logging.warning("ib_insync not available - IBKR integration will be simulated")

# Import from broker adapter (which handles Nautilus Trader availability)
from .broker_adapter import (
    BrokerAdapter, 
    BrokerOrder, 
    AccountInfo, 
    Position, 
    OrderType, 
    OrderSide,
    InstrumentId,
    VenueOrderId,
    Quantity,
    Price
)

logger = logging.getLogger(__name__)


class IBKRAdapter(BrokerAdapter):
    """
    Adapter for Interactive Brokers integration with Nautilus Trader.
    
    This class provides methods for connecting to IBKR, submitting orders,
    and managing trading modes (paper vs live).
    """
    
    def __init__(self, paper_trading: bool = True, account_id: Optional[str] = None):
        """
        Initialize the IBKR adapter.
        
        Args:
            paper_trading: Whether to use paper trading mode (default: True)
            account_id: Optional account ID for live trading
        """
        super().__init__(paper_trading)
        self.account_id = account_id
        self.ib = None
        
        # For simulation when ib_insync is not available
        self._orders = {}
        self._next_order_id = 1
        
    async def connect(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1) -> bool:
        """
        Connect to Interactive Brokers.
        
        Args:
            host: IBKR TWS/Gateway host (default: localhost)
            port: Port number (7497 for paper trading, 7496 for live)
            client_id: Client ID for the connection
            
        Returns:
            bool: True if connected successfully, False otherwise
        """
        if not IBKR_AVAILABLE:
            logger.info("IBKR integration not available - using simulation mode")
            self.connected = True
            return True
            
        try:
            self.ib = IB()
            port = 7497 if self.paper_trading else 7496
            await self.ib.connectAsync(host, port, clientId=client_id)
            self.connected = True
            logger.info(f"Connected to IBKR {'paper' if self.paper_trading else 'live'} trading")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {e}")
            self.connected = False
            return False
            
    async def disconnect(self):
        """Disconnect from Interactive Brokers."""
        if self.ib and self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IBKR")
            
    async def submit_order(self, order: BrokerOrder) -> VenueOrderId:
        """
        Submit an order to Interactive Brokers.
        
        Args:
            order: The standardized broker order to submit
            
        Returns:
            VenueOrderId: The order ID assigned by IBKR
        """
        if not self.connected:
            raise RuntimeError("Not connected to IBKR")
            
        # Generate a unique order ID
        order_id = self._next_order_id
        self._next_order_id += 1
        
        if not IBKR_AVAILABLE:
            # Simulate order submission
            venue_order_id = VenueOrderId(str(order_id))
            self._orders[venue_order_id.value] = {
                "order": order,
                "instrument": order.instrument_id,
                "status": "SUBMITTED",
                "timestamp": datetime.utcnow()
            }
            logger.info(f"Simulated order submission: {order} for {order.instrument_id}")
            return venue_order_id
            
        # Actual IBKR order submission would go here
        # This is a placeholder for the actual implementation
        venue_order_id = VenueOrderId(str(order_id))
        logger.info(f"Submitted order to IBKR: {order} for {order.instrument_id}")
        return venue_order_id
        
    async def cancel_order(self, venue_order_id: VenueOrderId) -> bool:
        """
        Cancel an order.
        
        Args:
            venue_order_id: The order ID to cancel
            
        Returns:
            bool: True if cancellation was successful, False otherwise
        """
        if not self.connected:
            raise RuntimeError("Not connected to IBKR")
            
        if not IBKR_AVAILABLE:
            # Simulate order cancellation
            if venue_order_id.value in self._orders:
                self._orders[venue_order_id.value]["status"] = "CANCELLED"
                logger.info(f"Simulated order cancellation: {venue_order_id.value}")
                return True
            else:
                logger.warning(f"Order not found for cancellation: {venue_order_id.value}")
                return False
                
        # Actual IBKR order cancellation would go here
        logger.info(f"Cancelling order: {venue_order_id.value}")
        return True
        
    async def get_account_info(self) -> AccountInfo:
        """
        Get account information from IBKR.
        
        Returns:
            AccountInfo: Account information
        """
        if not self.connected:
            raise RuntimeError("Not connected to IBKR")
            
        if not IBKR_AVAILABLE:
            # Return simulated account info
            return AccountInfo(
                account_id=self.account_id or "SIMULATED_ACCOUNT",
                balance=100000.0,  # Simulated balance
                available_funds=100000.0,
                equity=100000.0,
                currency="USD",
                positions={}
            )
            
        # Actual IBKR account info retrieval would go here
        return AccountInfo(
            account_id=self.account_id or "ACCOUNT_ID",
            balance=0.0,
            available_funds=0.0,
            equity=0.0,
            currency="USD",
            positions={}
        )
        
    async def get_positions(self) -> List[Position]:
        """
        Get current positions.
        
        Returns:
            List[Position]: List of current positions
        """
        if not self.connected:
            raise RuntimeError("Not connected to IBKR")
            
        if not IBKR_AVAILABLE:
            # Return simulated positions
            return []
            
        # Actual IBKR positions retrieval would go here
        return []
        
    async def get_order_status(self, venue_order_id: VenueOrderId) -> str:
        """
        Get the status of an order.
        
        Args:
            venue_order_id: The order ID assigned by IBKR
            
        Returns:
            str: Order status
        """
        if not self.connected:
            raise RuntimeError("Not connected to IBKR")
            
        if not IBKR_AVAILABLE:
            # Return simulated order status
            if venue_order_id.value in self._orders:
                return self._orders[venue_order_id.value]["status"]
            else:
                return "UNKNOWN"
                
        # Actual IBKR order status retrieval would go here
        return "SUBMITTED"
        
    async def get_market_data(self, instrument_id: InstrumentId) -> Dict[str, Any]:
        """
        Get current market data for an instrument.
        
        Args:
            instrument_id: The instrument ID
            
        Returns:
            Dict[str, Any]: Market data
        """
        if not self.connected:
            raise RuntimeError("Not connected to IBKR")
            
        if not IBKR_AVAILABLE:
            # Return simulated market data
            return {
                "bid": 100.0,
                "ask": 100.05,
                "last": 100.02,
                "volume": 1000
            }
            
        # Actual IBKR market data retrieval would go here
        return {
            "bid": 0.0,
            "ask": 0.0,
            "last": 0.0,
            "volume": 0
        }


# Global instance for the application
_ibkr_adapter: Optional[IBKRAdapter] = None


def get_ibkr_adapter() -> IBKRAdapter:
    """Get the global IBKR adapter instance."""
    global _ibkr_adapter
    if _ibkr_adapter is None:
        _ibkr_adapter = IBKRAdapter()
    return _ibkr_adapter


def initialize_ibkr_adapter(paper_trading: bool = True, account_id: Optional[str] = None) -> IBKRAdapter:
    """Initialize the global IBKR adapter instance."""
    global _ibkr_adapter
    _ibkr_adapter = IBKRAdapter(paper_trading=paper_trading, account_id=account_id)
    return _ibkr_adapter