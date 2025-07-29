"""
Connection Pool
High-performance connection pooling and reuse
"""

import asyncio
import time
import socket
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import logging


@dataclass
class ConnectionConfig:
    """Connection pool configuration"""
    max_connections: int = 100
    max_connections_per_host: int = 10
    connection_timeout: float = 5.0
    keep_alive_timeout: float = 30.0
    idle_timeout: float = 60.0
    health_check_interval: float = 10.0
    enable_keep_alive: bool = True
    enable_tcp_nodelay: bool = True


class PooledConnection:
    """Wrapper for pooled connections"""
    
    def __init__(self, socket_obj: socket.socket, host: str, port: int):
        self.socket = socket_obj
        self.host = host
        self.port = port
        self.created_at = time.time()
        self.last_used = time.time()
        self.use_count = 0
        self.is_healthy = True
        self.in_use = False
    
    def mark_used(self):
        """Mark connection as used"""
        self.last_used = time.time()
        self.use_count += 1
        self.in_use = True
    
    def mark_returned(self):
        """Mark connection as returned to pool"""
        self.in_use = False
    
    def is_expired(self, idle_timeout: float) -> bool:
        """Check if connection has expired"""
        return (time.time() - self.last_used) > idle_timeout
    
    def is_stale(self, keep_alive_timeout: float) -> bool:
        """Check if connection is stale"""
        return (time.time() - self.created_at) > keep_alive_timeout
    
    async def health_check(self) -> bool:
        """Perform health check on connection"""
        try:
            # Simple health check - try to get socket error
            error = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            self.is_healthy = (error == 0)
            return self.is_healthy
        except Exception:
            self.is_healthy = False
            return False
    
    def close(self):
        """Close the connection"""
        try:
            self.socket.close()
        except Exception:
            pass
        self.is_healthy = False


class ConnectionPool:
    """
    High-performance connection pool
    
    Features:
    - Per-host connection limits
    - Connection reuse and keep-alive
    - Health monitoring
    - Automatic cleanup of stale connections
    - Connection statistics
    """
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Connection storage
        self._pools: Dict[Tuple[str, int], List[PooledConnection]] = defaultdict(list)
        self._active_connections: Dict[Tuple[str, int], int] = defaultdict(int)
        self._total_connections = 0
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Statistics
        self._stats = {
            'connections_created': 0,
            'connections_reused': 0,
            'connections_closed': 0,
            'connections_failed': 0,
            'pool_hits': 0,
            'pool_misses': 0
        }
        
        # Locks for thread safety
        self._pool_locks: Dict[Tuple[str, int], asyncio.Lock] = defaultdict(asyncio.Lock)
    
    async def start(self):
        """Start the connection pool"""
        if self._running:
            return
        
        self._running = True
        
        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_worker())
        self._health_check_task = asyncio.create_task(self._health_check_worker())
        
        self.logger.info("Connection pool started")
    
    async def stop(self):
        """Stop the connection pool and close all connections"""
        self._running = False
        
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._health_check_task:
            self._health_check_task.cancel()
        
        # Close all connections
        await self._close_all_connections()
        
        self.logger.info("Connection pool stopped")
    
    async def get_connection(self, host: str, port: int) -> Optional[socket.socket]:
        """Get a connection from the pool or create a new one"""
        pool_key = (host, port)
        
        async with self._pool_locks[pool_key]:
            # Try to get from pool first
            pool = self._pools[pool_key]
            
            # Find a healthy, non-expired connection
            for i, conn in enumerate(pool):
                if (not conn.in_use and 
                    conn.is_healthy and 
                    not conn.is_expired(self.config.idle_timeout) and
                    not conn.is_stale(self.config.keep_alive_timeout)):
                    
                    # Health check before reuse
                    if await conn.health_check():
                        conn.mark_used()
                        self._stats['connections_reused'] += 1
                        self._stats['pool_hits'] += 1
                        return conn.socket
                    else:
                        # Remove unhealthy connection
                        pool.pop(i)
                        conn.close()
                        self._total_connections -= 1
                        break
            
            # No suitable connection found in pool
            self._stats['pool_misses'] += 1
            
            # Check if we can create a new connection
            if (self._total_connections >= self.config.max_connections or
                self._active_connections[pool_key] >= self.config.max_connections_per_host):
                
                self.logger.warning(f"Connection limit reached for {host}:{port}")
                return None
            
            # Create new connection
            try:
                conn = await self._create_connection(host, port)
                if conn:
                    pool.append(conn)
                    self._active_connections[pool_key] += 1
                    self._total_connections += 1
                    self._stats['connections_created'] += 1
                    conn.mark_used()
                    return conn.socket
                
            except Exception as e:
                self.logger.error(f"Failed to create connection to {host}:{port}: {e}")
                self._stats['connections_failed'] += 1
                return None
        
        return None
    
    async def return_connection(self, socket_obj: socket.socket, host: str, port: int):
        """Return a connection to the pool"""
        pool_key = (host, port)
        
        async with self._pool_locks[pool_key]:
            pool = self._pools[pool_key]
            
            # Find the connection in the pool
            for conn in pool:
                if conn.socket == socket_obj:
                    conn.mark_returned()
                    
                    # Check if connection is still healthy
                    if not await conn.health_check():
                        pool.remove(conn)
                        conn.close()
                        self._active_connections[pool_key] -= 1
                        self._total_connections -= 1
                    
                    return
            
            # Connection not found in pool, close it
            try:
                socket_obj.close()
            except Exception:
                pass
    
    async def close_connection(self, socket_obj: socket.socket, host: str, port: int):
        """Close a connection and remove it from the pool"""
        pool_key = (host, port)
        
        async with self._pool_locks[pool_key]:
            pool = self._pools[pool_key]
            
            # Find and remove the connection
            for i, conn in enumerate(pool):
                if conn.socket == socket_obj:
                    pool.pop(i)
                    conn.close()
                    self._active_connections[pool_key] -= 1
                    self._total_connections -= 1
                    self._stats['connections_closed'] += 1
                    return
            
            # Connection not found in pool, just close it
            try:
                socket_obj.close()
            except Exception:
                pass
    
    async def _create_connection(self, host: str, port: int) -> Optional[PooledConnection]:
        """Create a new connection"""
        try:
            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Apply optimizations
            self._optimize_socket(sock)
            
            # Set timeout for connection
            sock.settimeout(self.config.connection_timeout)
            
            # Connect
            await asyncio.get_event_loop().run_in_executor(
                None, sock.connect, (host, port)
            )
            
            # Set back to non-blocking
            sock.setblocking(False)
            
            # Create pooled connection
            conn = PooledConnection(sock, host, port)
            
            self.logger.debug(f"Created new connection to {host}:{port}")
            return conn
            
        except Exception as e:
            self.logger.error(f"Failed to create connection to {host}:{port}: {e}")
            return None
    
    def _optimize_socket(self, sock: socket.socket):
        """Apply socket optimizations"""
        try:
            # Disable Nagle's algorithm for low latency
            if self.config.enable_tcp_nodelay:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            # Enable keep-alive
            if self.config.enable_keep_alive:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                
                # Set keep-alive parameters if available
                if hasattr(socket, 'TCP_KEEPIDLE'):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
                if hasattr(socket, 'TCP_KEEPINTVL'):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 3)
                if hasattr(socket, 'TCP_KEEPCNT'):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
            
            # Set socket buffer sizes
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            
        except Exception as e:
            self.logger.warning(f"Failed to optimize socket: {e}")
    
    async def _cleanup_worker(self):
        """Background worker to clean up expired connections"""
        while self._running:
            try:
                await self._cleanup_expired_connections()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup worker error: {e}")
                await asyncio.sleep(10)
    
    async def _health_check_worker(self):
        """Background worker for connection health checks"""
        while self._running:
            try:
                await self._health_check_connections()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health check worker error: {e}")
                await asyncio.sleep(10)
    
    async def _cleanup_expired_connections(self):
        """Clean up expired and stale connections"""
        cleaned_count = 0
        
        for pool_key, pool in list(self._pools.items()):
            async with self._pool_locks[pool_key]:
                expired_connections = []
                
                for i, conn in enumerate(pool):
                    if (not conn.in_use and 
                        (conn.is_expired(self.config.idle_timeout) or 
                         conn.is_stale(self.config.keep_alive_timeout))):
                        expired_connections.append(i)
                
                # Remove expired connections (in reverse order to maintain indices)
                for i in reversed(expired_connections):
                    conn = pool.pop(i)
                    conn.close()
                    self._active_connections[pool_key] -= 1
                    self._total_connections -= 1
                    cleaned_count += 1
                
                # Remove empty pools
                if not pool:
                    del self._pools[pool_key]
                    if pool_key in self._active_connections:
                        del self._active_connections[pool_key]
        
        if cleaned_count > 0:
            self.logger.debug(f"Cleaned up {cleaned_count} expired connections")
    
    async def _health_check_connections(self):
        """Perform health checks on idle connections"""
        unhealthy_count = 0
        
        for pool_key, pool in list(self._pools.items()):
            async with self._pool_locks[pool_key]:
                unhealthy_connections = []
                
                for i, conn in enumerate(pool):
                    if not conn.in_use:
                        if not await conn.health_check():
                            unhealthy_connections.append(i)
                
                # Remove unhealthy connections
                for i in reversed(unhealthy_connections):
                    conn = pool.pop(i)
                    conn.close()
                    self._active_connections[pool_key] -= 1
                    self._total_connections -= 1
                    unhealthy_count += 1
        
        if unhealthy_count > 0:
            self.logger.debug(f"Removed {unhealthy_count} unhealthy connections")
    
    async def _close_all_connections(self):
        """Close all connections in all pools"""
        total_closed = 0
        
        for pool_key, pool in list(self._pools.items()):
            async with self._pool_locks[pool_key]:
                for conn in pool:
                    conn.close()
                    total_closed += 1
                
                pool.clear()
                self._active_connections[pool_key] = 0
        
        self._pools.clear()
        self._active_connections.clear()
        self._total_connections = 0
        
        self.logger.info(f"Closed {total_closed} connections")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        pool_stats = {}
        
        for pool_key, pool in self._pools.items():
            host, port = pool_key
            pool_stats[f"{host}:{port}"] = {
                'total_connections': len(pool),
                'active_connections': sum(1 for conn in pool if conn.in_use),
                'idle_connections': sum(1 for conn in pool if not conn.in_use),
                'healthy_connections': sum(1 for conn in pool if conn.is_healthy)
            }
        
        return {
            'total_connections': self._total_connections,
            'total_pools': len(self._pools),
            'pool_stats': pool_stats,
            'statistics': self._stats.copy(),
            'config': {
                'max_connections': self.config.max_connections,
                'max_connections_per_host': self.config.max_connections_per_host,
                'connection_timeout': self.config.connection_timeout,
                'keep_alive_timeout': self.config.keep_alive_timeout,
                'idle_timeout': self.config.idle_timeout
            }
        }