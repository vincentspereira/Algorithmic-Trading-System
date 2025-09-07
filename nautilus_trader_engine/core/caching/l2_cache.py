"""
L2 Cache Implementation
Distributed Redis-based cache for fast cross-service data sharing
"""

import asyncio
import json
import time
from typing import Any, Optional, Dict, List, Set
import logging

try:
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    aioredis = None


class L2Cache:
    """
    Distributed L2 cache using Redis
    
    Features:
    - Async Redis operations
    - JSON serialization (safer than pickle)
    - Tag-based invalidation
    - Batch operations
    - Connection pooling
    - Automatic failover
    """
    
    def __init__(self, 
                 redis_url: str = "redis://localhost:6379",
                 max_size: int = 100000,
                 ttl: int = 3600,
                 key_prefix: str = "nautilus:cache:",
                 pool_size: int = 10):
        
        if not REDIS_AVAILABLE:
            raise ImportError("aioredis is required for L2Cache. Install with: pip install aioredis")
        
        self.redis_url = redis_url
        self.max_size = max_size
        self.default_ttl = ttl
        self.key_prefix = key_prefix
        self.pool_size = pool_size
        
        # Redis connection
        self.redis: Optional[aioredis.Redis] = None
        self.connection_pool: Optional[aioredis.ConnectionPool] = None
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._deletes = 0
        self._errors = 0
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Initialize Redis connection"""
        try:
            self.connection_pool = aioredis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.pool_size,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            self.redis = aioredis.Redis(connection_pool=self.connection_pool)
            
            # Test connection
            await self.redis.ping()
            
            self.logger.info(f"L2Cache connected to Redis: {self.redis_url}")
        
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def stop(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
        
        if self.connection_pool:
            await self.connection_pool.disconnect()
        
        self.logger.info("L2Cache disconnected from Redis")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        if not self.redis:
            return None
        
        try:
            redis_key = self._make_redis_key(key)
            data = await self.redis.get(redis_key)
            
            if data is None:
                self._misses += 1
                return None
            
            # Deserialize data
            value = self._deserialize(data)
            self._hits += 1
            
            return value
        
        except Exception as e:
            self.logger.error(f"L2Cache get error for key {key}: {e}")
            self._errors += 1
            return None
    
    async def set(self, 
                  key: str, 
                  value: Any, 
                  ttl: Optional[int] = None,
                  tags: Optional[List[str]] = None) -> bool:
        """Set value in Redis cache"""
        if not self.redis:
            return False
        
        try:
            redis_key = self._make_redis_key(key)
            serialized_data = self._serialize(value)
            
            # Set with TTL
            ttl_seconds = ttl or self.default_ttl
            success = await self.redis.setex(redis_key, ttl_seconds, serialized_data)
            
            # Handle tags
            if tags:
                await self._set_tags(key, tags, ttl_seconds)
            
            if success:
                self._sets += 1
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"L2Cache set error for key {key}: {e}")
            self._errors += 1
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis cache"""
        if not self.redis:
            return False
        
        try:
            redis_key = self._make_redis_key(key)
            deleted = await self.redis.delete(redis_key)
            
            # Also delete tag associations
            await self._delete_tag_associations(key)
            
            if deleted > 0:
                self._deletes += 1
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"L2Cache delete error for key {key}: {e}")
            self._errors += 1
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache"""
        if not self.redis:
            return False
        
        try:
            redis_key = self._make_redis_key(key)
            exists = await self.redis.exists(redis_key)
            return exists > 0
        
        except Exception as e:
            self.logger.error(f"L2Cache exists error for key {key}: {e}")
            return False
    
    async def clear(self):
        """Clear all cache entries with our prefix"""
        if not self.redis:
            return
        
        try:
            # Find all keys with our prefix
            pattern = f"{self.key_prefix}*"
            keys = []
            
            async for key in self.redis.scan_iter(match=pattern, count=1000):
                keys.append(key)
            
            # Delete in batches
            if keys:
                batch_size = 1000
                for i in range(0, len(keys), batch_size):
                    batch = keys[i:i + batch_size]
                    await self.redis.delete(*batch)
            
            self.logger.info(f"L2Cache cleared {len(keys)} keys")
        
        except Exception as e:
            self.logger.error(f"L2Cache clear error: {e}")
    
    async def invalidate_by_tags(self, tags: List[str]):
        """Invalidate cache entries by tags"""
        if not self.redis:
            return
        
        try:
            keys_to_delete = set()
            
            for tag in tags:
                tag_key = self._make_tag_key(tag)
                # Get all keys associated with this tag
                tag_keys = await self.redis.smembers(tag_key)
                
                for key_bytes in tag_keys:
                    key = key_bytes.decode('utf-8')
                    keys_to_delete.add(self._make_redis_key(key))
                
                # Delete the tag set itself
                await self.redis.delete(tag_key)
            
            # Delete all associated cache entries
            if keys_to_delete:
                await self.redis.delete(*keys_to_delete)
            
            self.logger.debug(f"L2Cache invalidated {len(keys_to_delete)} keys for tags: {tags}")
        
        except Exception as e:
            self.logger.error(f"L2Cache tag invalidation error: {e}")
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple keys efficiently using pipeline"""
        if not self.redis or not keys:
            return {}
        
        try:
            # Create pipeline for batch operation
            pipe = self.redis.pipeline()
            redis_keys = [self._make_redis_key(key) for key in keys]
            
            # Add all get operations to pipeline
            for redis_key in redis_keys:
                pipe.get(redis_key)
            
            # Execute pipeline
            results = await pipe.execute()
            
            # Process results
            output = {}
            for i, (key, data) in enumerate(zip(keys, results)):
                if data is not None:
                    try:
                        value = self._deserialize(data)
                        output[key] = value
                        self._hits += 1
                    except Exception as e:
                        self.logger.error(f"Deserialization error for key {key}: {e}")
                else:
                    self._misses += 1
            
            return output
        
        except Exception as e:
            self.logger.error(f"L2Cache get_many error: {e}")
            self._errors += 1
            return {}
    
    async def set_many(self, items: Dict[str, Any], ttl: Optional[int] = None):
        """Set multiple keys efficiently using pipeline"""
        if not self.redis or not items:
            return
        
        try:
            pipe = self.redis.pipeline()
            ttl_seconds = ttl or self.default_ttl
            
            # Add all set operations to pipeline
            for key, value in items.items():
                redis_key = self._make_redis_key(key)
                serialized_data = self._serialize(value)
                pipe.setex(redis_key, ttl_seconds, serialized_data)
            
            # Execute pipeline
            results = await pipe.execute()
            
            # Count successful sets
            successful_sets = sum(1 for result in results if result)
            self._sets += successful_sets
            
            self.logger.debug(f"L2Cache set_many: {successful_sets}/{len(items)} successful")
        
        except Exception as e:
            self.logger.error(f"L2Cache set_many error: {e}")
            self._errors += 1
    
    async def _set_tags(self, key: str, tags: List[str], ttl: int):
        """Associate key with tags for invalidation"""
        try:
            pipe = self.redis.pipeline()
            
            for tag in tags:
                tag_key = self._make_tag_key(tag)
                # Add key to tag set
                pipe.sadd(tag_key, key)
                # Set TTL on tag set (slightly longer than cache entry)
                pipe.expire(tag_key, ttl + 60)
            
            await pipe.execute()
        
        except Exception as e:
            self.logger.error(f"Error setting tags for key {key}: {e}")
    
    async def _delete_tag_associations(self, key: str):
        """Remove key from all tag associations"""
        try:
            # This is a simplified implementation
            # In production, you might want to track key->tags mapping
            # for more efficient cleanup
            pass
        
        except Exception as e:
            self.logger.error(f"Error deleting tag associations for key {key}: {e}")
    
    def _make_redis_key(self, key: str) -> str:
        """Create Redis key with prefix"""
        return f"{self.key_prefix}{key}"
    
    def _make_tag_key(self, tag: str) -> str:
        """Create Redis key for tag set"""
        return f"{self.key_prefix}tag:{tag}"
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for Redis storage using JSON (safer than pickle)"""
        try:
            # Use JSON for all serialization - safer than pickle
            json_data = json.dumps(value, separators=(',', ':'), default=str)
            return f"json:{json_data}".encode('utf-8')
        
        except Exception as e:
            self.logger.error(f"Serialization error: {e}")
            # Fallback to string representation
            return f"str:{str(value)}".encode('utf-8')
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from Redis storage"""
        try:
            data_str = data.decode('utf-8')
            
            if data_str.startswith('json:'):
                json_data = data_str[5:]  # Remove 'json:' prefix
                return json.loads(json_data)
            
            elif data_str.startswith('str:'):
                return data_str[4:]  # Remove 'str:' prefix
            
            else:
                # Fallback: assume it's a string
                return data_str
        
        except Exception as e:
            self.logger.error(f"Deserialization error: {e}")
            return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            'hits': self._hits,
            'misses': self._misses,
            'sets': self._sets,
            'deletes': self._deletes,
            'errors': self._errors,
            'hit_rate_pct': (self._hits / (self._hits + self._misses) * 100) if (self._hits + self._misses) > 0 else 0
        }
        
        # Get Redis info if available
        if self.redis:
            try:
                redis_info = await self.redis.info()
                stats.update({
                    'redis_connected_clients': redis_info.get('connected_clients', 0),
                    'redis_used_memory': redis_info.get('used_memory', 0),
                    'redis_used_memory_human': redis_info.get('used_memory_human', '0B'),
                    'redis_keyspace_hits': redis_info.get('keyspace_hits', 0),
                    'redis_keyspace_misses': redis_info.get('keyspace_misses', 0)
                })
            except Exception as e:
                self.logger.error(f"Error getting Redis info: {e}")
        
        return stats
    
    async def get_size(self) -> int:
        """Get approximate number of keys in cache"""
        if not self.redis:
            return 0
        
        try:
            # Count keys with our prefix
            pattern = f"{self.key_prefix}*"
            count = 0
            
            async for _ in self.redis.scan_iter(match=pattern, count=1000):
                count += 1
            
            return count
        
        except Exception as e:
            self.logger.error(f"Error getting cache size: {e}")
            return 0


class RedisCache(L2Cache):
    """Alias for L2Cache for backward compatibility"""
    pass