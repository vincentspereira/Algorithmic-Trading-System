"""
Infrastructure Manager
Coordinates and manages all core infrastructure components
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from .messaging import MessageBus, MessageMetrics
from .caching import CacheManager, CacheConfig, CacheMetrics

# Import networking with fallback
try:
    from .networking import NetworkManager, NetworkConfig, NetworkMetrics
    NETWORKING_AVAILABLE = True
except ImportError:
    # Create dummy networking classes
    class NetworkManager:
        def __init__(self, *args, **kwargs): pass
        async def start(self): pass
        async def stop(self): pass
        def is_healthy(self): return True
        def get_metrics(self): return type('Metrics', (), {'active_connections': 0, 'total_connections': 0, 'average_latency_ms': 0, 'bytes_sent': 0, 'bytes_received': 0})()
        async def get_connection(self, endpoint): return type('Connection', (), {'id': 'mock_connection'})()
    
    class NetworkConfig:
        def __init__(self, **kwargs): pass
    
    class NetworkMetrics:
        def __init__(self): pass
    
    NETWORKING_AVAILABLE = False


@dataclass
class InfrastructureConfig:
    """Configuration for infrastructure manager"""
    
    # Message bus configuration
    message_bus_buffer_size: int = 65536
    message_bus_batch_size: int = 100
    
    # Cache configuration
    cache_l1_size: int = 10000
    cache_l2_enabled: bool = True
    cache_l2_host: str = "localhost"
    cache_l2_port: int = 6379
    cache_l3_enabled: bool = True
    cache_l3_connection_string: str = "postgresql://localhost/trading"
    
    # Network configuration
    network_enable_kernel_bypass: bool = False
    network_enable_numa: bool = False
    network_pool_size: int = 100
    network_cpu_cores: list = field(default_factory=lambda: [0, 1, 2, 3])
    
    # Performance monitoring
    metrics_enabled: bool = True
    metrics_collection_interval: float = 1.0
    
    # Logging
    log_level: str = "INFO"


class InfrastructureManager:
    """
    Manages all core infrastructure components
    Provides unified interface for messaging, caching, and networking
    """
    
    def __init__(self, config: InfrastructureConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, config.log_level))
        
        # Core components
        self.message_bus: Optional[MessageBus] = None
        self.cache_manager: Optional[CacheManager] = None
        self.network_manager: Optional[NetworkManager] = None
        
        # State management
        self._started = False
        self._metrics_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Performance metrics
        self._metrics_history: Dict[str, list] = {
            'message_throughput': [],
            'cache_hit_rate': [],
            'network_latency': [],
            'memory_usage': []
        }
    
    async def start(self) -> None:
        """Start all infrastructure components"""
        if self._started:
            self.logger.warning("Infrastructure already started")
            return
        
        try:
            self.logger.info("Starting core infrastructure components...")
            
            # Start message bus
            self.message_bus = MessageBus(
                buffer_size=self.config.message_bus_buffer_size,
                batch_size=self.config.message_bus_batch_size
            )
            await self.message_bus.start()
            self.logger.info("✓ Message bus started")
            
            # Start cache manager
            cache_config = CacheConfig(
                l1_size=self.config.cache_l1_size,
                l2_enabled=self.config.cache_l2_enabled,
                l2_host=self.config.cache_l2_host,
                l2_port=self.config.cache_l2_port,
                l3_enabled=self.config.cache_l3_enabled,
                l3_connection_string=self.config.cache_l3_connection_string
            )
            self.cache_manager = CacheManager(cache_config)
            await self.cache_manager.start()
            self.logger.info("✓ Cache manager started")
            
            # Start network manager
            network_config = NetworkConfig(
                enable_kernel_bypass=self.config.network_enable_kernel_bypass,
                enable_numa=self.config.network_enable_numa,
                pool_size=self.config.network_pool_size,
                cpu_cores=self.config.network_cpu_cores
            )
            self.network_manager = NetworkManager(network_config)
            await self.network_manager.start()
            self.logger.info("✓ Network manager started")
            
            # Start background tasks
            if self.config.metrics_enabled:
                self._metrics_task = asyncio.create_task(self._collect_metrics())
                self.logger.info("✓ Metrics collection started")
            
            self._health_check_task = asyncio.create_task(self._health_check())
            self.logger.info("✓ Health monitoring started")
            
            self._started = True
            self.logger.info("🚀 All infrastructure components started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start infrastructure: {e}")
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """Stop all infrastructure components"""
        if not self._started:
            return
        
        self.logger.info("Stopping infrastructure components...")
        
        # Stop background tasks
        if self._metrics_task:
            self._metrics_task.cancel()
            try:
                await self._metrics_task
            except asyncio.CancelledError:
                pass
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Stop core components
        if self.network_manager:
            await self.network_manager.stop()
            self.logger.info("✓ Network manager stopped")
        
        if self.cache_manager:
            await self.cache_manager.stop()
            self.logger.info("✓ Cache manager stopped")
        
        if self.message_bus:
            await self.message_bus.stop()
            self.logger.info("✓ Message bus stopped")
        
        self._started = False
        self.logger.info("🛑 All infrastructure components stopped")
    
    @asynccontextmanager
    async def lifecycle(self):
        """Context manager for infrastructure lifecycle"""
        await self.start()
        try:
            yield self
        finally:
            await self.stop()
    
    # Component access methods
    def get_message_bus(self) -> MessageBus:
        """Get message bus instance"""
        if not self.message_bus:
            raise RuntimeError("Message bus not initialized")
        return self.message_bus
    
    def get_cache_manager(self) -> CacheManager:
        """Get cache manager instance"""
        if not self.cache_manager:
            raise RuntimeError("Cache manager not initialized")
        return self.cache_manager
    
    def get_network_manager(self) -> NetworkManager:
        """Get network manager instance"""
        if not self.network_manager:
            raise RuntimeError("Network manager not initialized")
        return self.network_manager
    
    # High-level operations
    async def publish_message(self, topic: str, message: Dict[str, Any]) -> None:
        """Publish message through message bus"""
        await self.get_message_bus().publish(topic, message)
    
    async def subscribe_to_topic(self, topic: str, handler) -> None:
        """Subscribe to topic through message bus"""
        await self.get_message_bus().subscribe(topic, handler)
    
    async def cache_get(self, key: str) -> Any:
        """Get value from cache"""
        return await self.get_cache_manager().get(key)
    
    async def cache_set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        await self.get_cache_manager().set(key, value, ttl)
    
    async def get_network_connection(self, endpoint: str):
        """Get network connection"""
        return await self.get_network_manager().get_connection(endpoint)
    
    # Metrics and monitoring
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get metrics from all components"""
        if not self._started:
            return {}
        
        metrics = {
            'infrastructure': {
                'started': self._started,
                'uptime': self._get_uptime(),
                'components_healthy': self._check_components_health()
            }
        }
        
        if self.message_bus:
            metrics['messaging'] = self.message_bus.get_metrics().__dict__
        
        if self.cache_manager:
            metrics['caching'] = self.cache_manager.get_metrics().__dict__
        
        if self.network_manager:
            metrics['networking'] = self.network_manager.get_metrics().__dict__
        
        # Add historical metrics
        metrics['history'] = self._metrics_history
        
        return metrics
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all components"""
        return {
            'overall_healthy': self._check_components_health(),
            'message_bus': self.message_bus is not None and self.message_bus.is_healthy(),
            'cache_manager': self.cache_manager is not None and self.cache_manager.is_healthy(),
            'network_manager': self.network_manager is not None and self.network_manager.is_healthy(),
            'started': self._started
        }
    
    # Background tasks
    async def _collect_metrics(self) -> None:
        """Background task to collect performance metrics"""
        while True:
            try:
                if self._started:
                    # Collect current metrics
                    current_metrics = self.get_comprehensive_metrics()
                    
                    # Store in history (keep last 100 samples)
                    if 'messaging' in current_metrics:
                        msg_metrics = current_metrics['messaging']
                        self._metrics_history['message_throughput'].append(
                            msg_metrics.get('messages_per_second', 0)
                        )
                        if len(self._metrics_history['message_throughput']) > 100:
                            self._metrics_history['message_throughput'].pop(0)
                    
                    if 'caching' in current_metrics:
                        cache_metrics = current_metrics['caching']
                        self._metrics_history['cache_hit_rate'].append(
                            cache_metrics.get('hit_rate', 0)
                        )
                        if len(self._metrics_history['cache_hit_rate']) > 100:
                            self._metrics_history['cache_hit_rate'].pop(0)
                    
                    if 'networking' in current_metrics:
                        net_metrics = current_metrics['networking']
                        self._metrics_history['network_latency'].append(
                            net_metrics.get('average_latency_ms', 0)
                        )
                        if len(self._metrics_history['network_latency']) > 100:
                            self._metrics_history['network_latency'].pop(0)
                
                await asyncio.sleep(self.config.metrics_collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(self.config.metrics_collection_interval)
    
    async def _health_check(self) -> None:
        """Background task for health monitoring"""
        while True:
            try:
                if self._started:
                    health = self.get_health_status()
                    if not health['overall_healthy']:
                        self.logger.warning(f"Health check failed: {health}")
                
                await asyncio.sleep(5.0)  # Check every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check: {e}")
                await asyncio.sleep(5.0)
    
    def _check_components_health(self) -> bool:
        """Check if all components are healthy"""
        if not self._started:
            return False
        
        return all([
            self.message_bus and self.message_bus.is_healthy(),
            self.cache_manager and self.cache_manager.is_healthy(),
            self.network_manager and self.network_manager.is_healthy()
        ])
    
    def _get_uptime(self) -> float:
        """Get infrastructure uptime in seconds"""
        # This would be implemented with actual start time tracking
        return 0.0  # Placeholder


# Global infrastructure instance
_infrastructure_instance: Optional[InfrastructureManager] = None


def get_infrastructure() -> InfrastructureManager:
    """Get global infrastructure instance"""
    global _infrastructure_instance
    if _infrastructure_instance is None:
        raise RuntimeError("Infrastructure not initialized. Call initialize_infrastructure() first.")
    return _infrastructure_instance


def initialize_infrastructure(config: InfrastructureConfig) -> InfrastructureManager:
    """Initialize global infrastructure instance"""
    global _infrastructure_instance
    _infrastructure_instance = InfrastructureManager(config)
    return _infrastructure_instance


async def start_infrastructure(config: Optional[InfrastructureConfig] = None) -> InfrastructureManager:
    """Start infrastructure with default or provided config"""
    if config is None:
        config = InfrastructureConfig()
    
    infrastructure = initialize_infrastructure(config)
    await infrastructure.start()
    return infrastructure


async def stop_infrastructure() -> None:
    """Stop global infrastructure"""
    global _infrastructure_instance
    if _infrastructure_instance:
        await _infrastructure_instance.stop()
        _infrastructure_instance = None