"""
Unit tests for base architecture components.
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nautilus_trader_engine.tests.testing_framework import TestCase, unit_test
from nautilus_trader_engine.core.base.dependency_injection import (
    DependencyContainer, ServiceLifetime, inject, injectable
)
from nautilus_trader_engine.core.base.plugin_system import (
    PluginManager, PluginInterface, PluginMetadata
)
from nautilus_trader_engine.core.base.configuration_manager import (
    ConfigurationManager, ConfigValidator
)
from nautilus_trader_engine.core.base.event_system import (
    EventSystem, Event, EventHandler, EventPriority
)


class TestDependencyInjection(TestCase):
    """Test cases for dependency injection system."""

    def setUp(self):
        super().setUp()
        self.container = DependencyContainer()

    @unit_test()
    def test_register_transient_service(self):
        """Test registering a transient service."""
        @injectable(lifetime=ServiceLifetime.TRANSIENT)
        class TestService:
            def __init__(self):
                self.value = 42

        self.container.register(TestService)
        service1 = self.container.resolve(TestService)
        service2 = self.container.resolve(TestService)

        self.assertIsInstance(service1, TestService)
        self.assertIsInstance(service2, TestService)
        self.assertNotEqual(id(service1), id(service2))  # Different instances

    @unit_test()
    def test_register_singleton_service(self):
        """Test registering a singleton service."""
        @injectable(lifetime=ServiceLifetime.SINGLETON)
        class TestService:
            def __init__(self):
                self.value = 42

        self.container.register(TestService)
        service1 = self.container.resolve(TestService)
        service2 = self.container.resolve(TestService)

        self.assertIsInstance(service1, TestService)
        self.assertIsInstance(service2, TestService)
        self.assertEqual(id(service1), id(service2))  # Same instance

    @unit_test()
    def test_dependency_injection(self):
        """Test dependency injection between services."""
        @injectable(lifetime=ServiceLifetime.SINGLETON)
        class Logger:
            def log(self, message: str):
                return f"LOG: {message}"

        @injectable(lifetime=ServiceLifetime.TRANSIENT)
        class Calculator:
            def __init__(self, logger: Logger):
                self.logger = logger

            def add(self, a: int, b: int) -> int:
                result = a + b
                self.logger.log(f"Calculated {a} + {b} = {result}")
                return result

        self.container.register(Logger)
        self.container.register(Calculator)

        calc = self.container.resolve(Calculator)
        result = calc.add(5, 3)

        self.assertEqual(result, 8)
        self.assertIsInstance(calc.logger, Logger)

    @unit_test()
    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        @injectable()
        class ServiceA:
            def __init__(self, service_b):
                self.service_b = service_b

        @injectable()
        class ServiceB:
            def __init__(self, service_a):
                self.service_a = service_a

        self.container.register(ServiceA)
        self.container.register(ServiceB)

        with self.assertRaises(RuntimeError):
            self.container.resolve(ServiceA)

    @unit_test()
    def test_service_override(self):
        """Test service registration override."""
        @injectable()
        class TestService:
            def __init__(self):
                self.value = "original"

        @injectable()
        class TestServiceOverride:
            def __init__(self):
                self.value = "override"

        self.container.register(TestService)
        service1 = self.container.resolve(TestService)
        self.assertEqual(service1.value, "original")

        # Override registration
        self.container.register(TestServiceOverride, name="TestService")
        service2 = self.container.resolve(TestService)
        self.assertEqual(service2.value, "override")


class TestPluginSystem(TestCase):
    """Test cases for plugin system."""

    def setUp(self):
        super().setUp()
        self.plugin_manager = PluginManager()

    @unit_test()
    def test_plugin_registration(self):
        """Test plugin registration and loading."""
        class TestPlugin(PluginInterface):
            def __init__(self):
                self.metadata = PluginMetadata(
                    name="test_plugin",
                    version="1.0.0",
                    description="Test plugin"
                )

            def initialize(self):
                pass

            def shutdown(self):
                pass

            def execute(self):
                return "test_result"

        plugin = TestPlugin()
        self.plugin_manager.register_plugin(plugin)

        loaded_plugin = self.plugin_manager.get_plugin("test_plugin")
        self.assertIsNotNone(loaded_plugin)
        self.assertEqual(loaded_plugin.metadata.name, "test_plugin")

    @unit_test()
    def test_plugin_execution(self):
        """Test plugin execution."""
        class TestPlugin(PluginInterface):
            def __init__(self):
                self.metadata = PluginMetadata(
                    name="calculator_plugin",
                    version="1.0.0",
                    description="Calculator plugin"
                )
                self.executed = False

            def initialize(self):
                pass

            def shutdown(self):
                pass

            def execute(self, a: int, b: int) -> int:
                self.executed = True
                return a + b

        plugin = TestPlugin()
        self.plugin_manager.register_plugin(plugin)

        result = self.plugin_manager.execute_plugin("calculator_plugin", 5, 3)
        self.assertEqual(result, 8)
        self.assertTrue(plugin.executed)

    @unit_test()
    def test_plugin_dependencies(self):
        """Test plugin dependency resolution."""
        class BasePlugin(PluginInterface):
            def __init__(self):
                self.metadata = PluginMetadata(
                    name="base_plugin",
                    version="1.0.0",
                    description="Base plugin"
                )

            def initialize(self):
                pass

            def shutdown(self):
                pass

            def execute(self):
                return "base"

        class DependentPlugin(PluginInterface):
            def __init__(self):
                self.metadata = PluginMetadata(
                    name="dependent_plugin",
                    version="1.0.0",
                    description="Dependent plugin",
                    dependencies=["base_plugin"]
                )

            def initialize(self):
                pass

            def shutdown(self):
                pass

            def execute(self):
                return "dependent"

        base_plugin = BasePlugin()
        dependent_plugin = DependentPlugin()

        self.plugin_manager.register_plugin(base_plugin)
        self.plugin_manager.register_plugin(dependent_plugin)

        # Should resolve dependencies automatically
        result = self.plugin_manager.execute_plugin("dependent_plugin")
        self.assertEqual(result, "dependent")

    @unit_test()
    def test_plugin_unloading(self):
        """Test plugin unloading."""
        class TestPlugin(PluginInterface):
            def __init__(self):
                self.metadata = PluginMetadata(
                    name="unload_test_plugin",
                    version="1.0.0",
                    description="Unload test plugin"
                )
                self.shutdown_called = False

            def initialize(self):
                pass

            def shutdown(self):
                self.shutdown_called = True

            def execute(self):
                return "test"

        plugin = TestPlugin()
        self.plugin_manager.register_plugin(plugin)

        # Verify plugin is loaded
        self.assertIsNotNone(self.plugin_manager.get_plugin("unload_test_plugin"))

        # Unload plugin
        self.plugin_manager.unload_plugin("unload_test_plugin")

        # Verify plugin is unloaded
        self.assertIsNone(self.plugin_manager.get_plugin("unload_test_plugin"))
        self.assertTrue(plugin.shutdown_called)


class TestConfigurationManager(TestCase):
    """Test cases for configuration management."""

    def setUp(self):
        super().setUp()
        self.config_manager = ConfigurationManager()

    @unit_test()
    def test_configuration_loading(self):
        """Test configuration loading from dictionary."""
        config_data = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "trading_db"
            },
            "trading": {
                "max_position_size": 100000,
                "risk_limit": 0.02
            }
        }

        self.config_manager.load_from_dict(config_data)

        self.assertEqual(self.config_manager.get("database.host"), "localhost")
        self.assertEqual(self.config_manager.get("database.port"), 5432)
        self.assertEqual(self.config_manager.get("trading.max_position_size"), 100000)

    @unit_test()
    def test_configuration_validation(self):
        """Test configuration validation."""
        schema = {
            "type": "object",
            "properties": {
                "database": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "integer", "minimum": 1, "maximum": 65535}
                    },
                    "required": ["host", "port"]
                }
            },
            "required": ["database"]
        }

        validator = ConfigValidator(schema)

        # Valid config
        valid_config = {
            "database": {
                "host": "localhost",
                "port": 5432
            }
        }

        self.assertTrue(validator.validate(valid_config))

        # Invalid config
        invalid_config = {
            "database": {
                "host": "localhost",
                "port": 99999  # Invalid port
            }
        }

        self.assertFalse(validator.validate(invalid_config))

    @unit_test()
    def test_configuration_environment_override(self):
        """Test environment variable override."""
        config_data = {
            "database": {
                "host": "localhost",
                "port": 5432
            }
        }

        self.config_manager.load_from_dict(config_data)

        # Override with environment variable
        with patch.dict(os.environ, {"DATABASE_HOST": "production-db"}):
            self.config_manager.load_from_environment()
            self.assertEqual(self.config_manager.get("database.host"), "production-db")

    @unit_test()
    def test_configuration_hot_reload(self):
        """Test configuration hot reload."""
        config_data = {
            "trading": {
                "max_position_size": 100000
            }
        }

        self.config_manager.load_from_dict(config_data)
        self.assertEqual(self.config_manager.get("trading.max_position_size"), 100000)

        # Update configuration
        new_config = {
            "trading": {
                "max_position_size": 200000
            }
        }

        self.config_manager.load_from_dict(new_config)
        self.assertEqual(self.config_manager.get("trading.max_position_size"), 200000)


class TestEventSystem(TestCase):
    """Test cases for event system."""

    def setUp(self):
        super().setUp()
        self.event_system = EventSystem()

    @unit_test()
    def test_event_subscription(self):
        """Test event subscription and publishing."""
        events_received = []

        def event_handler(event: Event):
            events_received.append(event)

        # Subscribe to event
        self.event_system.subscribe("test_event", event_handler)

        # Publish event
        test_event = Event("test_event", {"data": "test"})
        self.event_system.publish(test_event)

        # Verify event was received
        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0].type, "test_event")
        self.assertEqual(events_received[0].data["data"], "test")

    @unit_test()
    def test_event_priority(self):
        """Test event handler priority."""
        execution_order = []

        def high_priority_handler(event: Event):
            execution_order.append("high")

        def normal_priority_handler(event: Event):
            execution_order.append("normal")

        def low_priority_handler(event: Event):
            execution_order.append("low")

        # Subscribe with different priorities
        self.event_system.subscribe("test_event", high_priority_handler, EventPriority.HIGH)
        self.event_system.subscribe("test_event", normal_priority_handler, EventPriority.NORMAL)
        self.event_system.subscribe("test_event", low_priority_handler, EventPriority.LOW)

        # Publish event
        test_event = Event("test_event", {})
        self.event_system.publish(test_event)

        # Verify execution order (high -> normal -> low)
        self.assertEqual(execution_order, ["high", "normal", "low"])

    @unit_test()
    def test_event_filtering(self):
        """Test event filtering."""
        events_received = []

        def filtered_handler(event: Event):
            events_received.append(event)

        # Subscribe with filter
        def event_filter(event: Event) -> bool:
            return event.data.get("priority") == "high"

        self.event_system.subscribe("test_event", filtered_handler, filter_func=event_filter)

        # Publish events
        high_priority_event = Event("test_event", {"priority": "high", "message": "important"})
        low_priority_event = Event("test_event", {"priority": "low", "message": "unimportant"})

        self.event_system.publish(high_priority_event)
        self.event_system.publish(low_priority_event)

        # Only high priority event should be received
        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0].data["priority"], "high")

    @unit_test()
    def test_async_event_handling(self):
        """Test asynchronous event handling."""
        async def async_test():
            events_received = []

            async def async_handler(event: Event):
                await asyncio.sleep(0.01)  # Simulate async work
                events_received.append(event)

            # Subscribe async handler
            self.event_system.subscribe("async_test", async_handler)

            # Publish event
            test_event = Event("async_test", {"async": True})
            await self.event_system.publish_async(test_event)

            # Verify event was received
            self.assertEqual(len(events_received), 1)
            self.assertEqual(events_received[0].data["async"], True)

        asyncio.run(async_test())

    @unit_test()
    def test_event_unsubscription(self):
        """Test event unsubscription."""
        events_received = []

        def event_handler(event: Event):
            events_received.append(event)

        # Subscribe
        self.event_system.subscribe("test_event", event_handler)

        # Publish event
        self.event_system.publish(Event("test_event", {}))
        self.assertEqual(len(events_received), 1)

        # Unsubscribe
        self.event_system.unsubscribe("test_event", event_handler)

        # Publish another event
        self.event_system.publish(Event("test_event", {}))

        # Should not receive the second event
        self.assertEqual(len(events_received), 1)


if __name__ == "__main__":
    unittest.main()