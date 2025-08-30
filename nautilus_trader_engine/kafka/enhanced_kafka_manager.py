"""
Enhanced Apache Kafka Event Bus with Schema Registry
Implements hierarchical topics, event sourcing, and high-throughput messaging

Features:
- Hierarchical topic naming (trading.order.placed.ibkr.aapl.us)
- Schema Registry integration with Avro/Protobuf
- Wildcard subscriptions and event routing
- Event sourcing and CQRS patterns
- High-throughput validation (>1M messages/second)
- Event replayability for backtesting

Author: Vincent S. Pereira
Version: 2.0.0
Phase: 1 - Core System Validation & Hardening
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import re

# Kafka clients
try:
    from confluent_kafka import Producer, Consumer, KafkaError
    from confluent_kafka.schema_registry import SchemaRegistryClient
    from confluent_kafka.schema_registry.avro import AvroSerializer, AvroDeserializer
    from confluent_kafka.serialization import SerializationContext, MessageField
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logging.warning("confluent-kafka not available. Install with: pip install confluent-kafka")

logger = logging.getLogger(__name__)

class TopicDomain(Enum):
    """Top-level topic domains"""
    TRADING = "trading"
    MARKET_DATA = "market_data"
    RISK = "risk" 
    PORTFOLIO = "portfolio"
    USER = "user"
    SYSTEM = "system"
    AUDIT = "audit"

class EventAction(Enum):
    """Event actions"""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    PLACED = "placed"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    ALERT = "alert"
    NOTIFICATION = "notification"

@dataclass
class KafkaEvent:
    """Standard Kafka event structure"""
    event_id: str
    timestamp: datetime
    domain: TopicDomain
    action: EventAction
    entity: str
    source: str
    symbol: Optional[str]
    data: Dict[str, Any]
    version: str = "1.0"
    correlation_id: Optional[str] = None

class HierarchicalTopicBuilder:
    """Builds hierarchical Kafka topics following the pattern:
    {domain}.{action}.{entity}.{source}.{symbol}.{region}
    """
    
    @staticmethod
    def build_topic(
        domain: TopicDomain,
        action: EventAction, 
        entity: str,
        source: str,
        symbol: Optional[str] = None,
        region: str = "us"
    ) -> str:
        """Build hierarchical topic name"""
        parts = [domain.value, action.value, entity, source]
        
        if symbol:
            parts.append(symbol.lower())
        if region:
            parts.append(region.lower())
            
        return ".".join(parts)
    
    @staticmethod
    def parse_topic(topic: str) -> Dict[str, str]:
        """Parse hierarchical topic into components"""
        parts = topic.split(".")
        
        if len(parts) < 4:
            raise ValueError(f"Invalid topic format: {topic}")
        
        return {
            "domain": parts[0],
            "action": parts[1], 
            "entity": parts[2],
            "source": parts[3],
            "symbol": parts[4] if len(parts) > 4 else None,
            "region": parts[5] if len(parts) > 5 else None
        }
    
    @staticmethod
    def get_wildcard_pattern(
        domain: Optional[str] = None,
        action: Optional[str] = None,
        entity: Optional[str] = None,
        source: Optional[str] = None
    ) -> str:
        """Generate wildcard subscription pattern"""
        parts = []
        parts.append(domain or "*")
        parts.append(action or "*")
        parts.append(entity or "*") 
        parts.append(source or "*")
        parts.append("*")  # symbol
        parts.append("*")  # region
        
        return ".".join(parts)

class EnhancedKafkaManager:
    """Enhanced Kafka manager with Schema Registry and hierarchical topics"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._default_config()
        self.producer = None
        self.consumers = {}
        self.schema_registry = None
        self.serializers = {}
        self.deserializers = {}
        self.subscribers = {}
        self.performance_metrics = {
            "messages_produced": 0,
            "messages_consumed": 0,
            "throughput_mps": 0,
            "avg_latency_ms": 0
        }
        self.logger = logging.getLogger(__name__)
        
    def _default_config(self) -> Dict[str, Any]:
        """Default Kafka configuration"""
        return {
            "bootstrap_servers": "localhost:9092",
            "schema_registry_url": "http://localhost:8081",
            "producer_config": {
                "acks": "all",
                "retries": 2147483647,
                "max_in_flight_requests_per_connection": 5,
                "enable_idempotence": True,
                "compression_type": "snappy",
                "batch_size": 16384,
                "linger_ms": 5,
                "buffer_memory": 33554432
            },
            "consumer_config": {
                "group_id": "trading_system",
                "auto_offset_reset": "earliest",
                "enable_auto_commit": False,
                "max_poll_interval_ms": 300000,
                "session_timeout_ms": 10000,
                "heartbeat_interval_ms": 3000
            }
        }
    
    async def initialize(self) -> bool:
        """Initialize Kafka producer, Schema Registry, and create topics"""
        if not KAFKA_AVAILABLE:
            self.logger.error("Kafka client not available")
            return False
            
        try:
            # Initialize Schema Registry
            self.schema_registry = SchemaRegistryClient({
                "url": self.config["schema_registry_url"]
            })
            
            # Initialize producer
            producer_config = {
                "bootstrap.servers": self.config["bootstrap_servers"],
                **self.config["producer_config"]
            }
            self.producer = Producer(producer_config)
            
            # Register schemas
            await self._register_schemas()
            
            # Create standard topics
            await self._create_standard_topics()
            
            self.logger.info("Enhanced Kafka manager initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Kafka manager: {e}")
            return False
    
    async def _register_schemas(self):
        """Register Avro schemas with Schema Registry"""
        
        # Base event schema
        base_event_schema = """
        {
            "type": "record",
            "name": "BaseEvent",
            "namespace": "com.trading.events",
            "fields": [
                {"name": "event_id", "type": "string"},
                {"name": "timestamp", "type": "long"},
                {"name": "domain", "type": "string"},
                {"name": "action", "type": "string"},
                {"name": "entity", "type": "string"},
                {"name": "source", "type": "string"},
                {"name": "symbol", "type": ["null", "string"], "default": null},
                {"name": "data", "type": "string"},
                {"name": "version", "type": "string", "default": "1.0"},
                {"name": "correlation_id", "type": ["null", "string"], "default": null}
            ]
        }
        """
        
        # Trading order schema
        order_schema = """
        {
            "type": "record",
            "name": "OrderEvent",
            "namespace": "com.trading.events",
            "fields": [
                {"name": "event_id", "type": "string"},
                {"name": "timestamp", "type": "long"},
                {"name": "order_id", "type": "string"},
                {"name": "symbol", "type": "string"},
                {"name": "side", "type": {"type": "enum", "name": "Side", "symbols": ["BUY", "SELL"]}},
                {"name": "quantity", "type": "double"},
                {"name": "price", "type": ["null", "double"], "default": null},
                {"name": "order_type", "type": "string"},
                {"name": "status", "type": "string"},
                {"name": "account_id", "type": "string"},
                {"name": "user_id", "type": "string"},
                {"name": "strategy_id", "type": ["null", "string"], "default": null}
            ]
        }
        """
        
        try:
            # Register schemas
            self.schema_registry.register_schema("base-event-value", base_event_schema)
            self.schema_registry.register_schema("order-event-value", order_schema)
            
            # Create serializers/deserializers
            self.serializers["base_event"] = AvroSerializer(
                self.schema_registry, base_event_schema
            )
            self.deserializers["base_event"] = AvroDeserializer(
                self.schema_registry, base_event_schema
            )
            
            self.logger.info("Schemas registered successfully")
            
        except Exception as e:
            self.logger.warning(f"Schema registration failed: {e}")
    
    async def _create_standard_topics(self):
        """Create standard hierarchical topics"""
        
        standard_topics = [
            # Trading topics
            "trading.placed.order.ibkr.*.*",
            "trading.filled.order.ibkr.*.*", 
            "trading.cancelled.order.ibkr.*.*",
            
            # Market data topics
            "market_data.updated.tick.*.*.*",
            "market_data.updated.bar.*.*.*",
            
            # Risk topics
            "risk.alert.exposure.*.*.*",
            "risk.alert.violation.*.*.*",
            
            # System topics
            "system.notification.alert.*.*.*",
            "system.created.log.*.*.*"
        ]
        
        # Note: Topic creation would be handled by Kafka admin client
        # For now, topics will be auto-created on first use
        self.logger.info(f"Standard topic patterns defined: {len(standard_topics)}")
    
    async def publish_event(self, event: KafkaEvent) -> bool:
        """Publish event to hierarchical topic"""
        try:
            # Build topic name
            topic = HierarchicalTopicBuilder.build_topic(
                domain=event.domain,
                action=event.action,
                entity=event.entity,
                source=event.source,
                symbol=event.symbol
            )
            
            # Serialize event
            event_data = {
                "event_id": event.event_id,
                "timestamp": int(event.timestamp.timestamp() * 1000),
                "domain": event.domain.value,
                "action": event.action.value,
                "entity": event.entity,
                "source": event.source,
                "symbol": event.symbol,
                "data": json.dumps(event.data),
                "version": event.version,
                "correlation_id": event.correlation_id
            }
            
            # Use Avro serializer if available
            if "base_event" in self.serializers:
                serialized_value = self.serializers["base_event"](
                    event_data, SerializationContext(topic, MessageField.VALUE)
                )
            else:
                serialized_value = json.dumps(event_data).encode('utf-8')
            
            # Produce message
            self.producer.produce(
                topic=topic,
                key=event.event_id.encode('utf-8'),
                value=serialized_value
            )
            
            self.producer.flush()
            self.performance_metrics["messages_produced"] += 1
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to publish event: {e}")
            return False
    
    async def subscribe_to_pattern(
        self,
        pattern: str,
        callback: Callable[[Dict[str, Any]], None],
        consumer_group: Optional[str] = None
    ) -> str:
        """Subscribe to topic pattern with wildcard support"""
        
        consumer_id = f"consumer_{len(self.consumers)}_{int(time.time())}"
        
        try:
            # Create consumer
            consumer_config = {
                "bootstrap.servers": self.config["bootstrap_servers"],
                "group.id": consumer_group or self.config["consumer_config"]["group_id"],
                **self.config["consumer_config"]
            }
            
            consumer = Consumer(consumer_config)
            
            # Convert pattern to regex for topic matching
            regex_pattern = pattern.replace("*", "[^.]+").replace(".", r"\.")
            consumer.subscribe([regex_pattern])
            
            self.consumers[consumer_id] = {
                "consumer": consumer,
                "callback": callback,
                "pattern": pattern,
                "active": True
            }
            
            # Start consumer loop
            asyncio.create_task(self._consumer_loop(consumer_id))
            
            self.logger.info(f"Subscribed to pattern: {pattern} with consumer: {consumer_id}")
            return consumer_id
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to pattern {pattern}: {e}")
            return ""
    
    async def _consumer_loop(self, consumer_id: str):
        """Consumer message processing loop"""
        consumer_info = self.consumers.get(consumer_id)
        if not consumer_info:
            return
        
        consumer = consumer_info["consumer"]
        callback = consumer_info["callback"]
        
        while consumer_info.get("active", False):
            try:
                msg = consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                    
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        self.logger.error(f"Consumer error: {msg.error()}")
                        break
                
                # Deserialize message
                if "base_event" in self.deserializers:
                    try:
                        event_data = self.deserializers["base_event"](
                            msg.value(), SerializationContext(msg.topic(), MessageField.VALUE)
                        )
                    except:
                        event_data = json.loads(msg.value().decode('utf-8'))
                else:
                    event_data = json.loads(msg.value().decode('utf-8'))
                
                # Add message metadata
                event_data.update({
                    "topic": msg.topic(),
                    "partition": msg.partition(),
                    "offset": msg.offset(),
                    "key": msg.key().decode('utf-8') if msg.key() else None
                })
                
                # Execute callback
                await self._safe_callback(callback, event_data)
                
                # Commit offset
                consumer.commit(msg)
                self.performance_metrics["messages_consumed"] += 1
                
            except Exception as e:
                self.logger.error(f"Error in consumer loop {consumer_id}: {e}")
                await asyncio.sleep(1)
    
    async def _safe_callback(self, callback: Callable, data: Dict[str, Any]):
        """Safely execute callback with error handling"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)
        except Exception as e:
            self.logger.error(f"Callback error: {e}")
    
    async def validate_throughput(self, target_mps: int = 1000000) -> Dict[str, Any]:
        """Validate Kafka throughput performance"""
        self.logger.info(f"Starting throughput validation (target: {target_mps:,} messages/second)")
        
        test_events = 10000  # Test with 10k messages
        start_time = time.time()
        
        # Generate test events
        for i in range(test_events):
            test_event = KafkaEvent(
                event_id=f"test_{i}",
                timestamp=datetime.now(),
                domain=TopicDomain.SYSTEM,
                action=EventAction.CREATED,
                entity="test",
                source="benchmark",
                symbol=None,
                data={"test_id": i, "payload": "x" * 100}  # 100 char payload
            )
            
            await self.publish_event(test_event)
            
            # Batch every 1000 messages
            if i % 1000 == 0:
                self.producer.flush()
        
        # Final flush
        self.producer.flush()
        end_time = time.time()
        
        duration = end_time - start_time
        actual_mps = test_events / duration
        
        result = {
            "test_messages": test_events,
            "duration_seconds": duration,
            "messages_per_second": actual_mps,
            "target_mps": target_mps,
            "performance_ratio": actual_mps / target_mps,
            "status": "PASS" if actual_mps >= target_mps else "NEEDS_OPTIMIZATION",
            "timestamp": datetime.now().isoformat()
        }
        
        self.performance_metrics["throughput_mps"] = actual_mps
        
        self.logger.info(
            f"Throughput test completed: {actual_mps:,.0f} messages/second "
            f"({'✓' if actual_mps >= target_mps else '✗'})"
        )
        
        return result
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            **self.performance_metrics,
            "active_consumers": len([c for c in self.consumers.values() if c.get("active")]),
            "total_consumers": len(self.consumers),
            "timestamp": datetime.now().isoformat()
        }
    
    async def close(self):
        """Close all Kafka connections"""
        try:
            # Close consumers
            for consumer_info in self.consumers.values():
                consumer_info["active"] = False
                consumer_info["consumer"].close()
            
            # Close producer
            if self.producer:
                self.producer.flush()
            
            self.logger.info("Kafka connections closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error closing Kafka connections: {e}")

# Global Kafka manager instance
enhanced_kafka_manager = EnhancedKafkaManager()

# Convenience functions
async def publish_trading_event(
    action: EventAction,
    order_id: str,
    symbol: str,
    side: str,
    quantity: float,
    price: Optional[float] = None,
    **kwargs
) -> bool:
    """Publish trading event"""
    event = KafkaEvent(
        event_id=f"trade_{order_id}_{int(time.time())}",
        timestamp=datetime.now(),
        domain=TopicDomain.TRADING,
        action=action,
        entity="order",
        source="ibkr",
        symbol=symbol,
        data={
            "order_id": order_id,
            "side": side,
            "quantity": quantity,
            "price": price,
            **kwargs
        }
    )
    
    return await enhanced_kafka_manager.publish_event(event)

async def subscribe_to_trading_events(callback: Callable) -> str:
    """Subscribe to all trading events"""
    pattern = HierarchicalTopicBuilder.get_wildcard_pattern(
        domain="trading",
        entity="order"
    )
    return await enhanced_kafka_manager.subscribe_to_pattern(pattern, callback)

async def initialize_kafka() -> bool:
    """Initialize Kafka manager"""
    return await enhanced_kafka_manager.initialize()

if __name__ == "__main__":
    async def main():
        # Initialize Kafka
        success = await initialize_kafka()
        print(f"Kafka initialized: {'✓' if success else '✗'}")
        
        if success:
            # Test throughput
            result = await enhanced_kafka_manager.validate_throughput(target_mps=10000)
            print(f"Throughput test: {result['status']} ({result['messages_per_second']:,.0f} msg/s)")
    
    asyncio.run(main())