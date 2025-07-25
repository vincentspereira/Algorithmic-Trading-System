"""
Kafka Integration Module for Market Data Streaming

This module provides Kafka producer and consumer functionality for real-time
market data streaming in the algorithmic trading system.

Features:
- Market data publishing to Kafka topics
- Real-time data consumption
- Schema validation and serialization
- Error handling and retry logic
- Monitoring and metrics integration

Author: Vincent S. Pereira
Version: 1.0.0
"""

import json
import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
from kafka import KafkaProducer, KafkaConsumer, TopicPartition
from kafka.errors import KafkaError, KafkaTimeoutError
import structlog

from data_feeds import DataFeedManager, DataResponse, AssetClass, DataSource

# Configure structured logging
logger = structlog.get_logger(__name__)


class MarketDataTopic(Enum):
    """Kafka topics for different types of market data"""
    STOCK_PRICES = "market.stock.prices"
    FOREX_RATES = "market.forex.rates"
    CRYPTO_PRICES = "market.crypto.prices"
    FUTURES_PRICES = "market.futures.prices"
    OPTIONS_PRICES = "market.options.prices"
    COMMODITIES_PRICES = "market.commodities.prices"
    MARKET_NEWS = "market.news"
    ECONOMIC_INDICATORS = "market.indicators"
    TRADING_SIGNALS = "trading.signals"
    BACKTEST_RESULTS = "trading.backtest.results"


@dataclass
class MarketDataMessage:
    """Standardized market data message format"""
    symbol: str
    asset_class: str
    timestamp: float
    data_source: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    message_id: str
    version: str = "1.0"


@dataclass
class KafkaConfig:
    """Kafka configuration settings"""
    bootstrap_servers: str = "kafka:9092"
    client_id: str = "nautilus-trader-engine"
    group_id: str = "trading-system"
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = True
    auto_commit_interval_ms: int = 1000
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 3000
    max_poll_records: int = 500
    compression_type: str = "gzip"
    acks: str = "all"
    retries: int = 3
    batch_size: int = 16384
    linger_ms: int = 10
    buffer_memory: int = 33554432


class KafkaProducerService:
    """Kafka producer service for publishing market data"""
    
    def __init__(self, config: KafkaConfig):
        self.config = config
        self.producer = None
        self.is_connected = False
        self.message_count = 0
        self.error_count = 0
        
    async def initialize(self) -> bool:
        """Initialize Kafka producer connection"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.config.bootstrap_servers,
                client_id=self.config.client_id,
                compression_type=self.config.compression_type,
                acks=self.config.acks,
                retries=self.config.retries,
                batch_size=self.config.batch_size,
                linger_ms=self.config.linger_ms,
                buffer_memory=self.config.buffer_memory,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )
            
            # Test connection
            metadata = self.producer.list_topics(timeout=5)
            self.is_connected = True
            
            logger.info("Kafka producer initialized successfully", 
                       topics_count=len(metadata.topics))
            return True
            
        except Exception as e:
            logger.error("Failed to initialize Kafka producer", error=str(e))
            self.is_connected = False
            return False
    
    async def publish_market_data(self, topic: MarketDataTopic, 
                                 data_response: DataResponse) -> bool:
        """Publish market data to Kafka topic"""
        if not self.is_connected or not self.producer:
            logger.warning("Kafka producer not connected")
            return False
        
        try:
            # Convert DataFrame to records for JSON serialization
            data_records = []
            if not data_response.data.empty:
                data_records = data_response.data.reset_index().to_dict('records')
            
            # Create standardized message
            message = MarketDataMessage(
                symbol=data_response.ticker,
                asset_class=data_response.asset_class.value,
                timestamp=data_response.timestamp,
                data_source=data_response.source.value,
                data=data_records,
                metadata=data_response.metadata,
                message_id=f"{data_response.ticker}_{int(data_response.timestamp)}"
            )
            
            # Send message
            future = self.producer.send(
                topic.value,
                key=data_response.ticker,
                value=asdict(message)
            )
            
            # Wait for confirmation (with timeout)
            record_metadata = future.get(timeout=10)
            
            self.message_count += 1
            logger.info("Market data published successfully",
                       topic=topic.value,
                       symbol=data_response.ticker,
                       partition=record_metadata.partition,
                       offset=record_metadata.offset)
            
            return True
            
        except KafkaTimeoutError:
            self.error_count += 1
            logger.error("Kafka publish timeout", 
                        topic=topic.value, 
                        symbol=data_response.ticker)
            return False
            
        except Exception as e:
            self.error_count += 1
            logger.error("Failed to publish market data",
                        topic=topic.value,
                        symbol=data_response.ticker,
                        error=str(e))
            return False
    
    async def publish_trading_signal(self, signal: Dict[str, Any]) -> bool:
        """Publish trading signal to Kafka"""
        try:
            future = self.producer.send(
                MarketDataTopic.TRADING_SIGNALS.value,
                key=signal.get('symbol', 'unknown'),
                value=signal
            )
            
            future.get(timeout=10)
            self.message_count += 1
            
            logger.info("Trading signal published",
                       symbol=signal.get('symbol'),
                       signal_type=signal.get('type'))
            return True
            
        except Exception as e:
            self.error_count += 1
            logger.error("Failed to publish trading signal", error=str(e))
            return False
    
    async def close(self):
        """Close Kafka producer connection"""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            self.is_connected = False
            logger.info("Kafka producer closed")


class KafkaConsumerService:
    """Kafka consumer service for consuming market data"""
    
    def __init__(self, config: KafkaConfig):
        self.config = config
        self.consumer = None
        self.is_connected = False
        self.message_handlers: Dict[str, Callable] = {}
        self.consumed_count = 0
        self.error_count = 0
        self.running = False
        
    async def initialize(self, topics: List[MarketDataTopic]) -> bool:
        """Initialize Kafka consumer connection"""
        try:
            topic_names = [topic.value for topic in topics]
            
            self.consumer = KafkaConsumer(
                *topic_names,
                bootstrap_servers=self.config.bootstrap_servers,
                client_id=self.config.client_id,
                group_id=self.config.group_id,
                auto_offset_reset=self.config.auto_offset_reset,
                enable_auto_commit=self.config.enable_auto_commit,
                auto_commit_interval_ms=self.config.auto_commit_interval_ms,
                session_timeout_ms=self.config.session_timeout_ms,
                heartbeat_interval_ms=self.config.heartbeat_interval_ms,
                max_poll_records=self.config.max_poll_records,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None
            )
            
            self.is_connected = True
            logger.info("Kafka consumer initialized successfully",
                       topics=topic_names,
                       group_id=self.config.group_id)
            return True
            
        except Exception as e:
            logger.error("Failed to initialize Kafka consumer", error=str(e))
            self.is_connected = False
            return False
    
    def register_handler(self, topic: MarketDataTopic, handler: Callable):
        """Register message handler for specific topic"""
        self.message_handlers[topic.value] = handler
        logger.info("Handler registered for topic", topic=topic.value)
    
    async def start_consuming(self):
        """Start consuming messages from Kafka topics"""
        if not self.is_connected or not self.consumer:
            logger.warning("Kafka consumer not connected")
            return
        
        self.running = True
        logger.info("Starting Kafka message consumption")
        
        try:
            while self.running:
                # Poll for messages
                message_batch = self.consumer.poll(timeout_ms=1000)
                
                for topic_partition, messages in message_batch.items():
                    topic_name = topic_partition.topic
                    
                    for message in messages:
                        try:
                            await self._process_message(topic_name, message)
                            self.consumed_count += 1
                            
                        except Exception as e:
                            self.error_count += 1
                            logger.error("Error processing message",
                                       topic=topic_name,
                                       error=str(e))
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.01)
                
        except Exception as e:
            logger.error("Error in message consumption loop", error=str(e))
        finally:
            self.running = False
    
    async def _process_message(self, topic: str, message):
        """Process individual Kafka message"""
        try:
            # Get handler for topic
            handler = self.message_handlers.get(topic)
            if not handler:
                logger.warning("No handler registered for topic", topic=topic)
                return
            
            # Parse message
            message_data = message.value
            
            # Call handler
            if asyncio.iscoroutinefunction(handler):
                await handler(message_data)
            else:
                handler(message_data)
                
            logger.debug("Message processed successfully",
                        topic=topic,
                        key=message.key,
                        offset=message.offset)
            
        except Exception as e:
            logger.error("Error processing message",
                        topic=topic,
                        error=str(e))
            raise
    
    async def stop_consuming(self):
        """Stop consuming messages"""
        self.running = False
        logger.info("Stopping Kafka message consumption")
    
    async def close(self):
        """Close Kafka consumer connection"""
        if self.consumer:
            self.consumer.close()
            self.is_connected = False
            logger.info("Kafka consumer closed")


class MarketDataStreamer:
    """High-level service for streaming market data via Kafka"""
    
    def __init__(self, kafka_config: KafkaConfig):
        self.kafka_config = kafka_config
        self.producer = KafkaProducerService(kafka_config)
        self.consumer = KafkaConsumerService(kafka_config)
        self.data_feed_manager = DataFeedManager()
        self.streaming_symbols: Dict[str, Dict] = {}
        self.is_streaming = False
        
    async def initialize(self) -> bool:
        """Initialize the market data streamer"""
        try:
            # Initialize producer
            producer_ok = await self.producer.initialize()
            if not producer_ok:
                return False
            
            # Initialize consumer with all market data topics
            market_topics = [
                MarketDataTopic.STOCK_PRICES,
                MarketDataTopic.FOREX_RATES,
                MarketDataTopic.CRYPTO_PRICES,
                MarketDataTopic.FUTURES_PRICES,
                MarketDataTopic.OPTIONS_PRICES,
                MarketDataTopic.COMMODITIES_PRICES,
                MarketDataTopic.TRADING_SIGNALS
            ]
            
            consumer_ok = await self.consumer.initialize(market_topics)
            if not consumer_ok:
                return False
            
            # Register default handlers
            self._register_default_handlers()
            
            logger.info("Market data streamer initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize market data streamer", error=str(e))
            return False
    
    def _register_default_handlers(self):
        """Register default message handlers"""
        self.consumer.register_handler(
            MarketDataTopic.STOCK_PRICES, 
            self._handle_stock_data
        )
        self.consumer.register_handler(
            MarketDataTopic.FOREX_RATES, 
            self._handle_forex_data
        )
        self.consumer.register_handler(
            MarketDataTopic.CRYPTO_PRICES, 
            self._handle_crypto_data
        )
        self.consumer.register_handler(
            MarketDataTopic.TRADING_SIGNALS, 
            self._handle_trading_signal
        )
    
    async def _handle_stock_data(self, message_data: Dict[str, Any]):
        """Handle incoming stock price data"""
        logger.debug("Received stock data", symbol=message_data.get('symbol'))
        # TODO: Process stock data for trading engine
    
    async def _handle_forex_data(self, message_data: Dict[str, Any]):
        """Handle incoming forex rate data"""
        logger.debug("Received forex data", symbol=message_data.get('symbol'))
        # TODO: Process forex data for trading engine
    
    async def _handle_crypto_data(self, message_data: Dict[str, Any]):
        """Handle incoming crypto price data"""
        logger.debug("Received crypto data", symbol=message_data.get('symbol'))
        # TODO: Process crypto data for trading engine
    
    async def _handle_trading_signal(self, message_data: Dict[str, Any]):
        """Handle incoming trading signals"""
        logger.info("Received trading signal", 
                   symbol=message_data.get('symbol'),
                   signal_type=message_data.get('type'))
        # TODO: Process trading signal
    
    async def start_streaming_symbol(self, symbol: str, 
                                   asset_class: AssetClass,
                                   interval: str = "1m") -> bool:
        """Start streaming data for a specific symbol"""
        try:
            # Get topic based on asset class
            topic_map = {
                AssetClass.STOCK: MarketDataTopic.STOCK_PRICES,
                AssetClass.FOREX: MarketDataTopic.FOREX_RATES,
                AssetClass.CRYPTO: MarketDataTopic.CRYPTO_PRICES,
                AssetClass.FUTURES: MarketDataTopic.FUTURES_PRICES,
                AssetClass.OPTIONS: MarketDataTopic.OPTIONS_PRICES,
                AssetClass.COMMODITIES: MarketDataTopic.COMMODITIES_PRICES
            }
            
            topic = topic_map.get(asset_class, MarketDataTopic.STOCK_PRICES)
            
            # Store streaming configuration
            self.streaming_symbols[symbol] = {
                "asset_class": asset_class,
                "topic": topic,
                "interval": interval,
                "last_update": None
            }
            
            logger.info("Started streaming for symbol",
                       symbol=symbol,
                       asset_class=asset_class.value,
                       topic=topic.value)
            
            return True
            
        except Exception as e:
            logger.error("Failed to start streaming for symbol",
                        symbol=symbol,
                        error=str(e))
            return False
    
    async def publish_market_data_for_symbol(self, symbol: str) -> bool:
        """Fetch and publish market data for a symbol"""
        if symbol not in self.streaming_symbols:
            logger.warning("Symbol not configured for streaming", symbol=symbol)
            return False
        
        try:
            config = self.streaming_symbols[symbol]
            
            # Fetch data using data feed manager
            response = self.data_feed_manager.get_data(
                ticker=symbol,
                asset_class=config["asset_class"],
                interval=config["interval"],
                period="1d"  # Get recent data
            )
            
            if not response.success:
                logger.warning("Failed to fetch data for symbol", 
                             symbol=symbol,
                             error=response.error_message)
                return False
            
            # Publish to Kafka
            success = await self.producer.publish_market_data(
                config["topic"], 
                response
            )
            
            if success:
                config["last_update"] = time.time()
            
            return success
            
        except Exception as e:
            logger.error("Error publishing market data",
                        symbol=symbol,
                        error=str(e))
            return False
    
    async def start_consumer(self):
        """Start the Kafka consumer"""
        await self.consumer.start_consuming()
    
    async def stop_consumer(self):
        """Stop the Kafka consumer"""
        await self.consumer.stop_consuming()
    
    async def get_streaming_status(self) -> Dict[str, Any]:
        """Get current streaming status"""
        return {
            "is_streaming": self.is_streaming,
            "producer_connected": self.producer.is_connected,
            "consumer_connected": self.consumer.is_connected,
            "streaming_symbols": list(self.streaming_symbols.keys()),
            "messages_published": self.producer.message_count,
            "messages_consumed": self.consumer.consumed_count,
            "producer_errors": self.producer.error_count,
            "consumer_errors": self.consumer.error_count
        }
    
    async def close(self):
        """Close all Kafka connections"""
        await self.consumer.close()
        await self.producer.close()
        logger.info("Market data streamer closed")


# Convenience functions
async def create_market_data_streamer(bootstrap_servers: str = "kafka:9092") -> MarketDataStreamer:
    """Create and initialize a market data streamer"""
    config = KafkaConfig(bootstrap_servers=bootstrap_servers)
    streamer = MarketDataStreamer(config)
    
    if await streamer.initialize():
        return streamer
    else:
        raise Exception("Failed to initialize market data streamer")


if __name__ == "__main__":
    # Example usage
    async def main():
        # Create streamer
        streamer = await create_market_data_streamer()
        
        # Start streaming for AAPL
        await streamer.start_streaming_symbol("AAPL", AssetClass.STOCK)
        
        # Publish some data
        await streamer.publish_market_data_for_symbol("AAPL")
        
        # Get status
        status = await streamer.get_streaming_status()
        print(f"Streaming status: {status}")
        
        # Close
        await streamer.close()
    
    asyncio.run(main())