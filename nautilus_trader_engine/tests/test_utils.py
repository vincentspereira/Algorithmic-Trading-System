"""
Test Utilities and Fixtures for Nautilus Trader Engine.

This module provides comprehensive testing utilities, fixtures, and helpers
for unit, integration, performance, and stress testing of the trading system:

- Test Fixtures: Pre-configured test data and environments
- Mock Objects: Intelligent mocks for external dependencies
- Data Generators: Synthetic market data and trading scenarios
- Assertion Helpers: Specialized assertions for trading logic
- Test Context Managers: Setup/teardown utilities
- Performance Measurement: Detailed performance tracking
- Coverage Analysis: Test coverage reporting and analysis

The test utilities ensure consistent, reliable, and comprehensive testing
across all components of the institutional-grade trading system.
"""

import asyncio
import time
import random
import uuid
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, AsyncGenerator, Generator, Union
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import numpy as np
import pandas as pd

from ..core.dependency_injection import DependencyInjectionContainer, get_container
from ..core.event_system import EventBus, get_event_bus, EventType, EventPriority
from ..core.caching_layer import IntelligentCacheManager, get_cache_manager
from ..core.streaming_architecture import StreamingEngine, get_streaming_engine
from ..core.fault_tolerance import FaultToleranceManager, get_fault_tolerance_manager
from ..core.parallel_processing import ParallelProcessingEngine, get_parallel_engine


@dataclass
class MarketDataFixture:
    """Market data test fixture."""
    symbol: str = "AAPL"
    timeframe: str = "1m"
    start_date: datetime = field(default_factory=lambda: datetime.now() - timedelta(days=30))
    end_date: datetime = field(default_factory=datetime.now)
    base_price: float = 150.0
    volatility: float = 0.02
    trend: float = 0.0001  # Daily trend
    volume_base: int = 1000000

    def generate_ohlcv_data(self, periods: int = 1000) -> pd.DataFrame:
        """Generate synthetic OHLCV data."""
        dates = pd.date_range(self.start_date, self.end_date, periods=periods, freq='1min')

        # Generate random walk with trend and volatility
        price_changes = np.random.normal(self.trend, self.volatility, periods)
        prices = self.base_price * np.exp(np.cumsum(price_changes))

        # Generate OHLC from close prices with some noise
        high_mult = 1 + np.random.uniform(0, 0.02, periods)
        low_mult = 1 - np.random.uniform(0, 0.02, periods)
        open_prices = np.roll(prices, 1)
        open_prices[0] = self.base_price

        highs = prices * high_mult
        lows = prices * low_mult
        closes = prices

        # Generate volume
        volume_noise = np.random.uniform(0.5, 1.5, periods)
        volumes = (self.volume_base * volume_noise).astype(int)

        df = pd.DataFrame({
            'timestamp': dates,
            'open': open_prices,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes,
            'symbol': self.symbol
        })

        return df.set_index('timestamp')


@dataclass
class TradingStrategyFixture:
    """Trading strategy test fixture."""
    strategy_name: str = "TestStrategy"
    symbols: List[str] = field(default_factory=lambda: ["AAPL", "GOOGL", "MSFT"])
    initial_balance: float = 100000.0
    max_position_size: float = 0.1  # 10% of portfolio
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.05
    risk_per_trade_pct: float = 0.01

    def generate_portfolio_state(self) -> Dict[str, Any]:
        """Generate initial portfolio state."""
        return {
            'balance': self.initial_balance,
            'positions': {},
            'orders': [],
            'performance': {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0
            }
        }


@dataclass
class IndicatorTestFixture:
    """Technical indicator test fixture."""
    indicator_name: str = "SMA"
    parameters: Dict[str, Any] = field(default_factory=lambda: {'period': 20})
    input_data: Optional[pd.DataFrame] = None

    def __post_init__(self):
        if self.input_data is None:
            fixture = MarketDataFixture()
            self.input_data = fixture.generate_ohlcv_data(200)

    def get_expected_output_length(self) -> int:
        """Get expected output length after indicator calculation."""
        period = self.parameters.get('period', 20)
        return len(self.input_data) - period + 1


class MockMarketDataProvider:
    """Mock market data provider for testing."""

    def __init__(self, fixture: Optional[MarketDataFixture] = None):
        self.fixture = fixture or MarketDataFixture()
        self.data = self.fixture.generate_ohlcv_data()
        self.subscriptions: Dict[str, Callable] = {}

    async def subscribe(self, symbol: str, callback: Callable):
        """Subscribe to market data."""
        self.subscriptions[symbol] = callback

    async def unsubscribe(self, symbol: str):
        """Unsubscribe from market data."""
        self.subscriptions.pop(symbol, None)

    async def get_historical_data(self, symbol: str, start_date: datetime,
                                end_date: datetime) -> pd.DataFrame:
        """Get historical market data."""
        mask = (self.data.index >= start_date) & (self.data.index <= end_date)
        return self.data[mask].copy()

    async def publish_market_update(self, symbol: str, price: float, volume: int):
        """Publish a market data update."""
        if symbol in self.subscriptions:
            update_data = {
                'symbol': symbol,
                'price': price,
                'volume': volume,
                'timestamp': datetime.now()
            }
            await self.subscriptions[symbol](update_data)


class MockBroker:
    """Mock broker for testing trading operations."""

    def __init__(self, initial_balance: float = 100000.0):
        self.balance = initial_balance
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.orders: List[Dict[str, Any]] = []
        self.order_id_counter = 1

    async def place_order(self, symbol: str, side: str, quantity: int,
                         order_type: str = "market", price: Optional[float] = None) -> Dict[str, Any]:
        """Place a trading order."""
        order = {
            'order_id': f"order_{self.order_id_counter}",
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'order_type': order_type,
            'price': price,
            'status': 'filled',
            'timestamp': datetime.now()
        }

        self.orders.append(order)
        self.order_id_counter += 1

        # Update positions
        if side == 'buy':
            if symbol not in self.positions:
                self.positions[symbol] = {'quantity': 0, 'avg_price': 0.0}
            self.positions[symbol]['quantity'] += quantity
        elif side == 'sell':
            if symbol in self.positions:
                self.positions[symbol]['quantity'] -= quantity
                if self.positions[symbol]['quantity'] <= 0:
                    del self.positions[symbol]

        return order

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        for order in self.orders:
            if order['order_id'] == order_id and order['status'] == 'pending':
                order['status'] = 'cancelled'
                return True
        return False

    async def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """Get current positions."""
        return self.positions.copy()

    async def get_balance(self) -> float:
        """Get account balance."""
        return self.balance


class AsyncTestHelper:
    """Helper utilities for async testing."""

    @staticmethod
    async def wait_for_condition(condition_func: Callable[[], bool],
                               timeout: float = 5.0,
                               check_interval: float = 0.1) -> bool:
        """Wait for a condition to become true."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if condition_func():
                return True
            await asyncio.sleep(check_interval)

        return False

    @staticmethod
    async def collect_async_results(coro_list: List[asyncio.Future],
                                  timeout: Optional[float] = None) -> List[Any]:
        """Collect results from multiple async operations."""
        if timeout:
            results = await asyncio.wait_for(asyncio.gather(*coro_list, return_exceptions=True), timeout)
        else:
            results = await asyncio.gather(*coro_list, return_exceptions=True)

        return results

    @staticmethod
    @asynccontextmanager
    async def async_test_context():
        """Async context manager for test setup/cleanup."""
        # Setup
        yield
        # Cleanup


class PerformanceTestHelper:
    """Helper utilities for performance testing."""

    @staticmethod
    def measure_execution_time(func: Callable, *args, iterations: int = 100, **kwargs) -> Dict[str, float]:
        """Measure function execution time over multiple iterations."""
        times = []

        for _ in range(iterations):
            start_time = time.time()
            func(*args, **kwargs)
            end_time = time.time()
            times.append(end_time - start_time)

        times_array = np.array(times)

        return {
            'mean': np.mean(times_array),
            'median': np.median(times_array),
            'std': np.std(times_array),
            'min': np.min(times_array),
            'max': np.max(times_array),
            'p95': np.percentile(times_array, 95),
            'p99': np.percentile(times_array, 99),
            'iterations': iterations
        }

    @staticmethod
    async def measure_async_execution_time(coro_func: Callable, *args,
                                         iterations: int = 100, **kwargs) -> Dict[str, float]:
        """Measure async function execution time over multiple iterations."""
        times = []

        for _ in range(iterations):
            start_time = time.time()
            await coro_func(*args, **kwargs)
            end_time = time.time()
            times.append(end_time - start_time)

        times_array = np.array(times)

        return {
            'mean': np.mean(times_array),
            'median': np.median(times_array),
            'std': np.std(times_array),
            'min': np.min(times_array),
            'max': np.max(times_array),
            'p95': np.percentile(times_array, 95),
            'p99': np.percentile(times_array, 99),
            'iterations': iterations
        }

    @staticmethod
    def measure_memory_usage(func: Callable, *args, **kwargs) -> Dict[str, float]:
        """Measure memory usage of function execution."""
        import psutil
        import os

        process = psutil.Process(os.getpid())

        # Get initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Execute function
        func(*args, **kwargs)

        # Get final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        return {
            'initial_memory': initial_memory,
            'final_memory': final_memory,
            'memory_delta': final_memory - initial_memory,
            'peak_memory': final_memory  # Simplified
        }


class TestDataGenerator:
    """Generate test data for various scenarios."""

    @staticmethod
    def generate_random_portfolio(num_positions: int = 10,
                                total_value: float = 100000.0) -> Dict[str, Any]:
        """Generate a random portfolio."""
        symbols = [f"STOCK_{i}" for i in range(num_positions)]
        weights = np.random.random(num_positions)
        weights = weights / np.sum(weights)  # Normalize

        positions = {}
        for symbol, weight in zip(symbols, weights):
            position_value = total_value * weight
            price = np.random.uniform(10, 500)
            quantity = int(position_value / price)

            positions[symbol] = {
                'quantity': quantity,
                'avg_price': price,
                'current_price': price * np.random.uniform(0.9, 1.1),
                'market_value': quantity * price * np.random.uniform(0.9, 1.1)
            }

        return {
            'positions': positions,
            'total_value': sum(p['market_value'] for p in positions.values()),
            'cash': total_value * 0.1  # 10% cash
        }

    @staticmethod
    def generate_trading_signals(num_signals: int = 100,
                               symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Generate trading signals."""
        if symbols is None:
            symbols = [f"SYMBOL_{i}" for i in range(10)]

        signals = []
        signal_types = ['BUY', 'SELL', 'HOLD']

        for _ in range(num_signals):
            signal = {
                'symbol': random.choice(symbols),
                'signal_type': random.choice(signal_types),
                'strength': random.uniform(0.1, 1.0),
                'price': random.uniform(10, 500),
                'timestamp': datetime.now() - timedelta(minutes=random.randint(0, 1440)),
                'indicator': random.choice(['RSI', 'MACD', 'BB', 'SMA', 'EMA']),
                'confidence': random.uniform(0.5, 0.95)
            }
            signals.append(signal)

        return signals

    @staticmethod
    def generate_market_regime_data(periods: int = 1000) -> pd.DataFrame:
        """Generate market regime data."""
        dates = pd.date_range(datetime.now() - timedelta(days=periods), periods=periods, freq='D')

        # Generate different market regimes
        regimes = []
        volatility = []

        for i in range(periods):
            # Simple regime detection based on volatility clusters
            if i < periods // 3:
                regime = 'bull'
                vol = np.random.uniform(0.01, 0.03)
            elif i < 2 * periods // 3:
                regime = 'bear'
                vol = np.random.uniform(0.03, 0.06)
            else:
                regime = 'sideways'
                vol = np.random.uniform(0.015, 0.04)

            regimes.append(regime)
            volatility.append(vol)

        return pd.DataFrame({
            'date': dates,
            'regime': regimes,
            'volatility': volatility,
            'returns': np.random.normal(0, np.array(volatility))
        }).set_index('date')


class MockServiceFactory:
    """Factory for creating mock services."""

    @staticmethod
    def create_mock_container() -> DependencyInjectionContainer:
        """Create a mock dependency injection container."""
        container = DependencyInjectionContainer()

        # Register mock services
        container.register(MockMarketDataProvider(), MockMarketDataProvider)
        container.register(MockBroker(), MockBroker)
        container.register(MagicMock(), EventBus)
        container.register(MagicMock(), IntelligentCacheManager)
        container.register(MagicMock(), StreamingEngine)
        container.register(MagicMock(), FaultToleranceManager)
        container.register(MagicMock(), ParallelProcessingEngine)

        return container

    @staticmethod
    def create_mock_event_bus() -> EventBus:
        """Create a mock event bus."""
        mock_bus = MagicMock(spec=EventBus)

        # Configure mock methods
        mock_bus.publish_event = AsyncMock()
        mock_bus.subscribe = AsyncMock()
        mock_bus.unsubscribe = AsyncMock()
        mock_bus.create_event = MagicMock()

        return mock_bus

    @staticmethod
    def create_mock_cache_manager() -> IntelligentCacheManager:
        """Create a mock cache manager."""
        mock_cache = MagicMock(spec=IntelligentCacheManager)

        # Configure mock methods
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=True)
        mock_cache.delete = AsyncMock(return_value=True)

        return mock_cache


# Context managers for test setup
@contextmanager
def mock_services():
    """Context manager that mocks all external services."""
    with patch('nautilus_trader_engine.core.dependency_injection.get_container', MockServiceFactory.create_mock_container), \
         patch('nautilus_trader_engine.core.event_system.get_event_bus', MockServiceFactory.create_mock_event_bus), \
         patch('nautilus_trader_engine.core.caching_layer.get_cache_manager', MockServiceFactory.create_mock_cache_manager):

        yield


@asynccontextmanager
async def async_mock_services():
    """Async context manager that mocks all external services."""
    with mock_services():
        yield


# Custom assertion helpers
class TradingAssertions:
    """Custom assertions for trading logic testing."""

    @staticmethod
    def assert_portfolio_value(portfolio: Dict[str, Any], expected_value: float, tolerance: float = 0.01):
        """Assert portfolio total value within tolerance."""
        total_value = portfolio.get('total_value', 0)
        assert abs(total_value - expected_value) / expected_value <= tolerance, \
            f"Portfolio value {total_value} not within {tolerance*100}% of expected {expected_value}"

    @staticmethod
    def assert_position_size(position: Dict[str, Any], expected_quantity: int, tolerance: int = 1):
        """Assert position size within tolerance."""
        quantity = position.get('quantity', 0)
        assert abs(quantity - expected_quantity) <= tolerance, \
            f"Position size {quantity} not within {tolerance} of expected {expected_quantity}"

    @staticmethod
    def assert_signal_strength(signal: Dict[str, Any], min_strength: float = 0.0, max_strength: float = 1.0):
        """Assert signal strength is within valid range."""
        strength = signal.get('strength', 0)
        assert min_strength <= strength <= max_strength, \
            f"Signal strength {strength} not in range [{min_strength}, {max_strength}]"

    @staticmethod
    def assert_indicator_output_length(output: Union[List, np.ndarray, pd.Series],
                                     expected_length: int, tolerance: int = 1):
        """Assert indicator output length within tolerance."""
        actual_length = len(output)
        assert abs(actual_length - expected_length) <= tolerance, \
            f"Indicator output length {actual_length} not within {tolerance} of expected {expected_length}"

    @staticmethod
    def assert_valid_order(order: Dict[str, Any]):
        """Assert order has all required fields."""
        required_fields = ['order_id', 'symbol', 'side', 'quantity', 'status']
        for field in required_fields:
            assert field in order, f"Order missing required field: {field}"
            assert order[field] is not None, f"Order field {field} is None"

    @staticmethod
    def assert_portfolio_risk_metrics(metrics: Dict[str, Any]):
        """Assert portfolio risk metrics are valid."""
        required_metrics = ['sharpe_ratio', 'max_drawdown', 'var_95', 'expected_shortfall']
        for metric in required_metrics:
            assert metric in metrics, f"Risk metrics missing: {metric}"
            assert isinstance(metrics[metric], (int, float)), f"Risk metric {metric} is not numeric"