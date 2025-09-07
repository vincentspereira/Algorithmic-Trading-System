"""
Comprehensive Mocking Framework for Testing

This module provides comprehensive mocking capabilities for APIs, databases,
external services, market data, and trading scenarios with validation and
behavior verification.
"""

import os
import sys
import json
import random
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import logging
from decimal import Decimal
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockType(Enum):
    """Mock type enumeration"""
    API = "api"
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    MARKET_DATA = "market_data"
    TRADING_SERVICE = "trading_service"
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    TIME = "time"
    RANDOM = "random"


class MockBehavior(Enum):
    """Mock behavior enumeration"""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    INTERMITTENT = "intermittent"
    DELAYED = "delayed"
    CUSTOM = "custom"


@dataclass
class MockConfig:
    """Configuration for mock behavior"""
    mock_type: MockType
    behavior: MockBehavior
    success_rate: float = 1.0  # 0.0 to 1.0
    delay_range: Tuple[float, float] = (0.0, 0.0)  # min, max delay in seconds
    failure_exceptions: List[Exception] = field(default_factory=list)
    custom_responses: List[Any] = field(default_factory=list)
    call_count_limit: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MockCall:
    """Information about a mock call"""
    timestamp: datetime
    method_name: str
    args: Tuple
    kwargs: Dict[str, Any]
    return_value: Any
    exception: Optional[Exception] = None
    duration: float = 0.0


@dataclass
class MockValidationResult:
    """Result of mock validation"""
    mock_name: str
    total_calls: int
    expected_calls: int
    call_matches: bool
    behavior_matches: bool
    validation_errors: List[str]
    call_history: List[MockCall]
    success: bool


class MockFactory:
    """
    Factory for creating various types of mocks with predefined behaviors.
    
    This class provides methods to create mocks for APIs, databases, external services,
    market data, and trading scenarios with comprehensive validation capabilities.
    """
    
    def __init__(self):
        """Initialize the MockFactory."""
        self.created_mocks: Dict[str, Mock] = {}
        self.mock_configs: Dict[str, MockConfig] = {}
        self.call_history: Dict[str, List[MockCall]] = {}
        self.active_patches: List[Any] = []
    
    def create_api_mock(self, name: str, config: MockConfig, 
                       endpoints: Dict[str, Any]) -> Mock:
        """
        Create a mock for API services.
        
        Args:
            name: Name identifier for the mock
            config: Mock configuration
            endpoints: Dictionary of endpoint paths to response data
            
        Returns:
            Mock: Configured API mock
        """
        api_mock = MagicMock()
        
        # Configure endpoints
        for endpoint, response_data in endpoints.items():
            method_mock = self._create_method_mock(f"{name}.{endpoint}", config, response_data)
            setattr(api_mock, endpoint, method_mock)
        
        self.created_mocks[name] = api_mock
        self.mock_configs[name] = config
        self.call_history[name] = []
        
        logger.info(f"Created API mock: {name} with {len(endpoints)} endpoints")
        return api_mock
    
    def create_database_mock(self, name: str, config: MockConfig,
                           tables: Dict[str, List[Dict]]) -> Mock:
        """
        Create a mock for database operations.
        
        Args:
            name: Name identifier for the mock
            config: Mock configuration
            tables: Dictionary of table names to sample data
            
        Returns:
            Mock: Configured database mock
        """
        db_mock = MagicMock()
        
        # Mock connection
        connection_mock = MagicMock()
        cursor_mock = MagicMock()
        
        # Configure cursor methods
        cursor_mock.execute = self._create_method_mock(f"{name}.execute", config, True)
        cursor_mock.fetchone = self._create_method_mock(f"{name}.fetchone", config, None)
        cursor_mock.fetchall = self._create_method_mock(f"{name}.fetchall", config, [])
        cursor_mock.fetchmany = self._create_method_mock(f"{name}.fetchmany", config, [])
        
        connection_mock.cursor.return_value = cursor_mock
        connection_mock.commit = self._create_method_mock(f"{name}.commit", config, None)
        connection_mock.rollback = self._create_method_mock(f"{name}.rollback", config, None)
        connection_mock.close = self._create_method_mock(f"{name}.close", config, None)
        
        db_mock.connect.return_value = connection_mock
        db_mock.connection = connection_mock
        db_mock.cursor = cursor_mock
        
        self.created_mocks[name] = db_mock
        self.mock_configs[name] = config
        self.call_history[name] = []
        
        logger.info(f"Created database mock: {name} with {len(tables)} tables")
        return db_mock
    
    def _create_method_mock(self, method_name: str, config: MockConfig, 
                           default_return: Any) -> Mock:
        """Create a mock method with configured behavior."""
        method_mock = Mock()
        
        def mock_side_effect(*args, **kwargs):
            start_time = time.time()
            call_info = MockCall(
                timestamp=datetime.now(),
                method_name=method_name,
                args=args,
                kwargs=kwargs,
                return_value=None
            )
            
            try:
                # Apply delay if configured
                if config.delay_range[1] > 0:
                    delay = random.uniform(config.delay_range[0], config.delay_range[1])
                    time.sleep(delay)
                
                # Determine behavior based on configuration
                if config.behavior == MockBehavior.FAILURE:
                    exception = random.choice(config.failure_exceptions) if config.failure_exceptions else Exception("Mock failure")
                    call_info.exception = exception
                    raise exception
                
                elif config.behavior == MockBehavior.INTERMITTENT:
                    if random.random() > config.success_rate:
                        exception = random.choice(config.failure_exceptions) if config.failure_exceptions else Exception("Intermittent failure")
                        call_info.exception = exception
                        raise exception
                
                elif config.behavior == MockBehavior.TIMEOUT:
                    raise TimeoutError("Mock timeout")
                
                elif config.behavior == MockBehavior.RATE_LIMITED:
                    raise Exception("Rate limit exceeded")
                
                # Return configured response
                if callable(default_return):
                    result = default_return(*args, **kwargs)
                elif config.custom_responses:
                    result = random.choice(config.custom_responses)
                else:
                    result = default_return
                
                call_info.return_value = result
                return result
                
            finally:
                call_info.duration = time.time() - start_time
                
                # Store call history
                mock_name = method_name.split('.')[0]
                if mock_name in self.call_history:
                    self.call_history[mock_name].append(call_info)
        
        method_mock.side_effect = mock_side_effect
        return method_mock
    
    def validate_mock_behavior(self, mock_name: str, 
                              expected_calls: Optional[int] = None,
                              expected_methods: Optional[List[str]] = None) -> MockValidationResult:
        """
        Validate mock behavior and call patterns.
        
        Args:
            mock_name: Name of the mock to validate
            expected_calls: Expected number of calls
            expected_methods: Expected methods that should have been called
            
        Returns:
            MockValidationResult: Validation results
        """
        if mock_name not in self.created_mocks:
            return MockValidationResult(
                mock_name=mock_name,
                total_calls=0,
                expected_calls=expected_calls or 0,
                call_matches=False,
                behavior_matches=False,
                validation_errors=[f"Mock '{mock_name}' not found"],
                call_history=[],
                success=False
            )
        
        call_history = self.call_history.get(mock_name, [])
        total_calls = len(call_history)
        validation_errors = []
        
        # Validate call count
        call_matches = True
        if expected_calls is not None and total_calls != expected_calls:
            call_matches = False
            validation_errors.append(f"Expected {expected_calls} calls, got {total_calls}")
        
        # Validate expected methods were called
        behavior_matches = True
        if expected_methods:
            called_methods = set(call.method_name for call in call_history)
            expected_method_set = set(f"{mock_name}.{method}" for method in expected_methods)
            
            missing_methods = expected_method_set - called_methods
            if missing_methods:
                behavior_matches = False
                validation_errors.append(f"Missing method calls: {missing_methods}")
        
        success = call_matches and behavior_matches and len(validation_errors) == 0
        
        return MockValidationResult(
            mock_name=mock_name,
            total_calls=total_calls,
            expected_calls=expected_calls or 0,
            call_matches=call_matches,
            behavior_matches=behavior_matches,
            validation_errors=validation_errors,
            call_history=call_history,
            success=success
        )
    
    def get_mock_statistics(self, mock_name: str) -> Dict[str, Any]:
        """Get statistics for a specific mock."""
        if mock_name not in self.call_history:
            return {'error': f"Mock '{mock_name}' not found"}
        
        call_history = self.call_history[mock_name]
        
        if not call_history:
            return {
                'mock_name': mock_name,
                'total_calls': 0,
                'methods_called': [],
                'average_duration': 0.0,
                'total_duration': 0.0,
                'success_rate': 1.0,
                'error_count': 0
            }
        
        # Calculate statistics
        total_calls = len(call_history)
        methods_called = list(set(call.method_name for call in call_history))
        total_duration = sum(call.duration for call in call_history)
        average_duration = total_duration / total_calls if total_calls > 0 else 0.0
        error_count = sum(1 for call in call_history if call.exception is not None)
        success_rate = (total_calls - error_count) / total_calls if total_calls > 0 else 1.0
        
        return {
            'mock_name': mock_name,
            'total_calls': total_calls,
            'methods_called': methods_called,
            'average_duration': round(average_duration, 4),
            'total_duration': round(total_duration, 4),
            'success_rate': round(success_rate, 4),
            'error_count': error_count
        }
    
    def reset_mock(self, mock_name: str) -> bool:
        """Reset a mock's call history and state."""
        if mock_name not in self.created_mocks:
            return False
        
        self.created_mocks[mock_name].reset_mock()
        self.call_history[mock_name] = []
        
        logger.info(f"Reset mock: {mock_name}")
        return True
    
    def cleanup_mocks(self) -> None:
        """Clean up all created mocks and patches."""
        for patch_obj in self.active_patches:
            try:
                patch_obj.stop()
            except Exception as e:
                logger.warning(f"Failed to stop patch: {str(e)}")
        
        self.created_mocks.clear()
        self.mock_configs.clear()
        self.call_history.clear()
        self.active_patches.clear()
        
        logger.info("Cleaned up all mocks and patches")
    
    def create_market_data_mock(self, name: str, config: MockConfig, symbols: List[str]) -> Mock:
        """Create a mock for market data services."""
        market_mock = MagicMock()
        
        def generate_price_data(symbol: str) -> Dict[str, Any]:
            base_price = random.uniform(50, 500)
            return {
                'symbol': symbol,
                'price': round(base_price, 2),
                'bid': round(base_price - 0.01, 2),
                'ask': round(base_price + 0.01, 2),
                'volume': random.randint(1000, 100000),
                'timestamp': datetime.now().isoformat()
            }
        
        market_mock.get_quote = self._create_method_mock(f"{name}.get_quote", config, generate_price_data)
        market_mock.get_historical_data = self._create_method_mock(f"{name}.get_historical_data", config, [])
        market_mock.get_symbols = self._create_method_mock(f"{name}.get_symbols", config, symbols)
        market_mock.stream_data = self._create_method_mock(f"{name}.stream_data", config, generate_price_data)
        
        self.created_mocks[name] = market_mock
        self.mock_configs[name] = config
        self.call_history[name] = []
        
        logger.info(f"Created market data mock: {name} with {len(symbols)} symbols")
        return market_mock
    
    def create_trading_service_mock(self, name: str, config: MockConfig) -> Mock:
        """Create a mock for trading services."""
        trading_mock = MagicMock()
        
        def place_order(symbol: str, quantity: int, order_type: str, price: Optional[float] = None) -> Dict[str, Any]:
            return {
                'order_id': str(uuid.uuid4()),
                'symbol': symbol,
                'quantity': quantity,
                'order_type': order_type,
                'price': price,
                'status': 'PENDING'
            }
        
        trading_mock.place_order = self._create_method_mock(f"{name}.place_order", config, place_order)
        trading_mock.cancel_order = self._create_method_mock(f"{name}.cancel_order", config, {'status': 'CANCELLED'})
        trading_mock.get_order_status = self._create_method_mock(f"{name}.get_order_status", config, {'status': 'FILLED'})
        trading_mock.get_portfolio = self._create_method_mock(f"{name}.get_portfolio", config, {'cash': 10000})
        trading_mock.get_account_info = self._create_method_mock(f"{name}.get_account_info", config, {'account_id': 'TEST'})
        
        self.created_mocks[name] = trading_mock
        self.mock_configs[name] = config
        self.call_history[name] = []
        
        logger.info(f"Created trading service mock: {name}")
        return trading_mock
    
    def create_external_service_mock(self, name: str, config: MockConfig, service_endpoints: Dict[str, Any]) -> Mock:
        """Create a mock for external services."""
        service_mock = MagicMock()
        
        for endpoint, response_data in service_endpoints.items():
            method_mock = self._create_method_mock(f"{name}.{endpoint}", config, response_data)
            setattr(service_mock, endpoint, method_mock)
        
        self.created_mocks[name] = service_mock
        self.mock_configs[name] = config
        self.call_history[name] = []
        
        logger.info(f"Created external service mock: {name} with {len(service_endpoints)} endpoints")
        return service_mock


class MockDataGenerator:
    """Generator for realistic mock data for various scenarios."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize the MockDataGenerator."""
        self.seed = seed
        self.symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
        self.currencies = ['USD', 'EUR', 'GBP', 'JPY']
        self.crypto_symbols = ['BTC', 'ETH', 'ADA', 'DOT']
    
    def generate_market_data(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """Generate realistic market data for a symbol."""
        if self.seed is not None:
            random.seed(self.seed)
        
        data = []
        base_price = random.uniform(50, 500)
        
        for i in range(days):
            date = datetime.now() - timedelta(days=days-i)
            
            # Simulate price movement
            volatility = random.uniform(0.01, 0.05)
            price_change = random.gauss(0, volatility)
            base_price *= (1 + price_change)
            base_price = max(base_price, 1.0)
            
            # Generate OHLC data
            open_price = base_price * random.uniform(0.99, 1.01)
            close_price = base_price
            high_price = max(open_price, close_price) * random.uniform(1.0, 1.03)
            low_price = min(open_price, close_price) * random.uniform(0.97, 1.0)
            
            volume = random.randint(100000, 10000000)
            
            data.append({
                'symbol': symbol,
                'date': date.strftime('%Y-%m-%d'),
                'timestamp': date.isoformat(),
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume,
                'change': round(close_price - open_price, 2),
                'change_percent': round((close_price - open_price) / open_price * 100, 2)
            })
        
        return data
    
    def generate_order_book(self, symbol: str, levels: int = 10) -> Dict[str, Any]:
        """Generate realistic order book data."""
        mid_price = random.uniform(100, 500)
        spread = mid_price * random.uniform(0.001, 0.01)
        
        bids = []
        asks = []
        
        for i in range(levels):
            bid_price = mid_price - spread/2 - (i * spread * 0.1)
            bid_size = random.randint(100, 10000)
            bids.append({
                'price': round(bid_price, 2),
                'size': bid_size,
                'orders': random.randint(1, 10)
            })
            
            ask_price = mid_price + spread/2 + (i * spread * 0.1)
            ask_size = random.randint(100, 10000)
            asks.append({
                'price': round(ask_price, 2),
                'size': ask_size,
                'orders': random.randint(1, 10)
            })
        
        return {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'bids': bids,
            'asks': asks,
            'spread': round(spread, 4),
            'mid_price': round(mid_price, 2)
        }
    
    def generate_api_response(self, response_type: str, **kwargs) -> Dict[str, Any]:
        """Generate realistic API response data."""
        base_response = {
            'timestamp': datetime.now().isoformat(),
            'request_id': str(uuid.uuid4()),
            'status': 'success'
        }
        
        if response_type == 'market_quote':
            symbol = kwargs.get('symbol', 'AAPL')
            base_response.update({
                'data': {
                    'symbol': symbol,
                    'price': round(random.uniform(100, 500), 2),
                    'bid': round(random.uniform(100, 500), 2),
                    'ask': round(random.uniform(100, 500), 2),
                    'volume': random.randint(1000000, 100000000),
                    'change': round(random.uniform(-10, 10), 2),
                    'change_percent': round(random.uniform(-5, 5), 2)
                }
            })
        
        elif response_type == 'order_status':
            order_id = kwargs.get('order_id', str(uuid.uuid4()))
            base_response.update({
                'data': {
                    'order_id': order_id,
                    'status': random.choice(['PENDING', 'FILLED', 'CANCELLED']),
                    'symbol': kwargs.get('symbol', 'AAPL'),
                    'quantity': kwargs.get('quantity', random.randint(1, 1000)),
                    'filled_quantity': random.randint(0, kwargs.get('quantity', 100)),
                    'average_price': round(random.uniform(100, 500), 2)
                }
            })
        
        elif response_type == 'error':
            base_response.update({
                'status': 'error',
                'error': {
                    'code': kwargs.get('error_code', 'GENERIC_ERROR'),
                    'message': kwargs.get('error_message', 'An error occurred'),
                    'details': kwargs.get('error_details', {})
                }
            })
        
        return base_response    

    def create_market_data_mock(self, name: str, config: MockConfig, symbols: List[str]) -> Mock:
        """Create a mock for market data services."""
        market_mock = MagicMock()
        
        def generate_price_data(symbol: str) -> Dict[str, Any]:
            base_price = random.uniform(50, 500)
            return {
                'symbol': symbol,
                'price': round(base_price, 2),
                'bid': round(base_price - 0.01, 2),
                'ask': round(base_price + 0.01, 2),
                'volume': random.randint(1000, 100000),
                'timestamp': datetime.now().isoformat()
            }
        
        market_mock.get_quote = self._create_method_mock(f"{name}.get_quote", config, generate_price_data)
        market_mock.get_historical_data = self._create_method_mock(f"{name}.get_historical_data", config, [])
        market_mock.get_symbols = self._create_method_mock(f"{name}.get_symbols", config, symbols)
        market_mock.stream_data = self._create_method_mock(f"{name}.stream_data", config, generate_price_data)
        
        self.created_mocks[name] = market_mock
        self.mock_configs[name] = config
        self.call_history[name] = []
        
        logger.info(f"Created market data mock: {name} with {len(symbols)} symbols")
        return market_mock
    
    def create_trading_service_mock(self, name: str, config: MockConfig) -> Mock:
        """Create a mock for trading services."""
        trading_mock = MagicMock()
        
        def place_order(symbol: str, quantity: int, order_type: str, price: Optional[float] = None) -> Dict[str, Any]:
            return {
                'order_id': str(uuid.uuid4()),
                'symbol': symbol,
                'quantity': quantity,
                'order_type': order_type,
                'price': price,
                'status': 'PENDING'
            }
        
        trading_mock.place_order = self._create_method_mock(f"{name}.place_order", config, place_order)
        trading_mock.cancel_order = self._create_method_mock(f"{name}.cancel_order", config, {'status': 'CANCELLED'})
        trading_mock.get_order_status = self._create_method_mock(f"{name}.get_order_status", config, {'status': 'FILLED'})
        trading_mock.get_portfolio = self._create_method_mock(f"{name}.get_portfolio", config, {'cash': 10000})
        trading_mock.get_account_info = self._create_method_mock(f"{name}.get_account_info", config, {'account_id': 'TEST'})
        
        self.created_mocks[name] = trading_mock
        self.mock_configs[name] = config
        self.call_history[name] = []
        
        logger.info(f"Created trading service mock: {name}")
        return trading_mock
    
    def create_external_service_mock(self, name: str, config: MockConfig, service_endpoints: Dict[str, Any]) -> Mock:
        """Create a mock for external services."""
        service_mock = MagicMock()
        
        for endpoint, response_data in service_endpoints.items():
            method_mock = self._create_method_mock(f"{name}.{endpoint}", config, response_data)
            setattr(service_mock, endpoint, method_mock)
        
        self.created_mocks[name] = service_mock
        self.mock_configs[name] = config
        self.call_history[name] = []
        
        logger.info(f"Created external service mock: {name} with {len(service_endpoints)} endpoints")
        return service_mock    

    def generate_trade_data(self, symbol: str, count: int = 100) -> List[Dict[str, Any]]:
        """Generate realistic trade execution data."""
        trades = []
        base_price = random.uniform(100, 500)
        
        for i in range(count):
            price_change = random.gauss(0, 0.01)
            base_price *= (1 + price_change)
            
            trade = {
                'trade_id': str(uuid.uuid4()),
                'symbol': symbol,
                'timestamp': (datetime.now() - timedelta(minutes=count-i)).isoformat(),
                'price': round(base_price, 2),
                'size': random.randint(100, 10000),
                'side': random.choice(['BUY', 'SELL']),
                'trade_type': random.choice(['MARKET', 'LIMIT', 'STOP']),
                'venue': random.choice(['NYSE', 'NASDAQ', 'BATS', 'IEX'])
            }
            trades.append(trade)
        
        return trades
    
    def generate_portfolio_data(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate realistic portfolio data."""
        if symbols is None:
            symbols = random.sample(self.symbols, random.randint(3, 5))
        
        positions = []
        total_value = 0
        
        for symbol in symbols:
            quantity = random.randint(10, 1000)
            avg_price = random.uniform(50, 500)
            current_price = avg_price * random.uniform(0.8, 1.2)
            market_value = quantity * current_price
            
            total_value += market_value
            
            unrealized_pnl = quantity * (current_price - avg_price)
            
            positions.append({
                'symbol': symbol,
                'quantity': quantity,
                'average_price': round(avg_price, 2),
                'current_price': round(current_price, 2),
                'market_value': round(market_value, 2),
                'unrealized_pnl': round(unrealized_pnl, 2),
                'weight': 0.0
            })
        
        # Calculate position weights
        for position in positions:
            position['weight'] = round(position['market_value'] / total_value * 100, 2)
        
        cash_balance = round(random.uniform(10000, 100000), 2)
        
        return {
            'account_id': f"ACCOUNT_{random.randint(100000, 999999)}",
            'timestamp': datetime.now().isoformat(),
            'cash_balance': cash_balance,
            'total_market_value': round(total_value, 2),
            'total_value': round(total_value + cash_balance, 2),
            'positions': positions
        }
    
    def generate_user_data(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate realistic user data for testing."""
        users = []
        
        first_names = ['John', 'Jane', 'Michael', 'Sarah', 'David', 'Emily']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia']
        domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'company.com']
        
        for i in range(count):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            
            user = {
                'user_id': str(uuid.uuid4()),
                'username': f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}",
                'email': f"{first_name.lower()}.{last_name.lower()}@{random.choice(domains)}",
                'first_name': first_name,
                'last_name': last_name,
                'created_at': (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(),
                'last_login': (datetime.now() - timedelta(hours=random.randint(1, 168))).isoformat(),
                'account_type': random.choice(['BASIC', 'PREMIUM', 'PROFESSIONAL']),
                'status': random.choice(['ACTIVE', 'INACTIVE', 'SUSPENDED']),
                'preferences': {
                    'notifications': random.choice([True, False]),
                    'theme': random.choice(['light', 'dark']),
                    'language': random.choice(['en', 'es', 'fr', 'de'])
                }
            }
            users.append(user)
        
        return users