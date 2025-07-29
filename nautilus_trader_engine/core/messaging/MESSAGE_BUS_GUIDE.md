# High-Performance Message Bus Guide

## Overview

The High-Performance Message Bus is a zero-copy, lock-free inter-component communication system designed for ultra-low latency trading applications. It provides topic-based message routing, serialization/deserialization, and comprehensive performance monitoring for enterprise-grade trading systems.

## Key Features

### 🚀 **Ultra-Low Latency Architecture**
- **Lock-Free Ring Buffer**: Zero-contention message passing between components
- **Zero-Copy Semantics**: Direct memory access without data copying
- **CPU Cache Optimization**: Memory layout optimized for L1/L2/L3 cache efficiency
- **NUMA-Aware Design**: Optimized for multi-socket server architectures

### 📡 **Advanced Message Routing**
- **Topic-Based Subscriptions**: Flexible publish-subscribe pattern
- **Message Filtering**: Efficient content-based routing
- **Priority Queues**: Critical message prioritization
- **Broadcast and Multicast**: One-to-many message distribution

### 📊 **Performance Monitoring**
- **Real-Time Metrics**: Message throughput, latency, and queue depths
- **Performance Analytics**: Historical performance analysis and optimization
- **Bottleneck Detection**: Automatic identification of performance issues
- **Resource Utilization**: CPU, memory, and network usage tracking

### 🔧 **Enterprise Features**
- **Message Persistence**: Optional message durability for critical data
- **Error Handling**: Comprehensive error recovery and dead letter queues
- **Flow Control**: Backpressure handling and rate limiting
- **Security**: Message encryption and authentication support

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Message Bus Core                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Lock-Free   │  │ Zero-Copy   │  │ Topic-Based │        │
│  │ Ring Buffer │  │ Serializer  │  │ Router      │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Performance │  │ Message     │  │ Subscription│        │
│  │ Monitor     │  │ Persistence │  │ Manager     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### MessageBus Class

The main message bus implementation providing high-performance message routing:

```python
class MessageBus:
    def __init__(self, 
                 buffer_size: int = 1024 * 1024,
                 enable_persistence: bool = False,
                 enable_monitoring: bool = True):
        self.ring_buffer = LockFreeRingBuffer(buffer_size)
        self.serializer = ZeroCopySerializer()
        self.router = TopicBasedRouter()
        self.monitor = PerformanceMonitor() if enable_monitoring else None
        
    async def publish(self, topic: str, message: Any, priority: int = 0) -> bool
    async def subscribe(self, topic: str, callback: Callable) -> str
    async def unsubscribe(self, subscription_id: str) -> bool
    def get_metrics(self) -> Dict[str, Any]
```

### LockFreeRingBuffer Class

High-performance, lock-free circular buffer for message storage:

```python
class LockFreeRingBuffer:
    def __init__(self, size: int):
        self.buffer = np.zeros(size, dtype=np.uint8)
        self.head = AtomicInteger(0)
        self.tail = AtomicInteger(0)
        self.size = size
        
    def write(self, data: bytes) -> bool
    def read(self) -> Optional[bytes]
    def is_full(self) -> bool
    def is_empty(self) -> bool
    def available_space(self) -> int
```

### ZeroCopySerializer Class

Efficient serialization without memory copying:

```python
class ZeroCopySerializer:
    def __init__(self):
        self.schema_registry = SchemaRegistry()
        self.buffer_pool = MemoryPool()
        
    def serialize(self, obj: Any) -> MemoryView
    def deserialize(self, data: MemoryView, schema_id: int) -> Any
    def register_schema(self, schema: Schema) -> int
```

## Usage Examples

### Basic Message Publishing and Subscription

```python
import asyncio
from nautilus_trader_engine.core.messaging import MessageBus, Message

async def basic_messaging_example():
    # Initialize message bus
    bus = MessageBus(
        buffer_size=1024 * 1024,  # 1MB buffer
        enable_persistence=False,
        enable_monitoring=True
    )
    
    await bus.start()
    
    # Define message handler
    async def price_handler(message: Message):
        print(f"Received price update: {message.data}")
    
    # Subscribe to price updates
    subscription_id = await bus.subscribe("market.prices.AAPL", price_handler)
    
    # Publish price update
    price_message = Message(
        topic="market.prices.AAPL",
        data={"symbol": "AAPL", "price": 150.25, "timestamp": time.time()},
        priority=1
    )
    
    success = await bus.publish("market.prices.AAPL", price_message)
    print(f"Message published: {success}")
    
    # Wait for message processing
    await asyncio.sleep(0.1)
    
    # Unsubscribe
    await bus.unsubscribe(subscription_id)
    await bus.stop()

# Run example
asyncio.run(basic_messaging_example())
```

### High-Frequency Trading Message Flow

```python
async def hft_messaging_example():
    bus = MessageBus(
        buffer_size=10 * 1024 * 1024,  # 10MB for high throughput
        enable_persistence=False,
        enable_monitoring=True
    )
    
    await bus.start()
    
    # Order management subscription
    async def order_handler(message: Message):
        order_data = message.data
        print(f"Processing order: {order_data['order_id']}")
        
        # Simulate order processing
        if order_data['action'] == 'BUY':
            # Process buy order
            await process_buy_order(order_data)
        elif order_data['action'] == 'SELL':
            # Process sell order
            await process_sell_order(order_data)
    
    # Market data subscription
    async def market_data_handler(message: Message):
        market_data = message.data
        # High-frequency market data processing
        await update_trading_signals(market_data)
    
    # Subscribe to different topics
    await bus.subscribe("orders.new", order_handler)
    await bus.subscribe("orders.cancel", order_handler)
    await bus.subscribe("market.level1", market_data_handler)
    await bus.subscribe("market.level2", market_data_handler)
    
    # Simulate high-frequency message publishing
    for i in range(10000):
        # Publish market data
        market_msg = Message(
            topic="market.level1",
            data={
                "symbol": "AAPL",
                "bid": 150.20 + (i * 0.01),
                "ask": 150.25 + (i * 0.01),
                "timestamp": time.time_ns()
            },
            priority=2  # High priority for market data
        )
        
        await bus.publish("market.level1", market_msg)
        
        # Publish orders occasionally
        if i % 100 == 0:
            order_msg = Message(
                topic="orders.new",
                data={
                    "order_id": f"ORD_{i}",
                    "symbol": "AAPL",
                    "action": "BUY",
                    "quantity": 100,
                    "price": 150.20,
                    "timestamp": time.time_ns()
                },
                priority=1  # Critical priority for orders
            )
            
            await bus.publish("orders.new", order_msg)
    
    # Get performance metrics
    metrics = bus.get_metrics()
    print(f"Messages processed: {metrics['messages_processed']}")
    print(f"Average latency: {metrics['avg_latency_ns']}ns")
    print(f"Throughput: {metrics['messages_per_second']}/sec")
    
    await bus.stop()
```

### Topic-Based Message Filtering

```python
async def topic_filtering_example():
    bus = MessageBus()
    await bus.start()
    
    # Subscribe to specific instrument
    async def aapl_handler(message: Message):
        print(f"AAPL update: {message.data}")
    
    # Subscribe to all equity prices
    async def equity_handler(message: Message):
        print(f"Equity update: {message.data}")
    
    # Subscribe to all market data
    async def market_handler(message: Message):
        print(f"Market update: {message.data}")
    
    # Hierarchical topic subscriptions
    await bus.subscribe("market.prices.equity.AAPL", aapl_handler)
    await bus.subscribe("market.prices.equity.*", equity_handler)
    await bus.subscribe("market.*", market_handler)
    
    # Publish messages to different topics
    messages = [
        ("market.prices.equity.AAPL", {"price": 150.25}),
        ("market.prices.equity.MSFT", {"price": 300.50}),
        ("market.prices.forex.EURUSD", {"price": 1.0850}),
        ("market.volume.equity.AAPL", {"volume": 1000000})
    ]
    
    for topic, data in messages:
        await bus.publish(topic, Message(topic=topic, data=data))
    
    await asyncio.sleep(0.1)  # Allow message processing
    await bus.stop()
```

### Performance Monitoring and Optimization

```python
async def performance_monitoring_example():
    bus = MessageBus(enable_monitoring=True)
    await bus.start()
    
    # Set up performance monitoring
    monitor = bus.get_performance_monitor()
    
    # Configure alerts
    monitor.set_latency_threshold(1000)  # 1 microsecond
    monitor.set_throughput_threshold(1000000)  # 1M messages/sec
    
    async def performance_alert_handler(alert: PerformanceAlert):
        print(f"Performance Alert: {alert.type} - {alert.message}")
        
        if alert.type == AlertType.HIGH_LATENCY:
            # Optimize for latency
            await bus.optimize_for_latency()
        elif alert.type == AlertType.LOW_THROUGHPUT:
            # Optimize for throughput
            await bus.optimize_for_throughput()
    
    monitor.add_alert_handler(performance_alert_handler)
    
    # Simulate message load
    start_time = time.time()
    message_count = 100000
    
    for i in range(message_count):
        await bus.publish(
            f"test.topic.{i % 10}",
            Message(data={"id": i, "timestamp": time.time_ns()})
        )
    
    end_time = time.time()
    
    # Get detailed metrics
    metrics = bus.get_metrics()
    
    print("=== Performance Metrics ===")
    print(f"Total messages: {metrics['total_messages']}")
    print(f"Messages/second: {message_count / (end_time - start_time):.0f}")
    print(f"Average latency: {metrics['avg_latency_ns']}ns")
    print(f"P99 latency: {metrics['p99_latency_ns']}ns")
    print(f"Buffer utilization: {metrics['buffer_utilization']:.1%}")
    print(f"Memory usage: {metrics['memory_usage_mb']:.1f}MB")
    
    # Generate performance report
    report = monitor.generate_report()
    print(f"\\nPerformance Report:\\n{report}")
    
    await bus.stop()
```

### Message Persistence and Recovery

```python
async def persistence_example():
    bus = MessageBus(
        enable_persistence=True,
        persistence_config={
            'storage_path': '/var/lib/nautilus/messages',
            'retention_hours': 24,
            'compression': True
        }
    )
    
    await bus.start()
    
    # Subscribe with persistence
    async def critical_handler(message: Message):
        print(f"Processing critical message: {message.data}")
        # Simulate processing failure
        if message.data.get('simulate_failure'):
            raise Exception("Processing failed")
    
    await bus.subscribe(
        "critical.orders",
        critical_handler,
        persistence_options={
            'enable_replay': True,
            'max_retries': 3,
            'retry_delay': 1.0
        }
    )
    
    # Publish critical messages
    critical_messages = [
        {"order_id": "ORD_001", "amount": 10000},
        {"order_id": "ORD_002", "amount": 20000, "simulate_failure": True},
        {"order_id": "ORD_003", "amount": 15000}
    ]
    
    for msg_data in critical_messages:
        await bus.publish(
            "critical.orders",
            Message(data=msg_data),
            persistence_options={'durable': True}
        )
    
    # Wait for processing and retries
    await asyncio.sleep(5)
    
    # Check persistence metrics
    persistence_metrics = bus.get_persistence_metrics()
    print(f"Messages persisted: {persistence_metrics['messages_persisted']}")
    print(f"Messages replayed: {persistence_metrics['messages_replayed']}")
    print(f"Failed messages: {persistence_metrics['failed_messages']}")
    
    await bus.stop()
```

## Advanced Features

### Custom Message Serialization

```python
from nautilus_trader_engine.core.messaging import CustomSerializer

class ProtobufSerializer(CustomSerializer):
    def serialize(self, obj: Any) -> bytes:
        # Custom protobuf serialization
        return obj.SerializeToString()
    
    def deserialize(self, data: bytes, message_type: type) -> Any:
        # Custom protobuf deserialization
        obj = message_type()
        obj.ParseFromString(data)
        return obj

# Register custom serializer
bus = MessageBus()
bus.register_serializer('protobuf', ProtobufSerializer())
```

### Message Compression

```python
async def compression_example():
    bus = MessageBus(
        compression_config={
            'algorithm': 'lz4',  # or 'zstd', 'snappy'
            'level': 1,
            'min_size': 1024  # Only compress messages > 1KB
        }
    )
    
    await bus.start()
    
    # Large message that will be compressed
    large_data = {
        'market_data': [
            {'symbol': f'STOCK_{i}', 'price': 100 + i, 'volume': 1000 * i}
            for i in range(1000)
        ]
    }
    
    await bus.publish("market.bulk_data", Message(data=large_data))
    
    # Check compression metrics
    metrics = bus.get_compression_metrics()
    print(f"Compression ratio: {metrics['compression_ratio']:.2f}")
    print(f"Bytes saved: {metrics['bytes_saved']}")
    
    await bus.stop()
```

### Circuit Breaker Pattern

```python
async def circuit_breaker_example():
    bus = MessageBus(
        circuit_breaker_config={
            'failure_threshold': 5,
            'recovery_timeout': 30,
            'half_open_max_calls': 3
        }
    )
    
    await bus.start()
    
    async def unreliable_handler(message: Message):
        # Simulate intermittent failures
        if random.random() < 0.3:
            raise Exception("Handler failure")
        print(f"Processed: {message.data}")
    
    await bus.subscribe("unreliable.topic", unreliable_handler)
    
    # Publish messages that may trigger circuit breaker
    for i in range(20):
        await bus.publish("unreliable.topic", Message(data={"id": i}))
        await asyncio.sleep(0.1)
    
    # Check circuit breaker status
    cb_status = bus.get_circuit_breaker_status("unreliable.topic")
    print(f"Circuit breaker state: {cb_status['state']}")
    print(f"Failure count: {cb_status['failure_count']}")
    
    await bus.stop()
```

## Performance Optimization

### CPU Affinity and NUMA Optimization

```python
async def numa_optimization_example():
    bus = MessageBus(
        numa_config={
            'enable_numa_awareness': True,
            'cpu_affinity': [0, 1, 2, 3],  # Bind to specific CPU cores
            'memory_policy': 'local',  # Allocate memory on local NUMA node
            'interrupt_affinity': [4, 5]  # Separate cores for interrupts
        }
    )
    
    await bus.start()
    
    # Check NUMA configuration
    numa_info = bus.get_numa_info()
    print(f"NUMA nodes: {numa_info['numa_nodes']}")
    print(f"CPU affinity: {numa_info['cpu_affinity']}")
    print(f"Memory policy: {numa_info['memory_policy']}")
    
    await bus.stop()
```

### Memory Pool Management

```python
async def memory_pool_example():
    bus = MessageBus(
        memory_pool_config={
            'initial_size': 100 * 1024 * 1024,  # 100MB
            'max_size': 1024 * 1024 * 1024,     # 1GB
            'block_sizes': [64, 256, 1024, 4096],  # Different block sizes
            'preallocation': True
        }
    )
    
    await bus.start()
    
    # Memory pool will automatically manage message memory
    for i in range(10000):
        message = Message(data={"id": i, "payload": "x" * 1000})
        await bus.publish("memory.test", message)
    
    # Check memory pool statistics
    pool_stats = bus.get_memory_pool_stats()
    print(f"Pool utilization: {pool_stats['utilization']:.1%}")
    print(f"Allocations: {pool_stats['allocations']}")
    print(f"Deallocations: {pool_stats['deallocations']}")
    print(f"Peak usage: {pool_stats['peak_usage_mb']:.1f}MB")
    
    await bus.stop()
```

## Integration Examples

### Integration with Order Management System

```python
from nautilus_trader_engine.trading import OrderManager

async def oms_integration_example():
    bus = MessageBus()
    order_manager = OrderManager(message_bus=bus)
    
    await bus.start()
    await order_manager.start()
    
    # Order events will be automatically published to message bus
    order = await order_manager.create_order(
        symbol="AAPL",
        side="BUY",
        quantity=100,
        price=150.25
    )
    
    # Subscribe to order events
    async def order_event_handler(message: Message):
        event = message.data
        print(f"Order event: {event['type']} for {event['order_id']}")
    
    await bus.subscribe("orders.events.*", order_event_handler)
    
    # Execute order (will generate events)
    await order_manager.execute_order(order.id)
    
    await asyncio.sleep(1)
    await order_manager.stop()
    await bus.stop()
```

### Integration with Risk Management

```python
from nautilus_trader_engine.risk import RiskManager

async def risk_integration_example():
    bus = MessageBus()
    risk_manager = RiskManager(message_bus=bus)
    
    await bus.start()
    await risk_manager.start()
    
    # Risk manager subscribes to order and position events
    # and publishes risk alerts
    
    async def risk_alert_handler(message: Message):
        alert = message.data
        print(f"Risk Alert: {alert['type']} - {alert['message']}")
        
        if alert['severity'] == 'CRITICAL':
            # Take immediate action
            await emergency_risk_action(alert)
    
    await bus.subscribe("risk.alerts.*", risk_alert_handler)
    
    # Simulate position update that triggers risk check
    position_update = {
        "symbol": "AAPL",
        "quantity": 10000,
        "market_value": 1500000,
        "timestamp": time.time()
    }
    
    await bus.publish("positions.updates", Message(data=position_update))
    
    await asyncio.sleep(1)
    await risk_manager.stop()
    await bus.stop()
```

## Best Practices

### Message Design
1. **Keep Messages Small**: Optimize for cache efficiency and network bandwidth
2. **Use Structured Data**: Consistent message schemas for better performance
3. **Include Timestamps**: Essential for ordering and latency measurement
4. **Version Messages**: Support for schema evolution and backward compatibility

### Topic Naming
1. **Hierarchical Structure**: Use dot notation (e.g., "market.prices.equity.AAPL")
2. **Consistent Naming**: Follow established conventions across the system
3. **Avoid Deep Nesting**: Keep topic depth reasonable for performance
4. **Use Wildcards Wisely**: Balance flexibility with performance

### Performance Tuning
1. **Buffer Sizing**: Size buffers based on message volume and latency requirements
2. **CPU Affinity**: Bind message bus threads to specific CPU cores
3. **Memory Allocation**: Use memory pools to avoid garbage collection
4. **Batch Processing**: Group related messages for better throughput

### Error Handling
1. **Dead Letter Queues**: Handle messages that can't be processed
2. **Circuit Breakers**: Protect against cascading failures
3. **Retry Logic**: Implement exponential backoff for transient failures
4. **Monitoring**: Track error rates and performance metrics

## Troubleshooting

### Common Issues

```python
# Check message bus health
health_status = bus.get_health_status()
if not health_status['healthy']:
    print(f"Message bus issues: {health_status['issues']}")
    
    # Common fixes
    if 'buffer_full' in health_status['issues']:
        # Increase buffer size or improve consumer performance
        await bus.resize_buffer(new_size=2 * 1024 * 1024)
    
    if 'high_latency' in health_status['issues']:
        # Optimize for latency
        await bus.optimize_for_latency()
    
    if 'memory_pressure' in health_status['issues']:
        # Trigger garbage collection
        await bus.cleanup_memory()
```

### Diagnostic Tools

```python
# Enable debug logging
bus.set_log_level('DEBUG')

# Trace message flow
tracer = bus.get_message_tracer()
tracer.enable()

# Analyze performance bottlenecks
profiler = bus.get_performance_profiler()
profile_data = profiler.profile(duration=60)  # Profile for 60 seconds

print(f"Bottlenecks: {profile_data['bottlenecks']}")
print(f"Recommendations: {profile_data['recommendations']}")
```

## Conclusion

The High-Performance Message Bus provides a robust, scalable foundation for inter-component communication in trading systems. Its zero-copy, lock-free design ensures minimal latency while supporting high throughput requirements. The comprehensive monitoring and optimization features make it suitable for production use in demanding financial environments.

For optimal performance, carefully consider message design, topic structure, and system configuration based on your specific use case and performance requirements.