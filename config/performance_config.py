"""Performance optimization configuration for the algorithmic trading system.

This module provides comprehensive performance optimization settings including:
- Caching strategies (Redis, in-memory, distributed)
- Connection pooling for databases and external services
- Rate limiting and throttling
- Memory management and garbage collection tuning
- Async/await optimization
"""

import asyncio
import logging
from datetime import timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseSettings, Field, validator
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class CacheStrategy(str, Enum):
    """Available caching strategies."""
    REDIS = "redis"
    MEMORY = "memory"
    DISTRIBUTED = "distributed"
    HYBRID = "hybrid"
    NONE = "none"

class PoolStrategy(str, Enum):
    """Connection pool strategies."""
    FIXED = "fixed"
    DYNAMIC = "dynamic"
    ADAPTIVE = "adaptive"

class RateLimitStrategy(str, Enum):
    """Rate limiting strategies."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"

@dataclass
class CacheConfig:
    """Cache configuration settings."""
    strategy: CacheStrategy = CacheStrategy.REDIS
    ttl_seconds: int = 3600
    max_size: int = 10000
    eviction_policy: str = "lru"
    compression: bool = True
    serialization: str = "pickle"
    
    # Redis-specific settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_ssl: bool = False
    redis_cluster: bool = False
    redis_sentinel: bool = False
    
    # Memory cache settings
    memory_max_size: int = 1000
    memory_ttl: int = 300
    
    # Distributed cache settings
    distributed_nodes: List[str] = None
    consistency_level: str = "eventual"

@dataclass
class ConnectionPoolConfig:
    """Connection pool configuration."""
    strategy: PoolStrategy = PoolStrategy.ADAPTIVE
    min_connections: int = 5
    max_connections: int = 50
    connection_timeout: int = 30
    idle_timeout: int = 300
    max_lifetime: int = 3600
    health_check_interval: int = 60
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Database-specific pools
    postgres_pool_size: int = 20
    clickhouse_pool_size: int = 15
    redis_pool_size: int = 10
    
    # External service pools
    http_pool_size: int = 100
    websocket_pool_size: int = 50
    grpc_pool_size: int = 25

@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    requests_per_second: int = 100
    burst_size: int = 200
    window_size: int = 60
    
    # Per-service rate limits
    api_rate_limit: int = 1000  # requests per minute
    trading_rate_limit: int = 100  # orders per minute
    data_feed_rate_limit: int = 10000  # messages per second
    websocket_rate_limit: int = 500  # messages per second
    
    # Per-user rate limits
    user_api_limit: int = 100  # requests per minute
    user_trading_limit: int = 10  # orders per minute
    
    # Throttling settings
    enable_throttling: bool = True
    throttle_threshold: float = 0.8  # Throttle at 80% capacity
    throttle_delay: float = 0.1  # 100ms delay

@dataclass
class MemoryConfig:
    """Memory management configuration."""
    gc_threshold: int = 1000000  # Objects before GC
    gc_frequency: int = 60  # Seconds between forced GC
    max_memory_usage: int = 8 * 1024 * 1024 * 1024  # 8GB
    memory_warning_threshold: float = 0.8  # 80%
    
    # Object pooling
    enable_object_pooling: bool = True
    pool_sizes: Dict[str, int] = None
    
    # Memory profiling
    enable_profiling: bool = False
    profiling_interval: int = 300  # 5 minutes

@dataclass
class AsyncConfig:
    """Async/await optimization configuration."""
    event_loop_policy: str = "uvloop"  # uvloop, asyncio
    max_workers: int = 100
    thread_pool_size: int = 50
    process_pool_size: int = 4
    
    # Coroutine settings
    max_concurrent_tasks: int = 1000
    task_timeout: int = 300
    semaphore_limit: int = 100
    
    # I/O optimization
    buffer_size: int = 65536  # 64KB
    read_timeout: int = 30
    write_timeout: int = 30
    connect_timeout: int = 10

class PerformanceSettings(BaseSettings):
    """Performance optimization settings."""
    
    # Enable/disable performance features
    enable_caching: bool = Field(True, env="ENABLE_CACHING")
    enable_connection_pooling: bool = Field(True, env="ENABLE_CONNECTION_POOLING")
    enable_rate_limiting: bool = Field(True, env="ENABLE_RATE_LIMITING")
    enable_memory_optimization: bool = Field(True, env="ENABLE_MEMORY_OPTIMIZATION")
    enable_async_optimization: bool = Field(True, env="ENABLE_ASYNC_OPTIMIZATION")
    
    # Performance monitoring
    enable_performance_monitoring: bool = Field(True, env="ENABLE_PERFORMANCE_MONITORING")
    performance_log_level: str = Field("INFO", env="PERFORMANCE_LOG_LEVEL")
    metrics_collection_interval: int = Field(60, env="METRICS_COLLECTION_INTERVAL")
    
    # Cache settings
    cache_strategy: CacheStrategy = Field(CacheStrategy.REDIS, env="CACHE_STRATEGY")
    cache_ttl: int = Field(3600, env="CACHE_TTL")
    cache_max_size: int = Field(10000, env="CACHE_MAX_SIZE")
    
    # Redis cache settings
    redis_cache_host: str = Field("localhost", env="REDIS_CACHE_HOST")
    redis_cache_port: int = Field(6379, env="REDIS_CACHE_PORT")
    redis_cache_db: int = Field(1, env="REDIS_CACHE_DB")
    redis_cache_password: Optional[str] = Field(None, env="REDIS_CACHE_PASSWORD")
    
    # Connection pool settings
    pool_strategy: PoolStrategy = Field(PoolStrategy.ADAPTIVE, env="POOL_STRATEGY")
    min_connections: int = Field(5, env="MIN_CONNECTIONS")
    max_connections: int = Field(50, env="MAX_CONNECTIONS")
    connection_timeout: int = Field(30, env="CONNECTION_TIMEOUT")
    
    # Rate limiting settings
    rate_limit_strategy: RateLimitStrategy = Field(RateLimitStrategy.TOKEN_BUCKET, env="RATE_LIMIT_STRATEGY")
    api_rate_limit: int = Field(1000, env="API_RATE_LIMIT")
    trading_rate_limit: int = Field(100, env="TRADING_RATE_LIMIT")
    
    # Memory settings
    max_memory_usage: int = Field(8 * 1024 * 1024 * 1024, env="MAX_MEMORY_USAGE")
    gc_threshold: int = Field(1000000, env="GC_THRESHOLD")
    
    # Async settings
    event_loop_policy: str = Field("uvloop", env="EVENT_LOOP_POLICY")
    max_workers: int = Field(100, env="MAX_WORKERS")
    max_concurrent_tasks: int = Field(1000, env="MAX_CONCURRENT_TASKS")
    
    @validator('cache_strategy')
    def validate_cache_strategy(cls, v):
        if isinstance(v, str):
            return CacheStrategy(v)
        return v
    
    @validator('pool_strategy')
    def validate_pool_strategy(cls, v):
        if isinstance(v, str):
            return PoolStrategy(v)
        return v
    
    @validator('rate_limit_strategy')
    def validate_rate_limit_strategy(cls, v):
        if isinstance(v, str):
            return RateLimitStrategy(v)
        return v
    
    class Config:
        env_file = ".env"
        extra = "allow"

class PerformanceManager:
    """Manages performance optimization configurations and provides utilities."""
    
    def __init__(self, settings: Optional[PerformanceSettings] = None):
        self.settings = settings or PerformanceSettings()
        self.cache_config = self._create_cache_config()
        self.pool_config = self._create_pool_config()
        self.rate_limit_config = self._create_rate_limit_config()
        self.memory_config = self._create_memory_config()
        self.async_config = self._create_async_config()
        
        logger.info(f"Performance manager initialized with strategy: {self.settings.cache_strategy}")
    
    def _create_cache_config(self) -> CacheConfig:
        """Create cache configuration from settings."""
        return CacheConfig(
            strategy=self.settings.cache_strategy,
            ttl_seconds=self.settings.cache_ttl,
            max_size=self.settings.cache_max_size,
            redis_host=self.settings.redis_cache_host,
            redis_port=self.settings.redis_cache_port,
            redis_db=self.settings.redis_cache_db,
            redis_password=self.settings.redis_cache_password,
        )
    
    def _create_pool_config(self) -> ConnectionPoolConfig:
        """Create connection pool configuration from settings."""
        return ConnectionPoolConfig(
            strategy=self.settings.pool_strategy,
            min_connections=self.settings.min_connections,
            max_connections=self.settings.max_connections,
            connection_timeout=self.settings.connection_timeout,
        )
    
    def _create_rate_limit_config(self) -> RateLimitConfig:
        """Create rate limit configuration from settings."""
        return RateLimitConfig(
            strategy=self.settings.rate_limit_strategy,
            api_rate_limit=self.settings.api_rate_limit,
            trading_rate_limit=self.settings.trading_rate_limit,
        )
    
    def _create_memory_config(self) -> MemoryConfig:
        """Create memory configuration from settings."""
        return MemoryConfig(
            max_memory_usage=self.settings.max_memory_usage,
            gc_threshold=self.settings.gc_threshold,
            pool_sizes={
                "connection": 100,
                "request": 500,
                "response": 500,
                "order": 1000,
                "market_data": 10000,
            }
        )
    
    def _create_async_config(self) -> AsyncConfig:
        """Create async configuration from settings."""
        return AsyncConfig(
            event_loop_policy=self.settings.event_loop_policy,
            max_workers=self.settings.max_workers,
            max_concurrent_tasks=self.settings.max_concurrent_tasks,
        )
    
    def get_cache_config(self, cache_type: str = "default") -> Dict[str, Any]:
        """Get cache configuration for specific cache type."""
        base_config = {
            "strategy": self.cache_config.strategy.value,
            "ttl": self.cache_config.ttl_seconds,
            "max_size": self.cache_config.max_size,
        }
        
        if self.cache_config.strategy == CacheStrategy.REDIS:
            base_config.update({
                "host": self.cache_config.redis_host,
                "port": self.cache_config.redis_port,
                "db": self.cache_config.redis_db,
                "password": self.cache_config.redis_password,
            })
        
        # Cache-type specific configurations
        cache_configs = {
            "market_data": {"ttl": 60, "max_size": 50000},
            "user_sessions": {"ttl": 1800, "max_size": 10000},
            "api_responses": {"ttl": 300, "max_size": 5000},
            "trading_signals": {"ttl": 120, "max_size": 20000},
            "portfolio_data": {"ttl": 600, "max_size": 5000},
        }
        
        if cache_type in cache_configs:
            base_config.update(cache_configs[cache_type])
        
        return base_config
    
    def get_pool_config(self, service: str = "default") -> Dict[str, Any]:
        """Get connection pool configuration for specific service."""
        base_config = {
            "min_size": self.pool_config.min_connections,
            "max_size": self.pool_config.max_connections,
            "timeout": self.pool_config.connection_timeout,
            "idle_timeout": self.pool_config.idle_timeout,
            "max_lifetime": self.pool_config.max_lifetime,
        }
        
        # Service-specific pool configurations
        service_configs = {
            "postgres": {"max_size": self.pool_config.postgres_pool_size},
            "clickhouse": {"max_size": self.pool_config.clickhouse_pool_size},
            "redis": {"max_size": self.pool_config.redis_pool_size},
            "http": {"max_size": self.pool_config.http_pool_size},
            "websocket": {"max_size": self.pool_config.websocket_pool_size},
            "grpc": {"max_size": self.pool_config.grpc_pool_size},
        }
        
        if service in service_configs:
            base_config.update(service_configs[service])
        
        return base_config
    
    def get_rate_limit_config(self, endpoint: str = "default") -> Dict[str, Any]:
        """Get rate limit configuration for specific endpoint."""
        base_config = {
            "strategy": self.rate_limit_config.strategy.value,
            "requests_per_second": self.rate_limit_config.requests_per_second,
            "burst_size": self.rate_limit_config.burst_size,
        }
        
        # Endpoint-specific rate limit configurations
        endpoint_configs = {
            "api": {"requests_per_minute": self.rate_limit_config.api_rate_limit},
            "trading": {"requests_per_minute": self.rate_limit_config.trading_rate_limit},
            "data_feed": {"requests_per_second": self.rate_limit_config.data_feed_rate_limit},
            "websocket": {"requests_per_second": self.rate_limit_config.websocket_rate_limit},
        }
        
        if endpoint in endpoint_configs:
            base_config.update(endpoint_configs[endpoint])
        
        return base_config
    
    def optimize_event_loop(self):
        """Optimize the event loop for better performance."""
        if self.async_config.event_loop_policy == "uvloop":
            try:
                import uvloop
                asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
                logger.info("Enabled uvloop for better async performance")
            except ImportError:
                logger.warning("uvloop not available, using default asyncio")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        import psutil
        import gc
        
        return {
            "memory": {
                "usage": psutil.virtual_memory().percent,
                "available": psutil.virtual_memory().available,
                "gc_counts": gc.get_count(),
            },
            "cpu": {
                "usage": psutil.cpu_percent(),
                "count": psutil.cpu_count(),
            },
            "cache": {
                "strategy": self.cache_config.strategy.value,
                "enabled": self.settings.enable_caching,
            },
            "pools": {
                "strategy": self.pool_config.strategy.value,
                "enabled": self.settings.enable_connection_pooling,
            },
            "rate_limits": {
                "strategy": self.rate_limit_config.strategy.value,
                "enabled": self.settings.enable_rate_limiting,
            },
        }

# Global performance manager instance
performance_settings = PerformanceSettings()
performance_manager = PerformanceManager(performance_settings)

# Export commonly used configurations
__all__ = [
    "PerformanceSettings",
    "PerformanceManager",
    "CacheConfig",
    "ConnectionPoolConfig",
    "RateLimitConfig",
    "MemoryConfig",
    "AsyncConfig",
    "CacheStrategy",
    "PoolStrategy",
    "RateLimitStrategy",
    "performance_settings",
    "performance_manager",
]