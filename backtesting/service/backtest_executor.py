"""
Moving Average Crossover strategy implementation using NautilusTrader.
"""

from datetime import datetime
from decimal import Decimal
import logging
from typing import Dict, Optional
import json

from nautilus_trader.config import BacktestDataConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.models import BacktestConfiguration
from nautilus_trader.common.clock import TestClock
from nautilus_trader.common.factories import OrderFactory
from nautilus_trader.core.data import Data
from nautilus_trader.indicators.average.moving_average import MovingAverageSimple
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import Symbol, StrategyId, TraderId
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.trading.strategy import Strategy, StrategyConfig

from kafka import KafkaConsumer, KafkaProducer
import pandas as pd
import numpy as np

class MACrossoverConfig(StrategyConfig):
    """
    Configuration for MA Crossover strategy.
    """
    def __init__(
        self,
        symbol: str,
        fast_ma_period: int = 20,
        slow_ma_period: int = 50,
        trade_size: Decimal = Decimal("100"),
        position_size: Optional[Decimal] = None
    ):
        super().__init__()
        self.symbol = symbol
        self.fast_ma_period = fast_ma_period
        self.slow_ma_period = slow_ma_period
        self.trade_size = trade_size
        self.position_size = position_size or trade_size

class MACrossoverStrategy(Strategy):
    """
    Moving Average Crossover strategy implementation.
    """
    def __init__(
        self,
        config: MACrossoverConfig
    ):
        super().__init__(config)
        
        # Create strategy components
        self.symbol = Symbol.from_str(config.symbol)
        self.fast_ma = MovingAverageSimple(config.fast_ma_period)
        self.slow_ma = MovingAverageSimple(config.slow_ma_period)
        self.position_size = config.position_size
        self.trade_size = config.trade_size
        
        # Initialize state
        self.initialized = False
        self.last_signal = None
        
    def on_start(self):
        """Handle strategy start."""
        self.subscribe_bars(self.symbol)
        self.initialized = True
        
    def on_bar(self, bar):
        """
        Handle bar updates.
        """
        # Update indicators
        self.fast_ma.update_raw(bar.close.as_double())
        self.slow_ma.update_raw(bar.close.as_double())
        
        if not self.initialized:
            return
            
        # Generate trading signals
        if self.fast_ma.value >= self.slow_ma.value:
            signal = 1  # Buy signal
        else:
            signal = -1  # Sell signal
            
        # Check for signal change
        if signal != self.last_signal:
            self.last_signal = signal
            
            if signal == 1:
                # Buy signal
                self.buy()
            else:
                # Sell signal
                self.sell()
                
    def buy(self):
        """Execute buy order."""
        if self.portfolio.is_flat(self.symbol):
            order = self.order_factory.market(
                symbol=self.symbol,
                order_side=OrderSide.BUY,
                quantity=Quantity.from_int(self.trade_size),
                time_in_force=TimeInForce.IOC
            )
            self.submit_order(order)
            
    def sell(self):
        """Execute sell order."""
        if self.portfolio.is_long(self.symbol):
            position = self.portfolio.get_position(self.symbol)
            order = self.order_factory.market(
                symbol=self.symbol,
                order_side=OrderSide.SELL,
                quantity=position.quantity,
                time_in_force=TimeInForce.IOC
            )
            self.submit_order(order)

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import os
import redis

class BacktestExecutor:
    """
    Execute and manage backtests.
    """
    def __init__(
        self,
        kafka_servers: list = None,
        redis_host: str = None,
        redis_port: int = None,
    ):
        try:
            KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
            self.kafka_consumer = KafkaConsumer(
                'backtest_requests',
                bootstrap_servers=kafka_servers or [KAFKA_BOOTSTRAP_SERVERS],
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            
            self.kafka_producer = KafkaProducer(
                bootstrap_servers=kafka_servers or [KAFKA_BOOTSTRAP_SERVERS],
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Failed to initialize Kafka clients: {e}")
            self.kafka_consumer = None
            self.kafka_producer = None

        try:
            REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
            REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
            self.redis_client = redis.Redis(
                host=redis_host or REDIS_HOST,
                port=redis_port or REDIS_PORT,
                decode_responses=True
            )
            self.redis_client.ping()
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            self.redis_client = None
        
    def run_backtest(self, config: dict, data: pd.DataFrame) -> dict:
        """
        Run backtest with given configuration and data.
        """
        logger.info(f"Running backtest for symbol: {config['symbol']}")
        try:
            # Configure backtest engine
            engine = BacktestEngine()
            
            # Configure strategy
            strategy_config = MACrossoverConfig(
                symbol=config['symbol'],
                fast_ma_period=config['fast_ma'],
                slow_ma_period=config['slow_ma'],
                trade_size=Decimal(str(config.get('trade_size', 100)))
            )
            
            strategy = MACrossoverStrategy(strategy_config)
            
            # Add data to engine
            engine.add_data(
                symbol=config['symbol'],
                data=self._prepare_data(data)
            )
            
            # Add strategy to engine
            engine.add_strategy(strategy)
            
            # Run backtest
            engine.run()
            
            # Get results
            results = self._process_results(engine)
            logger.info(f"Backtest completed successfully for symbol: {config['symbol']}")
            return results
            
        except Exception as e:
            logger.error(f"Backtest error for symbol {config['symbol']}: {str(e)}")
            return {'error': str(e)}
            
    from nautilus_trader.model.data import Bar

    def _prepare_data(self, data: pd.DataFrame) -> list[Bar]:
        """
        Prepare data for NautilusTrader engine.
        """
        logger.info("Preparing data for backtest...")
        bars = []
        for _, row in data.iterrows():
            bar = Bar(
                symbol=self.symbol,
                timestamp=row["timestamp"],
                open=Price(row["open"], precision=2),
                high=Price(row["high"], precision=2),
                low=Price(row["low"], precision=2),
                close=Price(row["close"], precision=2),
                volume=Quantity(row["volume"], precision=0),
            )
            bars.append(bar)
        logger.info("Data preparation complete.")
        return bars
        
    def _process_results(self, engine: BacktestEngine) -> dict:
        """
        Process backtest results.
        """
        logger.info("Processing backtest results...")
        # Extract performance metrics
        metrics = {
            'total_return': float(engine.portfolio.returns),
            'sharpe_ratio': float(engine.portfolio.sharpe_ratio),
            'max_drawdown': float(engine.portfolio.max_drawdown),
            'win_rate': float(engine.portfolio.win_rate)
        }
        
        # Extract trade history
        trades = [
            {
                'timestamp': str(trade.timestamp),
                'symbol': str(trade.symbol),
                'side': str(trade.order_side),
                'quantity': float(trade.quantity),
                'price': float(trade.price),
                'pnl': float(trade.realized_pnl)
            }
            for trade in engine.portfolio.trades
        ]
        
        # Extract equity curve
        equity_curve = [
            {
                'timestamp': str(point.timestamp),
                'equity': float(point.equity)
            }
            for point in engine.portfolio.equity_points
        ]
        
        logger.info("Backtest results processed successfully.")
        return {
            'metrics': metrics,
            'trades': trades,
            'equity_curve': equity_curve
        }
        
    def start(self):
        """
        Start the backtest executor service.
        """
        if not self.kafka_consumer or not self.kafka_producer or not self.redis_client:
            logger.error("Service cannot start due to initialization errors.")
            return

        logger.info("Backtest executor service started.")
        try:
            for message in self.kafka_consumer:
                request = message.value
                request_id = request['request_id']
                logger.info(f"Received backtest request: {request_id}")
                
                # Wait for data ready event
                logger.info(f"Waiting for data for request: {request_id}")
                data = self._wait_for_data(request_id)
                
                if data:
                    logger.info(f"Data found for request: {request_id}")
                    # Run backtest
                    results = self.run_backtest(
                        request['strategy'],
                        pd.DataFrame(data)
                    )
                    
                    # Publish results
                    logger.info(f"Publishing results for request: {request_id}")
                    self.kafka_producer.send(
                        'backtest_results',
                        {
                            'request_id': request_id,
                            'results': results
                        }
                    )
                else:
                    logger.warning(f"Data not found for request: {request_id}. Timeout reached.")
                    
        except KeyboardInterrupt:
            logger.info("Shutting down backtest executor service.")
            self.kafka_consumer.close()
            self.kafka_producer.close()
            
    import time

    def _wait_for_data(self, request_id: str, timeout: int = 60) -> Optional[list]:
        """
        Wait for market data to be ready.
        """
        if not self.redis_client:
            logger.error("Redis client not available. Cannot wait for data.")
            return None

        for i in range(timeout):
            logger.debug(f"Waiting for data... ({i+1}/{timeout})")
            data = self.redis_client.get(f"data:{request_id}")
            if data:
                return json.loads(data)
            time.sleep(1)
        return None
        
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    executor = BacktestExecutor()
    executor.start()
