"""
Nautilus Trader SDK WebSocket Client

WebSocket client for real-time data streaming.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Callable
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from .models import Order, Position, Portfolio, MarketData
from .exceptions import WebSocketError

class WebSocketClient:
    """WebSocket client for real-time data"""
    
    def __init__(self, main_client):
        self.client = main_client
        self.ws_url = main_client.base_url.replace('http', 'ws') + '/ws'
        self.websocket = None
        self.subscriptions: Dict[str, Callable] = {}
        self.is_connected = False
        self.logger = logging.getLogger(__name__)
    
    async def connect(self):
        """Connect to WebSocket"""
        if self.is_connected:
            return
        
        try:
            headers = {}
            if self.client.api_key:
                headers['Authorization'] = f'Bearer {self.client.api_key}'
            
            self.websocket = await websockets.connect(
                self.ws_url,
                extra_headers=headers,
                ping_interval=30,
                ping_timeout=10
            )
            
            self.is_connected = True
            self.logger.info("WebSocket connected")
            
            # Start message handler
            asyncio.create_task(self._message_handler())
            
        except Exception as e:
            raise WebSocketError(f"Failed to connect to WebSocket: {e}")
    
    async def close(self):
        """Close WebSocket connection"""
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
        self.is_connected = False
        self.subscriptions.clear()
        self.logger.info("WebSocket disconnected")
    
    async def _message_handler(self):
        """Handle incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(data)
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid JSON received: {message}")
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
        except ConnectionClosed:
            self.logger.info("WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            self.logger.error(f"WebSocket error: {e}")
            self.is_connected = False
    
    async def _process_message(self, data: Dict[str, Any]):
        """Process incoming message"""
        message_type = data.get('type')
        if not message_type:
            return
        
        callback = self.subscriptions.get(message_type)
        if callback:
            try:
                # Convert data to appropriate model
                if message_type == 'order_update':
                    order = Order.from_dict(data['data'])
                    callback(order)
                elif message_type == 'position_update':
                    position = Position.from_dict(data['data'])
                    callback(position)
                elif message_type == 'portfolio_update':
                    portfolio = Portfolio.from_dict(data['data'])
                    callback(portfolio)
                elif message_type == 'market_data_update':
                    market_data = MarketData.from_dict(data['data'])
                    callback(market_data)
                else:
                    callback(data['data'])
            except Exception as e:
                self.logger.error(f"Error in callback for {message_type}: {e}")
    
    async def _subscribe(self, subscription_type: str, params: Optional[Dict] = None):
        """Send subscription message"""
        await self.connect()
        
        message = {
            'action': 'subscribe',
            'type': subscription_type,
            'params': params or {}
        }
        
        await self.websocket.send(json.dumps(message))
    
    async def _unsubscribe(self, subscription_type: str):
        """Send unsubscription message"""
        if not self.is_connected:
            return
        
        message = {
            'action': 'unsubscribe',
            'type': subscription_type
        }
        
        await self.websocket.send(json.dumps(message))
        
        # Remove callback
        if subscription_type in self.subscriptions:
            del self.subscriptions[subscription_type]
    
    async def subscribe_orders(self, callback: Callable[[Order], None]):
        """Subscribe to order updates"""
        self.subscriptions['order_update'] = callback
        await self._subscribe('order_update')
    
    async def subscribe_positions(self, callback: Callable[[Position], None]):
        """Subscribe to position updates"""
        self.subscriptions['position_update'] = callback
        await self._subscribe('position_update')
    
    async def subscribe_portfolio(self, callback: Callable[[Portfolio], None]):
        """Subscribe to portfolio updates"""
        self.subscriptions['portfolio_update'] = callback
        await self._subscribe('portfolio_update')
    
    async def subscribe_market_data(
        self,
        symbols: List[str],
        callback: Callable[[MarketData], None]
    ):
        """Subscribe to market data updates"""
        self.subscriptions['market_data_update'] = callback
        await self._subscribe('market_data_update', {'symbols': symbols})
    
    async def unsubscribe_orders(self):
        """Unsubscribe from order updates"""
        await self._unsubscribe('order_update')
    
    async def unsubscribe_positions(self):
        """Unsubscribe from position updates"""
        await self._unsubscribe('position_update')
    
    async def unsubscribe_portfolio(self):
        """Unsubscribe from portfolio updates"""
        await self._unsubscribe('portfolio_update')
    
    async def unsubscribe_market_data(self):
        """Unsubscribe from market data updates"""
        await self._unsubscribe('market_data_update')