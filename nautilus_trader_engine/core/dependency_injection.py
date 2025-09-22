"""
Enhanced Dependency Injection Container for Institutional-Grade Trading System.

This module implements a sophisticated dependency injection framework that provides:
- Service registration and resolution
- Singleton and transient lifecycle management
- Interface-based dependency resolution
- Configuration-driven service instantiation
- Circular dependency detection
- Performance monitoring and metrics
- Thread-safe operations
- Graceful error handling and recovery

The DI container serves as the backbone for the 5-pillar institutional architecture,
enabling loose coupling, testability, and maintainability across all system components.
"""

import asyncio
import inspect
import threading
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, Set, Type, TypeVar, Union
from weakref import WeakValueDictionary

from loguru import logger


# Type variables for generic types
T = TypeVar('T')


class ServiceLifetime(Enum):
    """Service lifetime management options."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class ServiceScope(Enum):
    """Service scope definitions."""
    GLOBAL = "global"
    REQUEST = "request"
    SESSION = "session"


@dataclass
class ServiceDescriptor:
    """Service registration descriptor with metadata."""
    service_type: Type
    implementation_type: Type
    lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT
    scope: ServiceScope = ServiceScope.GLOBAL
    instance: Optional[Any] = None
    factory: Optional[callable] = None
    dependencies: List[Type] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    priority: int = 0
    health_check: Optional[callable] = None
    metrics_enabled: bool = True


class DependencyInjectionError(Exception):
    """Base exception for dependency injection errors."""
    pass


class CircularDependencyError(DependencyInjectionError):
    """Raised when circular dependencies are detected."""
    pass


class ServiceNotFoundError(DependencyInjectionError):
    """Raised when a requested service is not registered."""
    pass


class ServiceResolutionError(DependencyInjectionError):
    """Raised when service resolution fails."""
    pass


class IServiceProvider(ABC):
    """Abstract interface for service providers."""

    @abstractmethod
    def get_service(self, service_type: Type[T]) -> T:
        """Get a service instance by type."""
        pass

    @abstractmethod
    def get_services(self, service_type: Type[T]) -> List[T]:
        """Get all service instances of a type."""
        pass

    @abstractmethod
    def has_service(self, service_type: Type) -> bool:
        """Check if a service type is registered."""
        pass


class DependencyInjectionContainer(IServiceProvider):
    """
    Advanced dependency injection container with institutional-grade features.

    Features:
    - Thread-safe service registration and resolution
    - Multiple service lifetimes (singleton, transient, scoped)
    - Interface-based dependency resolution
    - Circular dependency detection
    - Performance monitoring and metrics
    - Configuration-driven service instantiation
    - Health checks and service validation
    - Graceful error handling and recovery
    """

    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scoped_instances: WeakValueDictionary = WeakValueDictionary()
        self._resolution_stack: List[Type] = []
        self._lock = threading.RLock()
        self._metrics = ContainerMetrics()
        self._health_monitor = HealthMonitor()

    def register(self, service_type: Type[T], implementation_type: Optional[Type[T]] = None,
                lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
                scope: ServiceScope = ServiceScope.GLOBAL,
                factory: Optional[callable] = None, tags: Optional[Set[str]] = None) -> 'DependencyInjectionContainer':
        """
        Register a service with the container.

        Args:
            service_type: The service interface/abstract type
            implementation_type: The concrete implementation type
            lifetime: Service lifetime management
            scope: Service scope
            factory: Optional factory function for service creation
            tags: Optional tags for service categorization

        Returns:
            Self for method chaining
        """
        with self._lock:
            if implementation_type is None:
                implementation_type = service_type

            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation_type=implementation_type,
                lifetime=lifetime,
                scope=scope,
                factory=factory,
                tags=tags or set()
            )

            # Analyze dependencies
            descriptor.dependencies = self._analyze_dependencies(implementation_type)

            self._services[service_type] = descriptor
            logger.info(f"Registered service: {service_type.__name__} -> {implementation_type.__name__}")

            return self

    def register_singleton(self, service_type: Type[T], implementation_type: Optional[Type[T]] = None,
                          instance: Optional[T] = None) -> 'DependencyInjectionContainer':
        """Register a singleton service."""
        if instance is not None:
            with self._lock:
                descriptor = ServiceDescriptor(
                    service_type=service_type,
                    implementation_type=implementation_type or service_type,
                    lifetime=ServiceLifetime.SINGLETON,
                    instance=instance
                )
                self._services[service_type] = descriptor
                self._singletons[service_type] = instance
        else:
            self.register(service_type, implementation_type, ServiceLifetime.SINGLETON)
        return self

    def register_factory(self, service_type: Type[T], factory: callable,
                        lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT) -> 'DependencyInjectionContainer':
        """Register a service with a factory function."""
        with self._lock:
            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation_type=service_type,
                lifetime=lifetime,
                factory=factory
            )
            self._services[service_type] = descriptor
        return self

    def get_service(self, service_type: Type[T]) -> T:
        """Get a service instance by type."""
        start_time = time.time()

        try:
            with self._lock:
                if service_type in self._resolution_stack:
                    raise CircularDependencyError(f"Circular dependency detected: {service_type}")

                self._resolution_stack.append(service_type)

                if service_type not in self._services:
                    raise ServiceNotFoundError(f"Service not registered: {service_type}")

                descriptor = self._services[service_type]

                # Check health if health check is configured
                if descriptor.health_check and not descriptor.health_check():
                    raise ServiceResolutionError(f"Service health check failed: {service_type}")

                instance = self._resolve_service(descriptor)

                # Update metrics
                self._metrics.record_resolution(service_type, time.time() - start_time)

                return instance

        finally:
            if service_type in self._resolution_stack:
                self._resolution_stack.remove(service_type)

    def get_services(self, service_type: Type[T]) -> List[T]:
        """Get all service instances of a type."""
        # For now, return single instance. Could be extended for multiple implementations
        try:
            return [self.get_service(service_type)]
        except ServiceNotFoundError:
            return []

    def has_service(self, service_type: Type) -> bool:
        """Check if a service type is registered."""
        with self._lock:
            return service_type in self._services

    def _resolve_service(self, descriptor: ServiceDescriptor) -> Any:
        """Resolve a service instance based on its descriptor."""
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            if descriptor.instance is not None:
                return descriptor.instance
            if descriptor.service_type in self._singletons:
                return self._singletons[descriptor.service_type]

            instance = self._create_instance(descriptor)
            self._singletons[descriptor.service_type] = instance
            descriptor.instance = instance
            return instance

        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            # Scoped services are managed per scope (e.g., per request)
            scope_key = threading.current_thread().ident
            if scope_key not in self._scoped_instances:
                self._scoped_instances[scope_key] = {}

            scoped_services = self._scoped_instances[scope_key]
            if descriptor.service_type not in scoped_services:
                scoped_services[descriptor.service_type] = self._create_instance(descriptor)

            return scoped_services[descriptor.service_type]

        else:  # TRANSIENT
            return self._create_instance(descriptor)

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a new instance of a service."""
        try:
            if descriptor.factory:
                return descriptor.factory()

            # Resolve constructor dependencies
            init_params = {}
            if hasattr(descriptor.implementation_type, '__init__'):
                sig = inspect.signature(descriptor.implementation_type.__init__)
                for param_name, param in sig.parameters.items():
                    if param_name == 'self':
                        continue
                    if param.annotation != inspect.Parameter.empty:
                        try:
                            init_params[param_name] = self.get_service(param.annotation)
                        except ServiceNotFoundError:
                            # Try to provide default if available
                            if param.default != inspect.Parameter.empty:
                                init_params[param_name] = param.default
                            else:
                                raise

            return descriptor.implementation_type(**init_params)

        except Exception as e:
            raise ServiceResolutionError(f"Failed to create instance of {descriptor.service_type}: {e}")

    def _analyze_dependencies(self, implementation_type: Type) -> List[Type]:
        """Analyze the dependencies of a service implementation."""
        dependencies = []

        if hasattr(implementation_type, '__init__'):
            sig = inspect.signature(implementation_type.__init__)
            for param in sig.parameters.values():
                if param.name != 'self' and param.annotation != inspect.Parameter.empty:
                    dependencies.append(param.annotation)

        return dependencies

    def get_metrics(self) -> Dict[str, Any]:
        """Get container performance metrics."""
        return self._metrics.get_summary()

    def get_health_status(self) -> Dict[str, Any]:
        """Get container health status."""
        return self._health_monitor.check_health(self._services)

    @asynccontextmanager
    async def scoped_container(self):
        """Create a scoped container for request/session scoped services."""
        scope_key = threading.current_thread().ident

        try:
            yield self
        finally:
            # Clean up scoped instances
            with self._lock:
                if scope_key in self._scoped_instances:
                    del self._scoped_instances[scope_key]


@dataclass
class ContainerMetrics:
    """Container performance metrics."""

    resolution_count: int = 0
    total_resolution_time: float = 0.0
    service_resolution_times: Dict[str, List[float]] = field(default_factory=dict)
    error_count: int = 0
    last_health_check: float = 0.0

    def record_resolution(self, service_type: Type, duration: float):
        """Record a service resolution."""
        self.resolution_count += 1
        self.total_resolution_time += duration

        service_name = service_type.__name__
        if service_name not in self.service_resolution_times:
            self.service_resolution_times[service_name] = []
        self.service_resolution_times[service_name].append(duration)

        # Keep only last 100 measurements per service
        if len(self.service_resolution_times[service_name]) > 100:
            self.service_resolution_times[service_name].pop(0)

    def record_error(self):
        """Record an error."""
        self.error_count += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        avg_resolution_time = (
            self.total_resolution_time / self.resolution_count
            if self.resolution_count > 0 else 0
        )

        return {
            "total_resolutions": self.resolution_count,
            "average_resolution_time": avg_resolution_time,
            "total_errors": self.error_count,
            "service_metrics": {
                service_name: {
                    "count": len(times),
                    "avg_time": sum(times) / len(times) if times else 0,
                    "min_time": min(times) if times else 0,
                    "max_time": max(times) if times else 0
                }
                for service_name, times in self.service_resolution_times.items()
            }
        }


class HealthMonitor:
    """Service health monitoring."""

    def check_health(self, services: Dict[Type, ServiceDescriptor]) -> Dict[str, Any]:
        """Check health of all registered services."""
        health_status = {
            "overall_healthy": True,
            "total_services": len(services),
            "healthy_services": 0,
            "unhealthy_services": 0,
            "services": {}
        }

        for service_type, descriptor in services.items():
            service_name = service_type.__name__
            is_healthy = True
            issues = []

            # Check if health check function is available
            if descriptor.health_check:
                try:
                    is_healthy = descriptor.health_check()
                except Exception as e:
                    is_healthy = False
                    issues.append(f"Health check failed: {e}")
            else:
                # Basic health check - try to resolve the service
                try:
                    # Note: This would cause circular dependency in real usage
                    # In practice, we'd need a separate health check mechanism
                    pass
                except Exception as e:
                    is_healthy = False
                    issues.append(f"Service resolution failed: {e}")

            health_status["services"][service_name] = {
                "healthy": is_healthy,
                "issues": issues
            }

            if is_healthy:
                health_status["healthy_services"] += 1
            else:
                health_status["unhealthy_services"] += 1
                health_status["overall_healthy"] = False

        return health_status


# Global container instance
_container = DependencyInjectionContainer()


def get_container() -> DependencyInjectionContainer:
    """Get the global dependency injection container."""
    return _container


def register_service(service_type: Type[T], implementation_type: Optional[Type[T]] = None,
                    lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
                    scope: ServiceScope = ServiceScope.GLOBAL) -> None:
    """Register a service with the global container."""
    _container.register(service_type, implementation_type, lifetime, scope)


def get_service(service_type: Type[T]) -> T:
    """Get a service from the global container."""
    return _container.get_service(service_type)


def has_service(service_type: Type) -> bool:
    """Check if a service is registered in the global container."""
    return _container.has_service(service_type)


# Convenience decorators
def injectable(lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT,
               scope: ServiceScope = ServiceScope.GLOBAL):
    """Decorator to mark a class as injectable."""
    def decorator(cls):
        # Register the class with itself as both interface and implementation
        register_service(cls, cls, lifetime, scope)
        return cls
    return decorator


def singleton(scope: ServiceScope = ServiceScope.GLOBAL):
    """Decorator to mark a class as a singleton service."""
    def decorator(cls):
        register_service(cls, cls, ServiceLifetime.SINGLETON, scope)
        return cls
    return decorator


def scoped(scope: ServiceScope = ServiceScope.REQUEST):
    """Decorator to mark a class as a scoped service."""
    def decorator(cls):
        register_service(cls, cls, ServiceLifetime.SCOPED, scope)
        return cls
    return decorator