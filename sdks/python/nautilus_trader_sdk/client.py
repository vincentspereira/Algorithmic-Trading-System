"""
Nautilus Trader Python SDK Client

Main client class for interacting with the Nautilus Trader Engine.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime
import aiohttp
import websockets
from urllib.parse import urljoin

from . import __version__
from .models import *
from .exceptions import *
from .rest_client import RestClient
from .graphql_client import GraphQLClient
from .websocket_client import WebSocketClient
from .webhook_client import WebhookClient

class NautilusTraderClient:
    """
    Main client for Nautilus Trader Engine
    
    Provides unified access to:
    - REST API
    - GraphQL API
    - WebSocket connections
    - Webhook management
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        enable_logging: bool = True
    ):
        """
        Initialize Nautilus Trader client
        
        Args:
            base_url: Base URL of the Nautilus Trader Engine
            api_key: API key for authentication
            secret: Secret key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            enable_logging: Enable SDK logging
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.secret = secret
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Setup logging
        if enable_logging:
            logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize sub-clients
        self.rest = RestClient(self)
        self.graphql = GraphQLClient(self)
        self.websocket = WebSocketClient(self)
        self.webhooks = WebhookClient(self)
        
        # Session for HTTP requests
        self.session: Optional[aiohttp.ClientSession] = None
        self._closed = False
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def connect(self):
        """Initialize HTTP session and connections"""
        if self.session is None:
            connector = aiohttp.TCPConnector(limit=100)
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self._get_auth_headers()
            )
            self.logger.info(f"Connected to Nautilus Trader at {self.base_url}")
    
    async def close(self):
        """Close all connections"""
        if not self._closed:
            if self.session:
                await self.session.close()
            await self.websocket.close()
            self._closed = True
            self.logger.info("Disconnected from Nautilus Trader")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        headers = {
            'User-Agent': f'nautilus-trader-sdk-python/{__version__}',
            'Content-Type': 'application/json'
        }
        
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        
        return headers
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health status"""
        await self.connect()
        
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    self.logger.info("Health check passed")
                    return data
                else:
                    raise APIError(f"Health check failed: {response.status}")
        except aiohttp.ClientError as e:
            raise NetworkError(f"Network error during health check: {e}")
    
    # Order Management
    async def create_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "DAY",
        **kwargs
    ) -> Order:
        """
        Create a new order
        
        Args:
            symbol: Trading symbol (e.g., 'AAPL')
            side: Order side ('buy' or 'sell')
            quantity: Order quantity
            order_type: Order type ('market', 'limit', 'stop', 'stop_limit')
            price: Limit price (required for limit orders)
            stop_price: Stop price (required for stop orders)
            time_in_force: Time in force ('DAY', 'GTC', 'IOC', 'FOK')
            **kwargs: Additional order parameters
        
        Returns:
            Order object
        """
        return await self.rest.create_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            stop_price=stop_price,
            time_in_force=time_in_force,
            **kwargs
        )
    
    async def get_order(self, order_id: str) -> Order:
        """Get order by ID"""
        return await self.rest.get_order(order_id)
    
    async def get_orders(
        self,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Order]:
        """Get orders with optional filtering"""
        return await self.rest.get_orders(
            symbol=symbol,
            status=status,
            limit=limit,
            offset=offset
        )
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        return await self.rest.cancel_order(order_id)
    
    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        **kwargs
    ) -> Order:
        """Modify an existing order"""
        return await self.rest.modify_order(
            order_id=order_id,
            quantity=quantity,
            price=price,
            **kwargs
        )
    
    # Position Management
    async def get_positions(self) -> List[Position]:
        """Get all positions"""
        return await self.rest.get_positions()
    
    async def get_position(self, symbol: str) -> Position:
        """Get position for specific symbol"""
        return await self.rest.get_position(symbol)
    
    async def close_position(self, symbol: str, quantity: Optional[float] = None) -> bool:
        """Close position (partially or fully)"""
        return await self.rest.close_position(symbol, quantity)
    
    # Portfolio Management
    async def get_portfolio(self) -> Portfolio:
        """Get portfolio summary"""
        return await self.rest.get_portfolio()
    
    async def get_account_balance(self) -> Dict[str, float]:
        """Get account balance"""
        return await self.rest.get_account_balance()
    
    # Market Data
    async def get_market_data(self, symbol: str) -> MarketData:
        """Get current market data for symbol"""
        return await self.rest.get_market_data(symbol)
    
    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str = "1m",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get historical market data"""
        return await self.rest.get_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    
    # Strategy Management
    async def get_strategies(self) -> List[Strategy]:
        """Get all strategies"""
        return await self.rest.get_strategies()
    
    async def get_strategy(self, strategy_id: str) -> Strategy:
        """Get strategy by ID"""
        return await self.rest.get_strategy(strategy_id)
    
    async def create_strategy(self, strategy_config: Dict[str, Any]) -> Strategy:
        """Create new strategy"""
        return await self.rest.create_strategy(strategy_config)
    
    async def start_strategy(self, strategy_id: str) -> bool:
        """Start strategy"""
        return await self.rest.start_strategy(strategy_id)
    
    async def stop_strategy(self, strategy_id: str) -> bool:
        """Stop strategy"""
        return await self.rest.stop_strategy(strategy_id)
    
    # Backtesting
    async def run_backtest(self, backtest_config: Dict[str, Any]) -> Backtest:
        """Run backtest"""
        return await self.rest.run_backtest(backtest_config)
    
    async def get_backtest(self, backtest_id: str) -> Backtest:
        """Get backtest results"""
        return await self.rest.get_backtest(backtest_id)
    
    async def get_backtests(self, limit: int = 50) -> List[Backtest]:
        """Get backtest history"""
        return await self.rest.get_backtests(limit)
    
    # Risk Management
    async def get_risk_metrics(self) -> RiskMetrics:
        """Get current risk metrics"""
        return await self.rest.get_risk_metrics()
    
    async def set_risk_limits(self, limits: Dict[str, Any]) -> bool:
        """Set risk limits"""
        return await self.rest.set_risk_limits(limits)
    
    # Analytics
    async def get_analytics(self) -> Analytics:
        """Get trading analytics"""
        return await self.rest.get_analytics()
    
    async def get_performance_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get performance metrics"""
        return await self.rest.get_performance_metrics(start_date, end_date)
    
    # WebSocket Subscriptions
    async def subscribe_orders(self, callback: Callable[[Order], None]):
        """Subscribe to order updates"""
        await self.websocket.subscribe_orders(callback)
    
    async def subscribe_positions(self, callback: Callable[[Position], None]):
        """Subscribe to position updates"""
        await self.websocket.subscribe_positions(callback)
    
    async def subscribe_market_data(
        self,
        symbols: List[str],
        callback: Callable[[MarketData], None]
    ):
        """Subscribe to market data updates"""
        await self.websocket.subscribe_market_data(symbols, callback)
    
    async def subscribe_portfolio(self, callback: Callable[[Portfolio], None]):
        """Subscribe to portfolio updates"""
        await self.websocket.subscribe_portfolio(callback)
    
    # GraphQL Queries
    async def graphql_query(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute GraphQL query"""
        return await self.graphql.query(query, variables)
    
    async def graphql_mutation(self, mutation: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute GraphQL mutation"""
        return await self.graphql.mutation(mutation, variables)
    
    async def graphql_subscription(
        self,
        subscription: str,
        callback: Callable[[Dict], None],
        variables: Optional[Dict] = None
    ):
        """Subscribe to GraphQL subscription"""
        await self.graphql.subscription(subscription, callback, variables)
    
    # Webhook Management
    async def create_webhook(
        self,
        url: str,
        events: List[str],
        name: str,
        secret: Optional[str] = None,
        **kwargs
    ) -> str:
        """Create webhook endpoint"""
        return await self.webhooks.create_webhook(
            url=url,
            events=events,
            name=name,
            secret=secret,
            **kwargs
        )
    
    async def get_webhooks(self) -> List[Dict[str, Any]]:
        """Get all webhook endpoints"""
        return await self.webhooks.get_webhooks()
    
    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete webhook endpoint"""
        return await self.webhooks.delete_webhook(webhook_id)
    
    async def test_webhook(self, webhook_id: str, test_data: Optional[Dict] = None) -> bool:
        """Test webhook endpoint"""
        return await self.webhooks.test_webhook(webhook_id, test_data)
    
    # Utility Methods
    def format_symbol(self, symbol: str) -> str:
        """Format trading symbol"""
        return symbol.upper().strip()
    
    def validate_order_params(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str,
        price: Optional[float] = None
    ) -> bool:
        """Validate order parameters"""
        if not symbol or not isinstance(symbol, str):
            raise ValidationError("Symbol must be a non-empty string")
        
        if side not in ['buy', 'sell']:
            raise ValidationError("Side must be 'buy' or 'sell'")
        
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")
        
        if order_type not in ['market', 'limit', 'stop', 'stop_limit']:
            raise ValidationError("Invalid order type")
        
        if order_type in ['limit', 'stop_limit'] and price is None:
            raise ValidationError("Price is required for limit orders")
        
        return True
    
    async def get_server_time(self) -> datetime:
        """Get server timestamp"""
        await self.connect()
        
        try:
            async with self.session.get(f"{self.base_url}/api/v1/time") as response:
                if response.status == 200:
                    data = await response.json()
                    return datetime.fromisoformat(data['timestamp'])
                else:
                    raise APIError(f"Failed to get server time: {response.status}")
        except aiohttp.ClientError as e:
            raise NetworkError(f"Network error getting server time: {e}")

# Convenience functions
async def create_client(
    base_url: str = "http://localhost:8000",
    api_key: Optional[str] = None,
    secret: Optional[str] = None,
    **kwargs
) -> NautilusTraderClient:
    """
    Create and connect Nautilus Trader client
    
    Args:
        base_url: Base URL of the Nautilus Trader Engine
        api_key: API key for authentication
        secret: Secret key for authentication
        **kwargs: Additional client options
    
    Returns:
        Connected NautilusTraderClient instance
    """
    client = NautilusTraderClient(
        base_url=base_url,
        api_key=api_key,
        secret=secret,
        **kwargs
    )
    await client.connect()
    return client

# Example usage
if __name__ == "__main__":
    async def main():
        # Create client
        async with NautilusTraderClient() as client:
            # Check health
            health = await client.health_check()
            print(f"API Health: {health}")
            
            # Get portfolio
            portfolio = await client.get_portfolio()
            print(f"Portfolio Value: ${portfolio.total_value:,.2f}")
            
            # Create order
            order = await client.create_order(
                symbol="AAPL",
                side="buy",
                quantity=100,
                order_type="limit",
                price=150.25
            )
            print(f"Created order: {order.id}")
            
            # Subscribe to order updates
            def on_order_update(order):
                print(f"Order update: {order.id} - {order.status}")
            
            await client.subscribe_orders(on_order_update)
            
            # Keep connection alive
            await asyncio.sleep(10)
    
    asyncio.run(main())