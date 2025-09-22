"""
Usage Examples for Nautilus Trader Engine
Comprehensive examples demonstrating system capabilities and usage patterns.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nautilus_trader_engine.core.base.dependency_injection import DependencyContainer
from nautilus_trader_engine.core.base.event_system import EventSystem, Event
from nautilus_trader_engine.core.caching.cache_layer import MultiLevelCache, CacheLevel
from nautilus_trader_engine.core.streaming.streaming_architecture import (
    StreamManager, StreamPipeline, StreamMessage, StreamType,
    MarketDataProcessor, TechnicalIndicatorProcessor
)
from nautilus_trader_engine.analysis.indicators.adaptive_parameters import AdaptiveParameterManager
from nautilus_trader_engine.analysis.indicators.ensemble_methods import IndicatorEnsemble
from nautilus_trader_engine.engines.parallel_processing_engine import ParallelProcessor
from nautilus_trader_engine.strategies.modular_strategy_components import StrategyBuilder
from nautilus_trader_engine.strategies.risk_adaptive_strategies import RiskAdaptiveStrategy
from nautilus_trader_engine.strategies.multi_strategy_portfolios import MultiStrategyPortfolio


class BasicUsageExamples:
    """Basic usage examples for getting started with the system."""

    @staticmethod
    def example_1_dependency_injection():
        """Example 1: Basic dependency injection usage."""
        print("Example 1: Basic Dependency Injection")
        print("-" * 40)

        # Create dependency injection container
        container = DependencyContainer()

        # Register services
        @container.injectable()
        class MarketDataService:
            def get_price(self, symbol: str) -> float:
                return 100.0  # Mock price

        @container.injectable()
        class TradingStrategy:
            def __init__(self, market_data: MarketDataService):
                self.market_data = market_data

            def execute_trade(self, symbol: str) -> str:
                price = self.market_data.get_price(symbol)
                return f"Trading {symbol} at price {price}"

        # Register services
        container.register(MarketDataService)
        container.register(TradingStrategy)

        # Resolve and use services
        strategy = container.resolve(TradingStrategy)
        result = strategy.execute_trade("AAPL")

        print(f"Trade execution result: {result}")
        print()

    @staticmethod
    def example_2_event_system():
        """Example 2: Basic event system usage."""
        print("Example 2: Basic Event System")
        print("-" * 30)

        event_system = EventSystem()
        received_events = []

        # Define event handler
        def price_update_handler(event: Event):
            received_events.append(event.data)
            print(f"Price update received: {event.data}")

        # Subscribe to events
        event_system.subscribe("price_update", price_update_handler)

        # Publish events
        event_system.publish(Event("price_update", {"symbol": "AAPL", "price": 150.25}))
        event_system.publish(Event("price_update", {"symbol": "GOOGL", "price": 2800.50}))

        print(f"Total events received: {len(received_events)}")
        print()

    @staticmethod
    def example_3_caching():
        """Example 3: Basic caching usage."""
        print("Example 3: Basic Caching")
        print("-" * 25)

        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create cache
            cache = MultiLevelCache(
                levels=[CacheLevel.L1_MEMORY],
                memory_size=1000
            )

            # Cache expensive computation
            def expensive_calculation(n: int) -> int:
                print(f"Computing expensive calculation for {n}")
                return sum(i**2 for i in range(n))

            # First call - computation happens
            result1 = cache.get_or_compute("expensive_100", lambda: expensive_calculation(100))
            print(f"First result: {result1}")

            # Second call - result from cache
            result2 = cache.get_or_compute("expensive_100", lambda: expensive_calculation(100))
            print(f"Second result (cached): {result2}")

            print("Notice: Second call didn't print computation message")
            print()


class AdvancedUsageExamples:
    """Advanced usage examples demonstrating complex features."""

    @staticmethod
    async def example_4_streaming_pipeline():
        """Example 4: Streaming data pipeline."""
        print("Example 4: Streaming Data Pipeline")
        print("-" * 35)

        stream_manager = StreamManager()

        # Create pipeline
        pipeline = stream_manager.create_pipeline("trading_pipeline")

        # Add processors
        market_processor = MarketDataProcessor("AAPL")
        indicator_processor = TechnicalIndicatorProcessor(['SMA', 'RSI'])

        pipeline.add_processor(market_processor)
        pipeline.add_processor(indicator_processor)

        # Set up output handling
        results = []
        output_queue = asyncio.Queue()

        async def collect_results():
            while True:
                try:
                    result = output_queue.get_nowait()
                    results.append(result)
                    output_queue.task_done()
                except asyncio.QueueEmpty:
                    break

        pipeline.add_output_queue("results", output_queue)

        # Start pipeline
        await pipeline.start()

        # Send market data
        for i in range(5):
            message = StreamMessage(
                stream_type=StreamType.MARKET_DATA,
                symbol="AAPL",
                timestamp=datetime.now(),
                data={
                    'open': 150.0 + i * 0.5,
                    'high': 152.0 + i * 0.5,
                    'low': 148.0 + i * 0.5,
                    'close': 151.0 + i * 0.5,
                    'volume': 1000000 + i * 10000
                },
                sequence_number=i
            )
            await pipeline.ingest_message(message)

        # Wait for processing
        await asyncio.sleep(2)

        # Collect results
        await collect_results()

        # Stop pipeline
        await pipeline.stop()

        print(f"Processed {len(results)} data points")
        print()

    @staticmethod
    def example_5_indicator_ensemble():
        """Example 5: Using indicator ensembles."""
        print("Example 5: Indicator Ensemble")
        print("-" * 30)

        # Create ensemble
        ensemble = IndicatorEnsemble()

        # Add indicators
        ensemble.add_indicator("SMA", {"period": 20})
        ensemble.add_indicator("EMA", {"period": 20})
        ensemble.add_indicator("RSI", {"period": 14})
        ensemble.add_indicator("MACD", {"fast": 12, "slow": 26, "signal": 9})

        # Create sample data
        dates = pd.date_range('2023-01-01', periods=100, freq='1H')
        data = pd.DataFrame({
            'open': np.random.uniform(100, 110, 100),
            'high': np.random.uniform(105, 115, 100),
            'low': np.random.uniform(95, 105, 100),
            'close': np.random.uniform(100, 110, 100),
            'volume': np.random.uniform(1000000, 5000000, 100)
        }, index=dates)

        # Calculate ensemble
        results = ensemble.calculate_all(data)

        print(f"Calculated {len(results)} indicators")
        print("Available indicators:")
        for name in results.keys():
            print(f"  - {name}")
        print()

    @staticmethod
    def example_6_adaptive_parameters():
        """Example 6: Adaptive parameter optimization."""
        print("Example 6: Adaptive Parameters")
        print("-" * 30)

        # Create adaptive parameter manager
        param_manager = AdaptiveParameterManager()

        # Add parameters to optimize
        param_manager.add_parameter("rsi_period", 14, min_val=5, max_val=25)
        param_manager.add_parameter("sma_fast", 10, min_val=5, max_val=20)
        param_manager.add_parameter("sma_slow", 20, min_val=10, max_val=40)

        # Simulate market conditions
        returns = np.random.normal(0.001, 0.02, 100)  # Daily returns

        print("Initial parameters:")
        initial_params = param_manager.get_current_parameters()
        for name, value in initial_params.items():
            print(f"  {name}: {value}")

        # Optimize parameters
        for _ in range(10):  # 10 optimization iterations
            params = param_manager.get_current_parameters()

            # Simulate fitness calculation based on returns
            fitness = np.mean(returns) + np.random.normal(0, 0.01)

            param_manager.update_parameters(fitness, returns)

        print("\nOptimized parameters:")
        optimized_params = param_manager.get_current_parameters()
        for name, value in optimized_params.items():
            print(f"  {name}: {value}")
        print()

    @staticmethod
    async def example_7_parallel_processing():
        """Example 7: Parallel indicator calculation."""
        print("Example 7: Parallel Processing")
        print("-" * 30)

        processor = ParallelProcessor()

        # Create large dataset
        dates = pd.date_range('2023-01-01', periods=1000, freq='5min')
        data = pd.DataFrame({
            'open': np.random.uniform(100, 110, 1000),
            'high': np.random.uniform(105, 115, 1000),
            'low': np.random.uniform(95, 105, 1000),
            'close': np.random.uniform(100, 110, 1000),
            'volume': np.random.uniform(1000000, 5000000, 1000)
        }, index=dates)

        # Define indicators
        indicators = [
            {'name': 'SMA', 'parameters': {'period': 20}},
            {'name': 'EMA', 'parameters': {'period': 20}},
            {'name': 'RSI', 'parameters': {'period': 14}},
            {'name': 'MACD', 'parameters': {'fast': 12, 'slow': 26, 'signal': 9}}
        ]

        # Calculate indicators in parallel
        start_time = datetime.now()
        results = await processor.calculate_indicators_parallel(data, indicators)
        end_time = datetime.now()

        processing_time = (end_time - start_time).total_seconds()

        print(f"Processed {len(indicators)} indicators on {len(data)} data points")
        print(".2f")
        print(f"Calculated indicators: {list(results.keys())}")
        print()


class RealWorldExamples:
    """Real-world usage examples with complete trading scenarios."""

    @staticmethod
    def example_8_trading_strategy():
        """Example 8: Complete trading strategy implementation."""
        print("Example 8: Complete Trading Strategy")
        print("-" * 35)

        # Create strategy builder
        builder = StrategyBuilder()

        # Add components
        builder.add_indicator("SMA", {"period": 20})
        builder.add_indicator("RSI", {"period": 14})
        builder.add_indicator("MACD", {"fast": 12, "slow": 26, "signal": 9})

        # Add entry conditions
        builder.add_entry_condition("rsi_oversold", lambda data: data['RSI_14'] < 30)
        builder.add_entry_condition("macd_crossover", lambda data: data['MACD_12_26_9'] > data['MACD_Signal_12_26_9'])

        # Add exit conditions
        builder.add_exit_condition("rsi_overbought", lambda data: data['RSI_14'] > 70)
        builder.add_exit_condition("profit_target", lambda data: data.get('unrealized_pnl', 0) > 100)

        # Build strategy
        strategy = builder.build()

        # Create sample market data
        data = {
            'SMA_20': 105.0,
            'RSI_14': 25.0,  # Oversold
            'MACD_12_26_9': 0.5,
            'MACD_Signal_12_26_9': 0.3,
            'unrealized_pnl': 0
        }

        # Test strategy signals
        entry_signal = strategy.check_entry_conditions(data)
        exit_signal = strategy.check_exit_conditions(data)

        print(f"Entry signal: {entry_signal}")
        print(f"Exit signal: {exit_signal}")
        print()

    @staticmethod
    def example_9_risk_adaptive_strategy():
        """Example 9: Risk-adaptive strategy with dynamic position sizing."""
        print("Example 9: Risk-Adaptive Strategy")
        print("-" * 35)

        # Create risk-adaptive strategy
        strategy = RiskAdaptiveStrategy(
            base_position_size=1000,
            max_position_size=10000,
            volatility_lookback=20,
            max_volatility=0.05
        )

        # Simulate market conditions
        market_data = pd.DataFrame({
            'close': [100, 102, 98, 105, 103, 107, 105, 108, 106, 110],
            'volume': [1000000] * 10
        })

        # Calculate position sizes based on volatility
        position_sizes = []
        for i in range(len(market_data)):
            current_data = market_data.iloc[:i+1]
            if len(current_data) >= 5:  # Need minimum data
                size = strategy.calculate_position_size(current_data)
                position_sizes.append(size)
            else:
                position_sizes.append(strategy.base_position_size)

        print("Dynamic position sizing based on volatility:")
        for i, size in enumerate(position_sizes):
            print(f"  Period {i+1}: ${size:,.0f}")
        print()

    @staticmethod
    def example_10_multi_strategy_portfolio():
        """Example 10: Multi-strategy portfolio management."""
        print("Example 10: Multi-Strategy Portfolio")
        print("-" * 35)

        # Create multi-strategy portfolio
        portfolio = MultiStrategyPortfolio()

        # Add strategies with allocations
        portfolio.add_strategy("momentum_strategy", 0.4)
        portfolio.add_strategy("mean_reversion_strategy", 0.3)
        portfolio.add_strategy("trend_following_strategy", 0.3)

        # Simulate strategy performance
        strategy_returns = {
            "momentum_strategy": [0.02, 0.01, -0.01, 0.03, 0.02],
            "mean_reversion_strategy": [-0.01, 0.02, 0.01, -0.005, 0.015],
            "trend_following_strategy": [0.015, -0.005, 0.02, 0.01, 0.005]
        }

        # Update portfolio with returns
        for period in range(5):
            period_returns = {}
            for strategy_name in strategy_returns:
                if period < len(strategy_returns[strategy_name]):
                    period_returns[strategy_name] = strategy_returns[strategy_name][period]

            portfolio.update_performance(period_returns)

        # Get portfolio metrics
        metrics = portfolio.get_portfolio_metrics()

        print("Portfolio Performance:")
        print(".2f")
        print(".2f")
        print(".2f")
        print("\nStrategy Allocations:")
        for strategy, allocation in portfolio.strategy_allocations.items():
            print(".1%")
        print()


class IntegrationExamples:
    """Examples showing integration with external systems."""

    @staticmethod
    def example_11_plugin_system():
        """Example 11: Plugin system integration."""
        print("Example 11: Plugin System")
        print("-" * 25)

        # This would normally load plugins from external files
        # For demonstration, we'll simulate plugin loading

        print("Plugin system allows dynamic loading of:")
        print("  - Custom indicators")
        print("  - Trading strategies")
        print("  - Risk management modules")
        print("  - Data connectors")
        print("  - Analysis tools")
        print()

    @staticmethod
    def example_12_configuration_management():
        """Example 12: Configuration management."""
        print("Example 12: Configuration Management")
        print("-" * 35)

        # This would normally load from config files
        # For demonstration, we'll show configuration structure

        config_structure = {
            "trading": {
                "max_position_size": 10000,
                "max_daily_loss": 1000,
                "allowed_symbols": ["AAPL", "GOOGL", "MSFT"]
            },
            "indicators": {
                "rsi_period": 14,
                "sma_periods": [20, 50, 200],
                "macd_settings": {
                    "fast": 12,
                    "slow": 26,
                    "signal": 9
                }
            },
            "risk": {
                "var_confidence": 0.95,
                "max_drawdown": 0.1,
                "position_limits": {
                    "single_stock": 0.2,
                    "sector": 0.3
                }
            }
        }

        print("Configuration structure:")
        print(f"  Trading max position: ${config_structure['trading']['max_position_size']:,}")
        print(f"  RSI period: {config_structure['indicators']['rsi_period']}")
        print(f"  VaR confidence: {config_structure['risk']['var_confidence']:.0%}")
        print()

    @staticmethod
    def example_13_fault_tolerance():
        """Example 13: Fault tolerance demonstration."""
        print("Example 13: Fault Tolerance")
        print("-" * 25)

        from nautilus_trader_engine.core.fault_tolerance.fault_tolerance_system import fault_tolerant

        @fault_tolerant(retry_attempts=3)
        def unreliable_operation():
            if np.random.random() < 0.7:  # 70% failure rate
                raise ConnectionError("Simulated network failure")
            return "Operation successful"

        # Test fault tolerance
        successes = 0
        attempts = 10

        for _ in range(attempts):
            try:
                result = unreliable_operation()
                successes += 1
                print(f"✓ {result}")
            except Exception as e:
                print(f"✗ Failed: {e}")

        print(f"\nSuccess rate: {successes}/{attempts} ({successes/attempts:.1%})")
        print("Fault tolerance prevented complete failure despite high error rate")
        print()


def main():
    """Run all usage examples."""
    print("Nautilus Trader Engine - Usage Examples")
    print("=" * 45)
    print()

    # Basic examples
    basic = BasicUsageExamples()
    basic.example_1_dependency_injection()
    basic.example_2_event_system()
    basic.example_3_caching()

    # Advanced examples
    advanced = AdvancedUsageExamples()

    # Run async examples
    asyncio.run(advanced.example_4_streaming_pipeline())

    advanced.example_5_indicator_ensemble()
    advanced.example_6_adaptive_parameters()

    # Run parallel processing example
    asyncio.run(advanced.example_7_parallel_processing())

    # Real-world examples
    real_world = RealWorldExamples()
    real_world.example_8_trading_strategy()
    real_world.example_9_risk_adaptive_strategy()
    real_world.example_10_multi_strategy_portfolio()

    # Integration examples
    integration = IntegrationExamples()
    integration.example_11_plugin_system()
    integration.example_12_configuration_management()
    integration.example_13_fault_tolerance()

    print("All examples completed successfully!")
    print("\nFor more detailed examples, see the documentation at:")
    print("  - docs/architecture_decision_records.md")
    print("  - docs/api_documentation_generator.py")
    print("  - docs/performance_benchmarks.py")


if __name__ == "__main__":
    main()