"""
Enhanced Dependency Injection Container for Nautilus Trader Engine
Implements a robust DI system for better testability and modularity.
"""

import inspect
import threading
from typing import Any, Dict, Type, TypeVar, Optional, Callable, Union
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class Scope(Enum):
    """Dependency injection scopes."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class InjectionError(Exception):
    """Base exception for dependency injection errors."""
    pass


class CircularDependencyError(InjectionError):
    """Raised when circular dependencies are detected."""
    pass


class ServiceNotFoundError(InjectionError):
    """Raised when a requested service is not registered."""
    pass


@dataclass
class ServiceDescriptor:
    """Descriptor for a registered service."""
    service_type: Type
    implementation_type: Type
    scope: Scope
    factory: Optional[Callable] = None
    instance: Any = None
    dependencies: Dict[str, Type] = field(default_factory=dict)


class DependencyContainer:
    """
    Advanced dependency injection container with support for:
    - Multiple scopes (singleton, transient, scoped)
    - Factory methods
    - Circular dependency detection
    - Thread-safe operations
    - Service lifetime management
    """

    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._scoped_instances: Dict[str, Dict[Type, Any]] = {}
        self._lock = threading.RLock()
        self._current_scope: Optional[str] = None
        self._resolution_stack: list = []

    def register_singleton(self, service_type: Type[T], implementation_type: Optional[Type[T]] = None,
                          factory: Optional[Callable[[], T]] = None) -> None:
        """Register a singleton service."""
        self._register(service_type, implementation_type or service_type, Scope.SINGLETON, factory)

    def register_transient(self, service_type: Type[T], implementation_type: Optional[Type[T]] = None,
                          factory: Optional[Callable[[], T]] = None) -> None:
        """Register a transient service."""
        self._register(service_type, implementation_type or service_type, Scope.TRANSIENT, factory)

    def register_scoped(self, service_type: Type[T], implementation_type: Optional[Type[T]] = None,
                       factory: Optional[Callable[[], T]] = None) -> None:
        """Register a scoped service."""
        self._register(service_type, implementation_type or service_type, Scope.SCOPED, factory)

    def _register(self, service_type: Type[T], implementation_type: Type[T],
                 scope: Scope, factory: Optional[Callable[[], T]] = None) -> None:
        """Internal registration method."""
        with self._lock:
            if service_type in self._services:
                logger.warning(f"Service {service_type} is being overwritten")

            # Analyze dependencies
            dependencies = self._analyze_dependencies(implementation_type)

            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation_type=implementation_type,
                scope=scope,
                factory=factory,
                dependencies=dependencies
            )

            self._services[service_type] = descriptor
            logger.debug(f"Registered service: {service_type} -> {implementation_type} ({scope.value})")

    def _analyze_dependencies(self, implementation_type: Type) -> Dict[str, Type]:
        """Analyze constructor dependencies of a type."""
        if not hasattr(implementation_type, '__init__'):
            return {}

        signature = inspect.signature(implementation_type.__init__)
        dependencies = {}

        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue

            if param.annotation != inspect.Parameter.empty:
                dependencies[param_name] = param.annotation
            else:
                # Try to infer from default value
                if param.default != inspect.Parameter.empty:
                    dependencies[param_name] = type(param.default)

        return dependencies

    def resolve(self, service_type: Type[T], scope_name: Optional[str] = None) -> T:
        """Resolve a service instance."""
        with self._lock:
            if service_type in self._resolution_stack:
                raise CircularDependencyError(f"Circular dependency detected: {service_type}")

            self._resolution_stack.append(service_type)

            try:
                if service_type not in self._services:
                    raise ServiceNotFoundError(f"Service {service_type} is not registered")

                descriptor = self._services[service_type]

                # Handle different scopes
                if descriptor.scope == Scope.SINGLETON:
                    if descriptor.instance is None:
                        descriptor.instance = self._create_instance(descriptor)
                    return descriptor.instance

                elif descriptor.scope == Scope.TRANSIENT:
                    return self._create_instance(descriptor)

                elif descriptor.scope == Scope.SCOPED:
                    scope_key = scope_name or self._current_scope or "default"
                    if scope_key not in self._scoped_instances:
                        self._scoped_instances[scope_key] = {}

                    if service_type not in self._scoped_instances[scope_key]:
                        self._scoped_instances[scope_key][service_type] = self._create_instance(descriptor)

                    return self._scoped_instances[scope_key][service_type]

            finally:
                self._resolution_stack.pop()

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a new instance of a service."""
        if descriptor.factory:
            return descriptor.factory()

        # Resolve dependencies
        kwargs = {}
        for param_name, dep_type in descriptor.dependencies.items():
            try:
                kwargs[param_name] = self.resolve(dep_type)
            except ServiceNotFoundError:
                # Try to create with default if available
                if hasattr(descriptor.implementation_type, '__init__'):
                    sig = inspect.signature(descriptor.implementation_type.__init__)
                    if param_name in sig.parameters:
                        param = sig.parameters[param_name]
                        if param.default != inspect.Parameter.empty:
                            kwargs[param_name] = param.default
                        else:
                            raise

        return descriptor.implementation_type(**kwargs)

    @contextmanager
    def scope(self, scope_name: str):
        """Create a scoped context for scoped services."""
        old_scope = self._current_scope
        self._current_scope = scope_name

        try:
            yield
        finally:
            # Clean up scoped instances
            if scope_name in self._scoped_instances:
                del self._scoped_instances[scope_name]
            self._current_scope = old_scope

    def clear_scoped_instances(self, scope_name: Optional[str] = None) -> None:
        """Clear scoped instances."""
        with self._lock:
            if scope_name:
                self._scoped_instances.pop(scope_name, None)
            else:
                self._scoped_instances.clear()

    def get_registered_services(self) -> Dict[Type, ServiceDescriptor]:
        """Get all registered services."""
        return self._services.copy()

    def is_registered(self, service_type: Type) -> bool:
        """Check if a service type is registered."""
        return service_type in self._services


# Global container instance
_container = DependencyContainer()


def get_container() -> DependencyContainer:
    """Get the global dependency injection container."""
    return _container


def register_singleton(service_type: Type[T], implementation_type: Optional[Type[T]] = None,
                      factory: Optional[Callable[[], T]] = None) -> None:
    """Register a singleton service globally."""
    _container.register_singleton(service_type, implementation_type, factory)


def register_transient(service_type: Type[T], implementation_type: Optional[Type[T]] = None,
                      factory: Optional[Callable[[], T]] = None) -> None:
    """Register a transient service globally."""
    _container.register_transient(service_type, implementation_type, factory)


def register_scoped(service_type: Type[T], implementation_type: Optional[Type[T]] = None,
                   factory: Optional[Callable[[], T]] = None) -> None:
    """Register a scoped service globally."""
    _container.register_scoped(service_type, implementation_type, factory)


def resolve(service_type: Type[T], scope_name: Optional[str] = None) -> T:
    """Resolve a service instance globally."""
    return _container.resolve(service_type, scope_name)


def inject(func: Callable) -> Callable:
    """
    Decorator to automatically inject dependencies into a function.
    Analyzes function signature and resolves dependencies.
    """
    signature = inspect.signature(func)
    param_types = {}

    for param_name, param in signature.parameters.items():
        if param.annotation != inspect.Parameter.empty:
            param_types[param_name] = param.annotation

    def wrapper(*args, **kwargs):
        # Resolve missing dependencies
        resolved_kwargs = {}
        for param_name, param_type in param_types.items():
            if param_name not in kwargs and param_name not in [p.name for p in signature.parameters.values() if p.kind == inspect.Parameter.VAR_POSITIONAL]:
                try:
                    resolved_kwargs[param_name] = resolve(param_type)
                except ServiceNotFoundError:
                    pass  # Let the function handle missing parameters

        kwargs.update(resolved_kwargs)
        return func(*args, **kwargs)

    return wrapper


# Example usage and configuration
def configure_container():
    """Configure the global container with common services."""
    # This would be called during application startup
    # Example registrations would go here
    pass


if __name__ == "__main__":
    # Example usage
    class Database:
        def __init__(self, connection_string: str = "default"):
            self.connection_string = connection_string

    class UserService:
        def __init__(self, database: Database):
            self.database = database

    # Register services
    register_singleton(Database)
    register_transient(UserService)

    # Resolve services
    db = resolve(Database)
    user_service = resolve(UserService)

    print(f"Database connection: {db.connection_string}")
    print(f"UserService has database: {user_service.database is not None}")