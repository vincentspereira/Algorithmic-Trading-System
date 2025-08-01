"""
Nautilus Trader SDK REST Client

REST API client for the Nautilus Trader Python SDK.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from urllib.parse import urljoin, urlencode
import aiohttp

from .models import *
from .exceptions import *

class RestClient:
    """REST API client for Nautilus Trader"""
    
    def __init__(self, main_client):
        self.client = main_client
        self.base_url = f"{main_client.base_url}/api/v1"
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        await self.client.connect()
        
        url = urljoin(self.base_url + "/", endpoint.lstrip("/"))
        
        # Prepare request parameters
        request_headers = self.client._get_auth_headers()
        if headers:
            request_headers.update(headers)
        
        request_kwargs = {
            'headers': request_headers
        }
        
        if params:
            url += "?" + urlencode(params)
        
        if data:
            request_kwargs['json'] = data
        
        # Make request with retries
        for attempt in range(self.client.max_retries + 1):
            try:
                async with self.client.session.request(method, url, **request_kwargs) as response:
                    response_data = await response.json() if response.content_type == 'application/json' else {}
                    
                    if response.status == 200:
                        return response_data
                    elif response.status == 201:
                        return response_data
                    elif response.status == 204:
                        return {}
                    else:
                        # Handle error response
                        error_message = response_data.get('error', f'HTTP {response.status}')
                        if response_data.get('message'):
                            error_message = response_data['message']
                        
                        exception = create_exception_from_response(
                            response.status,
                            error_message,
                            response_data
                        )
                        raise exception
                        
            except aiohttp.ClientError as e:
                if attempt == self.client.max_retries:
                    raise NetworkError(f"Network error after {self.client.max_retries} retries: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
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
        """Create a new order"""
        data = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'order_type': order_type,
            'time_in_force': time_in_force,
            **kwargs
        }
        
        if price is not None:
            data['price'] = price
        if stop_price is not None:
            data['stop_price'] = stop_price
        
        response = await self._request('POST', '/orders', data=data)
        return Order.from_dict(response['data'])
    
    async def get_order(self, order_id: str) -> Order:
        """Get order by ID"""
        response = await self._request('GET', f'/orders/{order_id}')
        return Order.from_dict(response['data'])
    
    async def get_orders(
        self,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Order]:
        """Get orders with optional filtering"""
        params = {'limit': limit, 'offset': offset}
        if symbol:
            params['symbol'] = symbol
        if status:
            params['status'] = status
        
        response = await self._request('GET', '/orders', params=params)
        return parse_orders(response['data'])
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        response = await self._request('DELETE', f'/orders/{order_id}')
        return response.get('success', False)
    
    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        **kwargs
    ) -> Order:
        """Modify an existing order"""
        data = kwargs.copy()
        if quantity is not None:
            data['quantity'] = quantity
        if price is not None:
            data['price'] = price
        
        response = await self._request('PUT', f'/orders/{order_id}', data=data)
        return Order.from_dict(response['data'])
    
    # Position Management
    async def get_positions(self) -> List[Position]:
        """Get all positions"""
        response = await self._request('GET', '/positions')
        return parse_positions(response['data'])
    
    async def get_position(self, symbol: str) -> Position:
        """Get position for specific symbol"""
        response = await self._request('GET', f'/positions/{symbol}')
        return Position.from_dict(response['data'])
    
    async def close_position(self, symbol: str, quantity: Optional[float] = None) -> bool:
        """Close position (partially or fully)"""
        data = {}
        if quantity is not None:
            data['quantity'] = quantity
        
        response = await self._request('POST', f'/positions/{symbol}/close', data=data)
        return response.get('success', False)
    
    # Portfolio Management
    async def get_portfolio(self) -> Portfolio:
        """Get portfolio summary"""
        response = await self._request('GET', '/portfolio')
        return Portfolio.from_dict(response['data'])
    
    async def get_account_balance(self) -> Dict[str, float]:
        """Get account balance"""
        response = await self._request('GET', '/account/balance')
        return response['data']
    
    # Market Data
    async def get_market_data(self, symbol: str) -> MarketData:
        """Get current market data for symbol"""
        response = await self._request('GET', f'/market-data/{symbol}')
        return MarketData.from_dict(response['data'])
    
    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str = "1m",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get historical market data"""
        params = {
            'timeframe': timeframe,
            'limit': limit
        }
        
        if start_date:
            params['start_date'] = start_date.isoformat()
        if end_date:
            params['end_date'] = end_date.isoformat()
        
        response = await self._request('GET', f'/market-data/{symbol}/historical', params=params)
        return response['data']
    
    # Strategy Management
    async def get_strategies(self) -> List[Strategy]:
        """Get all strategies"""
        response = await self._request('GET', '/strategies')
        return parse_strategies(response['data'])
    
    async def get_strategy(self, strategy_id: str) -> Strategy:
        """Get strategy by ID"""
        response = await self._request('GET', f'/strategies/{strategy_id}')
        return Strategy.from_dict(response['data'])
    
    async def create_strategy(self, strategy_config: Dict[str, Any]) -> Strategy:
        """Create new strategy"""
        response = await self._request('POST', '/strategies', data=strategy_config)
        return Strategy.from_dict(response['data'])
    
    async def start_strategy(self, strategy_id: str) -> bool:
        """Start strategy"""
        response = await self._request('POST', f'/strategies/{strategy_id}/start')
        return response.get('success', False)
    
    async def stop_strategy(self, strategy_id: str) -> bool:
        """Stop strategy"""
        response = await self._request('POST', f'/strategies/{strategy_id}/stop')
        return response.get('success', False)
    
    # Backtesting
    async def run_backtest(self, backtest_config: Dict[str, Any]) -> Backtest:
        """Run backtest"""
        response = await self._request('POST', '/backtests', data=backtest_config)
        return Backtest.from_dict(response['data'])
    
    async def get_backtest(self, backtest_id: str) -> Backtest:
        """Get backtest results"""
        response = await self._request('GET', f'/backtests/{backtest_id}')
        return Backtest.from_dict(response['data'])
    
    async def get_backtests(self, limit: int = 50) -> List[Backtest]:
        """Get backtest history"""
        params = {'limit': limit}
        response = await self._request('GET', '/backtests', params=params)
        return parse_backtests(response['data'])
    
    # Risk Management
    async def get_risk_metrics(self) -> RiskMetrics:
        """Get current risk metrics"""
        response = await self._request('GET', '/risk/metrics')
        return RiskMetrics.from_dict(response['data'])
    
    async def set_risk_limits(self, limits: Dict[str, Any]) -> bool:
        """Set risk limits"""
        response = await self._request('POST', '/risk/limits', data=limits)
        return response.get('success', False)
    
    # Analytics
    async def get_analytics(self) -> Analytics:
        """Get trading analytics"""
        response = await self._request('GET', '/analytics')
        return Analytics.from_dict(response['data'])
    
    async def get_performance_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get performance metrics"""
        params = {}
        if start_date:
            params['start_date'] = start_date.isoformat()
        if end_date:
            params['end_date'] = end_date.isoformat()
        
        response = await self._request('GET', '/analytics/performance', params=params)
        return response['data']
    
    # Trades
    async def get_trades(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Trade]:
        """Get trades with optional filtering"""
        params = {'limit': limit, 'offset': offset}
        if symbol:
            params['symbol'] = symbol
        if start_date:
            params['start_date'] = start_date.isoformat()
        if end_date:
            params['end_date'] = end_date.isoformat()
        
        response = await self._request('GET', '/trades', params=params)
        return parse_trades(response['data'])