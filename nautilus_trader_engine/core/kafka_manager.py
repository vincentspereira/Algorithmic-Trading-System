"""
Kafka Management Service

This module provides high-level management functionality for Kafka integration
in the trading system, including API endpoints and background services.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog

from kafka_integration import (
    MarketDataStreamer, 
    KafkaConfig, 
    MarketDataTopic, 
    AssetClass
)
from data_feeds import DataFeedManager

logger = structlog.get_logger(__name__)


class KafkaManager:
    """High-level Kafka management service"""
    
    def __init__(self, bootstrap_servers: str = "kafka:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.config = KafkaConfig(bootstrap_servers=bootstrap_servers)
        self.streamer: Optional[MarketDataStreamer] = None
        self.background_tasks: Dict[str, asyncio.Task] = {}
        self.is_initialized = False
        self.streaming_active = False
        
    async def initialize(self) -> bool:
        """Initialize Kafka manager and connections"""
        try:
            logger.info("Initializing Kafka manager", 
                       bootstrap_servers=self.bootstrap_servers)
            
            # Create and initialize streamer
            self.streamer = MarketDataStreamer(self.config)
            success = await self.streamer.initialize()
            
            if success:
                self.is_initialized = True
                logger.info("Kafka manager initialized successfully")
                return True
            else:
                logger.error("Failed to initialize Kafka streamer")
                return False
                
        except Exception as e:
            logger.error("Error initializing Kafka manager", error=str(e))
            return False
    
    async def start_streaming_service(self) -> bool:
        """Start the background streaming service"""
        if not self.is_initialized or not self.streamer:
            logger.error("Kafka manager not initialized")
            return False
        
        try:
            # Start consumer in background
            consumer_task = asyncio.create_task(
                self.streamer.start_consumer(),
                name="kafka_consumer"
            )
            self.background_tasks["consumer"] = consumer_task
            
            # Start periodic data publishing
            publisher_task = asyncio.create_task(
                self._periodic_data_publisher(),
                name="data_publisher"
            )
            self.background_tasks["publisher"] = publisher_task
            
            self.streaming_active = True
            logger.info("Kafka streaming service started")
            return True
            
        except Exception as e:
            logger.error("Failed to start streaming service", error=str(e))
            return False
    
    async def stop_streaming_service(self):
        """Stop the background streaming service"""
        try:
            self.streaming_active = False
            
            # Stop consumer
            if self.streamer:
                await self.streamer.stop_consumer()
            
            # Cancel background tasks
            for task_name, task in self.background_tasks.items():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.info("Background task cancelled", task=task_name)
            
            self.background_tasks.clear()
            logger.info("Kafka streaming service stopped")
            
        except Exception as e:
            logger.error("Error stopping streaming service", error=str(e))
    
    async def _periodic_data_publisher(self):
        """Background task to periodically publish market data"""
        logger.info("Starting periodic data publisher")
        
        try:
            while self.streaming_active:
                # Get list of symbols to stream
                if self.streamer and self.streamer.streaming_symbols:
                    for symbol in list(self.streamer.streaming_symbols.keys()):
                        try:
                            await self.streamer.publish_market_data_for_symbol(symbol)
                        except Exception as e:
                            logger.error("Error publishing data for symbol",
                                       symbol=symbol, error=str(e))
                
                # Wait before next iteration (configurable interval)
                await asyncio.sleep(60)  # Publish every minute
                
        except asyncio.CancelledError:
            logger.info("Periodic data publisher cancelled")
        except Exception as e:
            logger.error("Error in periodic data publisher", error=str(e))
    
    async def add_streaming_symbol(self, symbol: str, asset_class: str, 
                                 interval: str = "1m") -> Dict[str, Any]:
        """Add a symbol to streaming"""
        if not self.streamer:
            return {"success": False, "error": "Kafka manager not initialized"}
        
        try:
            # Convert string to enum
            asset_class_enum = AssetClass(asset_class.lower())
            
            success = await self.streamer.start_streaming_symbol(
                symbol, asset_class_enum, interval
            )
            
            if success:
                # Immediately publish initial data
                await self.streamer.publish_market_data_for_symbol(symbol)
                
                return {
                    "success": True,
                    "message": f"Started streaming for {symbol}",
                    "symbol": symbol,
                    "asset_class": asset_class,
                    "interval": interval
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to start streaming for {symbol}"
                }
                
        except ValueError as e:
            return {
                "success": False,
                "error": f"Invalid asset class: {asset_class}"
            }
        except Exception as e:
            logger.error("Error adding streaming symbol", 
                        symbol=symbol, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def remove_streaming_symbol(self, symbol: str) -> Dict[str, Any]:
        """Remove a symbol from streaming"""
        if not self.streamer:
            return {"success": False, "error": "Kafka manager not initialized"}
        
        try:
            if symbol in self.streamer.streaming_symbols:
                del self.streamer.streaming_symbols[symbol]
                return {
                    "success": True,
                    "message": f"Stopped streaming for {symbol}",
                    "symbol": symbol
                }
            else:
                return {
                    "success": False,
                    "error": f"Symbol {symbol} not found in streaming list"
                }
                
        except Exception as e:
            logger.error("Error removing streaming symbol", 
                        symbol=symbol, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_streaming_status(self) -> Dict[str, Any]:
        """Get comprehensive streaming status"""
        if not self.streamer:
            return {
                "initialized": False,
                "error": "Kafka manager not initialized"
            }
        
        try:
            base_status = await self.streamer.get_streaming_status()
            
            # Add manager-specific information
            status = {
                **base_status,
                "initialized": self.is_initialized,
                "streaming_service_active": self.streaming_active,
                "background_tasks": {
                    name: not task.done() 
                    for name, task in self.background_tasks.items()
                },
                "kafka_config": {
                    "bootstrap_servers": self.config.bootstrap_servers,
                    "client_id": self.config.client_id,
                    "group_id": self.config.group_id
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return status
            
        except Exception as e:
            logger.error("Error getting streaming status", error=str(e))
            return {
                "initialized": self.is_initialized,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_streaming_symbols(self) -> Dict[str, Any]:
        """Get list of currently streaming symbols"""
        if not self.streamer:
            return {"symbols": [], "error": "Kafka manager not initialized"}
        
        try:
            symbols_info = []
            for symbol, config in self.streamer.streaming_symbols.items():
                symbols_info.append({
                    "symbol": symbol,
                    "asset_class": config["asset_class"].value,
                    "topic": config["topic"].value,
                    "interval": config["interval"],
                    "last_update": config.get("last_update")
                })
            
            return {
                "symbols": symbols_info,
                "count": len(symbols_info),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Error getting streaming symbols", error=str(e))
            return {
                "symbols": [],
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def publish_trading_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Publish a trading signal to Kafka"""
        if not self.streamer:
            return {"success": False, "error": "Kafka manager not initialized"}
        
        try:
            # Add timestamp if not present
            if "timestamp" not in signal:
                signal["timestamp"] = time.time()
            
            success = await self.streamer.producer.publish_trading_signal(signal)
            
            if success:
                return {
                    "success": True,
                    "message": "Trading signal published successfully",
                    "signal": signal
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to publish trading signal"
                }
                
        except Exception as e:
            logger.error("Error publishing trading signal", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_kafka_connection(self) -> Dict[str, Any]:
        """Test Kafka connection and basic functionality"""
        try:
            # Test producer connection
            producer_test = False
            consumer_test = False
            
            if self.streamer and self.streamer.producer.is_connected:
                # Try to publish a test message
                test_signal = {
                    "type": "test",
                    "symbol": "TEST",
                    "timestamp": time.time(),
                    "message": "Kafka connection test"
                }
                producer_test = await self.streamer.producer.publish_trading_signal(test_signal)
            
            if self.streamer and self.streamer.consumer.is_connected:
                consumer_test = True
            
            return {
                "success": producer_test and consumer_test,
                "producer_connected": producer_test,
                "consumer_connected": consumer_test,
                "bootstrap_servers": self.bootstrap_servers,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Error testing Kafka connection", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_kafka_topics(self) -> Dict[str, Any]:
        """Get list of available Kafka topics"""
        try:
            if not self.streamer or not self.streamer.producer.producer:
                return {"topics": [], "error": "Producer not available"}
            
            # Get topic metadata
            metadata = self.streamer.producer.producer.list_topics(timeout=5)
            
            topics_info = []
            for topic_name in metadata.topics:
                topic_metadata = metadata.topics[topic_name]
                topics_info.append({
                    "name": topic_name,
                    "partitions": len(topic_metadata.partitions),
                    "error": topic_metadata.error
                })
            
            return {
                "topics": topics_info,
                "count": len(topics_info),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Error getting Kafka topics", error=str(e))
            return {
                "topics": [],
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def close(self):
        """Close Kafka manager and all connections"""
        try:
            # Stop streaming service
            await self.stop_streaming_service()
            
            # Close streamer
            if self.streamer:
                await self.streamer.close()
            
            self.is_initialized = False
            logger.info("Kafka manager closed")
            
        except Exception as e:
            logger.error("Error closing Kafka manager", error=str(e))


# Global Kafka manager instance
_kafka_manager: Optional[KafkaManager] = None


async def get_kafka_manager() -> KafkaManager:
    """Get or create global Kafka manager instance"""
    global _kafka_manager
    
    if _kafka_manager is None:
        import os
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        _kafka_manager = KafkaManager(bootstrap_servers)
        
        # Initialize if not already done
        if not _kafka_manager.is_initialized:
            await _kafka_manager.initialize()
    
    return _kafka_manager


async def initialize_kafka_manager() -> bool:
    """Initialize the global Kafka manager"""
    try:
        manager = await get_kafka_manager()
        return manager.is_initialized
    except Exception as e:
        logger.error("Failed to initialize Kafka manager", error=str(e))
        return False


async def close_kafka_manager():
    """Close the global Kafka manager"""
    global _kafka_manager
    
    if _kafka_manager:
        await _kafka_manager.close()
        _kafka_manager = None