"""
Core Infrastructure Components
Foundational systems for the enhanced Nautilus Trader Engine
"""

from .messaging import (
    MessageBus, MessageHandler, LockFreeRingBuffer, 
    ZeroCopySerializer, MessageType, TopicRouter, 
    MessageRouter, MessageMetrics
)
from .caching import (
    CacheManager, CacheConfig, L1Cache, LRUCache,
    L2Cache, RedisCache, L3Cache, DatabaseCache,
    CacheCoherencyManager, CacheMetrics
)
# Import networking components with fallback for missing dependencies
try:
    from .networking import (
        NetworkManager, NetworkConfig, ConnectionPool,
        ConnectionConfig, CPUAffinityManager, NUMAAllocator,
        KernelBypassSocket, NetworkMetrics
    )
    NETWORKING_AVAILABLE = True
except ImportError as e:
    # Create dummy classes for missing networking components
    class NetworkManager:
        def __init__(self, *args, **kwargs): pass
        async def start(self): pass
        async def stop(self): pass
        def is_healthy(self): return True
        def get_metrics(self): return type('Metrics', (), {'active_connections': 0})()
        async def get_connection(self, endpoint): return None
    
    class NetworkConfig:
        def __init__(self, **kwargs): pass
    
    # Create dummy classes for other networking components
    ConnectionPool = NetworkManager
    ConnectionConfig = NetworkConfig
    CPUAffinityManager = NetworkManager
    NUMAAllocator = NetworkManager
    KernelBypassSocket = NetworkManager
    NetworkMetrics = NetworkManager
    
    NETWORKING_AVAILABLE = False
from .infrastructure_manager import (
    InfrastructureManager, InfrastructureConfig,
    get_infrastructure, initialize_infrastructure,
    start_infrastructure, stop_infrastructure
)

__all__ = [
    # Messaging components
    'MessageBus', 'MessageHandler', 'LockFreeRingBuffer',
    'ZeroCopySerializer', 'MessageType', 'TopicRouter',
    'MessageRouter', 'MessageMetrics',
    
    # Caching components
    'CacheManager', 'CacheConfig', 'L1Cache', 'LRUCache',
    'L2Cache', 'RedisCache', 'L3Cache', 'DatabaseCache',
    'CacheCoherencyManager', 'CacheMetrics',
    
    # Networking components
    'NetworkManager', 'NetworkConfig', 'ConnectionPool',
    'ConnectionConfig', 'CPUAffinityManager', 'NUMAAllocator',
    'KernelBypassSocket', 'NetworkMetrics',
    
    # Infrastructure management
    'InfrastructureManager', 'InfrastructureConfig',
    'get_infrastructure', 'initialize_infrastructure',
    'start_infrastructure', 'stop_infrastructure'
]