import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

import pandas as pd
from ib_insync import IB, Contract, Order, Trade, Position, AccountValue
from ib_insync import Stock, Forex, Future, Option, Index, CFD
from ib_insync.objects import BarData, TickData

from nautilus_trader.adapters.interactive_brokers.common import IBContract
from nautilus_trader.adapters.interactive_brokers.client import InteractiveBrokersClient
from nautilus_trader.core.correctness import PyCondition
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.enums import OrderSide, OrderType, TimeInForce
from nautilus_trader.model.identifiers import ClientOrderId, InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.orders import Order as NautilusOrder
from nautilus_trader.model.position import Position as NautilusPosition

# Configure logging
logger = logging.getLogger(__name__)

class IBConnectionState(Enum):
    """Interactive Brokers connection states."""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    AUTHENTICATED = "AUTHENTICATED"
    ERROR = "ERROR"

@dataclass
class IBCredentials:
    """Interactive Brokers credentials configuration."""
    host: str = "127.0.0.1"
    port: int = 4001  # Paper trading port (7497 for live)
    client_id: int = 1
    account: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    trading_mode: str = "paper"  # "paper" or "live"
    
    def __post_init__(self):
        """Validate credentials after initialization."""
        if self.trading_mode not in ["paper", "live"]:
            raise ValueError("trading_mode must be 'paper' or 'live'")
        
        if self.trading_mode == "live" and self.port == 4001:
            logger.warning("Live trading mode with paper trading port. Consider using port 7497.")
        elif self.trading_mode == "paper" and self.port == 7497:
            logger.warning("Paper trading mode with live trading port. Consider using port 4001.")

class IBIntegrationError(Exception):
    """Base exception for Interactive Brokers integration errors."""
    pass

class IBConnectionError(IBIntegrationError):
    """Exception raised for connection-related errors."""
    pass

class IBAuthenticationError(IBIntegrationError):
    """Exception raised for authentication-related errors."""
    pass

class IBTradingError(IBIntegrationError):
    """Exception raised for trading operation errors."""
    pass

class IBDataError(IBIntegrationError):
    """Exception raised for data-related errors."""
    pass

class InteractiveBrokersIntegration:
    """
    Enhanced Interactive Brokers integration with comprehensive error handling,
    authentication, and paper trading compliance.
    
    This class provides a robust interface to Interactive Brokers TWS/Gateway
    with proper error handling, connection management, and trading operations.
    """
    
    def __init__(
        self,
        credentials: IBCredentials,
        event_handler: Optional[Callable] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize the Interactive Brokers integration.
        
        Parameters
        ----------
        credentials : IBCredentials
            The IB connection credentials
        event_handler : Callable, optional
            Event handler for IB events
        max_retries : int
            Maximum number of connection retries
        retry_delay : float
            Delay between retry attempts in seconds
        """
        self._credentials = credentials
        self._event_handler = event_handler
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        
        # Connection state
        self._connection_state = IBConnectionState.DISCONNECTED
        self._ib_client: Optional[IB] = None
        self._account_info: Dict[str, Any] = {}
        self._positions: Dict[str, Position] = {}
        self._orders: Dict[str, Order] = {}
        
        # Error tracking
        self._error_count = 0
        self._last_error: Optional[Exception] = None
        self._connection_attempts = 0
        
        # Event callbacks
        self._on_connected_callbacks: List[Callable] = []
        self._on_disconnected_callbacks: List[Callable] = []
        self._on_error_callbacks: List[Callable] = []
        self._on_order_callbacks: List[Callable] = []
        self._on_trade_callbacks: List[Callable] = []
        
        logger.info(f"Initialized IB integration for {credentials.trading_mode} trading")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Interactive Brokers."""
        return (
            self._ib_client is not None and 
            self._ib_client.isConnected() and
            self._connection_state == IBConnectionState.CONNECTED
        )
    
    @property
    def is_authenticated(self) -> bool:
        """Check if authenticated with Interactive Brokers."""
        return self._connection_state == IBConnectionState.AUTHENTICATED
    
    @property
    def connection_state(self) -> IBConnectionState:
        """Get current connection state."""
        return self._connection_state
    
    @property
    def account_info(self) -> Dict[str, Any]:
        """Get account information."""
        return self._account_info.copy()
    
    async def connect(self) -> bool:
        """
        Connect to Interactive Brokers with retry logic and proper error handling.
        
        Returns
        -------
        bool
            True if connection successful, False otherwise
        """
        if self.is_connected:
            logger.info("Already connected to Interactive Brokers")
            return True
        
        self._connection_state = IBConnectionState.CONNECTING
        self._connection_attempts = 0
        
        while self._connection_attempts < self._max_retries:
            try:
                self._connection_attempts += 1
                logger.info(
                    f"Attempting to connect to IB (attempt {self._connection_attempts}/{self._max_retries})"
                )
                
                # Create new IB client
                self._ib_client = IB()
                
                # Set up event handlers
                self._setup_event_handlers()
                
                # Attempt connection
                await self._ib_client.connectAsync(
                    host=self._credentials.host,
                    port=self._credentials.port,
                    clientId=self._credentials.client_id,
                    timeout=10
                )
                
                # Verify connection
                if not self._ib_client.isConnected():
                    raise IBConnectionError("Failed to establish connection")
                
                self._connection_state = IBConnectionState.CONNECTED
                logger.info("Successfully connected to Interactive Brokers")
                
                # Authenticate and get account info
                await self._authenticate()
                
                # Notify connection callbacks
                await self._notify_connected()
                
                return True
                
            except Exception as e:
                self._last_error = e
                self._error_count += 1
                
                error_msg = f"Connection attempt {self._connection_attempts} failed: {str(e)}"
                logger.error(error_msg)
                
                if self._connection_attempts < self._max_retries:
                    logger.info(f"Retrying in {self._retry_delay} seconds...")
                    await asyncio.sleep(self._retry_delay)
                else:
                    self._connection_state = IBConnectionState.ERROR
                    await self._notify_error(IBConnectionError(f"Failed to connect after {self._max_retries} attempts"))
                    return False
        
        return False
    
    async def disconnect(self) -> None:
        """
        Disconnect from Interactive Brokers.
        """
        if self._ib_client and self._ib_client.isConnected():
            try:
                logger.info("Disconnecting from Interactive Brokers")
                self._ib_client.disconnect()
                await self._notify_disconnected()
            except Exception as e:
                logger.error(f"Error during disconnection: {str(e)}")
            finally:
                self._connection_state = IBConnectionState.DISCONNECTED
                self._ib_client = None
    
    async def _authenticate(self) -> None:
        """
        Authenticate with Interactive Brokers and retrieve account information.
        """
        try:
            if not self._ib_client:
                raise IBAuthenticationError("No active connection")
            
            # Get account summary
            account_summary = self._ib_client.accountSummary()
            if not account_summary:
                raise IBAuthenticationError("Failed to retrieve account summary")
            
            # Process account information
            self._account_info = self._process_account_summary(account_summary)
            
            # Verify paper trading compliance
            await self._verify_paper_trading_compliance()
            
            # Get positions and orders
            await self._sync_positions()
            await self._sync_orders()
            
            self._connection_state = IBConnectionState.AUTHENTICATED
            logger.info(f"Successfully authenticated with account: {self._account_info.get('account_id', 'Unknown')}")
            
        except Exception as e:
            self._connection_state = IBConnectionState.ERROR
            raise IBAuthenticationError(f"Authentication failed: {str(e)}")
    
    async def _verify_paper_trading_compliance(self) -> None:
        """
        Verify compliance with paper trading requirements.
        """
        if self._credentials.trading_mode == "paper":
            # Check if we're actually connected to paper trading
            account_id = self._account_info.get('account_id', '')
            
            # Paper trading accounts typically have specific patterns
            if not (account_id.startswith('DU') or 'PAPER' in account_id.upper()):
                logger.warning(
                    f"Account {account_id} may not be a paper trading account. "
                    "Please verify you're connected to the correct environment."
                )
            
            # Additional paper trading validations
            net_liquidation = self._account_info.get('net_liquidation', 0)
            if net_liquidation > 1000000:  # Suspiciously high for paper account
                logger.warning(
                    f"Account has high net liquidation value ({net_liquidation}). "
                    "Please verify this is a paper trading account."
                )
            
            logger.info("Paper trading compliance verification completed")
    
    def _process_account_summary(self, account_summary: List[AccountValue]) -> Dict[str, Any]:
        """
        Process account summary data into a structured format.
        """
        account_info = {}
        
        for item in account_summary:
            key = item.tag.lower().replace(' ', '_')
            
            # Convert numeric values
            try:
                if item.value and item.value != '':
                    account_info[key] = float(item.value)
                else:
                    account_info[key] = item.value
            except (ValueError, TypeError):
                account_info[key] = item.value
            
            # Store account ID
            if not account_info.get('account_id'):
                account_info['account_id'] = item.account
        
        return account_info
    
    async def _sync_positions(self) -> None:
        """
        Synchronize positions from Interactive Brokers.
        """
        try:
            if not self._ib_client:
                return
            
            positions = self._ib_client.positions()
            self._positions = {}
            
            for pos in positions:
                position_key = f"{pos.contract.symbol}_{pos.contract.secType}"
                self._positions[position_key] = pos
            
            logger.info(f"Synchronized {len(self._positions)} positions")
            
        except Exception as e:
            logger.error(f"Error synchronizing positions: {str(e)}")
            raise IBDataError(f"Failed to sync positions: {str(e)}")
    
    async def _sync_orders(self) -> None:
        """
        Synchronize orders from Interactive Brokers.
        """
        try:
            if not self._ib_client:
                return
            
            orders = self._ib_client.orders()
            self._orders = {}
            
            for order in orders:
                self._orders[str(order.orderId)] = order
            
            logger.info(f"Synchronized {len(self._orders)} orders")
            
        except Exception as e:
            logger.error(f"Error synchronizing orders: {str(e)}")
            raise IBDataError(f"Failed to sync orders: {str(e)}")
    
    def _setup_event_handlers(self) -> None:
        """
        Set up event handlers for IB client events.
        """
        if not self._ib_client:
            return
        
        # Connection events
        self._ib_client.connectedEvent += self._on_ib_connected
        self._ib_client.disconnectedEvent += self._on_ib_disconnected
        self._ib_client.errorEvent += self._on_ib_error
        
        # Trading events
        self._ib_client.orderStatusEvent += self._on_ib_order_status
        self._ib_client.execDetailsEvent += self._on_ib_execution
        self._ib_client.positionEvent += self._on_ib_position
        
        # Market data events
        self._ib_client.tickerUpdateEvent += self._on_ib_ticker_update
        self._ib_client.barUpdateEvent += self._on_ib_bar_update
    
    def _on_ib_connected(self) -> None:
        """Handle IB connection event."""
        logger.info("IB client connected event received")
    
    def _on_ib_disconnected(self) -> None:
        """Handle IB disconnection event."""
        logger.warning("IB client disconnected event received")
        self._connection_state = IBConnectionState.DISCONNECTED
        asyncio.create_task(self._notify_disconnected())
    
    def _on_ib_error(self, reqId: int, errorCode: int, errorString: str, contract: Contract) -> None:
        """Handle IB error events."""
        error_msg = f"IB Error {errorCode}: {errorString} (reqId: {reqId})"
        logger.error(error_msg)
        
        # Handle critical errors
        if errorCode in [502, 503, 504]:  # Connection errors
            self._connection_state = IBConnectionState.ERROR
            asyncio.create_task(self._notify_error(IBConnectionError(error_msg)))
        elif errorCode in [200, 201, 202]:  # Order errors
            asyncio.create_task(self._notify_error(IBTradingError(error_msg)))
        else:
            asyncio.create_task(self._notify_error(IBIntegrationError(error_msg)))
    
    def _on_ib_order_status(self, trade: Trade) -> None:
        """Handle order status updates."""
        logger.info(f"Order status update: {trade.orderStatus.status} for order {trade.order.orderId}")
        asyncio.create_task(self._notify_order_update(trade))
    
    def _on_ib_execution(self, trade: Trade, fill) -> None:
        """Handle trade executions."""
        logger.info(f"Trade execution: {fill.shares} shares at {fill.price} for order {trade.order.orderId}")
        asyncio.create_task(self._notify_trade_execution(trade, fill))
    
    def _on_ib_position(self, position: Position) -> None:
        """Handle position updates."""
        position_key = f"{position.contract.symbol}_{position.contract.secType}"
        self._positions[position_key] = position
        logger.info(f"Position update: {position.position} shares of {position.contract.symbol}")
    
    def _on_ib_ticker_update(self, ticker) -> None:
        """Handle ticker updates."""
        if self._event_handler:
            asyncio.create_task(self._event_handler('ticker_update', ticker))
    
    def _on_ib_bar_update(self, bars, hasNewBar: bool) -> None:
        """Handle bar updates."""
        if self._event_handler and hasNewBar:
            asyncio.create_task(self._event_handler('bar_update', bars))
    
    # Event notification methods
    async def _notify_connected(self) -> None:
        """Notify connection callbacks."""
        for callback in self._on_connected_callbacks:
            try:
                await callback()
            except Exception as e:
                logger.error(f"Error in connection callback: {str(e)}")
    
    async def _notify_disconnected(self) -> None:
        """Notify disconnection callbacks."""
        for callback in self._on_disconnected_callbacks:
            try:
                await callback()
            except Exception as e:
                logger.error(f"Error in disconnection callback: {str(e)}")
    
    async def _notify_error(self, error: Exception) -> None:
        """Notify error callbacks."""
        self._last_error = error
        for callback in self._on_error_callbacks:
            try:
                await callback(error)
            except Exception as e:
                logger.error(f"Error in error callback: {str(e)}")
    
    async def _notify_order_update(self, trade: Trade) -> None:
        """Notify order update callbacks."""
        for callback in self._on_order_callbacks:
            try:
                await callback(trade)
            except Exception as e:
                logger.error(f"Error in order callback: {str(e)}")
    
    async def _notify_trade_execution(self, trade: Trade, fill) -> None:
        """Notify trade execution callbacks."""
        for callback in self._on_trade_callbacks:
            try:
                await callback(trade, fill)
            except Exception as e:
                logger.error(f"Error in trade callback: {str(e)}")
    
    # Public callback registration methods
    def on_connected(self, callback: Callable) -> None:
        """Register callback for connection events."""
        self._on_connected_callbacks.append(callback)
    
    def on_disconnected(self, callback: Callable) -> None:
        """Register callback for disconnection events."""
        self._on_disconnected_callbacks.append(callback)
    
    def on_error(self, callback: Callable) -> None:
        """Register callback for error events."""
        self._on_error_callbacks.append(callback)
    
    def on_order_update(self, callback: Callable) -> None:
        """Register callback for order updates."""
        self._on_order_callbacks.append(callback)
    
    def on_trade_execution(self, callback: Callable) -> None:
        """Register callback for trade executions."""
        self._on_trade_callbacks.append(callback)
    
    async def place_order(
        self,
        contract: Contract,
        order: Order,
        validate_paper_trading: bool = True
    ) -> Optional[Trade]:
        """
        Place an order with comprehensive error handling and paper trading validation.
        
        Parameters
        ----------
        contract : Contract
            The IB contract to trade
        order : Order
            The order details
        validate_paper_trading : bool
            Whether to validate paper trading compliance
        
        Returns
        -------
        Optional[Trade]
            The trade object if successful, None otherwise
        """
        try:
            if not self.is_authenticated:
                raise IBTradingError("Not authenticated with Interactive Brokers")
            
            # Validate paper trading compliance
            if validate_paper_trading and self._credentials.trading_mode == "paper":
                await self._validate_paper_trading_order(contract, order)
            
            # Place the order
            trade = self._ib_client.placeOrder(contract, order)
            
            if trade:
                logger.info(f"Order placed successfully: {order.orderId}")
                return trade
            else:
                raise IBTradingError("Failed to place order - no trade object returned")
                
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            raise IBTradingError(f"Failed to place order: {str(e)}")
    
    async def _validate_paper_trading_order(self, contract: Contract, order: Order) -> None:
        """
        Validate order compliance with paper trading requirements.
        """
        # Check order size limits for paper trading
        if order.totalQuantity > 10000:  # Example limit
            raise IBTradingError(
                f"Order quantity {order.totalQuantity} exceeds paper trading limit of 10,000"
            )
        
        # Check if contract is allowed for paper trading
        if contract.secType not in ['STK', 'OPT', 'FUT', 'CASH']:  # Common paper trading types
            logger.warning(f"Contract type {contract.secType} may not be supported in paper trading")
        
        # Additional paper trading validations can be added here
        logger.debug(f"Paper trading validation passed for order {order.orderId}")
    
    async def cancel_order(self, order_id: int) -> bool:
        """
        Cancel an order with proper error handling.
        
        Parameters
        ----------
        order_id : int
            The order ID to cancel
        
        Returns
        -------
        bool
            True if cancellation successful, False otherwise
        """
        try:
            if not self.is_authenticated:
                raise IBTradingError("Not authenticated with Interactive Brokers")
            
            # Find the order
            order = self._orders.get(str(order_id))
            if not order:
                raise IBTradingError(f"Order {order_id} not found")
            
            # Cancel the order
            self._ib_client.cancelOrder(order)
            logger.info(f"Order {order_id} cancellation requested")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {str(e)}")
            raise IBTradingError(f"Failed to cancel order: {str(e)}")
    
    async def get_positions(self) -> List[Position]:
        """
        Get current positions with error handling.
        
        Returns
        -------
        List[Position]
            List of current positions
        """
        try:
            if not self.is_authenticated:
                raise IBDataError("Not authenticated with Interactive Brokers")
            
            await self._sync_positions()
            return list(self._positions.values())
            
        except Exception as e:
            logger.error(f"Error getting positions: {str(e)}")
            raise IBDataError(f"Failed to get positions: {str(e)}")
    
    async def get_orders(self) -> List[Order]:
        """
        Get current orders with error handling.
        
        Returns
        -------
        List[Order]
            List of current orders
        """
        try:
            if not self.is_authenticated:
                raise IBDataError("Not authenticated with Interactive Brokers")
            
            await self._sync_orders()
            return list(self._orders.values())
            
        except Exception as e:
            logger.error(f"Error getting orders: {str(e)}")
            raise IBDataError(f"Failed to get orders: {str(e)}")
    
    async def get_account_summary(self) -> Dict[str, Any]:
        """
        Get account summary with error handling.
        
        Returns
        -------
        Dict[str, Any]
            Account summary information
        """
        try:
            if not self.is_authenticated:
                raise IBDataError("Not authenticated with Interactive Brokers")
            
            # Refresh account info
            account_summary = self._ib_client.accountSummary()
            self._account_info = self._process_account_summary(account_summary)
            
            return self._account_info.copy()
            
        except Exception as e:
            logger.error(f"Error getting account summary: {str(e)}")
            raise IBDataError(f"Failed to get account summary: {str(e)}")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get detailed connection status information.
        
        Returns
        -------
        Dict[str, Any]
            Connection status details
        """
        return {
            'state': self._connection_state.value,
            'is_connected': self.is_connected,
            'is_authenticated': self.is_authenticated,
            'connection_attempts': self._connection_attempts,
            'error_count': self._error_count,
            'last_error': str(self._last_error) if self._last_error else None,
            'trading_mode': self._credentials.trading_mode,
            'host': self._credentials.host,
            'port': self._credentials.port,
            'client_id': self._credentials.client_id
        }

# Factory function for easy instantiation
def create_ib_integration(
    host: str = "127.0.0.1",
    port: int = 4001,
    client_id: int = 1,
    trading_mode: str = "paper",
    **kwargs
) -> InteractiveBrokersIntegration:
    """
    Factory function to create an Interactive Brokers integration instance.
    
    Parameters
    ----------
    host : str
        IB Gateway/TWS host
    port : int
        IB Gateway/TWS port (4001 for paper, 7497 for live)
    client_id : int
        Client ID for the connection
    trading_mode : str
        Trading mode ('paper' or 'live')
    **kwargs
        Additional arguments for IBCredentials and InteractiveBrokersIntegration
    
    Returns
    -------
    InteractiveBrokersIntegration
        Configured IB integration instance
    """
    credentials = IBCredentials(
        host=host,
        port=port,
        client_id=client_id,
        trading_mode=trading_mode,
        **{k: v for k, v in kwargs.items() if k in ['account', 'username', 'password']}
    )
    
    integration_kwargs = {k: v for k, v in kwargs.items() if k in ['event_handler', 'max_retries', 'retry_delay']}
    
    return InteractiveBrokersIntegration(credentials, **integration_kwargs)