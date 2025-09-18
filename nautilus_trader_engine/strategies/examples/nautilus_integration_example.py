#!/usr/bin/env python3
"""
NautilusTrader Integration Example

This example demonstrates how to integrate the RSI(2) strategy and backtesting framework
with NautilusTrader for production-ready trading and Kafka event streaming.

Features:
- NautilusTrader engine integration
- Kafka event streaming for real-time data
- Live trading simulation
- Risk management integration
- Performance monitoring
- Multi-asset trading
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import json

# NautilusTrader imports
try:
    from nautilus_trader.core.datetime import dt_to_unix_nanos
    from nautilus_trader.model.currencies import USD
    from nautilus_trader.model.enums import AccountType, OmsType
    from nautilus_trader.model.identifiers import TraderId, StrategyId, AccountId
    from nautilus_trader.model.objects import Money
    from nautilus_trader.trading.strategy import Strategy
    from nautilus_trader.backtest.engine import BacktestEngine as NautilusBacktestEngine
    from nautilus_trader.backtest.models import FillModel
    from nautilus_trader.persistence.wranglers import QuoteTickDataWrangler
    from nautilus_trader.test_kit.providers import TestInstrumentProvider
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    logging.warning("NautilusTrader not available. Using mock implementation.")

# Kafka imports
try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logging.warning("Kafka not available. Using mock implementation.")

# Strategy and backtesting imports
from nautilus_trader_engine.strategies.mean_reversion.rsi2_mean_reversion_strategy import (
    RSI2MeanReversionStrategy,
    create_rsi2_strategy
)
from nautilus_trader_engine.strategies.backtesting.integration import (
    IntegratedBacktestEngine,
    KafkaConfig,
    NautilusIntegration
)

import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockNautilusStrategy:
    """
    Mock NautilusTrader strategy for when NautilusTrader is not available.
    """
    
    def __init__(self, strategy_id: str, config: dict):
        self.strategy_id = strategy_id
        self.config = config
        self.is_running = False
        self.positions = {}
        self.orders = []
        
    async def start(self):
        self.is_running = True
        logger.info(f"Mock strategy {self.strategy_id} started")
        
    async def stop(self):
        self.is_running = False
        logger.info(f"Mock strategy {self.strategy_id} stopped")
        
    def on_bar(self, bar_data):
        """Process bar data"""
        if self.is_running:
            logger.debug(f"Processing bar: {bar_data}")


class MockKafkaProducer:
    """
    Mock Kafka producer for when Kafka is not available.
    """
    
    def __init__(self, **kwargs):
        self.config = kwargs
        logger.info("Mock Kafka producer initialized")
        
    def send(self, topic: str, value: bytes, key: bytes = None):
        logger.debug(f"Mock send to topic '{topic}': {len(value)} bytes")
        return self
        
    def get(self, timeout=1):
        return type('MockFuture', (), {'value': None, 'exception': None})()
        
    def close(self):
        logger.info("Mock Kafka producer closed")


class MockKafkaConsumer:
    """
    Mock Kafka consumer for when Kafka is not available.
    """
    
    def __init__(self, *topics, **kwargs):
        self.topics = topics
        self.config = kwargs
        logger.info(f"Mock Kafka consumer initialized for topics: {topics}")
        
    def __iter__(self):
        return self
        
    def __next__(self):
        # Simulate no messages
        raise StopIteration
        
    def close(self):
        logger.info("Mock Kafka consumer closed")


class NautilusIntegrationExample:
    """
    Comprehensive example demonstrating NautilusTrader integration
    with Kafka event streaming and real-time trading.
    """
    
    def __init__(self):
        self.results_dir = Path("nautilus_integration_results")
        self.results_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.kafka_config = self._create_kafka_config()
        self.nautilus_integration = None
        self.integrated_engine = None
        self.kafka_producer = None
        self.kafka_consumer = None
        
        # Strategy tracking
        self.active_strategies = {}
        self.performance_metrics = {}
        
    def _create_kafka_config(self) -> KafkaConfig:
        """
        Create Kafka configuration for event streaming.
        """
        return KafkaConfig(
            bootstrap_servers=['localhost:9092'],
            market_data_topic='market_data',
            strategy_signals_topic='strategy_signals',
            trade_executions_topic='trade_executions',
            risk_alerts_topic='risk_alerts',
            performance_topic='performance_metrics',
            consumer_group='trading_system',
            enable_auto_commit=True,
            auto_offset_reset='latest'
        )
    
    async def setup_kafka_streaming(self):
        """
        Setup Kafka producers and consumers for event streaming.
        """
        logger.info("Setting up Kafka streaming...")
        
        try:
            if KAFKA_AVAILABLE:
                # Initialize Kafka producer
                self.kafka_producer = KafkaProducer(
                    bootstrap_servers=self.kafka_config.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None
                )
                
                # Initialize Kafka consumer
                self.kafka_consumer = KafkaConsumer(
                    self.kafka_config.market_data_topic,
                    bootstrap_servers=self.kafka_config.bootstrap_servers,
                    consumer_timeout_ms=1000,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
                )
                
                logger.info("Kafka streaming setup completed")
            else:
                # Use mock implementations
                self.kafka_producer = MockKafkaProducer(
                    bootstrap_servers=self.kafka_config.bootstrap_servers
                )
                self.kafka_consumer = MockKafkaConsumer(
                    self.kafka_config.market_data_topic,
                    bootstrap_servers=self.kafka_config.bootstrap_servers
                )
                
                logger.info("Mock Kafka streaming setup completed")
                
        except Exception as e:
            logger.error(f"Error setting up Kafka streaming: {e}")
            # Fallback to mock implementations
            self.kafka_producer = MockKafkaProducer()
            self.kafka_consumer = MockKafkaConsumer()
    
    async def setup_nautilus_integration(self):
        """
        Setup NautilusTrader integration.
        """
        logger.info("Setting up NautilusTrader integration...")
        
        try:
            if NAUTILUS_AVAILABLE:
                # Initialize NautilusTrader integration
                self.nautilus_integration = NautilusIntegration(
                    trader_id=TraderId("TRADER-001"),
                    account_id=AccountId("SIM-001"),
                    initial_balance=Money(100000, USD)
                )
                
                # Initialize integrated backtest engine
                self.integrated_engine = IntegratedBacktestEngine(
                    backtest_config=self._create_backtest_config(),
                    kafka_config=self.kafka_config
                )
                
                logger.info("NautilusTrader integration setup completed")
            else:
                logger.info("Using mock NautilusTrader integration")
                
        except Exception as e:
            logger.error(f"Error setting up NautilusTrader integration: {e}")
    
    def _create_backtest_config(self):
        """
        Create backtest configuration for NautilusTrader.
        """
        from nautilus_trader_engine.strategies.backtesting.config import (
from nautilus_trader_engine.indicators.consolidated_indicators import ConsolidatedIndicators

            BacktestConfig, BacktestMode, RebalanceFrequency,
            BenchmarkType, TransactionCosts, RiskLimits
        )
        
        transaction_costs = TransactionCosts(
            commission_per_trade=1.0,
            commission_percent=0.001,
            bid_ask_spread=0.01,
            slippage_percent=0.001
        )
        
        risk_limits = RiskLimits(
            max_position_size=0.1,
            max_portfolio_leverage=2.0,
            max_sector_exposure=0.3,
            var_limit=0.02,
            max_drawdown=0.15
        )
        
        return BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=100000.0,
            mode=BacktestMode.EVENT_DRIVEN,
            rebalance_frequency=RebalanceFrequency.DAILY,
            benchmark=BenchmarkType.SPY,
            transaction_costs=transaction_costs,
            risk_limits=risk_limits,
            enable_short_selling=True
        )
    
    async def create_sample_market_data(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Create sample market data for multiple symbols.
        """
        logger.info(f"Creating sample market data for {symbols}")
        
        data_dict = {}
        
        for symbol in symbols:
            # Generate synthetic data
            dates = pd.date_range(
                start='2023-01-01', 
                end='2023-12-31', 
                freq='D'
            )
            dates = dates[dates.weekday < 5]  # Remove weekends
            
            n_days = len(dates)
            np.random.seed(hash(symbol) % 2**32)  # Different seed per symbol
            
            # Generate price movements
            returns = np.random.normal(0.0005, 0.02, n_days)
            prices = 100 * np.exp(np.cumsum(returns))
            
            # Create OHLCV data
            data_dict[symbol] = pd.DataFrame({
                'timestamp': dates,
                'open': prices * np.random.uniform(0.99, 1.01, n_days),
                'high': prices * (1 + np.abs(np.random.normal(0, 0.01, n_days))),
                'low': prices * (1 - np.abs(np.random.normal(0, 0.01, n_days))),
                'close': prices,
                'volume': np.random.randint(1000000, 10000000, n_days),
                'symbol': symbol
            })
        
        return data_dict
    
    async def stream_market_data(self, data_dict: Dict[str, pd.DataFrame]):
        """
        Stream market data through Kafka.
        """
        logger.info("Starting market data streaming...")
        
        try:
            # Stream data for each symbol
            for symbol, data in data_dict.items():
                for _, row in data.iterrows():
                    market_data = {
                        'symbol': symbol,
                        'timestamp': row['timestamp'].isoformat(),
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': int(row['volume'])
                    }
                    
                    # Send to Kafka
                    future = self.kafka_producer.send(
                        self.kafka_config.market_data_topic,
                        value=market_data,
                        key=symbol
                    )
                    
                    # Wait for send to complete (in real implementation, this would be async)
                    try:
                        future.get(timeout=1)
                    except Exception as e:
                        logger.debug(f"Kafka send timeout (expected in mock): {e}")
            
            logger.info("Market data streaming completed")
            
        except Exception as e:
            logger.error(f"Error streaming market data: {e}")
    
    async def deploy_strategy(self, strategy_id: str, config: dict, symbols: List[str]):
        """
        Deploy a strategy with NautilusTrader integration.
        """
        logger.info(f"Deploying strategy {strategy_id} for symbols {symbols}")
        
        try:
            if NAUTILUS_AVAILABLE and self.nautilus_integration:
                # Create NautilusTrader strategy
                strategy = self.nautilus_integration.create_strategy(
                    strategy_class=RSI2MeanReversionStrategy,
                    strategy_id=StrategyId(strategy_id),
                    config=config
                )
                
                # Add instruments
                for symbol in symbols:
                    instrument = TestInstrumentProvider.default_fx_ccy(symbol)
                    self.nautilus_integration.add_instrument(instrument)
                
                # Start strategy
                await self.nautilus_integration.start_strategy(strategy)
                
            else:
                # Use mock strategy
                strategy = MockNautilusStrategy(strategy_id, config)
                await strategy.start()
            
            # Track active strategy
            self.active_strategies[strategy_id] = {
                'strategy': strategy,
                'config': config,
                'symbols': symbols,
                'start_time': datetime.now(),
                'status': 'running'
            }
            
            logger.info(f"Strategy {strategy_id} deployed successfully")
            
        except Exception as e:
            logger.error(f"Error deploying strategy {strategy_id}: {e}")
    
    async def monitor_strategies(self, duration_minutes: int = 5):
        """
        Monitor active strategies and stream performance metrics.
        """
        logger.info(f"Monitoring strategies for {duration_minutes} minutes...")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        while datetime.now() < end_time:
            try:
                # Check each active strategy
                for strategy_id, strategy_info in self.active_strategies.items():
                    if strategy_info['status'] == 'running':
                        # Generate mock performance metrics
                        metrics = {
                            'strategy_id': strategy_id,
                            'timestamp': datetime.now().isoformat(),
                            'pnl': np.random.normal(100, 50),
                            'positions': len(strategy_info['symbols']),
                            'trades_today': np.random.randint(0, 10),
                            'sharpe_ratio': np.random.uniform(0.5, 2.0),
                            'max_drawdown': np.random.uniform(0.01, 0.05)
                        }
                        
                        # Stream metrics to Kafka
                        future = self.kafka_producer.send(
                            self.kafka_config.performance_topic,
                            value=metrics,
                            key=strategy_id
                        )
                        
                        try:
                            future.get(timeout=0.1)
                        except Exception:
                            pass  # Expected in mock implementation
                        
                        # Store metrics
                        if strategy_id not in self.performance_metrics:
                            self.performance_metrics[strategy_id] = []
                        self.performance_metrics[strategy_id].append(metrics)
                
                # Wait before next monitoring cycle
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in strategy monitoring: {e}")
        
        logger.info("Strategy monitoring completed")
    
    async def run_live_simulation(self):
        """
        Run a complete live trading simulation.
        """
        logger.info("Starting live trading simulation...")
        
        try:
            # Setup infrastructure
            await self.setup_kafka_streaming()
            await self.setup_nautilus_integration()
            
            # Create sample data
            symbols = ['EURUSD', 'GBPUSD', 'USDJPY']
            data_dict = await self.create_sample_market_data(symbols)
            
            # Deploy strategies
            strategies = [
                {
                    'id': 'rsi2_eur',
                    'config': {
                        'rsi_period': 2,
                        'rsi_oversold': 10,
                        'rsi_overbought': 90,
                        'position_size': 0.05
                    },
                    'symbols': ['EURUSD']
                },
                {
                    'id': 'rsi2_gbp',
                    'config': {
                        'rsi_period': 3,
                        'rsi_oversold': 15,
                        'rsi_overbought': 85,
                        'position_size': 0.03
                    },
                    'symbols': ['GBPUSD']
                }
            ]
            
            # Deploy each strategy
            for strategy in strategies:
                await self.deploy_strategy(
                    strategy['id'],
                    strategy['config'],
                    strategy['symbols']
                )
            
            # Start market data streaming (in background)
            streaming_task = asyncio.create_task(
                self.stream_market_data(data_dict)
            )
            
            # Monitor strategies
            monitoring_task = asyncio.create_task(
                self.monitor_strategies(duration_minutes=2)
            )
            
            # Wait for tasks to complete
            await asyncio.gather(streaming_task, monitoring_task)
            
            # Generate summary report
            await self.generate_simulation_report()
            
            logger.info("Live trading simulation completed successfully")
            
        except Exception as e:
            logger.error(f"Error in live simulation: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def generate_simulation_report(self):
        """
        Generate a comprehensive simulation report.
        """
        logger.info("Generating simulation report...")
        
        report = {
            'simulation_summary': {
                'start_time': min(
                    s['start_time'] for s in self.active_strategies.values()
                ).isoformat() if self.active_strategies else None,
                'end_time': datetime.now().isoformat(),
                'strategies_deployed': len(self.active_strategies),
                'total_symbols': sum(
                    len(s['symbols']) for s in self.active_strategies.values()
                )
            },
            'strategy_performance': {},
            'infrastructure_status': {
                'kafka_available': KAFKA_AVAILABLE,
                'nautilus_available': NAUTILUS_AVAILABLE,
                'topics_used': [
                    self.kafka_config.market_data_topic,
                    self.kafka_config.performance_topic
                ]
            }
        }
        
        # Add performance metrics for each strategy
        for strategy_id, metrics_list in self.performance_metrics.items():
            if metrics_list:
                latest_metrics = metrics_list[-1]
                report['strategy_performance'][strategy_id] = {
                    'final_pnl': latest_metrics['pnl'],
                    'total_trades': latest_metrics['trades_today'],
                    'sharpe_ratio': latest_metrics['sharpe_ratio'],
                    'max_drawdown': latest_metrics['max_drawdown'],
                    'metrics_count': len(metrics_list)
                }
        
        # Save report
        report_path = self.results_dir / "simulation_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Simulation report saved to {report_path}")
        
        # Print summary
        print("\n=== Simulation Summary ===")
        print(f"Strategies deployed: {report['simulation_summary']['strategies_deployed']}")
        print(f"Total symbols: {report['simulation_summary']['total_symbols']}")
        print(f"Kafka available: {report['infrastructure_status']['kafka_available']}")
        print(f"NautilusTrader available: {report['infrastructure_status']['nautilus_available']}")
        
        for strategy_id, perf in report['strategy_performance'].items():
            print(f"\nStrategy {strategy_id}:")
            print(f"  Final PnL: ${perf['final_pnl']:.2f}")
            print(f"  Sharpe Ratio: {perf['sharpe_ratio']:.2f}")
            print(f"  Max Drawdown: {perf['max_drawdown']:.2%}")
    
    async def cleanup(self):
        """
        Clean up resources.
        """
        logger.info("Cleaning up resources...")
        
        try:
            # Stop strategies
            for strategy_id, strategy_info in self.active_strategies.items():
                if hasattr(strategy_info['strategy'], 'stop'):
                    await strategy_info['strategy'].stop()
                strategy_info['status'] = 'stopped'
            
            # Close Kafka connections
            if self.kafka_producer:
                self.kafka_producer.close()
            
            if self.kafka_consumer:
                self.kafka_consumer.close()
            
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


async def main():
    """
    Main function to run the NautilusTrader integration example.
    """
    logger.info("Starting NautilusTrader Integration Example")
    
    # Check dependencies
    logger.info(f"NautilusTrader available: {NAUTILUS_AVAILABLE}")
    logger.info(f"Kafka available: {KAFKA_AVAILABLE}")
    
    if not NAUTILUS_AVAILABLE:
        logger.warning("NautilusTrader not installed. Using mock implementation.")
        logger.info("To install: pip install nautilus_trader")
    
    if not KAFKA_AVAILABLE:
        logger.warning("Kafka not installed. Using mock implementation.")
        logger.info("To install: pip install kafka-python")
    
    # Initialize and run example
    example = NautilusIntegrationExample()
    
    try:
        await example.run_live_simulation()
        logger.info("NautilusTrader Integration Example completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in integration example: {e}")
        raise


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())