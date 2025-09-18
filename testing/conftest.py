"""Pytest configuration and shared fixtures for the trading system.

This module provides common fixtures, utilities, and configuration
for all test types across the trading system.
"""

import asyncio
import os
import sys
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Test configuration
TEST_DATABASE_URL = "sqlite:///test_trading_system.db"
TEST_REDIS_URL = "redis://localhost:6379/15"  # Use DB 15 for tests
TEST_KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

# Initialize Faker for test data generation
fake = Faker()
Faker.seed(42)  # Reproducible test data


# ============================================================================
# Session-scoped fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config() -> Dict[str, Any]:
    """Provide test configuration settings."""
    return {
        "database_url": TEST_DATABASE_URL,
        "redis_url": TEST_REDIS_URL,
        "kafka_bootstrap_servers": TEST_KAFKA_BOOTSTRAP_SERVERS,
        "environment": "test",
        "debug": True,
        "testing": True,
        "log_level": "DEBUG",
        "secret_key": "test-secret-key-not-for-production",
        "jwt_secret": "test-jwt-secret-not-for-production",
        "encryption_key": "test-encryption-key-32-bytes-long",
        "api_rate_limit": 1000,  # Higher limit for tests
        "cache_ttl": 60,
        "session_timeout": 3600,
    }


@pytest.fixture(scope="session")
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


# ============================================================================
# Database fixtures
# ============================================================================

@pytest.fixture(scope="session")
def db_engine(test_config):
    """Create a test database engine."""
    engine = create_engine(
        test_config["database_url"],
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a database session for each test."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    
    # Start a transaction
    transaction = session.begin()
    
    try:
        yield session
    finally:
        # Rollback transaction to clean up
        transaction.rollback()
        session.close()


@pytest.fixture(scope="function")
async def async_db_session(db_engine):
    """Create an async database session for each test."""
    # This would be implemented with async SQLAlchemy
    # For now, return a mock
    mock_session = AsyncMock()
    yield mock_session


# ============================================================================
# Redis fixtures
# ============================================================================

@pytest.fixture(scope="session")
def redis_client(test_config):
    """Create a Redis client for tests."""
    try:
        import redis
        client = redis.from_url(test_config["redis_url"])
        # Test connection
        client.ping()
        yield client
        # Clean up test database
        client.flushdb()
    except ImportError:
        # Return mock if Redis not available
        yield MagicMock()
    except Exception:
        # Return mock if Redis not running
        yield MagicMock()


@pytest.fixture(scope="function")
async def async_redis_client(test_config):
    """Create an async Redis client for tests."""
    try:
        import aioredis
        client = aioredis.from_url(test_config["redis_url"])
        yield client
        await client.flushdb()
        await client.close()
    except ImportError:
        # Return mock if aioredis not available
        yield AsyncMock()
    except Exception:
        # Return mock if Redis not running
        yield AsyncMock()


# ============================================================================
# Kafka fixtures
# ============================================================================

@pytest.fixture(scope="session")
def kafka_producer(test_config):
    """Create a Kafka producer for tests."""
    try:
        from kafka import KafkaProducer
        producer = KafkaProducer(
            bootstrap_servers=test_config["kafka_bootstrap_servers"],
            value_serializer=lambda v: str(v).encode('utf-8')
        )
        yield producer
        producer.close()
    except ImportError:
        yield MagicMock()
    except Exception:
        yield MagicMock()


@pytest.fixture(scope="session")
def kafka_consumer(test_config):
    """Create a Kafka consumer for tests."""
    try:
        from kafka import KafkaConsumer
        consumer = KafkaConsumer(
            bootstrap_servers=test_config["kafka_bootstrap_servers"],
            auto_offset_reset='earliest',
            value_deserializer=lambda m: m.decode('utf-8')
        )
        yield consumer
        consumer.close()
    except ImportError:
        yield MagicMock()
    except Exception:
        yield MagicMock()


# ============================================================================
# Trading system fixtures
# ============================================================================

@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """Generate sample user data for tests."""
    return {
        "id": str(uuid.uuid4()),
        "username": fake.user_name(),
        "email": fake.email(),
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "created_at": fake.date_time_this_year(),
        "is_active": True,
        "is_verified": True,
        "role": "trader",
    }


@pytest.fixture
def sample_portfolio_data() -> Dict[str, Any]:
    """Generate sample portfolio data for tests."""
    return {
        "id": str(uuid.uuid4()),
        "name": fake.company(),
        "description": fake.text(max_nb_chars=200),
        "initial_capital": fake.pydecimal(left_digits=6, right_digits=2, positive=True),
        "current_value": fake.pydecimal(left_digits=6, right_digits=2, positive=True),
        "currency": fake.currency_code(),
        "created_at": fake.date_time_this_year(),
        "risk_tolerance": fake.random_element(["conservative", "moderate", "aggressive"]),
    }


@pytest.fixture
def sample_order_data() -> Dict[str, Any]:
    """Generate sample order data for tests."""
    return {
        "id": str(uuid.uuid4()),
        "symbol": fake.random_element(["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]),
        "side": fake.random_element(["BUY", "SELL"]),
        "order_type": fake.random_element(["MARKET", "LIMIT", "STOP"]),
        "quantity": fake.random_int(min=1, max=1000),
        "price": fake.pydecimal(left_digits=3, right_digits=2, positive=True),
        "status": fake.random_element(["PENDING", "FILLED", "CANCELLED"]),
        "created_at": fake.date_time_this_year(),
        "filled_at": None,
    }


@pytest.fixture
def sample_market_data() -> Dict[str, Any]:
    """Generate sample market data for tests."""
    base_price = fake.pydecimal(left_digits=3, right_digits=2, positive=True)
    return {
        "symbol": fake.random_element(["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]),
        "timestamp": datetime.utcnow(),
        "open": base_price,
        "high": base_price * fake.pydecimal(left_digits=1, right_digits=3, positive=True, min_value=1.0, max_value=1.1),
        "low": base_price * fake.pydecimal(left_digits=1, right_digits=3, positive=True, min_value=0.9, max_value=1.0),
        "close": base_price * fake.pydecimal(left_digits=1, right_digits=3, positive=True, min_value=0.95, max_value=1.05),
        "volume": fake.random_int(min=1000, max=1000000),
        "bid": base_price * 0.999,
        "ask": base_price * 1.001,
    }


# ============================================================================
# Mock fixtures
# ============================================================================

@pytest.fixture
def mock_trading_engine():
    """Mock trading engine for tests."""
    mock = MagicMock()
    mock.submit_order = AsyncMock(return_value={"order_id": str(uuid.uuid4()), "status": "SUBMITTED"})
    mock.cancel_order = AsyncMock(return_value={"status": "CANCELLED"})
    mock.get_positions = AsyncMock(return_value=[])
    mock.get_orders = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_market_data_service():
    """Mock market data service for tests."""
    mock = MagicMock()
    mock.get_quote = AsyncMock(return_value={"symbol": "AAPL", "price": 150.0, "timestamp": datetime.utcnow()})
    mock.get_historical_data = AsyncMock(return_value=[])
    mock.subscribe = AsyncMock()
    mock.unsubscribe = AsyncMock()
    return mock


@pytest.fixture
def mock_portfolio_manager():
    """Mock portfolio manager for tests."""
    mock = MagicMock()
    mock.get_portfolio = AsyncMock(return_value={"total_value": 100000.0, "positions": []})
    mock.calculate_performance = AsyncMock(return_value={"return": 0.05, "volatility": 0.15})
    mock.rebalance = AsyncMock(return_value={"status": "SUCCESS"})
    return mock


@pytest.fixture
def mock_risk_manager():
    """Mock risk manager for tests."""
    mock = MagicMock()
    mock.check_risk_limits = AsyncMock(return_value={"approved": True, "warnings": []})
    mock.calculate_var = AsyncMock(return_value=5000.0)
    mock.get_exposure = AsyncMock(return_value={"total": 50000.0, "by_sector": {}})
    return mock


# ============================================================================
# HTTP client fixtures
# ============================================================================

@pytest.fixture
async def http_client():
    """Create an HTTP client for API tests."""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            yield client
    except ImportError:
        yield AsyncMock()


@pytest.fixture
def api_headers(test_config) -> Dict[str, str]:
    """Generate API headers for tests."""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {test_config['jwt_secret']}",
        "X-API-Key": "test-api-key",
    }


# ============================================================================
# Performance testing fixtures
# ============================================================================

@pytest.fixture
def performance_metrics():
    """Track performance metrics during tests."""
    metrics = {
        "start_time": datetime.utcnow(),
        "memory_usage": [],
        "cpu_usage": [],
        "response_times": [],
    }
    yield metrics
    metrics["end_time"] = datetime.utcnow()
    metrics["duration"] = (metrics["end_time"] - metrics["start_time"]).total_seconds()


# ============================================================================
# Security testing fixtures
# ============================================================================

@pytest.fixture
def security_context():
    """Provide security context for tests."""
    return {
        "user_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "permissions": ["read", "write", "execute"],
        "ip_address": fake.ipv4(),
        "user_agent": fake.user_agent(),
        "timestamp": datetime.utcnow(),
    }


# ============================================================================
# Utility functions
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Create reports directory if it doesn't exist
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    (reports_dir / "coverage").mkdir(exist_ok=True)
    (reports_dir / "html").mkdir(exist_ok=True)
    (reports_dir / "junit").mkdir(exist_ok=True)
    (reports_dir / "logs").mkdir(exist_ok=True)


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file paths."""
    for item in items:
        # Add markers based on file path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "system" in str(item.fspath):
            item.add_marker(pytest.mark.system)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        elif "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)
        elif "acceptance" in str(item.fspath):
            item.add_marker(pytest.mark.acceptance)
        
        # Add speed markers based on test name patterns
        if "slow" in item.name or "load" in item.name:
            item.add_marker(pytest.mark.slow)
        elif "fast" in item.name or "quick" in item.name:
            item.add_marker(pytest.mark.fast)
        else:
            item.add_marker(pytest.mark.medium)


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, test_config):
    """Set up test environment variables."""
    for key, value in test_config.items():
        monkeypatch.setenv(key.upper(), str(value))


@pytest.fixture
def cleanup_files():
    """Clean up test files after test completion."""
    files_to_cleanup = []
    yield files_to_cleanup
    
    # Clean up files
    for file_path in files_to_cleanup:
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception:
            pass  # Ignore cleanup errors


# ============================================================================
# Async utilities
# ============================================================================

@pytest.fixture
def anyio_backend():
    """Use asyncio backend for async tests."""
    return "asyncio"


# ============================================================================
# Custom assertions
# ============================================================================

def assert_valid_uuid(value: str) -> None:
    """Assert that a string is a valid UUID."""
    try:
        uuid.UUID(value)
    except ValueError:
        pytest.fail(f"'{value}' is not a valid UUID")


def assert_valid_timestamp(value: datetime) -> None:
    """Assert that a datetime is valid and recent."""
    if not isinstance(value, datetime):
        pytest.fail(f"Expected datetime, got {type(value)}")
    
    now = datetime.utcnow()
    if value > now + timedelta(minutes=1):
        pytest.fail(f"Timestamp {value} is in the future")
    
    if value < now - timedelta(days=1):
        pytest.fail(f"Timestamp {value} is too old")


def assert_positive_number(value: float, name: str = "value") -> None:
    """Assert that a number is positive."""
    if not isinstance(value, (int, float)):
        pytest.fail(f"Expected number, got {type(value)} for {name}")
    
    if value <= 0:
        pytest.fail(f"{name} must be positive, got {value}")


# Export utility functions
__all__ = [
    "assert_valid_uuid",
    "assert_valid_timestamp", 
    "assert_positive_number",
    "fake",
]