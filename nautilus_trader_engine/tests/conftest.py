"""
Pytest Configuration and Fixtures for Nautilus Trader Engine.

This module provides pytest configuration, global fixtures, and test setup
for comprehensive testing of the institutional-grade trading system:

- Global test configuration and settings
- Common test fixtures for all test types
- Test data setup and teardown
- Mock service initialization
- Performance and coverage configuration
- Async test support and utilities

The configuration ensures consistent test execution across unit, integration,
performance, and stress tests with proper isolation and resource management.
"""

import pytest
import asyncio
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Generator, AsyncGenerator
import numpy as np
import pandas as pd

from nautilus_trader_engine.tests.test_utils import (
    MarketDataFixture,
    TradingStrategyFixture,
    IndicatorTestFixture,
    MockMarketDataProvider,
    MockBroker,
    MockServiceFactory,
    mock_services,
    async_mock_services,
    TestDataGenerator
)

# Configure logging for tests
logging.basicConfig(
    level=logging.WARNING,  # Reduce log noise during tests
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Disable verbose logging for external libraries
logging.getLogger('matplotlib').setLevel(logging.ERROR)
logging.getLogger('pandas').setLevel(logging.WARNING)
logging.getLogger('numpy').setLevel(logging.WARNING)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "stress: Stress tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "flaky: Tests that may be unstable")

    # Set test execution settings
    config.option.asyncio_mode = "auto"
    config.option.disable_warnings = True


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers and skip slow tests."""
    for item in items:
        # Add markers based on test path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        elif "stress" in str(item.fspath):
            item.add_marker(pytest.mark.stress)

        # Mark slow tests
        if "performance" in item.keywords or "stress" in item.keywords:
            item.add_marker(pytest.mark.slow)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for the test session."""
    temp_path = tempfile.mkdtemp(prefix="nautilus_test_")
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture(scope="function")
def market_data_fixture():
    """Provide a market data fixture for tests."""
    return MarketDataFixture()


@pytest.fixture(scope="function")
def trading_strategy_fixture():
    """Provide a trading strategy fixture for tests."""
    return TradingStrategyFixture()


@pytest.fixture(scope="function")
def indicator_test_fixture():
    """Provide an indicator test fixture for tests."""
    return IndicatorTestFixture()


@pytest.fixture(scope="function")
def mock_market_data_provider():
    """Provide a mock market data provider."""
    return MockMarketDataProvider()


@pytest.fixture(scope="function")
def mock_broker():
    """Provide a mock broker."""
    return MockBroker()


@pytest.fixture(scope="function")
def sample_ohlcv_data():
    """Provide sample OHLCV data for testing."""
    fixture = MarketDataFixture()
    return fixture.generate_ohlcv_data(100)


@pytest.fixture(scope="function")
def sample_portfolio():
    """Provide a sample portfolio for testing."""
    return TestDataGenerator.generate_random_portfolio()


@pytest.fixture(scope="function")
def sample_trading_signals():
    """Provide sample trading signals for testing."""
    return TestDataGenerator.generate_trading_signals(50)


@pytest.fixture(scope="function")
def sample_market_regime_data():
    """Provide sample market regime data for testing."""
    return TestDataGenerator.generate_market_regime_data(100)


@pytest.fixture(scope="function")
def mock_container():
    """Provide a mock dependency injection container."""
    return MockServiceFactory.create_mock_container()


@pytest.fixture(scope="function")
def mock_event_bus():
    """Provide a mock event bus."""
    return MockServiceFactory.create_mock_event_bus()


@pytest.fixture(scope="function")
def mock_cache_manager():
    """Provide a mock cache manager."""
    return MockServiceFactory.create_mock_cache_manager()


@pytest.fixture(autouse=True)
def mock_external_services():
    """Automatically mock external services for all tests."""
    with mock_services():
        yield


@pytest.fixture(scope="function")
async def async_mock_services_fixture():
    """Provide async mock services context manager."""
    async with async_mock_services():
        yield


@pytest.fixture(scope="function")
def performance_config():
    """Provide performance test configuration."""
    return {
        'iterations': 100,
        'warmup_iterations': 10,
        'timeout': 300.0,
        'memory_threshold': 100.0,  # MB
        'cpu_threshold': 80.0,      # %
        'latency_p95_threshold': 1.0,  # seconds
        'throughput_threshold': 10.0   # ops/sec
    }


@pytest.fixture(scope="function")
def stress_config():
    """Provide stress test configuration."""
    return {
        'duration': 30.0,      # seconds
        'concurrent_users': 10,
        'ramp_up_time': 5.0,   # seconds
        'max_response_time': 5.0,  # seconds
        'error_rate_threshold': 0.05,  # 5%
        'throughput_threshold': 50.0   # req/sec
    }


@pytest.fixture(scope="function")
def coverage_config():
    """Provide test coverage configuration."""
    return {
        'source': ['nautilus_trader_engine'],
        'omit': [
            '*/tests/*',
            '*/test_*',
            '*/conftest.py',
            '*/__pycache__/*',
            '*/migrations/*'
        ],
        'include': ['*.py'],
        'target': 95.0,  # Minimum coverage percentage
        'fail_under': 90.0,  # Fail if below this percentage
        'show_missing': True,
        'skip_covered': False
    }


# Custom pytest hooks for enhanced reporting
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Add custom information to test reports."""
    outcome = yield
    report = outcome.get_result()

    # Add performance metrics if available
    if hasattr(item, '_performance_metrics'):
        report.performance_metrics = item._performance_metrics

    # Add memory usage if available
    if hasattr(item, '_memory_usage'):
        report.memory_usage = item._memory_usage

    # Add custom markers
    if call.excinfo is not None:
        # Add failure information
        report.failure_info = {
            'exception_type': call.excinfo.type.__name__,
            'exception_message': str(call.excinfo.value),
            'traceback': str(call.excinfo.traceback)
        }


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up the test environment."""
    # Set random seed for reproducible tests
    np.random.seed(42)

    # Configure pandas for testing
    pd.set_option('mode.chained_assignment', None)  # Suppress warnings

    # Set up any global test state
    yield

    # Clean up global test state
    pass


@pytest.fixture(scope="function", autouse=True)
def reset_random_state():
    """Reset random state for each test."""
    np.random.seed(42)
    # Reset any other random state as needed


# Async test utilities
@pytest.fixture(scope="function")
def async_runner():
    """Provide an async test runner."""
    return asyncio.get_event_loop()


# Performance test fixtures
@pytest.fixture(scope="function")
def benchmark_config():
    """Provide benchmark configuration."""
    return {
        'rounds': 10,
        'iterations': 100,
        'warmup_rounds': 2,
        'calibration_precision': 10,
        'add_stats': ['mean', 'std', 'min', 'max', 'median', 'iqr'],
        'sort': 'mean'
    }


# Integration test fixtures
@pytest.fixture(scope="function")
def integration_config():
    """Provide integration test configuration."""
    return {
        'timeout': 60.0,
        'retry_attempts': 3,
        'retry_delay': 1.0,
        'cleanup_timeout': 10.0,
        'service_startup_timeout': 30.0
    }


# Custom test markers for conditional execution
def pytest_runtest_setup(item):
    """Set up conditional test execution."""
    # Skip performance tests in CI unless explicitly requested
    if item.get_closest_marker("performance"):
        if not item.config.getoption("--run-performance", default=False):
            pytest.skip("Performance tests skipped (use --run-performance to run)")

    # Skip stress tests in CI unless explicitly requested
    if item.get_closest_marker("stress"):
        if not item.config.getoption("--run-stress", default=False):
            pytest.skip("Stress tests skipped (use --run-stress to run)")

    # Skip slow tests unless explicitly requested
    if item.get_closest_marker("slow"):
        if item.config.getoption("--skip-slow", default=False):
            pytest.skip("Slow test skipped")


# Custom command line options
def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-performance",
        action="store_true",
        default=False,
        help="Run performance tests"
    )

    parser.addoption(
        "--run-stress",
        action="store_true",
        default=False,
        help="Run stress tests"
    )

    parser.addoption(
        "--skip-slow",
        action="store_true",
        default=False,
        help="Skip slow tests"
    )

    parser.addoption(
        "--coverage-target",
        type=float,
        default=95.0,
        help="Target test coverage percentage"
    )


# Test data factories for complex objects
@pytest.fixture(scope="function")
def create_complex_portfolio():
    """Factory fixture for creating complex portfolio data."""
    def _create_portfolio(num_assets: int = 20, total_value: float = 1000000.0):
        return TestDataGenerator.generate_random_portfolio(num_assets, total_value)
    return _create_portfolio


@pytest.fixture(scope="function")
def create_market_scenario():
    """Factory fixture for creating market scenarios."""
    def _create_scenario(scenario_type: str = "normal", periods: int = 1000):
        if scenario_type == "crash":
            # Generate crash scenario
            fixture = MarketDataFixture(volatility=0.1, trend=-0.01)
        elif scenario_type == "bull":
            # Generate bull market
            fixture = MarketDataFixture(volatility=0.02, trend=0.001)
        elif scenario_type == "bear":
            # Generate bear market
            fixture = MarketDataFixture(volatility=0.05, trend=-0.0005)
        else:
            # Normal market
            fixture = MarketDataFixture()

        return fixture.generate_ohlcv_data(periods)
    return _create_scenario


@pytest.fixture(scope="function")
def create_strategy_config():
    """Factory fixture for creating strategy configurations."""
    def _create_config(strategy_type: str = "momentum", **kwargs):
        base_config = {
            'strategy_type': strategy_type,
            'symbols': ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'],
            'initial_balance': 100000.0,
            'max_position_size': 0.1,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.05,
            'risk_per_trade_pct': 0.01
        }
        base_config.update(kwargs)
        return base_config
    return _create_config


# Test isolation utilities
@pytest.fixture(scope="function")
def isolated_filesystem(temp_dir):
    """Provide an isolated filesystem for tests."""
    test_dir = temp_dir / "test_isolation"
    test_dir.mkdir(exist_ok=True)

    original_cwd = Path.cwd()
    try:
        import os
        os.chdir(test_dir)
        yield test_dir
    finally:
        os.chdir(original_cwd)


@pytest.fixture(scope="function")
def clean_cache():
    """Ensure cache is clean before and after tests."""
    # This would integrate with the actual cache manager
    yield
    # Clean up cache after test


# Environment detection for conditional testing
@pytest.fixture(scope="session")
def is_ci():
    """Detect if running in CI environment."""
    import os
    return os.getenv('CI', '').lower() in ('true', '1', 'yes')


@pytest.fixture(scope="session")
def is_github_actions():
    """Detect if running in GitHub Actions."""
    import os
    return os.getenv('GITHUB_ACTIONS', '').lower() == 'true'


@pytest.fixture(scope="session")
def test_environment(is_ci, is_github_actions):
    """Provide test environment information."""
    return {
        'is_ci': is_ci,
        'is_github_actions': is_github_actions,
        'platform': 'ci' if is_ci else 'local',
        'parallel_safe': not is_ci  # Disable parallel execution in CI for stability
    }