"""Risk Manager Configuration

Centralized configuration management for the risk management system,
including risk limits, monitoring settings, and API configuration.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

class Environment(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

class LogLevel(Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str = "trading_system"
    username: str = "postgres"
    password: str = "password"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    @property
    def url(self) -> str:
        """Get database URL"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: Optional[str] = None
    max_connections: int = 10
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    
    @property
    def url(self) -> str:
        """Get Redis URL"""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.database}"

@dataclass
class KafkaConfig:
    """Kafka configuration"""
    bootstrap_servers: List[str] = field(default_factory=lambda: ["localhost:9092"])
    client_id: str = "risk-manager"
    group_id: str = "risk-manager-group"
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = True
    auto_commit_interval_ms: int = 1000
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 3000
    max_poll_records: int = 500
    
    # Topics
    risk_events_topic: str = "risk.events"
    risk_violations_topic: str = "risk.violations"
    risk_assessments_topic: str = "risk.assessments"
    portfolio_updates_topic: str = "portfolio.updates"
    order_events_topic: str = "orders.events"

@dataclass
class RiskLimitsConfig:
    """Risk limits configuration"""
    # Position limits
    max_position_size: float = 50000.0
    max_position_count: int = 100
    
    # Portfolio limits
    max_portfolio_exposure: float = 500000.0
    max_concentration_percent: float = 10.0
    max_leverage: float = 2.0
    
    # Loss limits
    max_daily_loss: float = 10000.0
    max_weekly_loss: float = 25000.0
    max_monthly_loss: float = 50000.0
    max_drawdown_percent: float = 15.0
    
    # VaR limits
    max_var_percentage: float = 5.0
    var_confidence_level: float = 0.95
    var_time_horizon: int = 1
    
    # Sector/Asset class limits
    max_sector_concentration: float = 25.0
    max_asset_class_concentration: float = 50.0
    
    # Correlation limits
    max_correlation_exposure: float = 30.0
    correlation_threshold: float = 0.7

@dataclass
class MonitoringConfig:
    """Real-time monitoring configuration"""
    enabled: bool = True
    update_interval: float = 1.0
    cleanup_interval: int = 300  # 5 minutes
    
    # Alert thresholds
    warning_threshold: float = 80.0  # % of limit
    critical_threshold: float = 95.0  # % of limit
    
    # History retention
    max_history_records: int = 10000
    history_retention_days: int = 30
    
    # Performance settings
    max_concurrent_assessments: int = 100
    assessment_timeout: int = 30
    cache_ttl: int = 60

@dataclass
class APIConfig:
    """API configuration"""
    host: str = "0.0.0.0"
    port: int = 8003
    workers: int = 4
    reload: bool = False
    
    # CORS settings
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    cors_methods: List[str] = field(default_factory=lambda: ["*"])
    cors_headers: List[str] = field(default_factory=lambda: ["*"])
    
    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    # Authentication
    auth_enabled: bool = False
    jwt_secret: str = "your-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600  # seconds

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # File logging
    file_enabled: bool = True
    file_path: str = "logs/risk_manager.log"
    file_max_size: int = 10 * 1024 * 1024  # 10MB
    file_backup_count: int = 5
    
    # Console logging
    console_enabled: bool = True
    
    # Structured logging
    json_format: bool = False
    
    # Log levels for specific modules
    module_levels: Dict[str, str] = field(default_factory=lambda: {
        "risk_manager": "INFO",
        "uvicorn": "INFO",
        "fastapi": "INFO",
        "sqlalchemy": "WARNING"
    })

@dataclass
class SecurityConfig:
    """Security configuration"""
    # Encryption
    encryption_enabled: bool = True
    encryption_key: Optional[str] = None
    
    # API Security
    api_key_enabled: bool = False
    api_keys: List[str] = field(default_factory=list)
    
    # IP Whitelisting
    ip_whitelist_enabled: bool = False
    allowed_ips: List[str] = field(default_factory=list)
    
    # SSL/TLS
    ssl_enabled: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None

@dataclass
class PerformanceConfig:
    """Performance configuration"""
    # Threading
    max_workers: int = 4
    thread_pool_size: int = 10
    
    # Async settings
    async_timeout: int = 30
    max_concurrent_requests: int = 100
    
    # Caching
    cache_enabled: bool = True
    cache_size: int = 1000
    cache_ttl: int = 300
    
    # Memory management
    max_memory_usage: int = 1024 * 1024 * 1024  # 1GB
    gc_threshold: int = 700

@dataclass
class RiskManagerConfig:
    """Main risk manager configuration"""
    
    # Environment
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    
    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    kafka: KafkaConfig = field(default_factory=KafkaConfig)
    risk_limits: RiskLimitsConfig = field(default_factory=RiskLimitsConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    api: APIConfig = field(default_factory=APIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # Service settings
    service_name: str = "risk-manager"
    service_version: str = "1.0.0"
    
    @classmethod
    def from_env(cls) -> 'RiskManagerConfig':
        """Create configuration from environment variables"""
        
        config = cls()
        
        # Environment
        env_name = os.getenv("ENVIRONMENT", "development")
        config.environment = Environment(env_name)
        config.debug = os.getenv("DEBUG", "true").lower() == "true"
        
        # Database
        config.database.host = os.getenv("DB_HOST", config.database.host)
        config.database.port = int(os.getenv("DB_PORT", str(config.database.port)))
        config.database.database = os.getenv("DB_NAME", config.database.database)
        config.database.username = os.getenv("DB_USER", config.database.username)
        config.database.password = os.getenv("DB_PASSWORD", config.database.password)
        
        # Redis
        config.redis.host = os.getenv("REDIS_HOST", config.redis.host)
        config.redis.port = int(os.getenv("REDIS_PORT", str(config.redis.port)))
        config.redis.password = os.getenv("REDIS_PASSWORD", config.redis.password)
        
        # Kafka
        kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        if kafka_servers:
            config.kafka.bootstrap_servers = kafka_servers.split(",")
        
        # API
        config.api.host = os.getenv("API_HOST", config.api.host)
        config.api.port = int(os.getenv("API_PORT", str(config.api.port)))
        config.api.workers = int(os.getenv("API_WORKERS", str(config.api.workers)))
        
        # Risk Limits
        config.risk_limits.max_position_size = float(
            os.getenv("MAX_POSITION_SIZE", str(config.risk_limits.max_position_size))
        )
        config.risk_limits.max_portfolio_exposure = float(
            os.getenv("MAX_PORTFOLIO_EXPOSURE", str(config.risk_limits.max_portfolio_exposure))
        )
        config.risk_limits.max_leverage = float(
            os.getenv("MAX_LEVERAGE", str(config.risk_limits.max_leverage))
        )
        
        # Monitoring
        config.monitoring.enabled = os.getenv("MONITORING_ENABLED", "true").lower() == "true"
        config.monitoring.update_interval = float(
            os.getenv("MONITORING_INTERVAL", str(config.monitoring.update_interval))
        )
        
        # Logging
        log_level = os.getenv("LOG_LEVEL", "INFO")
        config.logging.level = LogLevel(log_level)
        
        return config
    
    @classmethod
    def from_file(cls, file_path: str) -> 'RiskManagerConfig':
        """Load configuration from JSON file"""
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RiskManagerConfig':
        """Create configuration from dictionary"""
        
        config = cls()
        
        # Update configuration with provided data
        for key, value in data.items():
            if hasattr(config, key):
                attr = getattr(config, key)
                if hasattr(attr, '__dict__'):  # It's a dataclass
                    for sub_key, sub_value in value.items():
                        if hasattr(attr, sub_key):
                            setattr(attr, sub_key, sub_value)
                else:
                    setattr(config, key, value)
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        
        result = {}
        
        for key, value in self.__dict__.items():
            if hasattr(value, '__dict__'):  # It's a dataclass
                result[key] = value.__dict__
            elif isinstance(value, Enum):
                result[key] = value.value
            else:
                result[key] = value
        
        return result
    
    def to_file(self, file_path: str) -> None:
        """Save configuration to JSON file"""
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        
        errors = []
        
        # Validate risk limits
        if self.risk_limits.max_position_size <= 0:
            errors.append("max_position_size must be positive")
        
        if self.risk_limits.max_portfolio_exposure <= 0:
            errors.append("max_portfolio_exposure must be positive")
        
        if self.risk_limits.max_leverage <= 0:
            errors.append("max_leverage must be positive")
        
        if not (0 < self.risk_limits.var_confidence_level < 1):
            errors.append("var_confidence_level must be between 0 and 1")
        
        # Validate monitoring settings
        if self.monitoring.update_interval <= 0:
            errors.append("monitoring update_interval must be positive")
        
        # Validate API settings
        if not (1 <= self.api.port <= 65535):
            errors.append("API port must be between 1 and 65535")
        
        if self.api.workers <= 0:
            errors.append("API workers must be positive")
        
        # Validate database settings
        if not (1 <= self.database.port <= 65535):
            errors.append("Database port must be between 1 and 65535")
        
        # Validate Kafka settings
        if not self.kafka.bootstrap_servers:
            errors.append("Kafka bootstrap_servers cannot be empty")
        
        return errors
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == Environment.DEVELOPMENT

# Global configuration instance
_config: Optional[RiskManagerConfig] = None

def get_config() -> RiskManagerConfig:
    """Get global configuration instance"""
    
    global _config
    
    if _config is None:
        # Try to load from file first, then environment
        config_file = os.getenv("RISK_CONFIG_FILE")
        
        if config_file and Path(config_file).exists():
            _config = RiskManagerConfig.from_file(config_file)
        else:
            _config = RiskManagerConfig.from_env()
        
        # Validate configuration
        errors = _config.validate()
        if errors:
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")
    
    return _config

def set_config(config: RiskManagerConfig) -> None:
    """Set global configuration instance"""
    
    global _config
    _config = config

def reset_config() -> None:
    """Reset global configuration instance"""
    
    global _config
    _config = None

# Configuration presets for different environments

def get_development_config() -> RiskManagerConfig:
    """Get development configuration preset"""
    
    config = RiskManagerConfig()
    config.environment = Environment.DEVELOPMENT
    config.debug = True
    config.api.reload = True
    config.logging.level = LogLevel.DEBUG
    config.monitoring.update_interval = 5.0  # Slower updates for development
    
    return config

def get_production_config() -> RiskManagerConfig:
    """Get production configuration preset"""
    
    config = RiskManagerConfig()
    config.environment = Environment.PRODUCTION
    config.debug = False
    config.api.reload = False
    config.logging.level = LogLevel.INFO
    config.security.encryption_enabled = True
    config.security.api_key_enabled = True
    config.monitoring.update_interval = 1.0  # Fast updates for production
    
    return config

def get_testing_config() -> RiskManagerConfig:
    """Get testing configuration preset"""
    
    config = RiskManagerConfig()
    config.environment = Environment.TESTING
    config.debug = True
    config.database.database = "trading_system_test"
    config.redis.database = 1  # Use different Redis DB for testing
    config.logging.level = LogLevel.WARNING
    
    return config