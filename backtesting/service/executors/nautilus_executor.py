
import json
import logging
import time
from decimal import Decimal
from typing import Optional

import pandas as pd
import redis
from kafka import KafkaConsumer, KafkaProducer
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.model.data import Bar
from nautilus_trader.model.objects import Price, Quantity

from strategies.ma_crossover import MACrossoverConfig, MACrossoverStrategy
from shared.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BacktestExecutor:
    """
    Execute and manage backtests.
    """
    def __init__(
        self,
    ):
        try:
            self.kafka_consumer = KafkaConsumer(
                'backtest_requests',
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )

            self.kafka_producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Failed to initialize Kafka clients: {e}")
            self.kafka_consumer = None
            self.kafka_producer = None

        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
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
                data=self._prepare_data(data, config['symbol'])
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

    def _prepare_data(self, data: pd.DataFrame, symbol: str) -> list[Bar]:
        """
        Prepare data for NautilusTrader engine.
        """
        logger.info("Preparing data for backtest...")
        bars = []
        for _, row in data.iterrows():
            bar = Bar(
                symbol=symbol,
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
