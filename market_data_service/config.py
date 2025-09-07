"""Market Data Service Configuration

Centralized configuration management for data providers, API settings,
performance parameters, and service-specific configurations.
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from shared.config import settings
from utils.logging_config import get_logger

logger = get_logger(__name__)

class ServiceMode(Enum):
    """Service operation modes"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"

class DataQuality(Enum):
    """Data quality levels"""
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

@dataclass
class PerformanceConfig:
    """Performance-related configuration"""
    # Request timeouts (seconds)
    default_timeout: float = 5.0
    fast_timeout: float = 3.0
    slow_timeout: float = 10.0
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    exponential_backoff: bool = True
    
    # Circuit breaker settings
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60  # seconds
    
    # Rate limiting
    requests_per_second: int = 10
    burst_limit: int = 50
    
    # Caching
    cache_ttl_seconds: int = 30
    max_cache_size: int = 10000
    
    # Concurrent requests
    max_concurrent_requests: int = 100
    semaphore_limit: int = 50

@dataclass
class KafkaConfig:
    """Kafka configuration for market data streaming"""
    bootstrap_servers: List[str] = field(default_factory=lambda: [
        os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    ])
    
    # Producer settings
    producer_config: Dict[str, Any] = field(default_factory=lambda: {
        'acks': 'all',
        'retries': 3,
        'batch_size': 16384,
        'linger_ms': 10,
        'buffer_memory': 33554432,
        'compression_type': 'snappy',
        'max_in_flight_requests_per_connection': 5,
        'enable_idempotence': True
    })
    
    # Consumer settings
    consumer_config: Dict[str, Any] = field(default_factory=lambda: {
        'group_id': 'market_data_service',
        'auto_offset_reset': 'latest',
        'enable_auto_commit': True,
        'auto_commit_interval_ms': 1000,
        'session_timeout_ms': 30000,
        'heartbeat_interval_ms': 3000
    })
    
    # Topic configuration
    topic_config: Dict[str, Any] = field(default_factory=lambda: {
        'num_partitions': 12,
        'replication_factor': 3,
        'cleanup_policy': 'delete',
        'retention_ms': 604800000,  # 7 days
        'segment_ms': 86400000,     # 1 day
        'compression_type': 'snappy'
    })
    
    # Schema Registry
    schema_registry_url: str = os.getenv('SCHEMA_REGISTRY_URL', 'http://localhost:8081')
    
    # Topic naming
    topic_prefix: str = "market_data"
    
@dataclass
class DatabaseConfig:
    """Database configuration for caching and persistence"""
    # Redis configuration
    redis_host: str = os.getenv('REDIS_HOST', 'localhost')
    redis_port: int = int(os.getenv('REDIS_PORT', '6379'))
    redis_db: int = int(os.getenv('REDIS_DB', '0'))
    redis_password: Optional[str] = os.getenv('REDIS_PASSWORD')
    redis_ssl: bool = os.getenv('REDIS_SSL', 'false').lower() == 'true'
    
    # Connection pool settings
    redis_max_connections: int = 20
    redis_retry_on_timeout: bool = True
    redis_socket_timeout: float = 5.0
    
    # Cache settings
    default_cache_ttl: int = 300  # 5 minutes
    real_time_cache_ttl: int = 30  # 30 seconds
    historical_cache_ttl: int = 3600  # 1 hour
    
@dataclass
class SecurityConfig:
    """Security configuration"""
    # API key encryption
    encryption_key: Optional[str] = os.getenv('ENCRYPTION_KEY')
    
    # Rate limiting
    enable_rate_limiting: bool = True
    rate_limit_per_minute: int = 1000
    
    # API authentication
    require_api_key: bool = os.getenv('REQUIRE_API_KEY', 'false').lower() == 'true'
    api_key_header: str = 'X-API-Key'
    
    # CORS settings
    allowed_origins: List[str] = field(default_factory=lambda: [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://localhost:3000",
        "https://localhost:8000"
    ])
    
    # SSL/TLS
    ssl_verify: bool = True
    ssl_cert_path: Optional[str] = os.getenv('SSL_CERT_PATH')
    ssl_key_path: Optional[str] = os.getenv('SSL_KEY_PATH')

@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration"""
    # Metrics collection
    enable_metrics: bool = True
    metrics_port: int = 8002
    
    # Health checks
    health_check_interval: int = 30  # seconds
    provider_health_timeout: float = 5.0
    
    # Logging
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    log_format: str = 'json'
    
    # Alerting thresholds
    error_rate_threshold: float = 0.05  # 5%
    latency_threshold_ms: float = 1000.0
    availability_threshold: float = 0.99  # 99%
    
    # Prometheus metrics
    prometheus_enabled: bool = True
    prometheus_port: int = 8003
    
@dataclass
class ProviderAPIConfig:
    """API configuration for data providers"""
    # Yahoo Finance
    yahoo_finance_enabled: bool = True
    yahoo_finance_timeout: float = 5.0
    yahoo_finance_rate_limit: int = 2000  # requests per hour
    
    # Alpha Vantage
    alpha_vantage_enabled: bool = True
    alpha_vantage_api_key: Optional[str] = os.getenv('ALPHA_VANTAGE_API_KEY')
    alpha_vantage_timeout: float = 10.0
    alpha_vantage_rate_limit: int = 5  # requests per minute (free tier)
    
    # Finnhub
    finnhub_enabled: bool = True
    finnhub_api_key: Optional[str] = os.getenv('FINNHUB_API_KEY')
    finnhub_timeout: float = 5.0
    finnhub_rate_limit: int = 60  # requests per minute (free tier)
    
    # Polygon.io
    polygon_enabled: bool = True
    polygon_api_key: Optional[str] = os.getenv('POLYGON_API_KEY')
    polygon_timeout: float = 5.0
    polygon_rate_limit: int = 5  # requests per minute (free tier)
    
    # Twelve Data
    twelve_data_enabled: bool = True
    twelve_data_api_key: Optional[str] = os.getenv('TWELVE_DATA_API_KEY')
    twelve_data_timeout: float = 5.0
    twelve_data_rate_limit: int = 8  # requests per minute (free tier)
    
    # Interactive Brokers
    ibkr_enabled: bool = True
    ibkr_host: str = getattr(settings, 'IB_HOST', 'localhost')
    ibkr_port: int = getattr(settings, 'IB_PAPER_PORT', 7497)
    ibkr_client_id: int = getattr(settings, 'IB_CLIENT_ID', 1)
    ibkr_timeout: float = 10.0
    
    # OANDA (Forex)
    oanda_enabled: bool = True
    oanda_api_key: Optional[str] = os.getenv('OANDA_API_KEY')
    oanda_account_id: Optional[str] = os.getenv('OANDA_ACCOUNT_ID')
    oanda_environment: str = os.getenv('OANDA_ENVIRONMENT', 'practice')  # practice or live
    oanda_timeout: float = 5.0
    
    # Coinbase (Crypto)
    coinbase_enabled: bool = True
    coinbase_api_key: Optional[str] = os.getenv('COINBASE_API_KEY')
    coinbase_api_secret: Optional[str] = os.getenv('COINBASE_API_SECRET')
    coinbase_passphrase: Optional[str] = os.getenv('COINBASE_PASSPHRASE')
    coinbase_sandbox: bool = os.getenv('COINBASE_SANDBOX', 'true').lower() == 'true'
    coinbase_timeout: float = 5.0
    
@dataclass
class MarketDataServiceConfig:
    """Main configuration class for Market Data Service"""
    # Service settings
    service_name: str = "market_data_service"
    service_version: str = "1.0.0"
    service_mode: ServiceMode = ServiceMode.DEVELOPMENT
    
    # API settings
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = os.getenv('DEBUG', 'true').lower() == 'true'
    
    # Data quality requirements
    min_data_quality: DataQuality = DataQuality.STANDARD
    require_real_time: bool = True
    require_historical: bool = True
    
    # Asset class support
    supported_asset_classes: List[str] = field(default_factory=lambda: [
        "stock", "etf", "option", "future", "forex", "commodity", "crypto"
    ])
    
    # Configuration components
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    kafka: KafkaConfig = field(default_factory=KafkaConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    providers: ProviderAPIConfig = field(default_factory=ProviderAPIConfig)
    
    def __post_init__(self):
        """Post-initialization validation and setup"""
        self._validate_config()
        self._setup_environment_overrides()
        
    def _validate_config(self):
        """Validate configuration settings"""
        # Validate required API keys based on enabled providers
        if self.providers.alpha_vantage_enabled and not self.providers.alpha_vantage_api_key:
            logger.warning("Alpha Vantage enabled but no API key provided")
            
        if self.providers.finnhub_enabled and not self.providers.finnhub_api_key:
            logger.warning("Finnhub enabled but no API key provided")
            
        if self.providers.polygon_enabled and not self.providers.polygon_api_key:
            logger.warning("Polygon.io enabled but no API key provided")
            
        # Validate performance settings
        if self.performance.circuit_breaker_threshold < 1:
            raise ValueError("Circuit breaker threshold must be at least 1")
            
        if self.performance.max_concurrent_requests < 1:
            raise ValueError("Max concurrent requests must be at least 1")
            
        # Validate Kafka settings
        if not self.kafka.bootstrap_servers:
            raise ValueError("Kafka bootstrap servers must be specified")
            
    def _setup_environment_overrides(self):
        """Apply environment variable overrides"""
        # Service mode override
        env_mode = os.getenv('SERVICE_MODE')
        if env_mode:
            try:
                self.service_mode = ServiceMode(env_mode.lower())
            except ValueError:
                logger.warning(f"Invalid service mode: {env_mode}")
                
        # Port override
        env_port = os.getenv('SERVICE_PORT')
        if env_port:
            try:
                self.port = int(env_port)
            except ValueError:
                logger.warning(f"Invalid port number: {env_port}")
                
        # Debug override
        env_debug = os.getenv('DEBUG')
        if env_debug is not None:
            self.debug = env_debug.lower() == 'true'
            
    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """Get configuration for a specific provider"""
        provider_configs = {
            'yahoo_finance': {
                'enabled': self.providers.yahoo_finance_enabled,
                'timeout': self.providers.yahoo_finance_timeout,
                'rate_limit': self.providers.yahoo_finance_rate_limit
            },
            'alpha_vantage': {
                'enabled': self.providers.alpha_vantage_enabled,
                'api_key': self.providers.alpha_vantage_api_key,
                'timeout': self.providers.alpha_vantage_timeout,
                'rate_limit': self.providers.alpha_vantage_rate_limit
            },
            'finnhub': {
                'enabled': self.providers.finnhub_enabled,
                'api_key': self.providers.finnhub_api_key,
                'timeout': self.providers.finnhub_timeout,
                'rate_limit': self.providers.finnhub_rate_limit
            },
            'polygon': {
                'enabled': self.providers.polygon_enabled,
                'api_key': self.providers.polygon_api_key,
                'timeout': self.providers.polygon_timeout,
                'rate_limit': self.providers.polygon_rate_limit
            },
            'twelve_data': {
                'enabled': self.providers.twelve_data_enabled,
                'api_key': self.providers.twelve_data_api_key,
                'timeout': self.providers.twelve_data_timeout,
                'rate_limit': self.providers.twelve_data_rate_limit
            },
            'ibkr': {
                'enabled': self.providers.ibkr_enabled,
                'host': self.providers.ibkr_host,
                'port': self.providers.ibkr_port,
                'client_id': self.providers.ibkr_client_id,
                'timeout': self.providers.ibkr_timeout
            },
            'oanda': {
                'enabled': self.providers.oanda_enabled,
                'api_key': self.providers.oanda_api_key,
                'account_id': self.providers.oanda_account_id,
                'environment': self.providers.oanda_environment,
                'timeout': self.providers.oanda_timeout
            },
            'coinbase': {
                'enabled': self.providers.coinbase_enabled,
                'api_key': self.providers.coinbase_api_key,
                'api_secret': self.providers.coinbase_api_secret,
                'passphrase': self.providers.coinbase_passphrase,
                'sandbox': self.providers.coinbase_sandbox,
                'timeout': self.providers.coinbase_timeout
            }
        }
        
        return provider_configs.get(provider_name, {})
        
    def is_provider_enabled(self, provider_name: str) -> bool:
        """Check if a provider is enabled"""
        config = self.get_provider_config(provider_name)
        return config.get('enabled', False)
        
    def get_kafka_topic_name(self, asset_class: str, data_type: str) -> str:
        """Generate Kafka topic name"""
        return f"{self.kafka.topic_prefix}.{asset_class}.{data_type}"
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'service_name': self.service_name,
            'service_version': self.service_version,
            'service_mode': self.service_mode.value,
            'host': self.host,
            'port': self.port,
            'debug': self.debug,
            'supported_asset_classes': self.supported_asset_classes,
            'performance': {
                'default_timeout': self.performance.default_timeout,
                'max_retries': self.performance.max_retries,
                'circuit_breaker_threshold': self.performance.circuit_breaker_threshold,
                'requests_per_second': self.performance.requests_per_second,
                'max_concurrent_requests': self.performance.max_concurrent_requests
            },
            'kafka': {
                'bootstrap_servers': self.kafka.bootstrap_servers,
                'topic_prefix': self.kafka.topic_prefix
            },
            'monitoring': {
                'enable_metrics': self.monitoring.enable_metrics,
                'log_level': self.monitoring.log_level,
                'prometheus_enabled': self.monitoring.prometheus_enabled
            }
        }

# Global configuration instance
_config: Optional[MarketDataServiceConfig] = None

def get_config() -> MarketDataServiceConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = MarketDataServiceConfig()
        logger.info(f"Market Data Service configuration loaded (mode: {_config.service_mode.value})")
    return _config

def reload_config() -> MarketDataServiceConfig:
    """Reload configuration from environment"""
    global _config
    _config = MarketDataServiceConfig()
    logger.info("Market Data Service configuration reloaded")
    return _config

# Configuration validation functions
def validate_provider_credentials() -> Dict[str, bool]:
    """Validate that required provider credentials are available"""
    config = get_config()
    credentials_status = {}
    
    # Check each provider's credentials
    if config.providers.alpha_vantage_enabled:
        credentials_status['alpha_vantage'] = bool(config.providers.alpha_vantage_api_key)
        
    if config.providers.finnhub_enabled:
        credentials_status['finnhub'] = bool(config.providers.finnhub_api_key)
        
    if config.providers.polygon_enabled:
        credentials_status['polygon'] = bool(config.providers.polygon_api_key)
        
    if config.providers.twelve_data_enabled:
        credentials_status['twelve_data'] = bool(config.providers.twelve_data_api_key)
        
    if config.providers.oanda_enabled:
        credentials_status['oanda'] = bool(
            config.providers.oanda_api_key and config.providers.oanda_account_id
        )
        
    if config.providers.coinbase_enabled:
        credentials_status['coinbase'] = bool(
            config.providers.coinbase_api_key and 
            config.providers.coinbase_api_secret and 
            config.providers.coinbase_passphrase
        )
        
    # Yahoo Finance and IBKR don't require API keys for basic functionality
    if config.providers.yahoo_finance_enabled:
        credentials_status['yahoo_finance'] = True
        
    if config.providers.ibkr_enabled:
        credentials_status['ibkr'] = True
        
    return credentials_status

def get_environment_info() -> Dict[str, Any]:
    """Get environment information for debugging"""
    config = get_config()
    
    return {
        'service_mode': config.service_mode.value,
        'debug_enabled': config.debug,
        'supported_asset_classes': config.supported_asset_classes,
        'enabled_providers': [
            provider for provider in [
                'yahoo_finance', 'alpha_vantage', 'finnhub', 'polygon',
                'twelve_data', 'ibkr', 'oanda', 'coinbase'
            ] if config.is_provider_enabled(provider)
        ],
        'kafka_bootstrap_servers': config.kafka.bootstrap_servers,
        'redis_host': config.database.redis_host,
        'metrics_enabled': config.monitoring.enable_metrics,
        'prometheus_enabled': config.monitoring.prometheus_enabled
    }