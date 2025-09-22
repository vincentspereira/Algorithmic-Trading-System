"""
Configuration Management System for Nautilus Trader Engine
Provides centralized configuration with validation, environment support, and hot reloading.
"""

import json
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from contextlib import contextmanager
import hashlib
import time
from threading import Lock
import copy

logger = logging.getLogger(__name__)


class ConfigFormat(Enum):
    """Supported configuration formats."""
    JSON = "json"
    YAML = "yaml"
    ENV = "env"


class ConfigError(Exception):
    """Base exception for configuration errors."""
    pass


class ValidationError(ConfigError):
    """Raised when configuration validation fails."""
    pass


class ConfigNotFoundError(ConfigError):
    """Raised when a configuration file is not found."""
    pass


@dataclass
class ConfigSchema:
    """Schema definition for configuration validation."""
    type: str
    required: bool = False
    default: Any = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[List[Any]] = None
    pattern: Optional[str] = None
    custom_validator: Optional[Callable] = None


@dataclass
class ConfigSection:
    """Configuration section with schema and data."""
    name: str
    schema: Dict[str, ConfigSchema] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConfigurationManager:
    """
    Advanced configuration manager with features:
    - Multiple format support (JSON, YAML, ENV)
    - Schema validation
    - Environment-specific configurations
    - Hot reloading
    - Encrypted sensitive data
    - Configuration inheritance
    """

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path(__file__).parent.parent.parent / "config"
        self.configs: Dict[str, ConfigSection] = {}
        self.environment = os.getenv("NAUTILUS_ENV", "development")
        self._file_watchers: Dict[Path, float] = {}
        self._lock = Lock()
        self._validators: Dict[str, Callable] = {}
        self._encrypted_keys: Set[str] = set()

    def load_config(self, name: str, file_path: Optional[Path] = None,
                   format_type: ConfigFormat = ConfigFormat.JSON) -> ConfigSection:
        """Load a configuration file."""
        if file_path is None:
            file_path = self._find_config_file(name, format_type)

        if not file_path.exists():
            raise ConfigNotFoundError(f"Configuration file not found: {file_path}")

        with self._lock:
            # Load the configuration
            data = self._load_file(file_path, format_type)

            # Create or update section
            if name not in self.configs:
                self.configs[name] = ConfigSection(name=name)

            section = self.configs[name]
            section.data.update(data)
            section.metadata["file_path"] = str(file_path)
            section.metadata["last_loaded"] = time.time()

            # Set up file watching for hot reloading
            self._file_watchers[file_path] = os.path.getmtime(file_path)

            logger.info(f"Loaded configuration: {name} from {file_path}")
            return section

    def _find_config_file(self, name: str, format_type: ConfigFormat) -> Path:
        """Find configuration file with environment-specific naming."""
        extensions = {
            ConfigFormat.JSON: ".json",
            ConfigFormat.YAML: ".yaml",
            ConfigFormat.ENV: ".env"
        }

        # Try environment-specific first
        env_file = self.config_dir / f"{name}.{self.environment}{extensions[format_type]}"
        if env_file.exists():
            return env_file

        # Try base name
        base_file = self.config_dir / f"{name}{extensions[format_type]}"
        if base_file.exists():
            return base_file

        # Try without environment
        default_file = self.config_dir / f"{name}.default{extensions[format_type]}"
        if default_file.exists():
            return default_file

        raise ConfigNotFoundError(f"No configuration file found for {name}")

    def _load_file(self, file_path: Path, format_type: ConfigFormat) -> Dict[str, Any]:
        """Load configuration from file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            if format_type == ConfigFormat.JSON:
                return json.load(f)
            elif format_type == ConfigFormat.YAML:
                return yaml.safe_load(f)
            elif format_type == ConfigFormat.ENV:
                return self._parse_env_file(f.read())
            else:
                raise ConfigError(f"Unsupported format: {format_type}")

    def _parse_env_file(self, content: str) -> Dict[str, Any]:
        """Parse environment file format."""
        config = {}
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    # Try to parse as JSON, fallback to string
                    try:
                        config[key.strip()] = json.loads(value.strip())
                    except (json.JSONDecodeError, ValueError):
                        config[key.strip()] = value.strip()
        return config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        with self._lock:
            keys = key.split('.')
            section_name = keys[0]
            config_key = '.'.join(keys[1:])

            if section_name not in self.configs:
                return default

            section = self.configs[section_name]
            return self._get_nested_value(section.data, config_key.split('.'), default)

    def _get_nested_value(self, data: Dict[str, Any], keys: List[str], default: Any) -> Any:
        """Get nested value from configuration data."""
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        with self._lock:
            keys = key.split('.')
            section_name = keys[0]
            config_key = '.'.join(keys[1:])

            if section_name not in self.configs:
                self.configs[section_name] = ConfigSection(name=section_name)

            section = self.configs[section_name]
            self._set_nested_value(section.data, config_key.split('.'), value)

            # Mark as modified
            section.metadata["modified"] = True
            section.metadata["last_modified"] = time.time()

    def _set_nested_value(self, data: Dict[str, Any], keys: List[str], value: Any) -> None:
        """Set nested value in configuration data."""
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def validate_config(self, section_name: str) -> List[str]:
        """Validate a configuration section."""
        if section_name not in self.configs:
            return [f"Configuration section '{section_name}' not found"]

        section = self.configs[section_name]
        errors = []

        for key, schema in section.schema.items():
            value = self._get_nested_value(section.data, key.split('.'), None)

            if value is None:
                if schema.required:
                    errors.append(f"Required configuration '{key}' is missing")
                continue

            # Type validation
            if not self._validate_type(value, schema.type):
                errors.append(f"Configuration '{key}' has invalid type. Expected {schema.type}")

            # Range validation
            if schema.min_value is not None and isinstance(value, (int, float)):
                if value < schema.min_value:
                    errors.append(f"Configuration '{key}' is below minimum value {schema.min_value}")

            if schema.max_value is not None and isinstance(value, (int, float)):
                if value > schema.max_value:
                    errors.append(f"Configuration '{key}' is above maximum value {schema.max_value}")

            # Allowed values validation
            if schema.allowed_values and value not in schema.allowed_values:
                errors.append(f"Configuration '{key}' has invalid value. Allowed: {schema.allowed_values}")

            # Pattern validation
            if schema.pattern and isinstance(value, str):
                import re
                if not re.match(schema.pattern, value):
                    errors.append(f"Configuration '{key}' does not match pattern {schema.pattern}")

            # Custom validation
            if schema.custom_validator:
                try:
                    if not schema.custom_validator(value):
                        errors.append(f"Configuration '{key}' failed custom validation")
                except Exception as e:
                    errors.append(f"Configuration '{key}' custom validation error: {e}")

        return errors

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate value type."""
        type_map = {
            "string": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict
        }

        expected = type_map.get(expected_type)
        if expected:
            return isinstance(value, expected)

        return True  # Unknown type, assume valid

    def save_config(self, section_name: str, file_path: Optional[Path] = None,
                   format_type: ConfigFormat = ConfigFormat.JSON) -> None:
        """Save a configuration section to file."""
        if section_name not in self.configs:
            raise ConfigError(f"Configuration section '{section_name}' not found")

        section = self.configs[section_name]

        if file_path is None:
            file_path = Path(section.metadata.get("file_path", f"{section_name}.{format_type.value}"))

        # Create directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            if format_type == ConfigFormat.JSON:
                json.dump(section.data, f, indent=2)
            elif format_type == ConfigFormat.YAML:
                yaml.dump(section.data, f, default_flow_style=False)
            else:
                raise ConfigError(f"Unsupported format for saving: {format_type}")

        logger.info(f"Saved configuration: {section_name} to {file_path}")

    def reload_configs(self) -> List[str]:
        """Reload modified configuration files."""
        reloaded = []

        for file_path, last_mtime in self._file_watchers.items():
            try:
                current_mtime = os.path.getmtime(file_path)
                if current_mtime > last_mtime:
                    # File has been modified
                    section_name = self._get_section_name_from_path(file_path)
                    if section_name:
                        self.load_config(section_name, file_path)
                        reloaded.append(section_name)
                        self._file_watchers[file_path] = current_mtime
            except OSError:
                logger.warning(f"Could not check modification time for {file_path}")

        return reloaded

    def _get_section_name_from_path(self, file_path: Path) -> Optional[str]:
        """Get section name from file path."""
        filename = file_path.stem
        # Remove environment suffix
        if f".{self.environment}" in filename:
            return filename.replace(f".{self.environment}", "")
        return filename

    def add_validator(self, section_name: str, validator: Callable) -> None:
        """Add a custom validator for a configuration section."""
        self._validators[section_name] = validator

    def encrypt_sensitive_data(self, key: str) -> None:
        """Mark a configuration key as containing sensitive data."""
        self._encrypted_keys.add(key)

    def get_environment_variables(self) -> Dict[str, str]:
        """Get all environment variables starting with NAUTILUS_."""
        return {k: v for k, v in os.environ.items() if k.startswith("NAUTILUS_")}

    def override_from_environment(self) -> None:
        """Override configuration values from environment variables."""
        env_vars = self.get_environment_variables()

        for env_key, env_value in env_vars.items():
            # Convert NAUTILUS_SECTION_KEY to section.key
            config_key = env_key.replace("NAUTILUS_", "").lower().replace("_", ".")
            self.set(config_key, env_value)

    def create_backup(self, section_name: str) -> Path:
        """Create a backup of a configuration section."""
        if section_name not in self.configs:
            raise ConfigError(f"Configuration section '{section_name}' not found")

        section = self.configs[section_name]
        timestamp = int(time.time())

        backup_dir = self.config_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        backup_file = backup_dir / f"{section_name}_backup_{timestamp}.json"

        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(section.data, f, indent=2)

        logger.info(f"Created backup: {backup_file}")
        return backup_file

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of all configurations."""
        summary = {
            "environment": self.environment,
            "sections": {},
            "total_sections": len(self.configs),
            "watched_files": len(self._file_watchers)
        }

        for name, section in self.configs.items():
            summary["sections"][name] = {
                "keys_count": len(section.data),
                "has_schema": len(section.schema) > 0,
                "last_modified": section.metadata.get("last_modified"),
                "file_path": section.metadata.get("file_path")
            }

        return summary


# Global configuration manager instance
_config_manager = ConfigurationManager()


def get_config_manager() -> ConfigurationManager:
    """Get the global configuration manager."""
    return _config_manager


# Convenience functions
def get_config(key: str, default: Any = None) -> Any:
    """Get a configuration value globally."""
    return _config_manager.get(key, default)


def set_config(key: str, value: Any) -> None:
    """Set a configuration value globally."""
    _config_manager.set(key, value)


def load_config(name: str, file_path: Optional[Path] = None,
               format_type: ConfigFormat = ConfigFormat.JSON) -> ConfigSection:
    """Load a configuration globally."""
    return _config_manager.load_config(name, file_path, format_type)


# Example configuration schema
DEFAULT_SCHEMAS = {
    "trading": {
        "max_position_size": ConfigSchema(type="float", required=True, min_value=0.0),
        "max_daily_loss": ConfigSchema(type="float", required=True, min_value=0.0),
        "risk_per_trade": ConfigSchema(type="float", required=True, min_value=0.0, max_value=1.0),
        "allowed_instruments": ConfigSchema(type="list", required=False),
        "trading_hours": ConfigSchema(type="dict", required=False)
    },
    "indicators": {
        "default_period": ConfigSchema(type="int", required=False, default=14, min_value=1),
        "max_lookback": ConfigSchema(type="int", required=False, default=100, min_value=1),
        "cache_enabled": ConfigSchema(type="bool", required=False, default=True)
    }
}


if __name__ == "__main__":
    # Example usage
    manager = get_config_manager()

    # Load a configuration
    try:
        config = manager.load_config("trading")
        print(f"Loaded trading config with {len(config.data)} keys")
    except ConfigNotFoundError:
        print("Trading configuration not found")

    # Get configuration values
    max_loss = get_config("trading.max_daily_loss", 1000.0)
    print(f"Max daily loss: {max_loss}")

    # Set configuration values
    set_config("trading.new_setting", "test_value")
    print(f"New setting: {get_config('trading.new_setting')}")