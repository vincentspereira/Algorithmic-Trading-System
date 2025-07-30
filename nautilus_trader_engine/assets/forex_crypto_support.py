"""
Forex and Cryptocurrency Trading Support
Comprehensive implementation for forex and crypto trading with exchange integration,
currency pair handling, and specialized trading features
"""

import asyncio
import time
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
from abc import ABC, abstractmethod
import json
import hashlib
import hmac
import base64
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore', category=RuntimeWarning)

try:
    import websocket
    import requests
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    websocket = None
    requests = None


class CurrencyType(Enum):
    """Currency types"""
    FIAT = "fiat"
    CRYPTOCURRENCY = "cryptocurrency"
    COMMODITY = "commodity"


class ExchangeType(Enum):
    """Exchange types"""
    FOREX = "forex"
    CRYPTO = "crypto"
    HYBRID = "hybrid"


class OrderSide(Enum):
    """Order sides"""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Currency:
    """Currency specification"""
    code: str
    name: str
    currency_type: CurrencyType
    precision: int = 8
    min_amount: float = 0.00000001
    
    # Fiat-specific
    country: str = ""
    central_bank: str = ""
    
    # Crypto-specific
    blockchain: str = ""
    contract_address: str = ""
    total_supply: float = 0.0
    circulating_supply: float = 0.0
    
    # Trading info
    is_active: bool = True
    trading_fees: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CurrencyPair:
    """Currency pair specification"""
    base_currency: Currency
    quote_currency: Currency
    symbol: str = ""
    
    # Trading parameters
    min_trade_size: float = 0.0
    max_trade_size: float = float('inf')
    tick_size: float = 0.00001
    lot_size: float = 1.0
    
    # Market data
    current_price: float = 0.0
    bid_price: float = 0.0
    ask_price: float = 0.0
    volume_24h: float = 0.0
    
    # Volatility and risk
    volatility: float = 0.0
    correlation_matrix: Dict[str, float] = field(default_factory=dict)
    
    # Exchange info
    exchange: str = ""
    is_active: bool = True
    last_updated: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.symbol:
            self.symbol = f"{self.base_currency.code}/{self.quote_currency.code}"


@dataclass
class TradingOrder:
    """Trading order specification"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: float = 0.0
    stop_price: float = 0.0
    
    # Status and timing
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    
    # Execution details
    filled_quantity: float = 0.0
    average_price: float = 0.0
    fees: float = 0.0
    
    # Risk management
    time_in_force: str = "GTC"  # Good Till Cancelled
    reduce_only: bool = False
    post_only: bool = False
    
    # Metadata
    client_order_id: str = ""
    exchange_order_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExchangeConnector(ABC):
    """Abstract base class for exchange connectors"""
    
    def __init__(self, exchange_name: str, exchange_type: ExchangeType):
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type
        self.logger = logging.getLogger(f"{__name__}.{exchange_name}")
        self.is_connected = False
        self.api_key = ""
        self.api_secret = ""
        self.sandbox_mode = True
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to exchange"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from exchange"""
        pass
    
    @abstractmethod
    async def get_account_balance(self) -> Dict[str, float]:
        """Get account balance"""
        pass
    
    @abstractmethod
    async def place_order(self, order: TradingOrder) -> TradingOrder:
        """Place trading order"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order"""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> TradingOrder:
        """Get order status"""
        pass
    
    @abstractmethod
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data for symbol"""
        pass
    
    @abstractmethod
    async def get_supported_pairs(self) -> List[CurrencyPair]:
        """Get supported currency pairs"""
        pass


class ForexConnector(ExchangeConnector):
    """Forex exchange connector"""
    
    def __init__(self, broker_name: str = "OANDA"):
        super().__init__(broker_name, ExchangeType.FOREX)
        self.base_url = "https://api-fxpractice.oanda.com"  # Sandbox
        self.account_id = ""
        self.session = None
        
    async def connect(self) -> bool:
        """Connect to forex broker"""
        try:
            if not requests:
                self.logger.error("Requests library not available")
                return False
            
            self.session = requests.Session()
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
            
            # Test connection
            response = self.session.get(f"{self.base_url}/v3/accounts")
            if response.status_code == 200:
                accounts = response.json().get('accounts', [])
                if accounts:
                    self.account_id = accounts[0]['id']
                    self.is_connected = True
                    self.logger.info(f"Connected to {self.exchange_name}")
                    return True
            
            self.logger.error(f"Failed to connect to {self.exchange_name}")
            return False
            
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from forex broker"""
        try:
            if self.session:
                self.session.close()
            self.is_connected = False
            self.logger.info(f"Disconnected from {self.exchange_name}")
            return True
        except Exception as e:
            self.logger.error(f"Disconnect error: {e}")
            return False
    
    async def get_account_balance(self) -> Dict[str, float]:
        """Get forex account balance"""
        try:
            if not self.is_connected:
                return {}
            
            response = self.session.get(f"{self.base_url}/v3/accounts/{self.account_id}")
            if response.status_code == 200:
                account_data = response.json()['account']
                return {
                    'balance': float(account_data.get('balance', 0)),
                    'unrealized_pl': float(account_data.get('unrealizedPL', 0)),
                    'margin_used': float(account_data.get('marginUsed', 0)),
                    'margin_available': float(account_data.get('marginAvailable', 0))
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Failed to get account balance: {e}")
            return {}
    
    async def place_order(self, order: TradingOrder) -> TradingOrder:
        """Place forex order"""
        try:
            if not self.is_connected:
                order.status = OrderStatus.REJECTED
                return order
            
            # Convert to OANDA format
            oanda_order = {
                "order": {
                    "type": "MARKET" if order.order_type == OrderType.MARKET else "LIMIT",
                    "instrument": order.symbol.replace('/', '_'),
                    "units": str(int(order.quantity * (1 if order.side == OrderSide.BUY else -1))),
                }
            }
            
            if order.order_type == OrderType.LIMIT:
                oanda_order["order"]["price"] = str(order.price)
            
            response = self.session.post(
                f"{self.base_url}/v3/accounts/{self.account_id}/orders",
                json=oanda_order
            )
            
            if response.status_code == 201:
                result = response.json()
                order.exchange_order_id = result['orderCreateTransaction']['id']
                order.status = OrderStatus.OPEN
                order.updated_at = datetime.now()
                self.logger.info(f"Order placed: {order.order_id}")
            else:
                order.status = OrderStatus.REJECTED
                self.logger.error(f"Order rejected: {response.text}")
            
            return order
            
        except Exception as e:
            self.logger.error(f"Failed to place order: {e}")
            order.status = OrderStatus.REJECTED
            return order
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel forex order"""
        try:
            if not self.is_connected:
                return False
            
            response = self.session.put(
                f"{self.base_url}/v3/accounts/{self.account_id}/orders/{order_id}/cancel"
            )
            
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Failed to cancel order: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> TradingOrder:
        """Get forex order status"""
        try:
            if not self.is_connected:
                return None
            
            response = self.session.get(
                f"{self.base_url}/v3/accounts/{self.account_id}/orders/{order_id}"
            )
            
            if response.status_code == 200:
                order_data = response.json()['order']
                # Convert OANDA order to TradingOrder
                # This is a simplified conversion
                order = TradingOrder(
                    order_id=order_data['id'],
                    symbol=order_data['instrument'].replace('_', '/'),
                    side=OrderSide.BUY if float(order_data['units']) > 0 else OrderSide.SELL,
                    order_type=OrderType.MARKET if order_data['type'] == 'MARKET' else OrderType.LIMIT,
                    quantity=abs(float(order_data['units'])),
                    price=float(order_data.get('price', 0)),
                    status=OrderStatus.OPEN if order_data['state'] == 'PENDING' else OrderStatus.FILLED
                )
                return order
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get order status: {e}")
            return None
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get forex market data"""
        try:
            if not self.is_connected:
                return {}
            
            instrument = symbol.replace('/', '_')
            response = self.session.get(
                f"{self.base_url}/v3/instruments/{instrument}/candles",
                params={'count': 1, 'granularity': 'M1'}
            )
            
            if response.status_code == 200:
                candles = response.json()['candles']
                if candles:
                    latest = candles[-1]
                    return {
                        'symbol': symbol,
                        'bid': float(latest['bid']['c']),
                        'ask': float(latest['ask']['c']),
                        'mid': float(latest['mid']['c']),
                        'volume': float(latest['volume']),
                        'timestamp': latest['time']
                    }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Failed to get market data: {e}")
            return {}
    
    async def get_supported_pairs(self) -> List[CurrencyPair]:
        """Get supported forex pairs"""
        try:
            if not self.is_connected:
                return []
            
            response = self.session.get(f"{self.base_url}/v3/accounts/{self.account_id}/instruments")
            
            if response.status_code == 200:
                instruments = response.json()['instruments']
                pairs = []
                
                for instrument in instruments:
                    if instrument['type'] == 'CURRENCY':
                        base_code, quote_code = instrument['name'].split('_')
                        
                        base_currency = Currency(
                            code=base_code,
                            name=base_code,
                            currency_type=CurrencyType.FIAT,
                            precision=int(instrument['tradeUnitsPrecision'])
                        )
                        
                        quote_currency = Currency(
                            code=quote_code,
                            name=quote_code,
                            currency_type=CurrencyType.FIAT,
                            precision=int(instrument['displayPrecision'])
                        )
                        
                        pair = CurrencyPair(
                            base_currency=base_currency,
                            quote_currency=quote_currency,
                            symbol=f"{base_code}/{quote_code}",
                            min_trade_size=float(instrument['minimumTradeSize']),
                            tick_size=float(instrument['pipLocation']) ** -1,
                            exchange=self.exchange_name
                        )
                        
                        pairs.append(pair)
                
                return pairs
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get supported pairs: {e}")
            return []


class CryptoConnector(ExchangeConnector):
    """Cryptocurrency exchange connector"""
    
    def __init__(self, exchange_name: str = "Binance"):
        super().__init__(exchange_name, ExchangeType.CRYPTO)
        self.base_url = "https://testnet.binance.vision"  # Testnet
        self.ws_url = "wss://testnet.binance.vision/ws"
        self.session = None
        self.websocket = None
        
    def _generate_signature(self, query_string: str) -> str:
        """Generate HMAC signature for Binance API"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def connect(self) -> bool:
        """Connect to crypto exchange"""
        try:
            if not requests:
                self.logger.error("Requests library not available")
                return False
            
            self.session = requests.Session()
            
            # Test connection
            response = self.session.get(f"{self.base_url}/api/v3/ping")
            if response.status_code == 200:
                self.is_connected = True
                self.logger.info(f"Connected to {self.exchange_name}")
                return True
            
            self.logger.error(f"Failed to connect to {self.exchange_name}")
            return False
            
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from crypto exchange"""
        try:
            if self.session:
                self.session.close()
            if self.websocket:
                self.websocket.close()
            self.is_connected = False
            self.logger.info(f"Disconnected from {self.exchange_name}")
            return True
        except Exception as e:
            self.logger.error(f"Disconnect error: {e}")
            return False
    
    async def get_account_balance(self) -> Dict[str, float]:
        """Get crypto account balance"""
        try:
            if not self.is_connected or not self.api_key:
                return {}
            
            timestamp = int(time.time() * 1000)
            query_string = f"timestamp={timestamp}"
            signature = self._generate_signature(query_string)
            
            headers = {'X-MBX-APIKEY': self.api_key}
            response = self.session.get(
                f"{self.base_url}/api/v3/account",
                params={'timestamp': timestamp, 'signature': signature},
                headers=headers
            )
            
            if response.status_code == 200:
                account_data = response.json()
                balances = {}
                
                for balance in account_data['balances']:
                    asset = balance['asset']
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    
                    if free > 0 or locked > 0:
                        balances[asset] = {
                            'free': free,
                            'locked': locked,
                            'total': free + locked
                        }
                
                return balances
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Failed to get account balance: {e}")
            return {}
    
    async def place_order(self, order: TradingOrder) -> TradingOrder:
        """Place crypto order"""
        try:
            if not self.is_connected or not self.api_key:
                order.status = OrderStatus.REJECTED
                return order
            
            timestamp = int(time.time() * 1000)
            
            # Build order parameters
            params = {
                'symbol': order.symbol.replace('/', ''),
                'side': order.side.value.upper(),
                'type': order.order_type.value.upper(),
                'quantity': str(order.quantity),
                'timestamp': timestamp
            }
            
            if order.order_type == OrderType.LIMIT:
                params['price'] = str(order.price)
                params['timeInForce'] = 'GTC'
            
            # Generate signature
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            signature = self._generate_signature(query_string)
            params['signature'] = signature
            
            headers = {'X-MBX-APIKEY': self.api_key}
            response = self.session.post(
                f"{self.base_url}/api/v3/order",
                data=params,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                order.exchange_order_id = str(result['orderId'])
                order.status = OrderStatus.OPEN if result['status'] == 'NEW' else OrderStatus.FILLED
                order.updated_at = datetime.now()
                
                if result.get('fills'):
                    order.filled_quantity = float(result['executedQty'])
                    order.average_price = float(result['price']) if result.get('price') else 0
                
                self.logger.info(f"Order placed: {order.order_id}")
            else:
                order.status = OrderStatus.REJECTED
                self.logger.error(f"Order rejected: {response.text}")
            
            return order
            
        except Exception as e:
            self.logger.error(f"Failed to place order: {e}")
            order.status = OrderStatus.REJECTED
            return order
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel crypto order"""
        try:
            if not self.is_connected or not self.api_key:
                return False
            
            timestamp = int(time.time() * 1000)
            params = {
                'orderId': order_id,
                'timestamp': timestamp
            }
            
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            signature = self._generate_signature(query_string)
            params['signature'] = signature
            
            headers = {'X-MBX-APIKEY': self.api_key}
            response = self.session.delete(
                f"{self.base_url}/api/v3/order",
                params=params,
                headers=headers
            )
            
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Failed to cancel order: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> TradingOrder:
        """Get crypto order status"""
        try:
            if not self.is_connected or not self.api_key:
                return None
            
            timestamp = int(time.time() * 1000)
            params = {
                'orderId': order_id,
                'timestamp': timestamp
            }
            
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            signature = self._generate_signature(query_string)
            params['signature'] = signature
            
            headers = {'X-MBX-APIKEY': self.api_key}
            response = self.session.get(
                f"{self.base_url}/api/v3/order",
                params=params,
                headers=headers
            )
            
            if response.status_code == 200:
                order_data = response.json()
                
                # Map Binance status to our status
                status_map = {
                    'NEW': OrderStatus.OPEN,
                    'PARTIALLY_FILLED': OrderStatus.PARTIALLY_FILLED,
                    'FILLED': OrderStatus.FILLED,
                    'CANCELED': OrderStatus.CANCELLED,
                    'REJECTED': OrderStatus.REJECTED
                }
                
                order = TradingOrder(
                    order_id=str(order_data['orderId']),
                    symbol=order_data['symbol'],
                    side=OrderSide.BUY if order_data['side'] == 'BUY' else OrderSide.SELL,
                    order_type=OrderType.MARKET if order_data['type'] == 'MARKET' else OrderType.LIMIT,
                    quantity=float(order_data['origQty']),
                    price=float(order_data['price']) if order_data['price'] != '0.00000000' else 0,
                    status=status_map.get(order_data['status'], OrderStatus.PENDING),
                    filled_quantity=float(order_data['executedQty']),
                    average_price=float(order_data['price']) if order_data['price'] != '0.00000000' else 0
                )
                
                return order
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get order status: {e}")
            return None
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get crypto market data"""
        try:
            if not self.is_connected:
                return {}
            
            binance_symbol = symbol.replace('/', '')
            response = self.session.get(
                f"{self.base_url}/api/v3/ticker/24hr",
                params={'symbol': binance_symbol}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'symbol': symbol,
                    'price': float(data['lastPrice']),
                    'bid': float(data['bidPrice']),
                    'ask': float(data['askPrice']),
                    'volume': float(data['volume']),
                    'volume_quote': float(data['quoteVolume']),
                    'change_24h': float(data['priceChangePercent']),
                    'high_24h': float(data['highPrice']),
                    'low_24h': float(data['lowPrice']),
                    'timestamp': int(data['closeTime'])
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Failed to get market data: {e}")
            return {}
    
    async def get_supported_pairs(self) -> List[CurrencyPair]:
        """Get supported crypto pairs"""
        try:
            if not self.is_connected:
                return []
            
            response = self.session.get(f"{self.base_url}/api/v3/exchangeInfo")
            
            if response.status_code == 200:
                exchange_info = response.json()
                pairs = []
                
                for symbol_info in exchange_info['symbols']:
                    if symbol_info['status'] == 'TRADING':
                        base_code = symbol_info['baseAsset']
                        quote_code = symbol_info['quoteAsset']
                        
                        base_currency = Currency(
                            code=base_code,
                            name=base_code,
                            currency_type=CurrencyType.CRYPTOCURRENCY,
                            precision=symbol_info['baseAssetPrecision']
                        )
                        
                        quote_currency = Currency(
                            code=quote_code,
                            name=quote_code,
                            currency_type=CurrencyType.CRYPTOCURRENCY if quote_code not in ['USDT', 'BUSD', 'USD'] else CurrencyType.FIAT,
                            precision=symbol_info['quoteAssetPrecision']
                        )
                        
                        # Get lot size and tick size from filters
                        min_qty = 0.0
                        tick_size = 0.00000001
                        
                        for filter_info in symbol_info['filters']:
                            if filter_info['filterType'] == 'LOT_SIZE':
                                min_qty = float(filter_info['minQty'])
                            elif filter_info['filterType'] == 'PRICE_FILTER':
                                tick_size = float(filter_info['tickSize'])
                        
                        pair = CurrencyPair(
                            base_currency=base_currency,
                            quote_currency=quote_currency,
                            symbol=f"{base_code}/{quote_code}",
                            min_trade_size=min_qty,
                            tick_size=tick_size,
                            exchange=self.exchange_name
                        )
                        
                        pairs.append(pair)
                
                return pairs
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to get supported pairs: {e}")
            return []


class ForexCryptoTradingEngine:
    """Main trading engine for forex and crypto"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connectors: Dict[str, ExchangeConnector] = {}
        self.currency_pairs: Dict[str, CurrencyPair] = {}
        self.active_orders: Dict[str, TradingOrder] = {}
        self.order_history: List[TradingOrder] = []
        
        # Risk management
        self.max_position_size = 1000000  # Maximum position size
        self.max_daily_loss = 10000  # Maximum daily loss
        self.daily_pnl = 0.0
        
        # Performance tracking
        self.performance_metrics = defaultdict(dict)
        
    def add_connector(self, connector: ExchangeConnector):
        """Add exchange connector"""
        self.connectors[connector.exchange_name] = connector
        self.logger.info(f"Added connector for {connector.exchange_name}")
    
    async def connect_all(self) -> Dict[str, bool]:
        """Connect to all exchanges"""
        results = {}
        for name, connector in self.connectors.items():
            try:
                result = await connector.connect()
                results[name] = result
                if result:
                    # Load supported pairs
                    pairs = await connector.get_supported_pairs()
                    for pair in pairs:
                        self.currency_pairs[pair.symbol] = pair
                    self.logger.info(f"Loaded {len(pairs)} pairs from {name}")
            except Exception as e:
                self.logger.error(f"Failed to connect to {name}: {e}")
                results[name] = False
        
        return results
    
    async def disconnect_all(self) -> Dict[str, bool]:
        """Disconnect from all exchanges"""
        results = {}
        for name, connector in self.connectors.items():
            try:
                result = await connector.disconnect()
                results[name] = result
            except Exception as e:
                self.logger.error(f"Failed to disconnect from {name}: {e}")
                results[name] = False
        
        return results
    
    async def get_all_balances(self) -> Dict[str, Dict[str, float]]:
        """Get balances from all connected exchanges"""
        balances = {}
        for name, connector in self.connectors.items():
            if connector.is_connected:
                try:
                    balance = await connector.get_account_balance()
                    balances[name] = balance
                except Exception as e:
                    self.logger.error(f"Failed to get balance from {name}: {e}")
                    balances[name] = {}
        
        return balances
    
    def _validate_order(self, order: TradingOrder) -> bool:
        """Validate order before placement"""
        try:
            # Check if pair is supported
            if order.symbol not in self.currency_pairs:
                self.logger.error(f"Unsupported currency pair: {order.symbol}")
                return False
            
            pair = self.currency_pairs[order.symbol]
            
            # Check minimum trade size
            if order.quantity < pair.min_trade_size:
                self.logger.error(f"Order quantity below minimum: {order.quantity} < {pair.min_trade_size}")
                return False
            
            # Check maximum position size
            if order.quantity > self.max_position_size:
                self.logger.error(f"Order quantity exceeds maximum: {order.quantity} > {self.max_position_size}")
                return False
            
            # Check daily loss limit
            if self.daily_pnl < -self.max_daily_loss:
                self.logger.error(f"Daily loss limit exceeded: {self.daily_pnl}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Order validation error: {e}")
            return False
    
    async def place_order(self, exchange_name: str, order: TradingOrder) -> TradingOrder:
        """Place order on specific exchange"""
        try:
            # Validate order
            if not self._validate_order(order):
                order.status = OrderStatus.REJECTED
                return order
            
            # Get connector
            connector = self.connectors.get(exchange_name)
            if not connector or not connector.is_connected:
                self.logger.error(f"Exchange {exchange_name} not connected")
                order.status = OrderStatus.REJECTED
                return order
            
            # Place order
            result_order = await connector.place_order(order)
            
            # Track order
            if result_order.status in [OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]:
                self.active_orders[result_order.order_id] = result_order
            
            self.order_history.append(result_order)
            
            return result_order
            
        except Exception as e:
            self.logger.error(f"Failed to place order: {e}")
            order.status = OrderStatus.REJECTED
            return order
    
    async def cancel_order(self, exchange_name: str, order_id: str) -> bool:
        """Cancel order on specific exchange"""
        try:
            connector = self.connectors.get(exchange_name)
            if not connector or not connector.is_connected:
                return False
            
            result = await connector.cancel_order(order_id)
            
            if result and order_id in self.active_orders:
                self.active_orders[order_id].status = OrderStatus.CANCELLED
                self.active_orders[order_id].updated_at = datetime.now()
                del self.active_orders[order_id]
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to cancel order: {e}")
            return False
    
    async def update_order_statuses(self):
        """Update status of all active orders"""
        for order_id, order in list(self.active_orders.items()):
            try:
                # Find the exchange for this order
                exchange_name = None
                for name, connector in self.connectors.items():
                    if connector.is_connected:
                        updated_order = await connector.get_order_status(order.exchange_order_id)
                        if updated_order:
                            exchange_name = name
                            break
                
                if updated_order:
                    # Update order status
                    self.active_orders[order_id] = updated_order
                    
                    # Remove from active orders if filled or cancelled
                    if updated_order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                        del self.active_orders[order_id]
                        
                        # Update P&L if filled
                        if updated_order.status == OrderStatus.FILLED:
                            self._update_pnl(updated_order)
                
            except Exception as e:
                self.logger.error(f"Failed to update order {order_id}: {e}")
    
    def _update_pnl(self, order: TradingOrder):
        """Update P&L tracking"""
        try:
            # Simplified P&L calculation
            # In practice, this would be more sophisticated
            if order.side == OrderSide.BUY:
                # For buy orders, we assume we're opening a position
                # P&L will be calculated when we close
                pass
            else:
                # For sell orders, calculate basic P&L
                # This is a simplified example
                pnl = order.filled_quantity * order.average_price - order.fees
                self.daily_pnl += pnl
                
                self.performance_metrics[order.symbol]['total_pnl'] = \
                    self.performance_metrics[order.symbol].get('total_pnl', 0) + pnl
                
        except Exception as e:
            self.logger.error(f"Failed to update P&L: {e}")
    
    async def get_market_data_all(self, symbol: str) -> Dict[str, Dict[str, Any]]:
        """Get market data from all exchanges for a symbol"""
        market_data = {}
        for name, connector in self.connectors.items():
            if connector.is_connected:
                try:
                    data = await connector.get_market_data(symbol)
                    if data:
                        market_data[name] = data
                except Exception as e:
                    self.logger.error(f"Failed to get market data from {name}: {e}")
        
        return market_data
    
    def get_supported_pairs(self) -> List[str]:
        """Get all supported currency pairs"""
        return list(self.currency_pairs.keys())
    
    def get_pair_info(self, symbol: str) -> Optional[CurrencyPair]:
        """Get currency pair information"""
        return self.currency_pairs.get(symbol)
    
    def get_active_orders(self) -> List[TradingOrder]:
        """Get all active orders"""
        return list(self.active_orders.values())
    
    def get_order_history(self, limit: int = 100) -> List[TradingOrder]:
        """Get order history"""
        return self.order_history[-limit:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        return {
            'daily_pnl': self.daily_pnl,
            'active_orders_count': len(self.active_orders),
            'total_orders': len(self.order_history),
            'connected_exchanges': [name for name, conn in self.connectors.items() if conn.is_connected],
            'supported_pairs_count': len(self.currency_pairs),
            'performance_by_symbol': dict(self.performance_metrics)
        }


# Example usage and testing
async def main():
    """Example usage of Forex and Crypto Trading Support"""
    
    # Initialize trading engine
    engine = ForexCryptoTradingEngine()
    
    # Add connectors (in practice, you'd set API keys)
    forex_connector = ForexConnector("OANDA")
    crypto_connector = CryptoConnector("Binance")
    
    engine.add_connector(forex_connector)
    engine.add_connector(crypto_connector)
    
    print("=== Forex and Crypto Trading Engine ===")
    
    # Connect to exchanges (would need real API keys)
    print("\n--- Connection Status ---")
    connections = await engine.connect_all()
    for exchange, connected in connections.items():
        print(f"{exchange}: {'Connected' if connected else 'Failed'}")
    
    # Get supported pairs
    print(f"\n--- Supported Pairs ---")
    pairs = engine.get_supported_pairs()
    print(f"Total supported pairs: {len(pairs)}")
    if pairs:
        print("Sample pairs:", pairs[:5])
    
    # Example order creation (demo)
    print("\n--- Example Order Creation ---")
    demo_order = TradingOrder(
        order_id="demo_001",
        symbol="EUR/USD",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=10000,
        price=1.1000
    )
    
    print(f"Created demo order: {demo_order.symbol} {demo_order.side.value} {demo_order.quantity}")
    
    # Get performance summary
    print("\n--- Performance Summary ---")
    summary = engine.get_performance_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    # Disconnect
    print("\n--- Disconnecting ---")
    disconnections = await engine.disconnect_all()
    for exchange, disconnected in disconnections.items():
        print(f"{exchange}: {'Disconnected' if disconnected else 'Failed'}")


if __name__ == "__main__":
    asyncio.run(main())