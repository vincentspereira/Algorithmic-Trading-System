"""
Network Manager
Central management for ultra-low latency networking
"""

import asyncio
import socket
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import logging

from .connection_pool import ConnectionPool, ConnectionConfig
from .cpu_affinity import CPUAffinityManager
from .numa_allocator import NUMAAllocator
from .kernel_bypass import KernelBypassSocket
from .network_metrics import NetworkMetrics


class NetworkProtocol(Enum):
    """Supported network protocols"""
    TCP = "tcp"
    UDP = "udp"
    KERNEL_BYPASS = "kernel_bypass"


class NetworkMode(Enum):
    """Network operation modes"""
    STANDARD = "standard"
    LOW_LATENCY = "low_latency"
    ULTRA_LOW_LATENCY = "ultra_low_latency"


@dataclass
class NetworkConfig:
    """Network configuration"""
    # General settings
    mode: NetworkMode = NetworkMode.ULTRA_LOW_LATENCY
    enable_kernel_bypass: bool = True
    enable_cpu_affinity: bool = True
    enable_numa_awareness: bool = True
    
    # Connection pooling
    pool_size: int = 100
    max_connections_per_host: int = 10
    connection_timeout: float = 1.0
    keep_alive_timeout: float = 30.0
    
    # Performance tuning
    tcp_nodelay: bool = True
    tcp_quickack: bool = True
    socket_buffer_size: int = 65536
    receive_buffer_size: int = 262144
    send_buffer_size: int = 262144
    
    # CPU affinity
    network_cpu_cores: List[int] = None
    io_cpu_cores: List[int] = None
    
    # NUMA settings
    numa_node: Optional[int] = None
    memory_policy: str = "local"
    
    # Monitoring
    enable_metrics: bool = True
    metrics_interval: int = 1  # seconds
    
    def __post_init__(self):
        if self.network_cpu_cores is None:
            self.network_cpu_cores = [0, 1]  # Default to first 2 cores
        if self.io_cpu_cores is None:
            self.io_cpu_cores = [2, 3]  # Default to next 2 cores


class NetworkManager:
    """
    Ultra-low latency network manager
    
    Features:
    - Kernel bypass networking (DPDK-style)
    - CPU affinity management
    - NUMA-aware memory allocation
    - Connection pooling and reuse
    - Zero-copy operations where possible
    - Real-time performance monitoring
    """
    
    def __init__(self, config: NetworkConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.connection_pool: Optional[ConnectionPool] = None
        self.cpu_affinity_manager: Optional[CPUAffinityManager] = None
        self.numa_allocator: Optional[NUMAAllocator] = None
        self.metrics: Optional[NetworkMetrics] = None
        
        # Network interfaces
        self._kernel_bypass_sockets: Dict[str, KernelBypassSocket] = {}
        self._standard_sockets: Dict[str, socket.socket] = {}
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._running = False
        
        # Performance optimization
        self._message_handlers: Dict[str, Callable] = {}
        self._zero_copy_enabled = False
        
        # Thread pools for different operations
        self._network_thread_pool: Optional[threading.ThreadPoolExecutor] = None
        self._io_thread_pool: Optional[threading.ThreadPoolExecutor] = None
    
    async def start(self):
        """Initialize and start the network manager"""
        if self._running:
            return
        
        try:
            self.logger.info("Starting NetworkManager...")
            
            # Initialize CPU affinity management
            if self.config.enable_cpu_affinity:
                self.cpu_affinity_manager = CPUAffinityManager(
                    network_cores=self.config.network_cpu_cores,
                    io_cores=self.config.io_cpu_cores
                )
                await self.cpu_affinity_manager.start()
            
            # Initialize NUMA allocator
            if self.config.enable_numa_awareness:
                self.numa_allocator = NUMAAllocator(
                    numa_node=self.config.numa_node,
                    memory_policy=self.config.memory_policy
                )
                await self.numa_allocator.start()
            
            # Initialize connection pool
            pool_config = ConnectionConfig(
                max_connections=self.config.pool_size,
                max_connections_per_host=self.config.max_connections_per_host,
                connection_timeout=self.config.connection_timeout,
                keep_alive_timeout=self.config.keep_alive_timeout
            )
            self.connection_pool = ConnectionPool(pool_config)
            await self.connection_pool.start()
            
            # Initialize metrics
            if self.config.enable_metrics:
                self.metrics = NetworkMetrics()
                await self.metrics.start()
            
            # Setup thread pools with CPU affinity
            self._setup_thread_pools()
            
            # Start background tasks
            self._start_background_tasks()
            
            # Enable zero-copy if supported
            self._zero_copy_enabled = self._check_zero_copy_support()
            
            self._running = True
            self.logger.info("NetworkManager started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start NetworkManager: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the network manager and cleanup resources"""
        if not self._running:
            return
        
        self._running = False
        
        try:
            # Cancel background tasks
            for task in self._background_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            if self._background_tasks:
                await asyncio.gather(*self._background_tasks, return_exceptions=True)
            
            # Close all sockets
            await self._close_all_sockets()
            
            # Stop components
            if self.connection_pool:
                await self.connection_pool.stop()
            
            if self.cpu_affinity_manager:
                await self.cpu_affinity_manager.stop()
            
            if self.numa_allocator:
                await self.numa_allocator.stop()
            
            if self.metrics:
                await self.metrics.stop()
            
            # Shutdown thread pools
            if self._network_thread_pool:
                self._network_thread_pool.shutdown(wait=True)
            
            if self._io_thread_pool:
                self._io_thread_pool.shutdown(wait=True)
            
            self.logger.info("NetworkManager stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping NetworkManager: {e}")
    
    async def create_connection(self, 
                              host: str, 
                              port: int, 
                              protocol: NetworkProtocol = NetworkProtocol.TCP,
                              **kwargs) -> Any:
        """Create a new network connection"""
        start_time = time.time_ns()
        
        try:
            if protocol == NetworkProtocol.KERNEL_BYPASS and self.config.enable_kernel_bypass:
                connection = await self._create_kernel_bypass_connection(host, port, **kwargs)
            else:
                connection = await self._create_standard_connection(host, port, protocol, **kwargs)
            
            # Record metrics
            if self.metrics:
                latency_ns = time.time_ns() - start_time
                self.metrics.record_connection_created(protocol, latency_ns)
            
            return connection
            
        except Exception as e:
            if self.metrics:
                self.metrics.record_connection_error(protocol, str(e))
            raise
    
    async def send_message(self, 
                          connection: Any, 
                          data: bytes, 
                          use_zero_copy: bool = True) -> int:
        """Send message with optimal performance"""
        start_time = time.time_ns()
        
        try:
            if use_zero_copy and self._zero_copy_enabled:
                bytes_sent = await self._send_zero_copy(connection, data)
            else:
                bytes_sent = await self._send_standard(connection, data)
            
            # Record metrics
            if self.metrics:
                latency_ns = time.time_ns() - start_time
                self.metrics.record_message_sent(bytes_sent, latency_ns)
            
            return bytes_sent
            
        except Exception as e:
            if self.metrics:
                self.metrics.record_send_error(str(e))
            raise
    
    async def receive_message(self, 
                            connection: Any, 
                            buffer_size: Optional[int] = None) -> bytes:
        """Receive message with optimal performance"""
        start_time = time.time_ns()
        
        try:
            buffer_size = buffer_size or self.config.receive_buffer_size
            
            if self._zero_copy_enabled:
                data = await self._receive_zero_copy(connection, buffer_size)
            else:
                data = await self._receive_standard(connection, buffer_size)
            
            # Record metrics
            if self.metrics:
                latency_ns = time.time_ns() - start_time
                self.metrics.record_message_received(len(data), latency_ns)
            
            return data
            
        except Exception as e:
            if self.metrics:
                self.metrics.record_receive_error(str(e))
            raise
    
    async def _create_kernel_bypass_connection(self, host: str, port: int, **kwargs) -> KernelBypassSocket:
        """Create kernel bypass connection"""
        connection_key = f"{host}:{port}"
        
        if connection_key in self._kernel_bypass_sockets:
            return self._kernel_bypass_sockets[connection_key]
        
        # Create new kernel bypass socket
        kb_socket = KernelBypassSocket(
            numa_allocator=self.numa_allocator,
            cpu_affinity_manager=self.cpu_affinity_manager
        )
        
        await kb_socket.connect(host, port)
        self._kernel_bypass_sockets[connection_key] = kb_socket
        
        return kb_socket
    
    async def _create_standard_connection(self, 
                                        host: str, 
                                        port: int, 
                                        protocol: NetworkProtocol,
                                        **kwargs) -> socket.socket:
        """Create standard socket connection"""
        # Try to get from connection pool first
        if self.connection_pool:
            pooled_connection = await self.connection_pool.get_connection(host, port)
            if pooled_connection:
                return pooled_connection
        
        # Create new connection
        if protocol == NetworkProtocol.TCP:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Apply performance optimizations
            self._optimize_tcp_socket(sock)
            
            # Connect
            await asyncio.get_event_loop().run_in_executor(
                self._network_thread_pool,
                lambda: sock.connect((host, port))
            )
            
        elif protocol == NetworkProtocol.UDP:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Apply performance optimizations
            self._optimize_udp_socket(sock)
            
            # For UDP, we don't actually connect, just bind if needed
            if kwargs.get('bind_port'):
                sock.bind(('', kwargs['bind_port']))
        
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")
        
        connection_key = f"{host}:{port}"
        self._standard_sockets[connection_key] = sock
        
        return sock
    
    def _optimize_tcp_socket(self, sock: socket.socket):
        """Apply TCP socket optimizations"""
        try:
            # Disable Nagle's algorithm for low latency
            if self.config.tcp_nodelay:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            # Enable TCP quick ACK
            if self.config.tcp_quickack and hasattr(socket, 'TCP_QUICKACK'):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_QUICKACK, 1)
            
            # Set socket buffer sizes
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.config.receive_buffer_size)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self.config.send_buffer_size)
            
            # Enable keep-alive
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            # Set socket to non-blocking mode
            sock.setblocking(False)
            
        except Exception as e:
            self.logger.warning(f"Failed to apply TCP optimizations: {e}")
    
    def _optimize_udp_socket(self, sock: socket.socket):
        """Apply UDP socket optimizations"""
        try:
            # Set socket buffer sizes
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.config.receive_buffer_size)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self.config.send_buffer_size)
            
            # Set socket to non-blocking mode
            sock.setblocking(False)
            
        except Exception as e:
            self.logger.warning(f"Failed to apply UDP optimizations: {e}")
    
    async def _send_zero_copy(self, connection: Any, data: bytes) -> int:
        """Send data using zero-copy operations"""
        if isinstance(connection, KernelBypassSocket):
            return await connection.send_zero_copy(data)
        else:
            # Fallback to sendfile for regular sockets if supported
            return await self._send_standard(connection, data)
    
    async def _send_standard(self, connection: Any, data: bytes) -> int:
        """Send data using standard operations"""
        if isinstance(connection, socket.socket):
            return await asyncio.get_event_loop().run_in_executor(
                self._io_thread_pool,
                connection.send,
                data
            )
        elif isinstance(connection, KernelBypassSocket):
            return await connection.send(data)
        else:
            raise ValueError(f"Unsupported connection type: {type(connection)}")
    
    async def _receive_zero_copy(self, connection: Any, buffer_size: int) -> bytes:
        """Receive data using zero-copy operations"""
        if isinstance(connection, KernelBypassSocket):
            return await connection.receive_zero_copy(buffer_size)
        else:
            return await self._receive_standard(connection, buffer_size)
    
    async def _receive_standard(self, connection: Any, buffer_size: int) -> bytes:
        """Receive data using standard operations"""
        if isinstance(connection, socket.socket):
            return await asyncio.get_event_loop().run_in_executor(
                self._io_thread_pool,
                connection.recv,
                buffer_size
            )
        elif isinstance(connection, KernelBypassSocket):
            return await connection.receive(buffer_size)
        else:
            raise ValueError(f"Unsupported connection type: {type(connection)}")
    
    def _setup_thread_pools(self):
        """Setup thread pools with CPU affinity"""
        # Network thread pool for connection operations
        self._network_thread_pool = threading.ThreadPoolExecutor(
            max_workers=len(self.config.network_cpu_cores),
            thread_name_prefix="network"
        )
        
        # IO thread pool for data operations
        self._io_thread_pool = threading.ThreadPoolExecutor(
            max_workers=len(self.config.io_cpu_cores),
            thread_name_prefix="io"
        )
        
        # Set CPU affinity for threads if manager is available
        if self.cpu_affinity_manager:
            # This would be implemented to set affinity for thread pool threads
            pass
    
    def _start_background_tasks(self):
        """Start background monitoring and maintenance tasks"""
        if self.config.enable_metrics and self.metrics:
            task = asyncio.create_task(self._metrics_collector())
            self._background_tasks.append(task)
        
        # Connection health checker
        task = asyncio.create_task(self._connection_health_checker())
        self._background_tasks.append(task)
    
    async def _metrics_collector(self):
        """Background metrics collection"""
        while self._running:
            try:
                if self.metrics:
                    # Collect network interface statistics
                    await self.metrics.collect_system_metrics()
                
                await asyncio.sleep(self.config.metrics_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics collector error: {e}")
                await asyncio.sleep(5)
    
    async def _connection_health_checker(self):
        """Background connection health monitoring"""
        while self._running:
            try:
                # Check kernel bypass sockets
                dead_kb_sockets = []
                for key, kb_socket in self._kernel_bypass_sockets.items():
                    if not await kb_socket.is_alive():
                        dead_kb_sockets.append(key)
                
                # Remove dead connections
                for key in dead_kb_sockets:
                    kb_socket = self._kernel_bypass_sockets.pop(key)
                    await kb_socket.close()
                
                # Check standard sockets
                dead_sockets = []
                for key, sock in self._standard_sockets.items():
                    try:
                        # Simple health check - try to get socket error
                        error = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                        if error != 0:
                            dead_sockets.append(key)
                    except:
                        dead_sockets.append(key)
                
                # Remove dead connections
                for key in dead_sockets:
                    sock = self._standard_sockets.pop(key)
                    try:
                        sock.close()
                    except:
                        pass
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Connection health checker error: {e}")
                await asyncio.sleep(30)
    
    async def _close_all_sockets(self):
        """Close all open sockets"""
        # Close kernel bypass sockets
        for kb_socket in self._kernel_bypass_sockets.values():
            try:
                await kb_socket.close()
            except Exception as e:
                self.logger.error(f"Error closing kernel bypass socket: {e}")
        
        self._kernel_bypass_sockets.clear()
        
        # Close standard sockets
        for sock in self._standard_sockets.values():
            try:
                sock.close()
            except Exception as e:
                self.logger.error(f"Error closing standard socket: {e}")
        
        self._standard_sockets.clear()
    
    def _check_zero_copy_support(self) -> bool:
        """Check if zero-copy operations are supported"""
        try:
            # Check for sendfile support
            import os
            if hasattr(os, 'sendfile'):
                return True
            
            # Check for other zero-copy mechanisms
            # This would be expanded based on platform capabilities
            return False
            
        except Exception:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get network manager statistics"""
        stats = {
            'running': self._running,
            'config': {
                'mode': self.config.mode.value,
                'kernel_bypass_enabled': self.config.enable_kernel_bypass,
                'cpu_affinity_enabled': self.config.enable_cpu_affinity,
                'numa_awareness_enabled': self.config.enable_numa_awareness,
                'zero_copy_enabled': self._zero_copy_enabled
            },
            'connections': {
                'kernel_bypass_count': len(self._kernel_bypass_sockets),
                'standard_count': len(self._standard_sockets),
                'total_count': len(self._kernel_bypass_sockets) + len(self._standard_sockets)
            }
        }
        
        # Add component stats
        if self.connection_pool:
            stats['connection_pool'] = self.connection_pool.get_stats()
        
        if self.metrics:
            stats['metrics'] = self.metrics.get_stats()
        
        if self.cpu_affinity_manager:
            stats['cpu_affinity'] = self.cpu_affinity_manager.get_stats()
        
        if self.numa_allocator:
            stats['numa'] = self.numa_allocator.get_stats()
        
        return stats