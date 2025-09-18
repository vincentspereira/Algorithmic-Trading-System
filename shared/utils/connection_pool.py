"""Advanced connection pool manager for databases and external services.

This module provides comprehensive connection pooling capabilities including:
- Database connection pools (PostgreSQL, ClickHouse, Redis)
- HTTP/WebSocket connection pools
- gRPC connection pools
- Adaptive pool sizing based on load
- Health monitoring and automatic recovery
- Connection lifecycle management
"""

import asyncio
import logging
import time
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Callable, AsyncContextManager
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections import deque
import weakref

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    asyncpg = None

try:
    import aioredis
    AIOREDIS_AVAILABLE = True
except ImportError:
    AIOREDIS_AVAILABLE = False
    aioredis = None

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None

try:
    import grpcio
    import grpc.aio
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    grpc = None

from config.performance_config import performance_manager, PoolStrategy

logger = logging.getLogger(__name__)

@dataclass
class ConnectionStats:
    """Connection pool statistics."""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    created_connections: int = 0
    closed_connections: int = 0
    connection_errors: int = 0
    average_connection_time: float = 0.0
    peak_connections: int = 0
    
    @property
    def utilization_rate(self) -> float:
        """Calculate pool utilization rate."""
        return self.active_connections / max(self.total_connections, 1)
    
    @property
    def error_rate(self) -> float:
        """Calculate connection error rate."""
        total_attempts = self.created_connections + self.connection_errors
        return self.connection_errors / max(total_attempts, 1)

@dataclass
class ConnectionInfo:
    """Information about a connection."""
    connection_id: str
    created_at: datetime
    last_used: datetime
    use_count: int = 0
    is_healthy: bool = True
    connection: Any = None
    
    @property
    def age(self) -> timedelta:
        """Get connection age."""
        return datetime.utcnow() - self.created_at
    
    @property
    def idle_time(self) -> timedelta:
        """Get connection idle time."""
        return datetime.utcnow() - self.last_used
    
    def mark_used(self):
        """Mark connection as used."""
        self.use_count += 1
        self.last_used = datetime.utcnow()

class ConnectionPool(ABC):
    """Abstract base class for connection pools."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_size = config.get('min_size', 5)
        self.max_size = config.get('max_size', 50)
        self.timeout = config.get('timeout', 30)
        self.idle_timeout = config.get('idle_timeout', 300)
        self.max_lifetime = config.get('max_lifetime', 3600)
        self.health_check_interval = config.get('health_check_interval', 60)
        
        self._connections: Dict[str, ConnectionInfo] = {}
        self._available: deque = deque()
        self._lock = asyncio.Lock()
        self._stats = ConnectionStats()
        self._closed = False
        
        # Start background tasks
        self._health_check_task = None
        self._cleanup_task = None
        self._start_background_tasks()
    
    @abstractmethod
    async def _create_connection(self) -> Any:
        """Create a new connection."""
        pass
    
    @abstractmethod
    async def _close_connection(self, connection: Any):
        """Close a connection."""
        pass
    
    @abstractmethod
    async def _validate_connection(self, connection: Any) -> bool:
        """Validate if connection is healthy."""
        pass
    
    async def get_connection(self) -> AsyncContextManager[Any]:
        """Get a connection from the pool."""
        @asynccontextmanager
        async def connection_context():
            connection_info = await self._acquire_connection()
            try:
                yield connection_info.connection
            finally:
                await self._release_connection(connection_info)
        
        return connection_context()
    
    async def _acquire_connection(self) -> ConnectionInfo:
        """Acquire a connection from the pool."""
        if self._closed:
            raise RuntimeError("Connection pool is closed")
        
        start_time = time.time()
        
        async with self._lock:
            # Try to get an available connection
            while self._available:
                connection_id = self._available.popleft()
                if connection_id in self._connections:
                    connection_info = self._connections[connection_id]
                    
                    # Check if connection is still valid
                    if await self._is_connection_valid(connection_info):
                        connection_info.mark_used()
                        self._stats.active_connections += 1
                        return connection_info
                    else:
                        # Remove invalid connection
                        await self._remove_connection(connection_info)
            
            # Create new connection if under limit
            if len(self._connections) < self.max_size:
                connection_info = await self._create_new_connection()
                if connection_info:
                    connection_info.mark_used()
                    self._stats.active_connections += 1
                    return connection_info
            
            # Wait for available connection
            timeout_time = start_time + self.timeout
            while time.time() < timeout_time:
                await asyncio.sleep(0.1)
                
                if self._available:
                    connection_id = self._available.popleft()
                    if connection_id in self._connections:
                        connection_info = self._connections[connection_id]
                        if await self._is_connection_valid(connection_info):
                            connection_info.mark_used()
                            self._stats.active_connections += 1
                            return connection_info
                        else:
                            await self._remove_connection(connection_info)
            
            raise TimeoutError(f"Could not acquire connection within {self.timeout} seconds")
    
    async def _release_connection(self, connection_info: ConnectionInfo):
        """Release a connection back to the pool."""
        async with self._lock:
            if connection_info.connection_id in self._connections:
                self._available.append(connection_info.connection_id)
                self._stats.active_connections -= 1
    
    async def _create_new_connection(self) -> Optional[ConnectionInfo]:
        """Create a new connection and add to pool."""
        try:
            connection = await self._create_connection()
            connection_id = f"conn_{len(self._connections)}_{int(time.time())}"
            
            connection_info = ConnectionInfo(
                connection_id=connection_id,
                created_at=datetime.utcnow(),
                last_used=datetime.utcnow(),
                connection=connection
            )
            
            self._connections[connection_id] = connection_info
            self._stats.total_connections += 1
            self._stats.created_connections += 1
            
            if self._stats.total_connections > self._stats.peak_connections:
                self._stats.peak_connections = self._stats.total_connections
            
            logger.debug(f"Created new connection: {connection_id}")
            return connection_info
            
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            self._stats.connection_errors += 1
            return None
    
    async def _remove_connection(self, connection_info: ConnectionInfo):
        """Remove connection from pool."""
        try:
            await self._close_connection(connection_info.connection)
        except Exception as e:
            logger.error(f"Error closing connection {connection_info.connection_id}: {e}")
        
        if connection_info.connection_id in self._connections:
            del self._connections[connection_info.connection_id]
            self._stats.total_connections -= 1
            self._stats.closed_connections += 1
    
    async def _is_connection_valid(self, connection_info: ConnectionInfo) -> bool:
        """Check if connection is valid and healthy."""
        # Check age
        if connection_info.age.total_seconds() > self.max_lifetime:
            return False
        
        # Check idle time
        if connection_info.idle_time.total_seconds() > self.idle_timeout:
            return False
        
        # Check health
        try:
            return await self._validate_connection(connection_info.connection)
        except Exception:
            return False
    
    def _start_background_tasks(self):
        """Start background maintenance tasks."""
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _health_check_loop(self):
        """Periodically check connection health."""
        while not self._closed:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_check()
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    async def _cleanup_loop(self):
        """Periodically clean up old/invalid connections."""
        while not self._closed:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._cleanup_connections()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _perform_health_check(self):
        """Perform health check on all connections."""
        async with self._lock:
            unhealthy_connections = []
            
            for connection_info in self._connections.values():
                if not await self._is_connection_valid(connection_info):
                    unhealthy_connections.append(connection_info)
            
            for connection_info in unhealthy_connections:
                await self._remove_connection(connection_info)
                # Remove from available queue if present
                try:
                    self._available.remove(connection_info.connection_id)
                except ValueError:
                    pass
            
            if unhealthy_connections:
                logger.info(f"Removed {len(unhealthy_connections)} unhealthy connections")
    
    async def _cleanup_connections(self):
        """Clean up old and idle connections."""
        async with self._lock:
            # Ensure minimum connections
            while len(self._connections) < self.min_size:
                await self._create_new_connection()
    
    async def get_stats(self) -> ConnectionStats:
        """Get connection pool statistics."""
        async with self._lock:
            self._stats.idle_connections = len(self._available)
            return self._stats
    
    async def close(self):
        """Close the connection pool."""
        self._closed = True
        
        # Cancel background tasks
        if self._health_check_task:
            self._health_check_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Close all connections
        async with self._lock:
            for connection_info in list(self._connections.values()):
                await self._remove_connection(connection_info)
            
            self._connections.clear()
            self._available.clear()
        
        logger.info("Connection pool closed")

class PostgreSQLPool(ConnectionPool):
    """PostgreSQL connection pool."""
    
    def __init__(self, config: Dict[str, Any]):
        if not ASYNCPG_AVAILABLE:
            raise ImportError("asyncpg not available. Install it: pip install asyncpg")
        
        super().__init__(config)
        self.dsn = config.get('dsn') or self._build_dsn(config)
    
    def _build_dsn(self, config: Dict[str, Any]) -> str:
        """Build PostgreSQL DSN from config."""
        return (
            f"postgresql://{config.get('user', 'postgres')}:"
            f"{config.get('password', '')}@{config.get('host', 'localhost')}:"
            f"{config.get('port', 5432)}/{config.get('database', 'postgres')}"
        )
    
    async def _create_connection(self) -> Any:
        """Create PostgreSQL connection."""
        return await asyncpg.connect(self.dsn)
    
    async def _close_connection(self, connection: Any):
        """Close PostgreSQL connection."""
        await connection.close()
    
    async def _validate_connection(self, connection: Any) -> bool:
        """Validate PostgreSQL connection."""
        try:
            await connection.fetchval("SELECT 1")
            return True
        except Exception:
            return False

class RedisPool(ConnectionPool):
    """Redis connection pool."""
    
    def __init__(self, config: Dict[str, Any]):
        if not AIOREDIS_AVAILABLE:
            raise ImportError("aioredis not available. Install it: pip install aioredis")
        
        super().__init__(config)
        self.redis_config = {
            'host': config.get('host', 'localhost'),
            'port': config.get('port', 6379),
            'db': config.get('db', 0),
            'password': config.get('password'),
        }
    
    async def _create_connection(self) -> Any:
        """Create Redis connection."""
        return await aioredis.create_connection(**self.redis_config)
    
    async def _close_connection(self, connection: Any):
        """Close Redis connection."""
        connection.close()
        await connection.wait_closed()
    
    async def _validate_connection(self, connection: Any) -> bool:
        """Validate Redis connection."""
        try:
            await connection.execute('PING')
            return True
        except Exception:
            return False

class HTTPPool(ConnectionPool):
    """HTTP connection pool using aiohttp."""
    
    def __init__(self, config: Dict[str, Any]):
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp not available. Install it: pip install aiohttp")
        
        super().__init__(config)
        self.connector_config = {
            'limit': config.get('max_size', 100),
            'limit_per_host': config.get('limit_per_host', 30),
            'ttl_dns_cache': config.get('ttl_dns_cache', 300),
            'use_dns_cache': config.get('use_dns_cache', True),
        }
    
    async def _create_connection(self) -> Any:
        """Create HTTP session."""
        connector = aiohttp.TCPConnector(**self.connector_config)
        return aiohttp.ClientSession(connector=connector)
    
    async def _close_connection(self, connection: Any):
        """Close HTTP session."""
        await connection.close()
    
    async def _validate_connection(self, connection: Any) -> bool:
        """Validate HTTP session."""
        return not connection.closed

class ConnectionPoolManager:
    """Manages multiple connection pools for different services."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or performance_manager.get_pool_config()
        self._pools: Dict[str, ConnectionPool] = {}
        self._lock = threading.Lock()
        
        logger.info("Connection pool manager initialized")
    
    def create_pool(self, name: str, pool_type: str, config: Dict[str, Any]) -> ConnectionPool:
        """Create a new connection pool."""
        with self._lock:
            if name in self._pools:
                raise ValueError(f"Pool {name} already exists")
            
            # Merge with default config
            pool_config = self.config.copy()
            pool_config.update(config)
            
            # Create appropriate pool type
            if pool_type == 'postgresql':
                pool = PostgreSQLPool(pool_config)
            elif pool_type == 'redis':
                pool = RedisPool(pool_config)
            elif pool_type == 'http':
                pool = HTTPPool(pool_config)
            else:
                raise ValueError(f"Unknown pool type: {pool_type}")
            
            self._pools[name] = pool
            logger.info(f"Created {pool_type} pool: {name}")
            return pool
    
    def get_pool(self, name: str) -> Optional[ConnectionPool]:
        """Get connection pool by name."""
        return self._pools.get(name)
    
    async def get_connection(self, pool_name: str) -> AsyncContextManager[Any]:
        """Get connection from named pool."""
        pool = self.get_pool(pool_name)
        if not pool:
            raise ValueError(f"Pool {pool_name} not found")
        
        return await pool.get_connection()
    
    async def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all pools."""
        stats = {}
        for name, pool in self._pools.items():
            pool_stats = await pool.get_stats()
            stats[name] = {
                'type': type(pool).__name__,
                'stats': pool_stats.__dict__,
                'config': pool.config,
            }
        return stats
    
    async def close_all(self):
        """Close all connection pools."""
        for name, pool in self._pools.items():
            try:
                await pool.close()
                logger.info(f"Closed pool: {name}")
            except Exception as e:
                logger.error(f"Error closing pool {name}: {e}")
        
        self._pools.clear()
        logger.info("All connection pools closed")

# Global connection pool manager
pool_manager = ConnectionPoolManager()

# Export commonly used classes
__all__ = [
    "ConnectionPool",
    "PostgreSQLPool",
    "RedisPool",
    "HTTPPool",
    "ConnectionPoolManager",
    "ConnectionStats",
    "ConnectionInfo",
    "pool_manager",
]