"""
Shared utilities package for the Algorithmic Trading System.

This package contains consolidated utility functions that were previously
duplicated across multiple components in the system. It provides consistent
implementations for common operations like formatting, validation, error
handling, and rate limiting.

Modules:
    formatting: Currency, number, and data formatting utilities
    validation: Input validation and data sanitization functions
    time_utils: Time, timezone, and market hours utilities
    error_handling: Error handling, retry mechanisms, and exception management
    rate_limiting: Rate limiting implementations for APIs and system resources

Usage:
    from shared.utils.formatting import format_currency, format_percentage
    from shared.utils.validation import validate_symbol, validate_price
    from shared.utils.time_utils import parse_timestamp, is_market_open
    from shared.utils.error_handling import retry, handle_error
    from shared.utils.rate_limiting import RateLimiter, RateLimitRule
"""

# Version information
__version__ = "1.0.0"
__author__ = "Algorithmic Trading System Team"

# Import commonly used functions for convenience
from .formatting import (
    format_currency,
    format_percentage,
    format_number,
    format_compact_number,
    format_price,
    format_volume,
    clean_symbol
)

from .validation import (
    validate_symbol,
    validate_price,
    validate_quantity,
    validate_order_side,
    validate_order_type,
    validate_order_parameters,
    validate_email,
    sanitize_input
)

from .time_utils import (
    parse_timestamp,
    format_timestamp,
    is_market_open,
    get_market_session,
    get_market_hours,
    MarketSession
)

from .error_handling import (
    TradingSystemError,
    NetworkError,
    ValidationError,
    RateLimitError,
    AuthenticationError,
    DatabaseError,
    retry,
    handle_error,
    safe_execute,
    ErrorSeverity,
    ErrorCategory
)

from .rate_limiting import (
    RateLimiter,
    RateLimitRule,
    RateLimitAlgorithm,
    RateLimitResult,
    RateLimitInfo
)

from .database_utils import (
    DatabaseConfig,
    PostgreSQLConnectionManager,
    RedisConnectionManager,
    DuckDBConnectionManager,
    get_postgres_manager,
    get_redis_manager,
    get_duckdb_manager,
    test_all_connections,
    create_connection_string
)

from .logging_utils import (
    setup_logging,
    get_logger,
    configure_trading_logger,
    StructuredFormatter,
    PerformanceLogger,
    log_api_request,
    get_performance_logger,
    set_request_context,
    clear_request_context
)

from .kafka_utils import (
    get_kafka_broker,
    create_kafka_producer,
    create_kafka_consumer
)

# Export all public functions and classes
__all__ = [
    # Formatting utilities
    'format_currency',
    'format_percentage', 
    'format_number',
    'format_compact_number',
    'format_price',
    'format_volume',
    'clean_symbol',
    
    # Validation utilities
    'validate_symbol',
    'validate_price',
    'validate_quantity',
    'validate_order_side',
    'validate_order_type',
    'validate_order_parameters',
    'validate_email',
    'sanitize_input',
    
    # Time utilities
    'parse_timestamp',
    'format_timestamp',
    'is_market_open',
    'get_market_session',
    'get_market_hours',
    'MarketSession',
    
    # Error handling
    'TradingSystemError',
    'NetworkError',
    'ValidationError',
    'RateLimitError',
    'AuthenticationError',
    'DatabaseError',
    'retry',
    'handle_error',
    'safe_execute',
    'ErrorSeverity',
    'ErrorCategory',
    
    # Rate limiting
    'RateLimiter',
    'RateLimitRule',
    'RateLimitAlgorithm',
    'RateLimitResult',
    'RateLimitInfo',
    
    # Database utilities
    'DatabaseConfig',
    'PostgreSQLConnectionManager',
    'RedisConnectionManager',
    'DuckDBConnectionManager',
    'get_postgres_manager',
    'get_redis_manager',
    'get_duckdb_manager',
    'test_all_connections',
    'create_connection_string',
    
    # Logging utilities
    'setup_logging',
    'get_logger',
    'configure_trading_logger',
    'StructuredFormatter',
    'PerformanceLogger',
    'log_api_request',
    'get_performance_logger',
    'set_request_context',
    'clear_request_context',
    
    # Kafka utilities
    'get_kafka_broker',
    'create_kafka_producer',
    'create_kafka_consumer'
]