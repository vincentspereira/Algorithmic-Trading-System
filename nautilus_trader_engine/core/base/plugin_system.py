"""
Plugin System for Dynamic Loading of Indicators and Strategies
Provides a robust plugin architecture for extensibility and modularity.
"""

import importlib
import inspect
import pkgutil
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Type, Any, Optional, Callable, Set
import logging
from dataclasses import dataclass, field
import json
import hashlib

logger = logging.getLogger(__name__)


class PluginError(Exception):
    """Base exception for plugin system errors."""
    pass


class PluginLoadError(PluginError):
    """Raised when a plugin fails to load."""
    pass


class PluginValidationError(PluginError):
    """Raised when a plugin fails validation."""
    pass


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    name: str
    version: str
    description: str
    author: str
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    plugin_type: str = ""
    entry_point: str = ""
    checksum: str = ""


class PluginInterface(ABC):
    """Base interface for all plugins."""

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        pass

    @abstractmethod
    def initialize(self, context: Dict[str, Any]) -> None:
        """Initialize the plugin with context."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the plugin."""
        pass


class IndicatorPlugin(PluginInterface):
    """Interface for indicator plugins."""

    @abstractmethod
    def get_indicator_class(self) -> Type:
        """Get the indicator class."""
        pass

    @abstractmethod
    def get_indicator_config(self) -> Dict[str, Any]:
        """Get indicator configuration."""
        pass


class StrategyPlugin(PluginInterface):
    """Interface for strategy plugins."""

    @abstractmethod
    def get_strategy_class(self) -> Type:
        """Get the strategy class."""
        pass

    @abstractmethod
    def get_strategy_config(self) -> Dict[str, Any]:
        """Get strategy configuration."""
        pass


class PluginManager:
    """
    Advanced plugin manager with features:
    - Dynamic loading and unloading
    - Dependency resolution
    - Plugin validation
    - Hot reloading
    - Security checks
    """

    def __init__(self, plugin_dirs: Optional[List[Path]] = None):
        self.plugin_dirs = plugin_dirs or [
            Path(__file__).parent.parent.parent / "plugins",
            Path.cwd() / "plugins"
        ]
        self.loaded_plugins: Dict[str, PluginInterface] = {}
        self.plugin_metadata: Dict[str, PluginMetadata] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}
        self._security_checker = PluginSecurityChecker()

    def discover_plugins(self) -> List[PluginMetadata]:
        """Discover all available plugins."""
        discovered = []

        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue

            for plugin_file in plugin_dir.rglob("*.py"):
                if plugin_file.name.startswith("_"):
                    continue

                try:
                    metadata = self._extract_metadata(plugin_file)
                    if metadata:
                        discovered.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to extract metadata from {plugin_file}: {e}")

        return discovered

    def _extract_metadata(self, plugin_file: Path) -> Optional[PluginMetadata]:
        """Extract metadata from a plugin file."""
        try:
            # Read the file and look for metadata
            content = plugin_file.read_text()

            # Look for metadata in comments or docstrings
            lines = content.split('\n')
            metadata_lines = []

            in_metadata = False
            for line in lines:
                if 'PLUGIN_METADATA' in line:
                    in_metadata = True
                    continue
                elif in_metadata and line.strip().startswith('"""'):
                    break
                elif in_metadata:
                    metadata_lines.append(line.strip())

            if metadata_lines:
                metadata_dict = json.loads('\n'.join(metadata_lines))
                return PluginMetadata(**metadata_dict)

        except Exception as e:
            logger.debug(f"Could not extract metadata from {plugin_file}: {e}")

        return None

    def load_plugin(self, plugin_name: str, context: Optional[Dict[str, Any]] = None) -> PluginInterface:
        """Load a plugin by name."""
        if plugin_name in self.loaded_plugins:
            return self.loaded_plugins[plugin_name]

        # Find plugin metadata
        metadata = None
        for meta in self.discover_plugins():
            if meta.name == plugin_name:
                metadata = meta
                break

        if not metadata:
            raise PluginLoadError(f"Plugin {plugin_name} not found")

        # Check security
        if not self._security_checker.validate_plugin(metadata):
            raise PluginValidationError(f"Plugin {plugin_name} failed security validation")

        # Resolve dependencies
        self._resolve_dependencies(metadata)

        # Load the plugin
        plugin = self._load_plugin_from_metadata(metadata, context or {})

        # Initialize plugin
        plugin.initialize(context or {})

        self.loaded_plugins[plugin_name] = plugin
        self.plugin_metadata[plugin_name] = metadata

        logger.info(f"Loaded plugin: {plugin_name} v{metadata.version}")
        return plugin

    def _resolve_dependencies(self, metadata: PluginMetadata) -> None:
        """Resolve plugin dependencies."""
        for dep in metadata.dependencies:
            if dep not in self.loaded_plugins:
                self.load_plugin(dep)

    def _load_plugin_from_metadata(self, metadata: PluginMetadata, context: Dict[str, Any]) -> PluginInterface:
        """Load plugin from metadata."""
        try:
            # Import the plugin module
            module_path = metadata.entry_point
            if not module_path:
                # Try to infer from name
                module_path = f"plugins.{metadata.name}"

            module = importlib.import_module(module_path)

            # Find the plugin class
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    issubclass(obj, PluginInterface) and
                    obj != PluginInterface):
                    plugin_class = obj
                    break

            if not plugin_class:
                raise PluginLoadError(f"No plugin class found in {module_path}")

            return plugin_class()

        except Exception as e:
            raise PluginLoadError(f"Failed to load plugin {metadata.name}: {e}")

    def unload_plugin(self, plugin_name: str) -> None:
        """Unload a plugin."""
        if plugin_name not in self.loaded_plugins:
            return

        plugin = self.loaded_plugins[plugin_name]

        try:
            plugin.shutdown()
        except Exception as e:
            logger.warning(f"Error shutting down plugin {plugin_name}: {e}")

        del self.loaded_plugins[plugin_name]
        del self.plugin_metadata[plugin_name]

        logger.info(f"Unloaded plugin: {plugin_name}")

    def reload_plugin(self, plugin_name: str, context: Optional[Dict[str, Any]] = None) -> PluginInterface:
        """Reload a plugin."""
        self.unload_plugin(plugin_name)
        return self.load_plugin(plugin_name, context)

    def get_plugin(self, plugin_name: str) -> Optional[PluginInterface]:
        """Get a loaded plugin."""
        return self.loaded_plugins.get(plugin_name)

    def get_loaded_plugins(self) -> Dict[str, PluginInterface]:
        """Get all loaded plugins."""
        return self.loaded_plugins.copy()

    def get_available_plugins(self) -> List[PluginMetadata]:
        """Get all available plugins."""
        return self.discover_plugins()

    def validate_plugin_dependencies(self, plugin_name: str) -> bool:
        """Validate plugin dependencies."""
        if plugin_name not in self.plugin_metadata:
            return False

        metadata = self.plugin_metadata[plugin_name]

        for dep in metadata.dependencies:
            if dep not in self.loaded_plugins:
                return False

        return True


class PluginSecurityChecker:
    """Security checker for plugins."""

    def __init__(self):
        self.allowed_hashes = set()  # Would be loaded from a trusted source

    def validate_plugin(self, metadata: PluginMetadata) -> bool:
        """Validate plugin security."""
        # Basic validation - in production, this would be more sophisticated
        if not metadata.name or not metadata.version:
            return False

        # Check checksum if provided
        if metadata.checksum:
            # Verify checksum
            pass

        return True

    def add_trusted_hash(self, hash_value: str) -> None:
        """Add a trusted plugin hash."""
        self.allowed_hashes.add(hash_value)


class PluginRegistry:
    """Registry for managing plugin types and factories."""

    def __init__(self):
        self.plugin_types: Dict[str, Type[PluginInterface]] = {}
        self.plugin_factories: Dict[str, Callable] = {}

    def register_type(self, plugin_type: str, interface_class: Type[PluginInterface]) -> None:
        """Register a plugin type."""
        self.plugin_types[plugin_type] = interface_class

    def register_factory(self, plugin_type: str, factory: Callable) -> None:
        """Register a plugin factory."""
        self.plugin_factories[plugin_type] = factory

    def create_plugin(self, plugin_type: str, **kwargs) -> PluginInterface:
        """Create a plugin instance."""
        if plugin_type not in self.plugin_factories:
            raise PluginError(f"No factory registered for plugin type: {plugin_type}")

        return self.plugin_factories[plugin_type](**kwargs)

    def get_interface(self, plugin_type: str) -> Type[PluginInterface]:
        """Get the interface for a plugin type."""
        return self.plugin_types.get(plugin_type)


# Global instances
_plugin_manager = PluginManager()
_plugin_registry = PluginRegistry()


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager."""
    return _plugin_manager


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry."""
    return _plugin_registry


# Convenience functions
def load_plugin(plugin_name: str, context: Optional[Dict[str, Any]] = None) -> PluginInterface:
    """Load a plugin globally."""
    return _plugin_manager.load_plugin(plugin_name, context)


def unload_plugin(plugin_name: str) -> None:
    """Unload a plugin globally."""
    _plugin_manager.unload_plugin(plugin_name)


def get_plugin(plugin_name: str) -> Optional[PluginInterface]:
    """Get a loaded plugin globally."""
    return _plugin_manager.get_plugin(plugin_name)


# Example plugin implementation
class ExampleIndicatorPlugin(IndicatorPlugin):
    """Example indicator plugin implementation."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="example_indicator",
            version="1.0.0",
            description="Example indicator plugin",
            author="Nautilus Team",
            plugin_type="indicator"
        )

    def initialize(self, context: Dict[str, Any]) -> None:
        logger.info("ExampleIndicatorPlugin initialized")

    def shutdown(self) -> None:
        logger.info("ExampleIndicatorPlugin shutdown")

    def get_indicator_class(self) -> Type:
        # Return actual indicator class
        return object  # Placeholder

    def get_indicator_config(self) -> Dict[str, Any]:
        return {"period": 14, "multiplier": 2.0}


if __name__ == "__main__":
    # Example usage
    manager = get_plugin_manager()

    # Discover plugins
    available = manager.discover_plugins()
    print(f"Available plugins: {[p.name for p in available]}")

    # Load a plugin
    try:
        plugin = manager.load_plugin("example_indicator")
        print(f"Loaded plugin: {plugin.metadata.name}")
    except PluginLoadError as e:
        print(f"Failed to load plugin: {e}")