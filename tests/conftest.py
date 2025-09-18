"""Pytest Configuration and Shared Fixtures

Provides common test fixtures and configuration for the entire test suite.
Includes fixtures for authentication, trading system components, market data,
and comprehensive mocking capabilities.
"""

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pytest
import asyncio
import tempfile
import shutil
from typing import Generator, Dict, Any, AsyncGenerator
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from decimal import Decimal

# Import authentication components
from shared.auth import (
    JWTManager,
    RBACManager,
    UserManager,
    JWTBearer,
    UserProfile,
    Role,
    Permission,
    UserStatus
)

# Import FastAPI app
from services.order_management_service.src.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Provide test configuration settings."""
    return {
        "jwt": {
            "secret_key": "test-secret-key-for-testing-only",
            "algorithm": "HS256",
            "access_token_expire_minutes": 30,
            "refresh_token_expire_days": 7
        },
        "database": {
            "url": "sqlite:///:memory:",
            "echo": False
        },
        "redis": {
            "url": "redis://localhost:6379/1",
            "decode_responses": True
        },
        "logging": {
            "level": "DEBUG",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "kafka": {
            "bootstrap_servers": ["localhost:9092"],
            "consumer_group": "test_group",
            "auto_offset_reset": "earliest"
        },
        "trading": {
            "paper_trading": True,
            "max_position_size": 10000,
            "risk_limits": {
                "max_daily_loss": 1000,
                "max_portfolio_risk": 0.02
            }
        },
        "market_data": {
            "primary_source": "yahoo",
            "fallback_sources": ["alpha_vantage", "finnhub"],
            "cache_ttl": 300
        }
    }


@pytest.fixture
def jwt_manager(test_config) -> JWTManager:
    """Create a JWT manager instance for testing."""
    jwt_config = test_config["jwt"]
    return JWTManager(
        secret_key=jwt_config["secret_key"],
        algorithm=jwt_config["algorithm"],
        access_token_expire_minutes=jwt_config["access_token_expire_minutes"],
        refresh_token_expire_days=jwt_config["refresh_token_expire_days"]
    )


@pytest.fixture
def rbac_manager() -> RBACManager:
    """Create an RBAC manager instance for testing."""
    manager = RBACManager()
    manager.initialize_default_roles()
    return manager


@pytest.fixture
def user_manager(rbac_manager, jwt_manager) -> UserManager:
    """Create a user manager instance for testing."""
    return UserManager(rbac_manager, jwt_manager)


@pytest.fixture
def jwt_bearer(jwt_manager, rbac_manager) -> JWTBearer:
    """Create a JWT bearer instance for testing."""
    return JWTBearer(jwt_manager, rbac_manager)


@pytest.fixture
def auth_system(jwt_manager, rbac_manager, user_manager, jwt_bearer) -> Dict[str, Any]:
    """Create a complete authentication system for testing."""
    return {
        "jwt_manager": jwt_manager,
        "rbac_manager": rbac_manager,
        "user_manager": user_manager,
        "jwt_bearer": jwt_bearer
    }


@pytest.fixture
def test_client() -> TestClient:
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_users() -> Dict[str, Dict[str, Any]]:
    """Provide sample user data for testing."""
    return {
        "admin": {
            "username": "admin",
            "email": "admin@example.com",
            "password": "admin123",
            "first_name": "Admin",
            "last_name": "User",
            "roles": ["admin"]
        },
        "trader": {
            "username": "trader",
            "email": "trader@example.com",
            "password": "trader123",
            "first_name": "Trader",
            "last_name": "User",
            "roles": ["trader"]
        },
        "analyst": {
            "username": "analyst",
            "email": "analyst@example.com",
            "password": "analyst123",
            "first_name": "Analyst",
            "last_name": "User",
            "roles": ["analyst"]
        },
        "viewer": {
            "username": "viewer",
            "email": "viewer@example.com",
            "password": "viewer123",
            "first_name": "Viewer",
            "last_name": "User",
            "roles": ["viewer"]
        }
    }


@pytest.fixture
def created_users(user_manager, sample_users) -> Dict[str, UserProfile]:
    """Create sample users in the system for testing."""
    from shared.auth import UserCreateRequest
    
    users = {}
    for role, user_data in sample_users.items():
        request = UserCreateRequest(**user_data)
        user = user_manager.create_user(request)
        users[role] = user
    
    return users


@pytest.fixture
def valid_tokens(jwt_manager, created_users) -> Dict[str, Dict[str, str]]:
    """Generate valid tokens for test users."""
    tokens = {}
    
    for role, user in created_users.items():
        access_token = jwt_manager.create_access_token(
            user.user_id, user.username, [role]
        )
        refresh_token = jwt_manager.create_refresh_token(
            user.user_id, user.username
        )
        
        tokens[role] = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    return tokens


@pytest.fixture
def auth_headers(valid_tokens) -> Dict[str, Dict[str, str]]:
    """Generate authorization headers for test users."""
    headers = {}
    
    for role, token_data in valid_tokens.items():
        headers[role] = {
            "Authorization": f"Bearer {token_data['access_token']}"
        }
    
    return headers


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables."""
    # Set test environment variables
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    
    # Disable external service calls in tests
    monkeypatch.setenv("DISABLE_EXTERNAL_CALLS", "true")
    
    yield


# Trading System Fixtures

@pytest.fixture
def mock_database():
    """Mock database connection and operations."""
    with patch('shared.database.connection.DatabaseManager') as mock_db:
        mock_instance = AsyncMock()
        mock_db.return_value = mock_instance
        
        # Mock common database operations
        mock_instance.execute = AsyncMock(return_value=None)
        mock_instance.fetch_one = AsyncMock(return_value=None)
        mock_instance.fetch_all = AsyncMock(return_value=[])
        mock_instance.begin_transaction = AsyncMock()
        mock_instance.commit_transaction = AsyncMock()
        mock_instance.rollback_transaction = AsyncMock()
        
        yield mock_instance


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer for testing."""
    with patch('shared.messaging.kafka_client.KafkaProducer') as mock_producer:
        mock_instance = AsyncMock()
        mock_producer.return_value = mock_instance
        
        mock_instance.send = AsyncMock(return_value=None)
        mock_instance.flush = AsyncMock(return_value=None)
        mock_instance.close = AsyncMock(return_value=None)
        
        yield mock_instance


@pytest.fixture
def mock_kafka_consumer():
    """Mock Kafka consumer for testing."""
    with patch('shared.messaging.kafka_client.KafkaConsumer') as mock_consumer:
        mock_instance = AsyncMock()
        mock_consumer.return_value = mock_instance
        
        mock_instance.subscribe = AsyncMock(return_value=None)
        mock_instance.consume = AsyncMock(return_value=[])
        mock_instance.commit = AsyncMock(return_value=None)
        mock_instance.close = AsyncMock(return_value=None)
        
        yield mock_instance


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch('shared.cache.redis_client.RedisClient') as mock_redis:
        mock_instance = AsyncMock()
        mock_redis.return_value = mock_instance
        
        mock_instance.get = AsyncMock(return_value=None)
        mock_instance.set = AsyncMock(return_value=True)
        mock_instance.delete = AsyncMock(return_value=1)
        mock_instance.exists = AsyncMock(return_value=False)
        mock_instance.expire = AsyncMock(return_value=True)
        
        yield mock_instance


@pytest.fixture
def sample_market_data() -> pd.DataFrame:
    """Generate sample market data for testing."""
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='1min')
    np.random.seed(42)  # For reproducible tests
    
    base_price = 100.0
    returns = np.random.normal(0, 0.001, len(dates))
    prices = [base_price]
    
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    data = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
        'close': prices,
        'volume': np.random.randint(1000, 10000, len(dates)),
        'symbol': 'AAPL'
    })
    
    return data


@pytest.fixture
def sample_order_data() -> Dict[str, Any]:
    """Generate sample order data for testing."""
    return {
        'order_id': 'ORD_12345',
        'symbol': 'AAPL',
        'side': 'BUY',
        'quantity': Decimal('100'),
        'order_type': 'MARKET',
        'price': None,
        'strategy_id': 'STRAT_001',
        'portfolio_id': 'PORT_001',
        'timestamp': datetime.utcnow(),
        'status': 'PENDING'
    }


@pytest.fixture
def sample_execution_data() -> Dict[str, Any]:
    """Generate sample execution data for testing."""
    return {
        'execution_id': 'EXEC_12345',
        'order_id': 'ORD_12345',
        'symbol': 'AAPL',
        'executed_quantity': Decimal('100'),
        'execution_price': Decimal('150.25'),
        'commission': Decimal('1.00'),
        'execution_venue': 'NASDAQ',
        'timestamp': datetime.utcnow()
    }


@pytest.fixture
def sample_portfolio_data() -> Dict[str, Any]:
    """Generate sample portfolio data for testing."""
    return {
        'portfolio_id': 'PORT_001',
        'user_id': 'USER_001',
        'name': 'Test Portfolio',
        'cash_balance': Decimal('50000.00'),
        'total_value': Decimal('75000.00'),
        'positions': [
            {
                'symbol': 'AAPL',
                'quantity': Decimal('100'),
                'average_price': Decimal('150.00'),
                'current_price': Decimal('155.00'),
                'unrealized_pnl': Decimal('500.00')
            },
            {
                'symbol': 'GOOGL',
                'quantity': Decimal('50'),
                'average_price': Decimal('2800.00'),
                'current_price': Decimal('2850.00'),
                'unrealized_pnl': Decimal('2500.00')
            }
        ],
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }


@pytest.fixture
def mock_market_data_service():
    """Mock market data service for testing."""
    with patch('services.market_data.service.MarketDataService') as mock_service:
        mock_instance = AsyncMock()
        mock_service.return_value = mock_instance
        
        # Mock market data methods
        mock_instance.get_real_time_quote = AsyncMock(return_value={
            'symbol': 'AAPL',
            'price': 150.25,
            'bid': 150.20,
            'ask': 150.30,
            'volume': 1000000,
            'timestamp': datetime.utcnow()
        })
        
        mock_instance.get_historical_data = AsyncMock()
        mock_instance.subscribe_to_feed = AsyncMock()
        mock_instance.unsubscribe_from_feed = AsyncMock()
        
        yield mock_instance


@pytest.fixture
def mock_trading_engine():
    """Mock trading engine for testing."""
    with patch('services.trading_engine.engine.TradingEngine') as mock_engine:
        mock_instance = AsyncMock()
        mock_engine.return_value = mock_instance
        
        # Mock trading engine methods
        mock_instance.submit_order = AsyncMock(return_value='ORD_12345')
        mock_instance.cancel_order = AsyncMock(return_value=True)
        mock_instance.get_order_status = AsyncMock(return_value='FILLED')
        mock_instance.get_positions = AsyncMock(return_value=[])
        mock_instance.get_portfolio_value = AsyncMock(return_value=Decimal('75000.00'))
        
        yield mock_instance


@pytest.fixture
def mock_risk_manager():
    """Mock risk manager for testing."""
    with patch('services.risk_management.manager.RiskManager') as mock_risk:
        mock_instance = AsyncMock()
        mock_risk.return_value = mock_instance
        
        # Mock risk management methods
        mock_instance.validate_order = AsyncMock(return_value=True)
        mock_instance.calculate_var = AsyncMock(return_value=Decimal('1000.00'))
        mock_instance.check_risk_limits = AsyncMock(return_value=True)
        mock_instance.get_portfolio_risk = AsyncMock(return_value={
            'var_1d': Decimal('1000.00'),
            'var_10d': Decimal('3000.00'),
            'max_drawdown': Decimal('0.05')
        })
        
        yield mock_instance


@pytest.fixture
def mock_ai_assistant():
    """Mock AI assistant for testing."""
    with patch('services.ai_assistant.assistant.AIAssistant') as mock_ai:
        mock_instance = AsyncMock()
        mock_ai.return_value = mock_instance
        
        # Mock AI assistant methods
        mock_instance.process_request = AsyncMock(return_value={
            'response': 'Test response',
            'confidence': 0.95,
            'actions': []
        })
        
        mock_instance.analyze_market = AsyncMock(return_value={
            'sentiment': 'BULLISH',
            'confidence': 0.85,
            'signals': ['RSI_OVERSOLD', 'MACD_BULLISH']
        })
        
        yield mock_instance


class TestDataGenerator:
    """Utility class for generating test data."""
    
    @staticmethod
    def generate_price_series(symbol: str, start_date: datetime, 
                            end_date: datetime, frequency: str = '1min') -> pd.DataFrame:
        """Generate realistic price series for testing."""
        dates = pd.date_range(start=start_date, end=end_date, freq=frequency)
        np.random.seed(hash(symbol) % 2**32)  # Deterministic but symbol-specific
        
        base_price = 100.0 + (hash(symbol) % 1000)
        returns = np.random.normal(0, 0.001, len(dates))
        prices = [base_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
            'close': prices,
            'volume': np.random.randint(1000, 10000, len(dates)),
            'symbol': symbol
        })
    
    @staticmethod
    def generate_order_book(symbol: str, levels: int = 5) -> Dict[str, Any]:
        """Generate order book data for testing."""
        base_price = 100.0 + (hash(symbol) % 1000)
        
        bids = []
        asks = []
        
        for i in range(levels):
            bid_price = base_price - (i + 1) * 0.01
            ask_price = base_price + (i + 1) * 0.01
            
            bids.append({
                'price': round(bid_price, 2),
                'size': np.random.randint(100, 1000)
            })
            
            asks.append({
                'price': round(ask_price, 2),
                'size': np.random.randint(100, 1000)
            })
        
        return {
            'symbol': symbol,
            'bids': bids,
            'asks': asks,
            'timestamp': datetime.utcnow()
        }
    
    @staticmethod
    def generate_trade_data(symbol: str, count: int = 100) -> list:
        """Generate trade execution data for testing."""
        trades = []
        base_price = 100.0 + (hash(symbol) % 1000)
        
        for i in range(count):
            price_change = np.random.normal(0, 0.01)
            trade_price = base_price + price_change
            
            trades.append({
                'trade_id': f'TRADE_{i:06d}',
                'symbol': symbol,
                'price': round(trade_price, 2),
                'size': np.random.randint(10, 1000),
                'side': np.random.choice(['BUY', 'SELL']),
                'timestamp': datetime.utcnow() - timedelta(seconds=i)
            })
        
        return trades


class TestHelpers:
    """Helper methods for testing."""
    
    @staticmethod
    def create_mock_user(user_id: str = "test_user", username: str = "testuser", 
                        roles: list = None) -> Mock:
        """Create a mock user object."""
        if roles is None:
            roles = ["trader"]
        
        mock_user = Mock()
        mock_user.user_id = user_id
        mock_user.username = username
        mock_user.email = f"{username}@example.com"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.status = UserStatus.ACTIVE
        mock_user.roles = roles
        mock_user.created_at = "2024-01-01T00:00:00Z"
        mock_user.updated_at = "2024-01-01T00:00:00Z"
        
        return mock_user
    
    @staticmethod
    def create_mock_token_data(user_id: str = "test_user", username: str = "testuser",
                              roles: list = None, token_type: str = "access") -> Mock:
        """Create a mock token data object."""
        if roles is None:
            roles = ["trader"]
        
        mock_token = Mock()
        mock_token.user_id = user_id
        mock_token.username = username
        mock_token.roles = roles
        mock_token.token_type = token_type
        mock_token.jti = f"jti_{user_id}"
        mock_token.exp = 1234567890
        mock_token.iat = 1234567800
        
        return mock_token
    
    @staticmethod
    def assert_user_response(response_data: dict, expected_user: UserProfile):
        """Assert that a user response matches expected user data."""
        assert response_data["user_id"] == expected_user.user_id
        assert response_data["username"] == expected_user.username
        assert response_data["email"] == expected_user.email
        assert response_data["first_name"] == expected_user.first_name
        assert response_data["last_name"] == expected_user.last_name
        assert response_data["status"] == expected_user.status.value
    
    @staticmethod
    def assert_token_response(response_data: dict):
        """Assert that a token response has required fields."""
        assert "access_token" in response_data
        assert "refresh_token" in response_data
        assert "token_type" in response_data
        assert response_data["token_type"] == "bearer"
        assert isinstance(response_data["access_token"], str)
        assert isinstance(response_data["refresh_token"], str)
        assert len(response_data["access_token"]) > 0
        assert len(response_data["refresh_token"]) > 0
    
    @staticmethod
    def assert_order_response(response_data: dict, expected_order: dict):
        """Assert that an order response matches expected order data."""
        assert response_data["order_id"] == expected_order["order_id"]
        assert response_data["symbol"] == expected_order["symbol"]
        assert response_data["side"] == expected_order["side"]
        assert Decimal(str(response_data["quantity"])) == expected_order["quantity"]
        assert response_data["order_type"] == expected_order["order_type"]
    
    @staticmethod
    def assert_portfolio_response(response_data: dict, expected_portfolio: dict):
        """Assert that a portfolio response matches expected portfolio data."""
        assert response_data["portfolio_id"] == expected_portfolio["portfolio_id"]
        assert response_data["name"] == expected_portfolio["name"]
        assert Decimal(str(response_data["cash_balance"])) == expected_portfolio["cash_balance"]
        assert Decimal(str(response_data["total_value"])) == expected_portfolio["total_value"]
    
    @staticmethod
    def assert_market_data_response(response_data: dict):
        """Assert that market data response has required fields."""
        required_fields = ['symbol', 'price', 'timestamp']
        for field in required_fields:
            assert field in response_data
        
        assert isinstance(response_data['price'], (int, float, Decimal))
        assert response_data['price'] > 0
    
    @staticmethod
    def create_test_order(symbol: str = "AAPL", side: str = "BUY", 
                         quantity: Decimal = Decimal('100')) -> Dict[str, Any]:
        """Create a test order with default values."""
        return {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'order_type': 'MARKET',
            'strategy_id': 'TEST_STRATEGY',
            'portfolio_id': 'TEST_PORTFOLIO'
        }
    
    @staticmethod
    def create_test_portfolio(portfolio_id: str = "TEST_PORT") -> Dict[str, Any]:
        """Create a test portfolio with default values."""
        return {
            'portfolio_id': portfolio_id,
            'name': 'Test Portfolio',
            'cash_balance': Decimal('100000.00'),
            'positions': []
        }


# Make test helpers available as a fixture
@pytest.fixture
def test_helpers() -> TestHelpers:
    """Provide test helper methods."""
    return TestHelpers()


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (deselect with '-m \"not unit\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests (deselect with '-m \"not e2e\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "auth: marks tests as authentication related"
    )
    config.addinivalue_line(
        "markers", "trading: marks tests as trading engine related"
    )
    config.addinivalue_line(
        "markers", "market_data: marks tests as market data related"
    )
    config.addinivalue_line(
        "markers", "risk: marks tests as risk management related"
    )
    config.addinivalue_line(
        "markers", "portfolio: marks tests as portfolio management related"
    )
    config.addinivalue_line(
        "markers", "ai: marks tests as AI assistant related"
    )
    config.addinivalue_line(
        "markers", "kafka: marks tests that require Kafka"
    )
    config.addinivalue_line(
        "markers", "redis: marks tests that require Redis"
    )
    config.addinivalue_line(
        "markers", "database: marks tests that require database"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        
        # Add specific component markers
        if "auth" in str(item.fspath) or "authentication" in str(item.fspath):
            item.add_marker(pytest.mark.auth)
        elif "trading" in str(item.fspath):
            item.add_marker(pytest.mark.trading)
        elif "market_data" in str(item.fspath):
            item.add_marker(pytest.mark.market_data)
        elif "risk" in str(item.fspath):
            item.add_marker(pytest.mark.risk)
        elif "portfolio" in str(item.fspath):
            item.add_marker(pytest.mark.portfolio)
        elif "ai" in str(item.fspath):
            item.add_marker(pytest.mark.ai)
        
        # Add infrastructure markers based on test content
        if hasattr(item, 'function'):
            test_source = str(item.function.__code__.co_code)
            if 'kafka' in item.name.lower() or 'producer' in item.name.lower() or 'consumer' in item.name.lower():
                item.add_marker(pytest.mark.kafka)
            if 'redis' in item.name.lower():
                item.add_marker(pytest.mark.redis)
            if 'database' in item.name.lower() or 'db' in item.name.lower():
                item.add_marker(pytest.mark.database)