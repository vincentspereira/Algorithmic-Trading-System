"""
Unit Tests for Dependency Injection Container.

Tests the core dependency injection functionality including:
- Service registration and resolution
- Singleton and scoped lifetimes
- Service decoration and interception
- Circular dependency detection
- Service disposal and cleanup
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock
from nautilus_trader_engine.core.dependency_injection import (
    DependencyInjectionContainer,
    ServiceLifetime,
    ServiceResolutionError,
    CircularDependencyError,
    injectable,
    singleton,
    get_container
)


class TestService:
    """Test service for dependency injection testing."""

    def __init__(self, dependency=None):
        self.dependency = dependency
        self.initialized = True

    def get_value(self):
        return "test_value"

    async def async_method(self):
        return "async_result"


class DependentService:
    """Service that depends on TestService."""

    def __init__(self, test_service: TestService):
        self.test_service = test_service

    def get_combined_value(self):
        return f"dependent_{self.test_service.get_value()}"


class CircularServiceA:
    """Service for testing circular dependencies."""

    def __init__(self, service_b):
        self.service_b = service_b


class CircularServiceB:
    """Service for testing circular dependencies."""

    def __init__(self, service_a):
        self.service_a = service_a


class DisposableService:
    """Service that implements disposal."""

    def __init__(self):
        self.disposed = False

    def dispose(self):
        self.disposed = True


class TestDependencyInjectionContainer:

    def setup_method(self):
        """Set up test fixtures."""
        self.container = DependencyInjectionContainer()

    def test_container_initialization(self):
        """Test container initializes correctly."""
        assert self.container.services == {}
        assert self.container.singletons == {}
        assert self.container.scoped_services == {}

    def test_register_transient_service(self):
        """Test registering a transient service."""
        self.container.register(TestService, TestService, ServiceLifetime.TRANSIENT)

        # Service should be registered
        assert TestService in self.container.services
        service_info = self.container.services[TestService]
        assert service_info.implementation == TestService
        assert service_info.lifetime == ServiceLifetime.TRANSIENT

    def test_register_singleton_service(self):
        """Test registering a singleton service."""
        self.container.register(TestService, TestService, ServiceLifetime.SINGLETON)

        assert TestService in self.container.services
        service_info = self.container.services[TestService]
        assert service_info.lifetime == ServiceLifetime.SINGLETON

    def test_register_with_factory_function(self):
        """Test registering a service with a factory function."""
        def factory():
            return TestService()

        self.container.register(TestService, factory, ServiceLifetime.TRANSIENT)
        assert TestService in self.container.services

    def test_resolve_transient_service(self):
        """Test resolving a transient service."""
        self.container.register(TestService, TestService, ServiceLifetime.TRANSIENT)

        service1 = self.container.resolve(TestService)
        service2 = self.container.resolve(TestService)

        # Transient services should be different instances
        assert isinstance(service1, TestService)
        assert isinstance(service2, TestService)
        assert service1 is not service2

    def test_resolve_singleton_service(self):
        """Test resolving a singleton service."""
        self.container.register(TestService, TestService, ServiceLifetime.SINGLETON)

        service1 = self.container.resolve(TestService)
        service2 = self.container.resolve(TestService)

        # Singleton services should be the same instance
        assert isinstance(service1, TestService)
        assert isinstance(service2, TestService)
        assert service1 is service2

    def test_resolve_with_dependencies(self):
        """Test resolving services with dependencies."""
        self.container.register(TestService, TestService, ServiceLifetime.TRANSIENT)
        self.container.register(DependentService, DependentService, ServiceLifetime.TRANSIENT)

        dependent = self.container.resolve(DependentService)

        assert isinstance(dependent, DependentService)
        assert isinstance(dependent.test_service, TestService)
        assert dependent.get_combined_value() == "dependent_test_value"

    def test_resolve_unregistered_service(self):
        """Test resolving an unregistered service raises error."""
        with pytest.raises(ServiceResolutionError):
            self.container.resolve(TestService)

    def test_circular_dependency_detection(self):
        """Test that circular dependencies are detected."""
        self.container.register(CircularServiceA, CircularServiceA, ServiceLifetime.TRANSIENT)
        self.container.register(CircularServiceB, CircularServiceB, ServiceLifetime.TRANSIENT)

        with pytest.raises(CircularDependencyError):
            self.container.resolve(CircularServiceA)

    def test_service_disposal(self):
        """Test service disposal for disposable services."""
        self.container.register(DisposableService, DisposableService, ServiceLifetime.SINGLETON)

        service = self.container.resolve(DisposableService)
        assert not service.disposed

        self.container.dispose()
        assert service.disposed

    def test_register_with_interface(self):
        """Test registering service with interface."""
        # Register concrete implementation for an interface
        self.container.register(TestService, TestService, ServiceLifetime.TRANSIENT)

        # Should be able to resolve by concrete type
        service = self.container.resolve(TestService)
        assert isinstance(service, TestService)

    def test_register_duplicate_service(self):
        """Test registering the same service twice."""
        self.container.register(TestService, TestService, ServiceLifetime.TRANSIENT)
        # Should not raise error, should overwrite
        self.container.register(TestService, TestService, ServiceLifetime.SINGLETON)

        service_info = self.container.services[TestService]
        assert service_info.lifetime == ServiceLifetime.SINGLETON

    def test_resolve_with_parameters(self):
        """Test resolving service with additional parameters."""
        self.container.register(TestService, TestService, ServiceLifetime.TRANSIENT)

        # Resolve with additional parameter
        service = self.container.resolve(TestService, dependency="custom_dep")
        assert isinstance(service, TestService)
        assert service.dependency == "custom_dep"

    def test_scoped_lifetime(self):
        """Test scoped service lifetime."""
        self.container.register(TestService, TestService, ServiceLifetime.SCOPED)

        # Create a scope
        with self.container.create_scope() as scope:
            service1 = scope.resolve(TestService)
            service2 = scope.resolve(TestService)

            # Should be same instance within scope
            assert service1 is service2

        # Different scope should give different instance
        with self.container.create_scope() as scope:
            service3 = scope.resolve(TestService)
            assert service3 is not service1

    def test_async_service_resolution(self):
        """Test async service resolution."""
        async def async_factory():
            await asyncio.sleep(0.001)  # Simulate async work
            return TestService()

        self.container.register(TestService, async_factory, ServiceLifetime.TRANSIENT)

        # Should work with async resolution
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            service = loop.run_until_complete(self.container.resolve_async(TestService))
            assert isinstance(service, TestService)
        finally:
            loop.close()


class TestDecorators:

    def setup_method(self):
        """Set up test fixtures."""
        self.container = DependencyInjectionContainer()

    def test_injectable_decorator(self):
        """Test the injectable decorator."""
        @injectable(lifetime=ServiceLifetime.SINGLETON)
        class InjectableService:
            def __init__(self):
                self.value = "injectable"

        # Register the service
        self.container.register(InjectableService, InjectableService, ServiceLifetime.SINGLETON)

        service = self.container.resolve(InjectableService)
        assert isinstance(service, InjectableService)
        assert service.value == "injectable"

    def test_singleton_decorator(self):
        """Test the singleton decorator."""
        @singleton
        class SingletonService:
            def __init__(self):
                self.id = id(self)

        self.container.register(SingletonService, SingletonService, ServiceLifetime.SINGLETON)

        service1 = self.container.resolve(SingletonService)
        service2 = self.container.resolve(SingletonService)

        assert service1.id == service2.id


class TestGlobalContainer:

    def test_get_container_returns_same_instance(self):
        """Test that get_container returns the same instance."""
        container1 = get_container()
        container2 = get_container()

        assert container1 is container2

    def test_global_container_registration(self):
        """Test registering services in global container."""
        container = get_container()

        # Register a test service
        container.register(TestService, TestService, ServiceLifetime.TRANSIENT)

        # Should be able to resolve it
        service = container.resolve(TestService)
        assert isinstance(service, TestService)


class TestServiceDecoration:

    def setup_method(self):
        """Set up test fixtures."""
        self.container = DependencyInjectionContainer()

    def test_service_decoration(self):
        """Test service decoration functionality."""
        def logging_decorator(service):
            """Decorator that adds logging."""
            original_method = service.get_value
            def logged_method():
                print("Calling get_value")
                return original_method()
            service.get_value = logged_method
            return service

        self.container.register(TestService, TestService, ServiceLifetime.TRANSIENT)
        self.container.decorate(TestService, logging_decorator)

        service = self.container.resolve(TestService)
        assert isinstance(service, TestService)

        # The method should be decorated
        # Note: In a real implementation, we'd capture the print output
        result = service.get_value()
        assert result == "test_value"

    def test_multiple_decorators(self):
        """Test applying multiple decorators."""
        def decorator1(service):
            service.decorator1_applied = True
            return service

        def decorator2(service):
            service.decorator2_applied = True
            return service

        self.container.register(TestService, TestService, ServiceLifetime.TRANSIENT)
        self.container.decorate(TestService, decorator1)
        self.container.decorate(TestService, decorator2)

        service = self.container.resolve(TestService)
        assert hasattr(service, 'decorator1_applied')
        assert hasattr(service, 'decorator2_applied')
        assert service.decorator1_applied
        assert service.decorator2_applied


class TestErrorHandling:

    def setup_method(self):
        """Set up test fixtures."""
        self.container = DependencyInjectionContainer()

    def test_resolve_with_invalid_factory(self):
        """Test resolving with invalid factory function."""
        def invalid_factory():
            raise ValueError("Factory error")

        self.container.register(TestService, invalid_factory, ServiceLifetime.TRANSIENT)

        with pytest.raises(ServiceResolutionError):
            self.container.resolve(TestService)

    def test_resolve_with_missing_dependency(self):
        """Test resolving service with missing dependency."""
        self.container.register(DependentService, DependentService, ServiceLifetime.TRANSIENT)

        # Don't register TestService dependency
        with pytest.raises(ServiceResolutionError):
            self.container.resolve(DependentService)

    def test_dispose_non_disposable_service(self):
        """Test disposing services that don't implement dispose."""
        self.container.register(TestService, TestService, ServiceLifetime.SINGLETON)

        service = self.container.resolve(TestService)

        # Should not raise error even if service doesn't have dispose method
        self.container.dispose()