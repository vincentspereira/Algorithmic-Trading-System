# Advanced Caching System Guide

## Overview

The Advanced Caching System is a high-performance, multi-tier caching solution designed for ultra-low latency trading applications. It provides L1 in-memory caching, L2 distributed Redis-based caching, and L3 persistent database caching with intelligent cache coherency and invalidation mechanisms.

## Key Features

### 🚀 **Multi-Tier Cache Architecture**
- **L1 Cache**: In-memory cache with LRU eviction for microsecond access times
- **L2 Cache**: Distributed Redis-based cache for shared data across instances
- **L3 Cache**: Persistent database cache for long-term data storage
- **Intelligent Routing**: Automatic data placement across cache tiers

### 📊 **Advanced Cache Policies**
- **LRU (Least Recently Used)**: Optimal for temporal locality
- **LFU (Least Frequently Used)**: Optimal for frequency-based access patterns
- **TTL (Time To Live)**: Automatic expiration for time-sensitive data
- **Write-Through/Write-Back**: Configurable write policies for consistency vs performance

### 🔄 **Cache Coherency and Invalidation**
- **Event-Driven Invalidation**: Real-time cache invalidation based on data changes
- **Distributed Coherency**: Consistent cache state across multiple instances
- **Selective Invalidation**: Granular invalidation by key patterns or tags
- **Cascade Invalidation**: Automatic invalidation of dependent cache entries

### 📈 **Performance Optimization**
- **Prefetching**: Predictive data loading based on access patterns
- **Compression**: Automatic data compression for memory efficiency
- **Partitioning**: Data sharding across cache instances for scalability
- **Monitoring**: Comprehensive cache performance metrics and analytics

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Cache Manager                             │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ L1 Cache    │  │ L2 Cache    │  │ L3 Cache    │        │
│  │ (In-Memory) │  │ (Redis)     │  │ (Database)  │        │
│  │ <1μs        │  │ <100μs      │  │ <10ms       │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Cache       │  │ Invalidation│  │ Performance │        │
│  │ Coherency   │  │ Manager     │  │ Monitor     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### CacheManager Class

The main cache management interface providing unified access to all cache tiers:

```python
class CacheManager:
    def __init__(self, config: CacheConfig):
        self.l1_cache = L1Cache(config.l1_config)
        self.l2_cache = L2Cache(config.l2_config)
        self.l3_cache = L3Cache(config.l3_config)
        self.coherency_manager = CacheCoherencyManager()
        self.performance_monitor = CachePerformanceMonitor()
        
    async def get(self, key: str, default: Any = None) -> Any
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool
    async def delete(self, key: str) -> bool
    async def invalidate_pattern(self, pattern: str) -> int
    def get_metrics(self) -> Dict[str, Any]
```

### L1Cache Class

High-performance in-memory cache with LRU eviction:

```python
class L1Cache:
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 300):
        self.cache = {}
        self.access_order = OrderedDict()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.lock = asyncio.Lock()
        
    async def get(self, key: str) -> Optional[Any]
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool
    async def delete(self, key: str) -> bool
    def evict_expired(self) -> int
    def get_stats(self) -> Dict[str, Any]
```

### L2Cache Class

Distributed Redis-based cache for shared data:

```python
class L2Cache:
    def __init__(self, redis_config: RedisConfig):
        self.redis_pool = aioredis.ConnectionPool.from_url(
            redis_config.url,
            max_connections=redis_config.max_connections
        )
        self.compression_enabled = redis_config.compression
        self.serializer = CacheSerializer()
        
    async def get(self, key: str) -> Optional[Any]
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool
    async def delete(self, key: str) -> bool
    async def exists(self, key: str) -> bool
    async def scan_keys(self, pattern: str) -> List[str]
```

### L3Cache Class

Persistent database cache for long-term storage:

```python
class L3Cache:
    def __init__(self, db_config: DatabaseConfig):
        self.connection_pool = create_connection_pool(db_config)
        self.table_name = db_config.cache_table
        self.compression_enabled = db_config.compression
        
    async def get(self, key: str) -> Optional[Any]
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool
    async def delete(self, key: str) -> bool
    async def cleanup_expired(self) -> int
    async def get_size(self) -> int
```

## Usage Examples

### Basic Cache Operations

```python
import asyncio
from nautilus_trader_engine.core.caching import CacheManager, CacheConfig

async def basic_caching_example():
    # Initialize cache manager
    config = CacheConfig(
        l1_config={
            'max_size': 10000,
            'ttl_seconds': 300
        },
        l2_config={
            'redis_url': 'redis://localhost:6379',
            'max_connections': 20,
            'compression': True
        },
        l3_config={
            'database_url': 'postgresql://localhost/nautilus',
            'cache_table': 'cache_entries',
            'compression': True
        }
    )
    
    cache = CacheManager(config)
    await cache.start()
    
    # Basic set/get operations
    await cache.set('market_data:AAPL', {
        'symbol': 'AAPL',
        'price': 150.25,
        'volume': 1000000,
        'timestamp': time.time()
    }, ttl=60)
    
    # Retrieve from cache (will check L1 -> L2 -> L3)
    data = await cache.get('market_data:AAPL')
    print(f"Retrieved: {data}")
    
    # Check if key exists
    exists = await cache.exists('market_data:AAPL')
    print(f"Key exists: {exists}")
    
    # Delete from all cache tiers
    deleted = await cache.delete('market_data:AAPL')
    print(f"Deleted: {deleted}")
    
    await cache.stop()

# Run example
asyncio.run(basic_caching_example())
```

### High-Frequency Market Data Caching

```python
async def market_data_caching_example():
    cache = CacheManager(CacheConfig.for_market_data())
    await cache.start()
    
    # Cache market data with different TTLs
    market_data_types = {
        'level1': 1,      # 1 second TTL for Level 1 data
        'level2': 5,      # 5 seconds TTL for Level 2 data
        'trades': 10,     # 10 seconds TTL for trade data
        'analytics': 60   # 1 minute TTL for analytics
    }
    
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']
    
    # Simulate high-frequency data updates
    for i in range(10000):
        for symbol in symbols:
            for data_type, ttl in market_data_types.items():
                key = f"market:{data_type}:{symbol}"
                value = {
                    'symbol': symbol,
                    'type': data_type,
                    'sequence': i,
                    'price': 100 + (i * 0.01),
                    'timestamp': time.time_ns()
                }
                
                # Use write-through for critical data
                if data_type in ['level1', 'trades']:
                    await cache.set(key, value, ttl=ttl, write_policy='write_through')
                else:
                    await cache.set(key, value, ttl=ttl, write_policy='write_back')
    
    # Get cache performance metrics
    metrics = cache.get_metrics()
    print(f"L1 hit rate: {metrics['l1_hit_rate']:.2%}")
    print(f"L2 hit rate: {metrics['l2_hit_rate']:.2%}")
    print(f"L3 hit rate: {metrics['l3_hit_rate']:.2%}")
    print(f"Overall hit rate: {metrics['overall_hit_rate']:.2%}")
    print(f"Average get latency: {metrics['avg_get_latency_us']:.2f}μs")
    
    await cache.stop()
```

### Cache Warming and Prefetching

```python
async def cache_warming_example():
    cache = CacheManager(CacheConfig.with_prefetching())
    await cache.start()
    
    # Define cache warming strategy
    warming_strategy = {
        'market_data': {
            'symbols': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN'],
            'data_types': ['level1', 'level2', 'trades'],
            'prefetch_window': 300  # 5 minutes
        },
        'reference_data': {
            'types': ['instruments', 'exchanges', 'holidays'],
            'refresh_interval': 3600  # 1 hour
        }
    }
    
    # Warm up market data cache
    async def warm_market_data():
        for symbol in warming_strategy['market_data']['symbols']:
            for data_type in warming_strategy['market_data']['data_types']:
                key = f"market:{data_type}:{symbol}"
                
                # Simulate fetching from data source
                data = await fetch_market_data(symbol, data_type)
                await cache.set(key, data, ttl=300)
                
                print(f"Warmed cache for {key}")
    
    # Warm up reference data cache
    async def warm_reference_data():
        for ref_type in warming_strategy['reference_data']['types']:
            key = f"reference:{ref_type}"
            
            # Simulate fetching from database
            data = await fetch_reference_data(ref_type)
            await cache.set(key, data, ttl=3600)
            
            print(f"Warmed cache for {key}")
    
    # Execute cache warming
    await asyncio.gather(
        warm_market_data(),
        warm_reference_data()
    )
    
    # Enable predictive prefetching
    cache.enable_prefetching(
        prediction_model='access_pattern',
        prefetch_threshold=0.7,
        max_prefetch_items=1000
    )
    
    # Simulate access patterns that will trigger prefetching
    access_patterns = [
        'market:level1:AAPL',
        'market:level1:MSFT',
        'market:level2:AAPL',  # This might trigger prefetch of MSFT level2
        'market:trades:AAPL'
    ]
    
    for pattern in access_patterns:
        data = await cache.get(pattern)
        print(f"Accessed: {pattern}")
    
    # Check prefetching statistics
    prefetch_stats = cache.get_prefetch_stats()
    print(f"Prefetch hits: {prefetch_stats['hits']}")
    print(f"Prefetch accuracy: {prefetch_stats['accuracy']:.2%}")
    
    await cache.stop()
```

### Cache Invalidation and Coherency

```python
async def cache_invalidation_example():
    cache = CacheManager(CacheConfig.with_coherency())
    await cache.start()
    
    # Set up cache invalidation listeners
    async def price_update_handler(event):
        symbol = event['symbol']
        # Invalidate all price-related cache entries
        await cache.invalidate_pattern(f"market:*:{symbol}")
        await cache.invalidate_pattern(f"analytics:*:{symbol}")
        print(f"Invalidated cache for {symbol} price update")
    
    async def reference_data_handler(event):
        data_type = event['type']
        # Invalidate reference data cache
        await cache.invalidate_pattern(f"reference:{data_type}:*")
        print(f"Invalidated {data_type} reference data cache")
    
    # Register invalidation handlers
    cache.add_invalidation_handler('price_update', price_update_handler)
    cache.add_invalidation_handler('reference_update', reference_data_handler)
    
    # Cache some data
    await cache.set('market:level1:AAPL', {'price': 150.25}, ttl=300)
    await cache.set('market:level2:AAPL', {'bid': 150.20, 'ask': 150.30}, ttl=300)
    await cache.set('analytics:sma:AAPL', {'sma_20': 148.50}, ttl=600)
    await cache.set('reference:instrument:AAPL', {'name': 'Apple Inc.'}, ttl=3600)
    
    # Simulate price update event
    await cache.publish_event('price_update', {'symbol': 'AAPL', 'new_price': 151.00})
    
    # Verify cache invalidation
    level1_data = await cache.get('market:level1:AAPL')
    print(f"Level1 data after invalidation: {level1_data}")  # Should be None
    
    # Test cascade invalidation
    await cache.set('portfolio:positions:user123', {'AAPL': 100}, ttl=300)
    await cache.set('portfolio:value:user123', {'total': 15025}, ttl=300)
    
    # Set up cascade invalidation rule
    cache.add_cascade_rule(
        trigger_pattern='portfolio:positions:*',
        cascade_patterns=['portfolio:value:*', 'portfolio:analytics:*']
    )
    
    # Update position (should cascade to value and analytics)
    await cache.delete('portfolio:positions:user123')
    
    # Check cascade effect
    portfolio_value = await cache.get('portfolio:value:user123')
    print(f"Portfolio value after cascade: {portfolio_value}")  # Should be None
    
    await cache.stop()
```

### Performance Monitoring and Optimization

```python
async def performance_monitoring_example():
    cache = CacheManager(CacheConfig.with_monitoring())
    await cache.start()
    
    # Enable detailed performance monitoring
    cache.enable_detailed_monitoring(
        sample_rate=0.1,  # Sample 10% of operations
        track_access_patterns=True,
        track_memory_usage=True
    )
    
    # Simulate various cache operations
    operations = [
        ('set', 'test:key:1', {'data': 'value1'}),
        ('set', 'test:key:2', {'data': 'value2'}),
        ('get', 'test:key:1', None),
        ('get', 'test:key:2', None),
        ('get', 'test:key:3', None),  # Cache miss
        ('delete', 'test:key:1', None),
        ('get', 'test:key:1', None),  # Cache miss after delete
    ]
    
    for op_type, key, value in operations:
        if op_type == 'set':
            await cache.set(key, value)
        elif op_type == 'get':
            result = await cache.get(key)
        elif op_type == 'delete':
            await cache.delete(key)
    
    # Get comprehensive performance metrics
    metrics = cache.get_detailed_metrics()
    
    print("=== Cache Performance Metrics ===")
    print(f"Total operations: {metrics['total_operations']}")
    print(f"Hit rate: {metrics['hit_rate']:.2%}")
    print(f"Miss rate: {metrics['miss_rate']:.2%}")
    
    print("\\n=== Latency Metrics ===")
    print(f"Average get latency: {metrics['avg_get_latency_us']:.2f}μs")
    print(f"P95 get latency: {metrics['p95_get_latency_us']:.2f}μs")
    print(f"P99 get latency: {metrics['p99_get_latency_us']:.2f}μs")
    
    print("\\n=== Memory Usage ===")
    print(f"L1 memory usage: {metrics['l1_memory_mb']:.1f}MB")
    print(f"L2 memory usage: {metrics['l2_memory_mb']:.1f}MB")
    print(f"Total memory usage: {metrics['total_memory_mb']:.1f}MB")
    
    print("\\n=== Cache Tier Performance ===")
    for tier in ['l1', 'l2', 'l3']:
        tier_metrics = metrics[f'{tier}_metrics']
        print(f"{tier.upper()} - Hit Rate: {tier_metrics['hit_rate']:.2%}, "
              f"Avg Latency: {tier_metrics['avg_latency_us']:.2f}μs")
    
    # Generate optimization recommendations
    recommendations = cache.get_optimization_recommendations()
    print("\\n=== Optimization Recommendations ===")
    for rec in recommendations:
        print(f"- {rec['type']}: {rec['description']}")
        print(f"  Expected improvement: {rec['expected_improvement']}")
    
    # Apply automatic optimizations
    if recommendations:
        await cache.apply_optimizations(recommendations[:3])  # Apply top 3
        print("Applied optimization recommendations")
    
    await cache.stop()
```

### Distributed Cache Coherency

```python
async def distributed_coherency_example():
    # Set up multiple cache instances (simulating different servers)
    cache_configs = [
        CacheConfig.for_instance('server1', redis_cluster=['redis1:6379']),
        CacheConfig.for_instance('server2', redis_cluster=['redis2:6379']),
        CacheConfig.for_instance('server3', redis_cluster=['redis3:6379'])
    ]
    
    caches = [CacheManager(config) for config in cache_configs]
    
    # Start all cache instances
    await asyncio.gather(*[cache.start() for cache in caches])
    
    # Enable distributed coherency
    coherency_manager = DistributedCoherencyManager(caches)
    await coherency_manager.start()
    
    # Set data on first cache instance
    await caches[0].set('shared:data:key1', {'value': 'initial', 'version': 1})
    
    # Verify data is available on all instances
    for i, cache in enumerate(caches):
        data = await cache.get('shared:data:key1')
        print(f"Cache {i}: {data}")
    
    # Update data on second cache instance
    await caches[1].set('shared:data:key1', {'value': 'updated', 'version': 2})
    
    # Wait for coherency propagation
    await asyncio.sleep(0.1)
    
    # Verify all caches have updated data
    for i, cache in enumerate(caches):
        data = await cache.get('shared:data:key1')
        print(f"Cache {i} after update: {data}")
    
    # Test conflict resolution
    # Simulate concurrent updates
    await asyncio.gather(
        caches[0].set('shared:data:key2', {'value': 'from_cache0', 'timestamp': time.time()}),
        caches[1].set('shared:data:key2', {'value': 'from_cache1', 'timestamp': time.time() + 0.001}),
        caches[2].set('shared:data:key2', {'value': 'from_cache2', 'timestamp': time.time() + 0.002})
    )
    
    # Wait for conflict resolution (last-write-wins by default)
    await asyncio.sleep(0.2)
    
    # Check final resolved value
    for i, cache in enumerate(caches):
        data = await cache.get('shared:data:key2')
        print(f"Cache {i} after conflict resolution: {data}")
    
    # Get coherency statistics
    coherency_stats = coherency_manager.get_stats()
    print(f"\\nCoherency events: {coherency_stats['events_processed']}")
    print(f"Conflicts resolved: {coherency_stats['conflicts_resolved']}")
    print(f"Propagation latency: {coherency_stats['avg_propagation_latency_ms']:.2f}ms")
    
    # Cleanup
    await coherency_manager.stop()
    await asyncio.gather(*[cache.stop() for cache in caches])
```

## Advanced Features

### Custom Cache Policies

```python
from nautilus_trader_engine.core.caching import CustomCachePolicy

class TradingDataCachePolicy(CustomCachePolicy):
    def should_cache(self, key: str, value: Any) -> bool:
        # Only cache trading-related data
        return key.startswith(('market:', 'orders:', 'positions:'))
    
    def get_ttl(self, key: str, value: Any) -> int:
        # Different TTLs based on data type
        if 'level1' in key:
            return 1  # 1 second for Level 1 data
        elif 'level2' in key:
            return 5  # 5 seconds for Level 2 data
        elif 'reference' in key:
            return 3600  # 1 hour for reference data
        else:
            return 300  # 5 minutes default
    
    def should_evict(self, key: str, value: Any, access_time: float) -> bool:
        # Custom eviction logic
        age = time.time() - access_time
        if 'critical' in key:
            return age > 3600  # Keep critical data longer
        else:
            return age > 300   # Standard eviction

# Use custom policy
cache = CacheManager(CacheConfig.with_custom_policy(TradingDataCachePolicy()))
```

### Cache Compression

```python
async def compression_example():
    cache = CacheManager(CacheConfig.with_compression({
        'algorithm': 'lz4',  # Fast compression
        'level': 1,
        'min_size': 1024,  # Only compress data > 1KB
        'types': ['json', 'pickle']  # Compress specific data types
    }))
    
    await cache.start()
    
    # Large data that will benefit from compression
    large_market_data = {
        'symbol': 'AAPL',
        'orderbook': [
            {'price': 150.00 + (i * 0.01), 'size': 100 * (i + 1)}
            for i in range(1000)
        ],
        'trades': [
            {'price': 150.25, 'size': 100, 'timestamp': time.time() - i}
            for i in range(5000)
        ]
    }
    
    # Cache will automatically compress this data
    await cache.set('market:detailed:AAPL', large_market_data)
    
    # Retrieval will automatically decompress
    retrieved_data = await cache.get('market:detailed:AAPL')
    
    # Check compression statistics
    compression_stats = cache.get_compression_stats()
    print(f"Compression ratio: {compression_stats['ratio']:.2f}")
    print(f"Space saved: {compression_stats['bytes_saved']} bytes")
    print(f"Compression time: {compression_stats['avg_compression_time_us']:.2f}μs")
    print(f"Decompression time: {compression_stats['avg_decompression_time_us']:.2f}μs")
    
    await cache.stop()
```

### Cache Partitioning and Sharding

```python
async def partitioning_example():
    # Set up partitioned cache
    partition_config = {
        'strategy': 'consistent_hash',
        'partitions': 8,
        'replication_factor': 2,
        'partition_key_extractor': lambda key: key.split(':')[1] if ':' in key else key
    }
    
    cache = CacheManager(CacheConfig.with_partitioning(partition_config))
    await cache.start()
    
    # Data will be automatically partitioned based on key
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN', 'META', 'NFLX', 'NVDA']
    
    for symbol in symbols:
        await cache.set(f'market:price:{symbol}', {
            'symbol': symbol,
            'price': 100 + hash(symbol) % 100,
            'timestamp': time.time()
        })
    
    # Check partition distribution
    partition_stats = cache.get_partition_stats()
    for partition_id, stats in partition_stats.items():
        print(f"Partition {partition_id}: {stats['key_count']} keys, "
              f"{stats['memory_usage_mb']:.1f}MB")
    
    # Test partition failover
    await cache.simulate_partition_failure(partition_id=3)
    
    # Data should still be accessible due to replication
    for symbol in symbols:
        data = await cache.get(f'market:price:{symbol}')
        if data:
            print(f"{symbol}: Available (possibly from replica)")
        else:
            print(f"{symbol}: Unavailable")
    
    await cache.stop()
```

## Integration Examples

### Integration with Market Data Feed

```python
from nautilus_trader_engine.market_data import MarketDataFeed

async def market_data_integration():
    cache = CacheManager(CacheConfig.for_market_data())
    market_feed = MarketDataFeed(cache=cache)
    
    await cache.start()
    await market_feed.start()
    
    # Market data feed will automatically cache incoming data
    async def price_handler(symbol, price_data):
        # Data is automatically cached by the feed
        cached_data = await cache.get(f'market:level1:{symbol}')
        print(f"Cached price for {symbol}: {cached_data}")
    
    market_feed.subscribe('AAPL', price_handler)
    
    # Simulate market data updates
    await market_feed.publish_price('AAPL', {
        'bid': 150.20,
        'ask': 150.25,
        'last': 150.22,
        'volume': 1000000
    })
    
    await asyncio.sleep(1)
    await market_feed.stop()
    await cache.stop()
```

### Integration with Order Management

```python
from nautilus_trader_engine.trading import OrderManager

async def order_management_integration():
    cache = CacheManager(CacheConfig.for_orders())
    order_manager = OrderManager(cache=cache)
    
    await cache.start()
    await order_manager.start()
    
    # Orders are automatically cached for fast retrieval
    order = await order_manager.create_order(
        symbol='AAPL',
        side='BUY',
        quantity=100,
        price=150.25
    )
    
    # Order is now in cache
    cached_order = await cache.get(f'orders:{order.id}')
    print(f"Cached order: {cached_order}")
    
    # Update order (cache is automatically updated)
    await order_manager.modify_order(order.id, price=150.30)
    
    # Check updated cache
    updated_order = await cache.get(f'orders:{order.id}')
    print(f"Updated cached order: {updated_order}")
    
    await order_manager.stop()
    await cache.stop()
```

## Best Practices

### Cache Key Design
1. **Hierarchical Structure**: Use consistent naming patterns (e.g., "market:level1:AAPL")
2. **Avoid Long Keys**: Keep keys under 250 characters for optimal performance
3. **Use Prefixes**: Group related data with common prefixes for batch operations
4. **Include Versions**: Add version numbers for schema evolution

### TTL Management
1. **Data Freshness**: Set TTLs based on data update frequency
2. **Business Logic**: Align TTLs with business requirements
3. **Cascade TTLs**: Use shorter TTLs for derived data
4. **Monitor Expiration**: Track TTL effectiveness and adjust as needed

### Memory Management
1. **Size Limits**: Set appropriate cache size limits for each tier
2. **Eviction Policies**: Choose eviction policies based on access patterns
3. **Compression**: Use compression for large or infrequently accessed data
4. **Monitoring**: Continuously monitor memory usage and performance

### Performance Optimization
1. **Batch Operations**: Group related cache operations when possible
2. **Async Operations**: Use async/await for non-blocking cache access
3. **Connection Pooling**: Configure appropriate connection pool sizes
4. **Monitoring**: Use performance metrics to identify bottlenecks

## Troubleshooting

### Common Issues

```python
# Check cache health
health_status = cache.get_health_status()
if not health_status['healthy']:
    print(f"Cache issues: {health_status['issues']}")
    
    # Common fixes
    if 'memory_pressure' in health_status['issues']:
        # Trigger cleanup
        await cache.cleanup_expired()
        await cache.force_eviction(target_utilization=0.8)
    
    if 'high_latency' in health_status['issues']:
        # Check connection pool
        await cache.refresh_connections()
    
    if 'coherency_lag' in health_status['issues']:
        # Check distributed coherency
        await cache.sync_coherency()
```

### Performance Debugging

```python
# Enable debug mode
cache.set_debug_mode(True)

# Trace cache operations
tracer = cache.get_operation_tracer()
tracer.start()

# Perform operations
await cache.get('test:key')
await cache.set('test:key', 'value')

# Analyze trace
trace_data = tracer.get_trace()
for operation in trace_data:
    print(f"Operation: {operation['type']}, "
          f"Latency: {operation['latency_us']}μs, "
          f"Cache Tier: {operation['tier']}")

tracer.stop()
```

## Conclusion

The Advanced Caching System provides a comprehensive, high-performance caching solution for trading applications. Its multi-tier architecture, intelligent cache policies, and distributed coherency mechanisms ensure optimal performance while maintaining data consistency. The extensive monitoring and optimization features make it suitable for production use in demanding financial environments.

For optimal performance, carefully consider cache key design, TTL settings, and memory management based on your specific access patterns and performance requirements.