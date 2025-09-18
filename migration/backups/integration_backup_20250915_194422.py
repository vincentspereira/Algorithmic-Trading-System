"""Integration Module

Integrates backtesting framework with NautilusTrader engine and establishes
Kafka event streaming for real-time strategy execution and monitoring.
"""

from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
import asyncio
import logging
import json
import warnings
warnings.filterwarnings('ignore')

# Kafka integration
try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    KafkaProducer = None
    KafkaConsumer = None
    KafkaError = None

# NautilusTrader integration
try:
    from nautilus_trader.core.datetime import dt_to_unix_nanos
    from nautilus_trader.model.data.bar import Bar
    from nautilus_trader.model.data.tick import QuoteTick, TradeTick
    from nautilus_trader.model.events.order import OrderFilled
    from nautilus_trader.model.events.position import PositionOpened, PositionClosed
    from nautilus_trader.model.identifiers import InstrumentId, StrategyId
    from nautilus_trader.model.instruments import Instrument
    from nautilus_trader.trading.strategy import Strategy
    from nautilus_trader.backtest.engine import BacktestEngine as NautilusBacktestEngine
    from nautilus_trader.backtest.data.providers import TestDataProvider
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    Strategy = object
    logger = logging.getLogger(__name__)
    logger.warning("NautilusTrader not available. Limited integration capabilities.")

from .backtest_engine import BacktestEngine
from .results import BacktestResults, Trade, Position, PortfolioSnapshot
from .config import BacktestConfig


@dataclass
class EventMessage:
    """Event message structure for streaming"""
    event_type: str
    timestamp: datetime
    source: str
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        import json
        from dataclasses import asdict
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'EventMessage':
        """Create from JSON string"""
        data = json.loads(json_str)
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class KafkaEventStreamer:
    """Kafka-based event streamer for backtesting integration"""
    
    def __init__(self, bootstrap_servers: str = 'localhost:9092',
                 producer_config: Optional[Dict] = None,
                 consumer_config: Optional[Dict] = None):
        if not KAFKA_AVAILABLE:
            logger.warning("Kafka not available, using mock implementation")
            self._mock_mode = True
            self._messages = {}
            return
        
        self._mock_mode = False
        self.bootstrap_servers = bootstrap_servers
        self.producer_config = producer_config or {}
        self.consumer_config = consumer_config or {}
        
        # Default configurations
        self.producer_config.setdefault('bootstrap_servers', bootstrap_servers)
        self.producer_config.setdefault('value_serializer', lambda x: x.encode('utf-8'))
        
        self.consumer_config.setdefault('bootstrap_servers', bootstrap_servers)
        self.consumer_config.setdefault('value_deserializer', lambda x: x.decode('utf-8'))
        self.consumer_config.setdefault('auto_offset_reset', 'latest')
        
        self.producer = None
        self.consumers = {}
    
    def _get_producer(self):
        """Get or create Kafka producer"""
        if self._mock_mode:
            return None
        
        if self.producer is None:
            self.producer = KafkaProducer(**self.producer_config)
        return self.producer
    
    async def publish(self, topic: str, message: EventMessage) -> bool:
        """Publish message to Kafka topic"""
        if self._mock_mode:
            if topic not in self._messages:
                self._messages[topic] = []
            self._messages[topic].append(message)
            return True
        
        try:
            producer = self._get_producer()
            if producer:
                future = producer.send(topic, message.to_json())
                future.get(timeout=10)
                return True
        except Exception as e:
            logger.error(f"Failed to publish message to {topic}: {e}")
        
        return False
    
    async def subscribe(self, topic: str, callback: Callable[[EventMessage], None]) -> None:
        """Subscribe to Kafka topic with callback"""
        if self._mock_mode:
            logger.info(f"Mock subscription to topic {topic}")
            return
        
        try:
            consumer = KafkaConsumer(topic, **self.consumer_config)
            self.consumers[topic] = consumer
            logger.info(f"Subscribed to topic {topic}")
        except Exception as e:
            logger.error(f"Failed to subscribe to {topic}: {e}")
    
    async def stream_event(self, event_type: str, data: Dict[str, Any], topic: Optional[str] = None) -> bool:
        """Stream an event to Kafka
        
        Args:
            event_type: Type of event (e.g., 'trade', 'signal', 'position')
            data: Event data dictionary
            topic: Optional topic override, defaults to event_type
        
        Returns:
            True if event was successfully streamed
        """
        target_topic = topic or event_type
        
        # Create event message
        event_message = EventMessage(
            event_type=event_type,
            timestamp=datetime.now(),
            data=data,
            source='backtesting_engine'
        )
        
        return await self.publish(target_topic, event_message)
    
    async def close(self) -> None:
        """Close all connections"""
        if self._mock_mode:
            self._messages.clear()
            return
        
        if self.producer:
            self.producer.close()
        
        for consumer in self.consumers.values():
            consumer.close()
        
        self.consumers.clear()
        logger.info("Event streamer closed")
from .performance_analyzer import PerformanceAnalyzer
from .risk_analyzer import RiskAnalyzer
from .visualization import VisualizationEngine

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class KafkaConfig:
    """Kafka configuration for event streaming"""
    bootstrap_servers: List[str] = field(default_factory=lambda: ['localhost:9092'])
    topics: Dict[str, str] = field(default_factory=lambda: {
        'market_data': 'market-data',
        'orders': 'orders',
        'trades': 'trades',
        'positions': 'positions',
        'risk_events': 'risk-events',
        'strategy_signals': 'strategy-signals',
        'performance_metrics': 'performance-metrics'
    })
    producer_config: Dict[str, Any] = field(default_factory=lambda: {
        'value_serializer': lambda x: json.dumps(x, default=str).encode('utf-8'),
        'key_serializer': lambda x: str(x).encode('utf-8') if x else None,
        'acks': 'all',
        'retries': 3,
        'batch_size': 16384,
        'linger_ms': 10,
        'buffer_memory': 33554432
    })
    consumer_config: Dict[str, Any] = field(default_factory=lambda: {
        'value_deserializer': lambda x: json.loads(x.decode('utf-8')),
        'key_deserializer': lambda x: x.decode('utf-8') if x else None,
        'auto_offset_reset': 'latest',
        'enable_auto_commit': True,
        'group_id': 'backtesting-group'
    })


@dataclass
class IntegrationConfig:
    """Configuration for backtesting integration"""
    enable_kafka: bool = True
    enable_nautilus: bool = True
    enable_real_time: bool = False
    kafka_config: KafkaConfig = field(default_factory=KafkaConfig)
    backtest_config: BacktestConfig = field(default_factory=BacktestConfig)
    strategy_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    data_sources: List[str] = field(default_factory=lambda: ['yahoo', 'alpha_vantage'])
    fallback_enabled: bool = True
    performance_monitoring: bool = True
    risk_monitoring: bool = True


class EventStreamer:
    """Kafka event streaming for real-time backtesting and monitoring"""
    
    def __init__(self, config: KafkaConfig):
        self.config = config
        self.producer = None
        self.consumers = {}
        self.running = False
        
        if not KAFKA_AVAILABLE:
            logger.warning("Kafka not available. Event streaming disabled.")
            return
        
        self._initialize_producer()
        logger.info("Event streamer initialized")
    
    def _initialize_producer(self):
        """Initialize Kafka producer"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.config.bootstrap_servers,
                **self.config.producer_config
            )
            logger.info("Kafka producer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            self.producer = None
    
    def _initialize_consumer(self, topic: str, group_id: Optional[str] = None) -> Optional[KafkaConsumer]:
        """Initialize Kafka consumer for specific topic"""
        try:
            consumer_config = self.config.consumer_config.copy()
            if group_id:
                consumer_config['group_id'] = group_id
            
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=self.config.bootstrap_servers,
                **consumer_config
            )
            logger.info(f"Kafka consumer initialized for topic: {topic}")
            return consumer
        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer for {topic}: {e}")
            return None
    
    async def publish_event(self, topic: str, event_data: Dict[str, Any], key: Optional[str] = None):
        """Publish event to Kafka topic"""
        if not self.producer:
            logger.warning("Kafka producer not available")
            return
        
        try:
            # Add timestamp
            event_data['timestamp'] = datetime.now().isoformat()
            
            future = self.producer.send(
                topic,
                value=event_data,
                key=key
            )
            
            # Non-blocking send
            future.add_callback(lambda metadata: logger.debug(f"Event published to {topic}"))
            future.add_errback(lambda error: logger.error(f"Failed to publish to {topic}: {error}"))
            
        except Exception as e:
            logger.error(f"Error publishing event to {topic}: {e}")
    
    async def consume_events(self, topic: str, callback: Callable[[Dict[str, Any]], None], 
                           group_id: Optional[str] = None):
        """Consume events from Kafka topic"""
        consumer = self._initialize_consumer(topic, group_id)
        if not consumer:
            return
        
        self.consumers[topic] = consumer
        self.running = True
        
        try:
            while self.running:
                message_batch = consumer.poll(timeout_ms=1000)
                
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        try:
                            await callback(message.value)
                        except Exception as e:
                            logger.error(f"Error processing message from {topic}: {e}")
                
                await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
                
        except Exception as e:
            logger.error(f"Error consuming from {topic}: {e}")
        finally:
            consumer.close()
    
    def stop(self):
        """Stop event streaming"""
        self.running = False
        
        if self.producer:
            self.producer.flush()
            self.producer.close()
        
        for consumer in self.consumers.values():
            consumer.close()
        
        logger.info("Event streamer stopped")


class NautilusIntegration:
    """Integration with NautilusTrader engine"""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.engine = None
        self.strategies = {}
        
        if not NAUTILUS_AVAILABLE:
            logger.warning("NautilusTrader not available. Limited integration capabilities.")
            return
        
        logger.info("Nautilus integration initialized")
    
    def create_backtest_engine(self) -> Optional[Any]:
        """Create NautilusTrader backtest engine"""
        if not NAUTILUS_AVAILABLE:
            logger.error("NautilusTrader not available")
            return None
        
        try:
            # Create backtest engine with configuration
            self.engine = NautilusBacktestEngine(
                config=self.config.backtest_config
            )
            
            logger.info("NautilusTrader backtest engine created")
            return self.engine
            
        except Exception as e:
            logger.error(f"Failed to create NautilusTrader engine: {e}")
            return None
    
    def add_strategy(self, strategy_id: str, strategy_class: type, 
                    strategy_config: Dict[str, Any]) -> bool:
        """Add strategy to backtest engine"""
        if not self.engine:
            logger.error("Backtest engine not initialized")
            return False
        
        try:
            # Create strategy instance
            strategy = strategy_class(config=strategy_config)
            
            # Add to engine
            self.engine.add_strategy(strategy)
            self.strategies[strategy_id] = strategy
            
            logger.info(f"Strategy {strategy_id} added to engine")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add strategy {strategy_id}: {e}")
            return False
    
    def add_data(self, instrument_id: str, data: pd.DataFrame) -> bool:
        """Add market data to backtest engine"""
        if not self.engine:
            logger.error("Backtest engine not initialized")
            return False
        
        try:
            # Convert data to Nautilus format
            bars = self._convert_to_nautilus_bars(instrument_id, data)
            
            # Add data to engine
            self.engine.add_data(bars)
            
            logger.info(f"Data added for {instrument_id}: {len(bars)} bars")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add data for {instrument_id}: {e}")
            return False
    
    def _convert_to_nautilus_bars(self, instrument_id: str, data: pd.DataFrame) -> List[Any]:
        """Convert pandas DataFrame to Nautilus Bar objects"""
        bars = []
        
        for idx, row in data.iterrows():
            try:
                bar = Bar(
                    bar_type=f"{instrument_id}-1-MINUTE-LAST-EXTERNAL",
                    open_price=row['open'],
                    high_price=row['high'],
                    low_price=row['low'],
                    close_price=row['close'],
                    volume=row.get('volume', 0),
                    ts_event=dt_to_unix_nanos(idx),
                    ts_init=dt_to_unix_nanos(idx)
                )
                bars.append(bar)
            except Exception as e:
                logger.warning(f"Failed to convert bar at {idx}: {e}")
                continue
        
        return bars
    
    def run_backtest(self) -> Optional[BacktestResults]:
        """Run backtest using NautilusTrader engine"""
        if not self.engine:
            logger.error("Backtest engine not initialized")
            return None
        
        try:
            # Run backtest
            logger.info("Starting NautilusTrader backtest")
            self.engine.run()
            
            # Extract results
            results = self._extract_results()
            
            logger.info("NautilusTrader backtest completed")
            return results
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return None
    
    def _extract_results(self) -> BacktestResults:
        """Extract results from NautilusTrader engine"""
        # This would extract actual results from Nautilus engine
        # For now, return empty results structure
        return BacktestResults(
            strategy_id="nautilus_strategy",
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            initial_capital=100000.0,
            final_capital=100000.0,
            trades=[],
            positions_history=[],
            portfolio_history=pd.DataFrame(),
            returns_series=pd.Series(dtype=float),
            benchmark_returns=None,
            metadata={"engine": "nautilus"}
        )


class IntegratedBacktestEngine:
    """Integrated backtesting engine combining custom and NautilusTrader capabilities"""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.event_streamer = None
        self.nautilus_integration = None
        self.custom_engine = None
        self.performance_analyzer = None
        self.risk_analyzer = None
        self.visualization_engine = None
        
        self._initialize_components()
        logger.info("Integrated backtest engine initialized")
    
    def _initialize_components(self):
        """Initialize all components"""
        # Initialize event streaming
        if self.config.enable_kafka and KAFKA_AVAILABLE:
            self.event_streamer = EventStreamer(self.config.kafka_config)
        
        # Initialize Nautilus integration
        if self.config.enable_nautilus and NAUTILUS_AVAILABLE:
            self.nautilus_integration = NautilusIntegration(self.config)
        
        # Initialize custom backtest engine
        self.custom_engine = BacktestEngine(self.config.backtest_config)
    
    async def run_integrated_backtest(self, strategies: Dict[str, Any], 
                                     data: Dict[str, pd.DataFrame]) -> BacktestResults:
        """Run integrated backtest with event streaming"""
        logger.info("Starting integrated backtest")
        
        # Choose engine based on configuration
        if self.config.enable_nautilus and self.nautilus_integration:
            results = await self._run_nautilus_backtest(strategies, data)
        else:
            results = await self._run_custom_backtest(strategies, data)
        
        # Stream results if Kafka enabled
        if self.event_streamer:
            await self._stream_results(results)
        
        # Analyze results
        await self._analyze_results(results)
        
        logger.info("Integrated backtest completed")
        return results
    
    async def _run_nautilus_backtest(self, strategies: Dict[str, Any], 
                                    data: Dict[str, pd.DataFrame]) -> BacktestResults:
        """Run backtest using NautilusTrader"""
        logger.info("Running Nautilus backtest")
        
        # Create engine
        engine = self.nautilus_integration.create_backtest_engine()
        if not engine:
            logger.error("Failed to create Nautilus engine, falling back to custom")
            return await self._run_custom_backtest(strategies, data)
        
        # Add strategies
        for strategy_id, strategy_config in strategies.items():
            self.nautilus_integration.add_strategy(
                strategy_id, 
                strategy_config['class'], 
                strategy_config['config']
            )
        
        # Add data
        for instrument_id, instrument_data in data.items():
            self.nautilus_integration.add_data(instrument_id, instrument_data)
        
        # Run backtest
        results = self.nautilus_integration.run_backtest()
        return results or BacktestResults(
            strategy_id="failed_nautilus",
            start_date=datetime.now(),
            end_date=datetime.now(),
            initial_capital=0,
            final_capital=0,
            trades=[],
            positions_history=[],
            portfolio_history=pd.DataFrame(),
            returns_series=pd.Series(dtype=float),
            benchmark_returns=None,
            metadata={}
        )
    
    async def _run_custom_backtest(self, strategies: Dict[str, Any], 
                                  data: Dict[str, pd.DataFrame]) -> BacktestResults:
        """Run backtest using custom engine"""
        logger.info("Running custom backtest")
        
        # For now, create a simple example result
        # In practice, this would run the actual custom backtest
        
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now()
        
        # Generate sample data for demonstration
        dates = pd.date_range(start_date, end_date, freq='D')
        returns = np.random.normal(0.001, 0.02, len(dates))
        cumulative_returns = (1 + pd.Series(returns, index=dates)).cumprod()
        
        portfolio_history = pd.DataFrame({
            'portfolio_value': cumulative_returns * 100000,
            'cash': 50000,
            'positions_value': cumulative_returns * 50000
        }, index=dates)
        
        # Generate sample trades
        trades = []
        for i in range(50):
            entry_date = start_date + timedelta(days=np.random.randint(0, 300))
            exit_date = entry_date + timedelta(days=np.random.randint(1, 30))
            
            trade = Trade(
                trade_id=f"trade_{i}",
                symbol="AAPL",
                side="long" if np.random.random() > 0.5 else "short",
                quantity=100,
                entry_price=150 + np.random.normal(0, 10),
                exit_price=150 + np.random.normal(0, 15),
                entry_time=entry_date,
                exit_time=exit_date,
                pnl=np.random.normal(100, 500),
                commission=2.0
            )
            trades.append(trade)
        
        results = BacktestResults(
            strategy_id="custom_strategy",
            start_date=start_date,
            end_date=end_date,
            initial_capital=100000.0,
            final_capital=portfolio_history['portfolio_value'].iloc[-1],
            trades=trades,
            positions_history=[],
            portfolio_history=portfolio_history,
            returns_series=pd.Series(returns, index=dates),
            benchmark_returns=pd.Series(np.random.normal(0.0008, 0.015, len(dates)), index=dates),
            metadata={"engine": "custom"}
        )
        
        return results
    
    async def _stream_results(self, results: BacktestResults):
        """Stream backtest results to Kafka"""
        if not self.event_streamer:
            return
        
        logger.info("Streaming backtest results")
        
        # Stream performance metrics
        performance_data = {
            'strategy_id': results.strategy_id,
            'total_return': (results.final_capital - results.initial_capital) / results.initial_capital,
            'num_trades': len(results.trades),
            'win_rate': len([t for t in results.trades if t.pnl > 0]) / len(results.trades) if results.trades else 0,
            'final_capital': results.final_capital
        }
        
        await self.event_streamer.publish_event(
            self.config.kafka_config.topics['performance_metrics'],
            performance_data,
            key=results.strategy_id
        )
        
        # Stream individual trades
        for trade in results.trades:
            trade_data = {
                'trade_id': trade.trade_id,
                'strategy_id': results.strategy_id,
                'symbol': trade.symbol,
                'side': trade.side,
                'quantity': trade.quantity,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'pnl': trade.pnl,
                'entry_time': trade.entry_time.isoformat() if trade.entry_time else None,
                'exit_time': trade.exit_time.isoformat() if trade.exit_time else None
            }
            
            await self.event_streamer.publish_event(
                self.config.kafka_config.topics['trades'],
                trade_data,
                key=trade.trade_id
            )
    
    async def _analyze_results(self, results: BacktestResults):
        """Analyze backtest results"""
        logger.info("Analyzing backtest results")
        
        # Initialize analyzers
        if self.config.performance_monitoring:
            self.performance_analyzer = PerformanceAnalyzer(results)
            perf_metrics = self.performance_analyzer.calculate_performance_metrics()
            logger.info(f"Performance Analysis - Total Return: {perf_metrics.total_return:.2%}, "
                       f"Sharpe: {perf_metrics.sharpe_ratio:.2f}, Max DD: {perf_metrics.max_drawdown:.2%}")
        
        if self.config.risk_monitoring:
            self.risk_analyzer = RiskAnalyzer(results)
            risk_metrics = self.risk_analyzer.calculate_comprehensive_risk_metrics()
            logger.info(f"Risk Analysis - VaR 95%: {risk_metrics.portfolio_var.var_95:.2%}, "
                       f"Concentration: {risk_metrics.concentration_risk:.2%}")
        
        # Initialize visualization
        self.visualization_engine = VisualizationEngine(results)
    
    def generate_report(self, output_path: str, format: str = 'html') -> str:
        """Generate comprehensive backtest report"""
        if not self.visualization_engine:
            logger.error("Visualization engine not initialized")
            return ""
        
        if format.lower() == 'html':
            return self.visualization_engine.generate_html_report(output_path)
        else:
            logger.error(f"Unsupported report format: {format}")
            return ""
    
    def export_charts(self, output_dir: str, formats: List[str] = ['html', 'png']):
        """Export all visualization charts"""
        if not self.visualization_engine:
            logger.error("Visualization engine not initialized")
            return
        
        self.visualization_engine.export_charts(output_dir, formats)
    
    async def start_real_time_monitoring(self):
        """Start real-time monitoring of live strategies"""
        if not self.config.enable_real_time or not self.event_streamer:
            logger.warning("Real-time monitoring not enabled")
            return
        
        logger.info("Starting real-time monitoring")
        
        # Set up event consumers
        tasks = []
        
        # Monitor trades
        tasks.append(asyncio.create_task(
            self.event_streamer.consume_events(
                self.config.kafka_config.topics['trades'],
                self._handle_trade_event,
                'monitoring-trades'
            )
        ))
        
        # Monitor risk events
        tasks.append(asyncio.create_task(
            self.event_streamer.consume_events(
                self.config.kafka_config.topics['risk_events'],
                self._handle_risk_event,
                'monitoring-risk'
            )
        ))
        
        # Wait for all tasks
        await asyncio.gather(*tasks)
    
    async def _handle_trade_event(self, event_data: Dict[str, Any]):
        """Handle incoming trade events"""
        logger.info(f"Trade event received: {event_data.get('trade_id')}")
        # Process trade event for real-time monitoring
    
    async def _handle_risk_event(self, event_data: Dict[str, Any]):
        """Handle incoming risk events"""
        logger.warning(f"Risk event received: {event_data.get('event_type')}")
        # Process risk event for real-time monitoring
    
    def stop(self):
        """Stop all components"""
        if self.event_streamer:
            self.event_streamer.stop()
        
        logger.info("Integrated backtest engine stopped")


# Factory functions
def create_integrated_engine(config: Optional[IntegrationConfig] = None) -> IntegratedBacktestEngine:
    """Create integrated backtesting engine with default configuration"""
    if config is None:
        config = IntegrationConfig()
    
    return IntegratedBacktestEngine(config)


def create_kafka_config(bootstrap_servers: List[str] = None) -> KafkaConfig:
    """Create Kafka configuration with custom servers"""
    config = KafkaConfig()
    if bootstrap_servers:
        config.bootstrap_servers = bootstrap_servers
    return config


# Example usage
if __name__ == "__main__":
    async def main():
        # Create configuration
        config = IntegrationConfig(
            enable_kafka=True,
            enable_nautilus=False,  # Set to True when NautilusTrader is available
            enable_real_time=False
        )
        
        # Create integrated engine
        engine = create_integrated_engine(config)
        
        # Example strategies and data
        strategies = {
            'rsi_strategy': {
                'class': None,  # Would be actual strategy class
                'config': {'rsi_period': 14, 'oversold': 30, 'overbought': 70}
            }
        }
        
        data = {
            'AAPL': pd.DataFrame()  # Would contain actual market data
        }
        
        try:
            # Run backtest
            results = await engine.run_integrated_backtest(strategies, data)
            
            # Generate report
            report_path = 'backtest_report.html'
            engine.generate_report(report_path)
            
            # Export charts
            engine.export_charts('charts_output')
            
            print(f"Backtest completed. Report saved to {report_path}")
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
        finally:
            engine.stop()
    
    # Run example
    asyncio.run(main())