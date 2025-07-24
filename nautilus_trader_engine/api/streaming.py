"""
Enhanced gRPC Streaming Service for Market Data - Phase 2

This module implements a high-performance gRPC streaming service that provides
real-time market data streaming with microsecond-level latency. It connects to
Kafka for market data and streams ticks to clients efficiently.

New Features in Phase 2:
- Dynamic Kafka topic subscription management
- Connection pooling and more robust client handling
- Enhanced error recovery and reconnection logic
- Direct consumption from raw tick topics (e.g., raw.ticks.AAPL)
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Set, Optional, AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
import grpc
from grpc import aio
import structlog
from collections import defaultdict
import uuid

# Import Kafka integration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kafka_integration import (
    MarketDataStreamer, 
    KafkaConfig, 
    MarketDataTopic,
    MarketDataMessage
)
from data_feeds import AssetClass, DataSource

# Import generated gRPC stubs
try:
    from .generated import market_data_pb2, market_data_pb2_grpc
except ImportError:
    print("Warning: gRPC stubs not found. Run generate_grpc_stubs.py first.")
    from .generate_grpc_stubs import main as generate_stubs
    generate_stubs()
    from .generated import market_data_pb2, market_data_pb2_grpc

# Configure structured logging
logger = structlog.get_logger(__name__)


class ConnectionPool:
    """Manages active client connections and their subscriptions."""
    def __init__(self):
        self.clients = {} # client_id -> queue
        self.subscriptions = defaultdict(set) # topic -> {client_id, ...}

    def add_client(self, queue):
        client_id = str(uuid.uuid4())
        self.clients[client_id] = queue
        return client_id

    def remove_client(self, client_id):
        if client_id in self.clients:
            del self.clients[client_id]
        for topic in self.subscriptions:
            self.subscriptions[topic].discard(client_id)

    def subscribe(self, client_id, topics):
        for topic in topics:
            self.subscriptions[topic].add(client_id)

    def unsubscribe(self, client_id, topics):
        for topic in topics:
            self.subscriptions[topic].discard(client_id)

    async def broadcast(self, topic, message):
        if topic in self.subscriptions:
            for client_id in list(self.subscriptions[topic]):
                if client_id in self.clients:
                    try:
                        await self.clients[client_id].put(message)
                    except asyncio.QueueFull:
                        logger.warning("Client queue full, dropping message", client_id=client_id, topic=topic)
                else:
                    # Clean up stale client reference
                    self.subscriptions[topic].discard(client_id)


class MarketDataServicer(market_data_pb2_grpc.MarketDataServicer):
    """gRPC service implementation for market data streaming"""
    
    def __init__(self, kafka_config: KafkaConfig):
        self.kafka_config = kafka_config
        self.market_streamer = None
        self.is_initialized = False
        self.connection_pool = ConnectionPool()
        self.executor = ThreadPoolExecutor(max_workers=os.cpu_count() * 2)
        
        # Performance metrics
        self.stream_count = 0
        self.tick_count = 0
        self.error_count = 0
        self.start_time = time.time()
        
    async def initialize(self) -> bool:
        """Initialize and start the market data streamer with retry logic."""
        for attempt in range(5):  # Retry 5 times
            try:
                self.market_streamer = MarketDataStreamer(self.kafka_config)
                success = await self.market_streamer.initialize()
                
                if success:
                    # Generic handler for all topics
                    self.market_streamer.consumer.register_handler(None, self._handle_raw_market_data)
                    
                    # Start consuming in background
                    asyncio.create_task(self.market_streamer.start_consumer())
                    
                    self.is_initialized = True
                    logger.info("Market data gRPC service initialized successfully")
                    return True
                else:
                    logger.warning("Failed to initialize market data streamer, retrying...", attempt=attempt+1)
                    await asyncio.sleep(5 * (attempt + 1)) # Exponential backoff
                    
            except Exception as e:
                logger.error("Error initializing market data service, retrying...", error=str(e), attempt=attempt+1)
                await asyncio.sleep(5 * (attempt + 1))
        
        logger.error("Failed to initialize market data service after multiple attempts.")
        return False
    
    async def _handle_raw_market_data(self, message_data: Dict, topic: str):
        """Handle incoming raw market data from Kafka."""
        try:
            # message_data is expected to be a JSON string for raw ticks
            tick_data = json.loads(message_data)

            tick = market_data_pb2.Tick(
                symbol=tick_data.get('symbol', topic.split('.')[-1]),
                timestamp=int(tick_data.get('timestamp', time.time() * 1000000)),
                price=float(tick_data.get('price', 0.0)),
                volume=float(tick_data.get('volume', 0.0)),
                exchange=tick_data.get('exchange', "SIMULATED"),
            )
            
            await self.connection_pool.broadcast(topic, tick)
            self.tick_count += 1
            
        except json.JSONDecodeError:
            logger.warning("Received non-JSON message from Kafka", topic=topic)
        except Exception as e:
            self.error_count += 1
            logger.error("Error handling raw market data", error=str(e), topic=topic)
    
    async def StreamMarketData(self, request: market_data_pb2.SubscriptionRequest, context) -> AsyncGenerator:
        """Stream real-time market data for subscribed symbols."""
        
        if not self.is_initialized:
            await context.abort(grpc.StatusCode.UNAVAILABLE, "Service not yet initialized. Please try again later.")
            return

        client_queue = asyncio.Queue(maxsize=10000)
        client_id = self.connection_pool.add_client(client_queue)
        
        # Convert symbols to Kafka topic names
        topics = [f"raw.ticks.{symbol}" for symbol in request.symbols]
        self.connection_pool.subscribe(client_id, topics)

        # Subscribe consumer to these topics
        await self.market_streamer.consumer.subscribe(topics)
        
        logger.info("Client subscribed", client_id=client_id, symbols=list(request.symbols))
        self.stream_count += 1
        
        try:
            while True:
                try:
                    tick = await asyncio.wait_for(client_queue.get(), timeout=30.0)
                    yield tick
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    heartbeat = market_data_pb2.Tick(symbol="HEARTBEAT", timestamp=int(time.time() * 1000000))
                    yield heartbeat
                    
        except asyncio.CancelledError:
            logger.info("Client stream cancelled", client_id=client_id)
        except Exception as e:
            logger.error("Error in client stream", client_id=client_id, error=str(e))
            self.error_count += 1
            await context.abort(grpc.StatusCode.INTERNAL, f"Stream error: {str(e)}")
        finally:
            self.connection_pool.remove_client(client_id)
            # Unsubscribe logic can be added here if needed, but Kafka consumer handles it
            logger.info("Client stream ended", client_id=client_id)
            self.stream_count -= 1

    async def get_service_stats(self) -> Dict:
        """Get service performance statistics"""
        uptime = time.time() - self.start_time
        
        return {
            "uptime_seconds": uptime,
            "active_streams": self.stream_count,
            "total_ticks_processed": self.tick_count,
            "total_errors": self.error_count,
            "ticks_per_second": self.tick_count / uptime if uptime > 0 else 0,
            "connected_clients": len(self.connection_pool.clients),
            "kafka_status": await self.market_streamer.get_streaming_status() if self.market_streamer else {}
        }

async def create_grpc_server(port: int = 50051, kafka_bootstrap_servers: str = "kafka:9092"):
    """Create and start the gRPC server with connection pooling."""
    
    kafka_config = KafkaConfig(bootstrap_servers=kafka_bootstrap_servers)
    service = MarketDataServicer(kafka_config)
    
    if not await service.initialize():
        raise RuntimeError("Failed to initialize market data service after multiple retries.")
    
    server = aio.server(ThreadPoolExecutor(max_workers=os.cpu_count() * 5))
    market_data_pb2_grpc.add_MarketDataServicer_to_server(service, server)
    
    listen_addr = f'[::]:{port}'
    server.add_insecure_port(listen_addr)
    
    logger.info("Starting gRPC server", port=port, address=listen_addr)
    await server.start()
    logger.info("gRPC server started successfully", port=port)
    
    return server, service


async def main():
    """Main function to run the gRPC server"""
    import argparse
    parser = argparse.ArgumentParser(description='Enhanced Market Data gRPC Streaming Server')
    parser.add_argument('--port', type=int, default=os.getenv('GRPC_PORT', 50051), help='gRPC server port')
    parser.add_argument('--kafka', default=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'), help='Kafka bootstrap servers')
    
    args = parser.parse_args()
    
    server = None
    try:
        server, service = await create_grpc_server(args.port, args.kafka)
        
        # Keep process alive
        await server.wait_for_termination()
        
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server...")
        if server:
            await server.stop(grace=5)
    except Exception as e:
        logger.critical("Critical error running gRPC server", error=str(e), exc_info=True)
        if server:
            await server.stop(grace=1)
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    asyncio.run(main())