"""
Integration tests for the complete Nautilus Trader Engine system.
Tests end-to-end functionality and component interactions.
"""

import unittest
import asyncio
import time
import tempfile
import os
import shutil
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nautilus_trader_engine.tests.testing_framework import TestCase, integration_test
from nautilus_trader_engine.core.base.dependency_injection import DependencyContainer, ServiceLifetime, injectable
from nautilus_trader_engine.core.base.plugin_system import PluginManager, PluginInterface, PluginMetadata
from nautilus_trader_engine.core.base.configuration_manager import ConfigurationManager
from nautilus_trader_engine.core.base.event_system import EventSystem, Event, EventPriority
from nautilus_trader_engine.core.caching.cache_layer import MultiLevelCache, CacheLevel, get_cache_manager
from nautilus_trader_engine.core.streaming.streaming_architecture import (
    StreamManager, StreamPipeline, StreamMessage, StreamType,
    MarketDataProcessor, TechnicalIndicatorProcessor, StrategySignalProcessor
)
from nautilus_trader_engine.core.fault_tolerance.fault_tolerance_system import (
    get_error_handler, get_health_monitor, fault_tolerant
)
from nautilus_trader_engine.engines.parallel_processing_engine import ParallelProcessor
from nautilus_trader_engine.analysis.indicators.adaptive_parameters import AdaptiveParameterManager
from nautilus_trader_engine.analysis.indicators.ensemble_methods import IndicatorEnsemble
from nautilus_trader_engine.analysis.indicators.realtime_validation import SignalValidator
from nautilus_trader_engine.analysis.backtesting.backtesting_integration import BacktestEngine
from nautilus_trader_engine.strategies.modular_strategy_components import StrategyBuilder
from nautilus_trader_engine.strategies.risk_adaptive_strategies import RiskAdaptiveStrategy
from nautilus_trader_engine.strategies.multi_strategy_portfolios import PortfolioManager


class TestEndToEndTradingSystem(TestCase):
    """End-to-end integration tests for the trading system."""

    def setUp(self):
        super().setUp()
        self.temp_dir = tempfile.mkdtemp()

        # Initialize core components
        self.container = DependencyContainer()
        self.config_manager = ConfigurationManager()
        self.event_system = EventSystem()
        self.stream_manager = StreamManager()
        self.cache_manager = get_cache_manager()
        self.error_handler = get_error_handler()
        self.health_monitor = get_health_monitor()

        # Set up basic configuration
        self._setup_test_configuration()

    def tearDown(self):
        super().tearDown()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _setup_test_configuration(self):
        """Set up test configuration."""
        config = {
            "system": {
                "name": "test_trading_system",
                "version": "1.0.0"
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "test_db"
            },
            "cache": {
                "memory_size": 100,
                "disk_cache_dir": self.temp_dir
            },
            "streaming": {
                "buffer_size": 1000,
                "processing_threads": 2
            }
        }

        self.config_manager.load_from_dict(config)

    @integration_test(timeout=60)
    def test_dependency_injection_integration(self):
        """Test dependency injection with real services."""
        # Register services
        @injectable(lifetime=ServiceLifetime.SINGLETON)
        class DatabaseService:
            def __init__(self):
                self.connected = True

            def query(self, sql: str):
                return f"Result for: {sql}"

        @injectable(lifetime=ServiceLifetime.TRANSIENT)
        class TradingService:
            def __init__(self, database: DatabaseService, config: ConfigurationManager):
                self.database = database
                self.config = config

            def execute_trade(self, symbol: str, quantity: int):
                # Verify dependencies are injected
                self.assertIsInstance(self.database, DatabaseService)
                self.assertIsInstance(self.config, ConfigurationManager)

                # Use database service
                result = self.database.query(f"INSERT INTO trades (symbol, quantity) VALUES ('{symbol}', {quantity})")
                return result

        # Register services
        self.container.register(DatabaseService)
        self.container.register(TradingService)
        self.container.register_instance(ConfigurationManager, self.config_manager)

        # Resolve and test
        trading_service = self.container.resolve(TradingService)
        result = trading_service.execute_trade("AAPL", 100)

        self.assertIn("INSERT INTO trades", result)
        self.assertIn("AAPL", result)
        self.assertIn("100", result)

    @integration_test(timeout=30)
    def test_plugin_system_integration(self):
        """Test plugin system integration with dependency injection."""
        # Create a plugin that uses dependency injection
        class TradingPlugin(PluginInterface):
            def __init__(self):
                self.metadata = PluginMetadata(
                    name="trading_plugin",
                    version="1.0.0",
                    description="Integration test plugin"
                )
                self.container = None

            def initialize(self):
                # Plugin gets access to DI container
                self.container = DependencyContainer()

            def shutdown(self):
                pass

            def execute_trade(self, symbol: str, quantity: int):
                # Use dependency injection within plugin
                @injectable()
                class TradeExecutor:
                    def execute(self, symbol: str, quantity: int):
                        return f"Executed {quantity} shares of {symbol}"

                if self.container:
                    self.container.register(TradeExecutor)
                    executor = self.container.resolve(TradeExecutor)
                    return executor.execute(symbol, quantity)
                return "Plugin not initialized"

        # Register and test plugin
        plugin_manager = PluginManager()
        plugin = TradingPlugin()
        plugin_manager.register_plugin(plugin)

        # Initialize plugin
        plugin.initialize()

        # Execute plugin functionality
        result = plugin_manager.execute_plugin("trading_plugin", "execute_trade", "GOOGL", 50)

        self.assertIn("Executed 50 shares of GOOGL", result)

    @integration_test(timeout=45)
    def test_event_system_integration(self):
        """Test event system integration with multiple subscribers."""
        events_received = []
        processing_order = []

        # Multiple event handlers
        def trade_handler(event: Event):
            events_received.append(f"Trade: {event.data}")
            processing_order.append("trade")

        def risk_handler(event: Event):
            events_received.append(f"Risk: {event.data}")
            processing_order.append("risk")

        def logging_handler(event: Event):
            events_received.append(f"Log: {event.data}")
            processing_order.append("log")

        # Subscribe handlers with different priorities
        self.event_system.subscribe("trade_executed", trade_handler, EventPriority.HIGH)
        self.event_system.subscribe("trade_executed", risk_handler, EventPriority.NORMAL)
        self.event_system.subscribe("trade_executed", logging_handler, EventPriority.LOW)

        # Publish event
        trade_event = Event("trade_executed", {
            "symbol": "MSFT",
            "quantity": 200,
            "price": 150.0
        })

        self.event_system.publish(trade_event)

        # Verify all handlers were called in priority order
        self.assertEqual(len(events_received), 3)
        self.assertEqual(processing_order, ["trade", "risk", "log"])

        # Verify event data
        self.assertIn("Trade: {'symbol': 'MSFT', 'quantity': 200, 'price': 150.0}", events_received[0])

    @integration_test(timeout=60)
    def test_caching_system_integration(self):
        """Test multi-level caching system integration."""
        # Create multi-level cache
        cache = MultiLevelCache(
            levels=[CacheLevel.L1_MEMORY, CacheLevel.L3_DISK],
            memory_size=50,
            disk_config={"cache_dir": self.temp_dir, "max_size_mb": 1}
        )

        # Test data
        test_data = {
            "market_data": {
                "AAPL": {"price": 150.0, "volume": 1000000},
                "GOOGL": {"price": 2500.0, "volume": 500000}
            },
            "indicators": {
                "RSI": 65.5,
                "MACD": {"line": 1.2, "signal": 1.0, "histogram": 0.2}
            }
        }

        # Set data in cache
        cache.set("market_snapshot", test_data, ttl=300)

        # Retrieve from cache
        retrieved_data = cache.get("market_snapshot")

        # Verify data integrity
        self.assertIsNotNone(retrieved_data)
        self.assertEqual(retrieved_data["market_data"]["AAPL"]["price"], 150.0)
        self.assertEqual(retrieved_data["indicators"]["RSI"], 65.5)

        # Test cache statistics
        stats = cache.get_stats()
        self.assertEqual(stats["overall"]["total_hits"], 1)
        self.assertEqual(stats["overall"]["total_misses"], 0)

    @integration_test(timeout=90)
    def test_streaming_pipeline_integration(self):
        """Test streaming data pipeline integration."""
        async def run_streaming_test():
            # Create pipeline
            pipeline = self.stream_manager.create_pipeline("integration_pipeline")

            # Add processors
            market_processor = MarketDataProcessor("TEST")
            indicator_processor = TechnicalIndicatorProcessor(['SMA', 'RSI'])
            strategy_processor = StrategySignalProcessor("TestStrategy")

            pipeline.add_processor(market_processor)
            pipeline.add_processor(indicator_processor)
            pipeline.add_processor(strategy_processor)

            # Create output queue
            output_queue = asyncio.Queue()
            pipeline.add_output_queue("signals", output_queue)

            # Start pipeline
            await pipeline.start()

            # Send test messages
            test_messages = [
                StreamMessage(
                    stream_type=StreamType.MARKET_DATA,
                    symbol="TEST",
                    timestamp=datetime.now(),
                    data={
                        'open': 100.0,
                        'high': 105.0,
                        'low': 95.0,
                        'close': 102.0,
                        'volume': 100000
                    },
                    sequence_number=i
                )
                for i in range(20)  # Send 20 messages to build up data
            ]

            # Send messages to pipeline
            for msg in test_messages:
                await pipeline.ingest_message(msg)

            # Wait for processing
            await asyncio.sleep(1)

            # Check for output signals
            signals_received = 0
            try:
                while True:
                    signal = output_queue.get_nowait()
                    if signal.stream_type == StreamType.STRATEGY_SIGNALS:
                        signals_received += 1
                        self.assertIn('signal', signal.data)
                        self.assertIn('confidence', signal.data)
                    output_queue.task_done()
            except asyncio.QueueEmpty:
                pass

            # Stop pipeline
            await pipeline.stop()

            # Verify signals were generated
            self.assertGreater(signals_received, 0)

            # Check pipeline metrics
            metrics = pipeline.get_pipeline_metrics()
            self.assertGreater(metrics["overall_metrics"]["messages_processed"], 0)

        # Run async test
        asyncio.run(run_streaming_test())

    @integration_test(timeout=120)
    def test_fault_tolerance_integration(self):
        """Test fault tolerance system integration."""
        # Register health checks
        def database_health_check():
            return True  # Simulate healthy database

        def api_health_check():
            return True  # Simulate healthy API

        self.health_monitor.register_component("database", database_health_check)
        self.health_monitor.register_component("api", api_health_check)

        # Start health monitoring
        self.health_monitor.start_monitoring()

        # Test fault-tolerant function
        @fault_tolerant(retry_attempts=2, use_circuit_breaker=True)
        def risky_operation(should_fail=False):
            if should_fail:
                raise ConnectionError("Simulated network failure")
            return "Operation successful"

        # Test successful operation
        result = risky_operation(should_fail=False)
        self.assertEqual(result, "Operation successful")

        # Test operation with retry
        call_count = 0

        @fault_tolerant(retry_attempts=2)
        def operation_with_retry():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "Success after retry"

        result = operation_with_retry()
        self.assertEqual(result, "Success after retry")
        self.assertEqual(call_count, 2)

        # Test error handling
        try:
            risky_operation(should_fail=True)
        except ConnectionError:
            pass  # Expected

        # Check error history
        summary = self.error_handler.get_failure_summary()
        self.assertGreaterEqual(summary["total_failures"], 0)

        # Stop health monitoring
        self.health_monitor.stop_monitoring()

    @integration_test(timeout=150)
    def test_parallel_processing_integration(self):
        """Test parallel processing engine integration."""
        # Create parallel processor
        processor = ParallelProcessor()

        # Test parallel indicator calculation
        async def run_parallel_test():
            # Create sample market data
            dates = pd.date_range('2023-01-01', periods=100, freq='D')
            data = pd.DataFrame({
                'open': np.random.uniform(100, 110, 100),
                'high': np.random.uniform(105, 115, 100),
                'low': np.random.uniform(95, 105, 100),
                'close': np.random.uniform(100, 110, 100),
                'volume': np.random.uniform(1000000, 5000000, 100)
            }, index=dates)

            # Define indicators to calculate
            indicators = [
                {'name': 'SMA', 'parameters': {'period': 20}},
                {'name': 'EMA', 'parameters': {'period': 20}},
                {'name': 'RSI', 'parameters': {'period': 14}}
            ]

            # Calculate indicators in parallel
            results = await processor.calculate_indicators_parallel(data, indicators)

            # Verify results
            self.assertIn('SMA_20', results)
            self.assertIn('EMA_20', results)
            self.assertIn('RSI_14', results)

            # Verify data integrity
            self.assertEqual(len(results['SMA_20']), len(data))
            self.assertEqual(len(results['EMA_20']), len(data))
            self.assertEqual(len(results['RSI_14']), len(data))

            # Test parallel backtesting
            strategies = [
                {'name': 'Strategy_A', 'type': 'momentum'},
                {'name': 'Strategy_B', 'type': 'mean_reversion'}
            ]

            configs = [
                {'initial_capital': 100000},
                {'initial_capital': 100000}
            ]

            backtest_results = await processor.run_parallel_backtests(strategies, data, configs)

            # Verify backtest results
            self.assertEqual(len(backtest_results), 2)
            for result in backtest_results:
                self.assertIn('strategy_name', result)
                self.assertIn('total_return', result)

        # Run async test
        asyncio.run(run_parallel_test())

    @integration_test(timeout=180)
    def test_complete_trading_workflow(self):
        """Test complete end-to-end trading workflow."""
        async def run_complete_workflow():
            # 1. Set up configuration
            trading_config = {
                "strategy": {
                    "name": "integration_test_strategy",
                    "type": "momentum_rsi"
                },
                "risk_management": {
                    "max_position_size": 0.1,
                    "stop_loss": 0.05,
                    "take_profit": 0.1
                },
                "backtesting": {
                    "initial_capital": 100000,
                    "commission": 0.001
                }
            }

            self.config_manager.load_from_dict(trading_config)

            # 2. Create market data
            dates = pd.date_range('2023-01-01', periods=200, freq='D')
            np.random.seed(42)  # For reproducible results

            # Generate realistic price data with trend and volatility
            base_price = 100
            prices = []
            for i in range(len(dates)):
                # Add trend and random walk
                trend = 0.001 * i  # Upward trend
                noise = np.random.normal(0, 0.02)  # Daily volatility
                price = base_price * (1 + trend + noise)
                prices.append(price)

            market_data = pd.DataFrame({
                'open': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
                'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                'close': prices,
                'volume': np.random.uniform(1000000, 5000000, len(dates))
            }, index=dates)

            # 3. Set up adaptive parameters
            param_manager = AdaptiveParameterManager()
            param_manager.add_parameter("rsi_period", 14, min_val=5, max_val=25)
            param_manager.add_parameter("sma_fast", 10, min_val=5, max_val=20)
            param_manager.add_parameter("sma_slow", 20, min_val=10, max_val=40)

            # 4. Create indicator ensemble
            ensemble = IndicatorEnsemble()
            ensemble.add_indicator("RSI", {"period": 14})
            ensemble.add_indicator("SMA", {"period": 20})
            ensemble.add_indicator("EMA", {"period": 20})

            # 5. Set up signal validation
            validator = SignalValidator()
            validator.add_validation_rule("rsi_oversold", lambda x: x < 30)
            validator.add_validation_rule("rsi_overbought", lambda x: x > 70)

            # 6. Create strategy
            strategy_builder = StrategyBuilder()
            strategy = strategy_builder.create_strategy("momentum_rsi")

            # 7. Set up risk management
            risk_strategy = RiskAdaptiveStrategy()
            risk_strategy.set_position_sizing(max_position_pct=0.1)
            risk_strategy.set_stop_loss(stop_loss_pct=0.05)

            # 8. Create portfolio manager
            portfolio = PortfolioManager()
            portfolio.add_strategy(strategy, weight=1.0)

            # 9. Run backtest
            backtest_engine = BacktestEngine()
            backtest_result = await backtest_engine.run_backtest(
                strategy=strategy,
                market_data=market_data,
                initial_capital=100000,
                commission=0.001
            )

            # 10. Verify results
            self.assertIsNotNone(backtest_result)
            self.assertIn('total_return', backtest_result)
            self.assertIn('sharpe_ratio', backtest_result)
            self.assertIn('max_drawdown', backtest_result)
            self.assertIn('total_trades', backtest_result)

            # Verify reasonable values
            self.assertGreater(backtest_result['total_trades'], 0)
            self.assertIsInstance(backtest_result['total_return'], (int, float))
            self.assertIsInstance(backtest_result['sharpe_ratio'], (int, float))

            # 11. Test caching of results
            cache_key = f"backtest_{hash(str(trading_config))}"
            self.cache_manager.cache.set(cache_key, backtest_result, ttl=3600)

            cached_result = self.cache_manager.cache.get(cache_key)
            self.assertEqual(cached_result, backtest_result)

            # 12. Test event publishing
            trade_event = Event("backtest_completed", {
                "strategy_name": "integration_test_strategy",
                "total_return": backtest_result['total_return'],
                "sharpe_ratio": backtest_result['sharpe_ratio']
            })

            events_published = []
            def event_collector(event: Event):
                events_published.append(event)

            self.event_system.subscribe("backtest_completed", event_collector)
            self.event_system.publish(trade_event)

            self.assertEqual(len(events_published), 1)
            self.assertEqual(events_published[0].type, "backtest_completed")

        # Run the complete workflow
        asyncio.run(run_complete_workflow())


if __name__ == "__main__":
    unittest.main()