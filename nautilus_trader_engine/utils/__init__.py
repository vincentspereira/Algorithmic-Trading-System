"""Utilities Package for Nautilus Trader Engine

This package provides comprehensive utility functions for the algorithmic trading system:
- Shared utilities for common operations
- Trading-specific utilities for order management and risk calculations
- FIX protocol utilities for institutional connectivity
- Interactive Brokers utilities for broker integration
- Logging configuration utilities
"""

# Import shared utilities
from .shared_utilities import (
    # Validation functions
    validate_price,
    validate_quantity,
    validate_symbol,
    ValidationError,
    ConfigurationError,
    
    # Mathematical utilities
    safe_divide,
    calculate_percentage_change,
    normalize_value,
    
    # Time and date utilities
    get_current_utc_timestamp,
    convert_to_utc,
    is_market_hours,
    
    # Configuration utilities
    load_config,
    get_env_var,
    
    # Error handling utilities
    retry_on_exception,
    log_execution_time,
    
    # Performance monitoring
    PerformanceMonitor,
    performance_monitor,
    
    # Data processing utilities
    clean_dataframe,
    calculate_returns,
    
    # Module initialization
    initialize_shared_utilities
)

# Import trading utilities
from .trading_utilities import (
    # Enums
    OrderSide,
    OrderType,
    PositionSide,
    
    # Order management utilities
    calculate_order_value,
    calculate_lot_size,
    round_to_tick_size,
    
    # Position calculations
    calculate_position_pnl,
    calculate_position_return,
    calculate_average_price,
    
    # Risk management utilities
    calculate_var,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    
    # Portfolio analysis utilities
    calculate_portfolio_value,
    calculate_portfolio_weights,
    
    # Market data processing utilities
    calculate_vwap,
    calculate_typical_price,
    calculate_true_range,
    detect_gaps,
    
    # Backtesting utilities
    calculate_trade_statistics,
    calculate_equity_curve
)

# Import existing utilities
try:
    from .fix_utils import (
        create_fix_message,
        convert_to_fix_format,
        parse_fix_message
    )
except ImportError:
    # Handle case where fix_utils might not be available
    pass

try:
    from .ib_utils import (
        convert_nautilus_to_ib_order,
        convert_ib_to_nautilus_position,
        map_ib_contract_to_nautilus_instrument
    )
except ImportError:
    # Handle case where ib_utils might not be available
    pass

try:
    from .logging_config import setup_logging
except ImportError:
    # Handle case where logging_config might not be available
    pass

# Package version
__version__ = "1.0.0"

# Package metadata
__author__ = "Nautilus Trader Engine Team"
__description__ = "Comprehensive utilities for algorithmic trading system"

# All exported symbols
__all__ = [
    # Shared utilities
    'validate_price',
    'validate_quantity', 
    'validate_symbol',
    'ValidationError',
    'ConfigurationError',
    'safe_divide',
    'calculate_percentage_change',
    'normalize_value',
    'get_current_utc_timestamp',
    'convert_to_utc',
    'is_market_hours',
    'load_config',
    'get_env_var',
    'retry_on_exception',
    'log_execution_time',
    'PerformanceMonitor',
    'performance_monitor',
    'clean_dataframe',
    'calculate_returns',
    'initialize_shared_utilities',
    
    # Trading utilities
    'OrderSide',
    'OrderType',
    'PositionSide',
    'calculate_order_value',
    'calculate_lot_size',
    'round_to_tick_size',
    'calculate_position_pnl',
    'calculate_position_return',
    'calculate_average_price',
    'calculate_var',
    'calculate_max_drawdown',
    'calculate_sharpe_ratio',
    'calculate_sortino_ratio',
    'calculate_portfolio_value',
    'calculate_portfolio_weights',
    'calculate_vwap',
    'calculate_typical_price',
    'calculate_true_range',
    'detect_gaps',
    'calculate_trade_statistics',
    'calculate_equity_curve',
    
    # Existing utilities (if available)
    'create_fix_message',
    'convert_to_fix_format',
    'parse_fix_message',
    'convert_nautilus_to_ib_order',
    'convert_ib_to_nautilus_position',
    'map_ib_contract_to_nautilus_instrument',
    'setup_logging'
]

# Remove None values from __all__ (for optional imports)
__all__ = [item for item in __all__ if item in globals()]


def get_available_utilities() -> dict:
    """Get information about available utility functions
    
    Returns:
        dict: Dictionary containing utility categories and functions
    """
    utilities = {
        'validation': [
            'validate_price', 'validate_quantity', 'validate_symbol'
        ],
        'mathematical': [
            'safe_divide', 'calculate_percentage_change', 'normalize_value'
        ],
        'time_date': [
            'get_current_utc_timestamp', 'convert_to_utc', 'is_market_hours'
        ],
        'configuration': [
            'load_config', 'get_env_var'
        ],
        'error_handling': [
            'retry_on_exception', 'log_execution_time'
        ],
        'performance': [
            'PerformanceMonitor', 'performance_monitor'
        ],
        'data_processing': [
            'clean_dataframe', 'calculate_returns'
        ],
        'order_management': [
            'calculate_order_value', 'calculate_lot_size', 'round_to_tick_size'
        ],
        'position_calculations': [
            'calculate_position_pnl', 'calculate_position_return', 'calculate_average_price'
        ],
        'risk_management': [
            'calculate_var', 'calculate_max_drawdown', 'calculate_sharpe_ratio', 'calculate_sortino_ratio'
        ],
        'portfolio_analysis': [
            'calculate_portfolio_value', 'calculate_portfolio_weights'
        ],
        'market_data': [
            'calculate_vwap', 'calculate_typical_price', 'calculate_true_range', 'detect_gaps'
        ],
        'backtesting': [
            'calculate_trade_statistics', 'calculate_equity_curve'
        ]
    }
    
    # Filter out functions that aren't actually available
    available_utilities = {}
    for category, functions in utilities.items():
        available_functions = [func for func in functions if func in globals()]
        if available_functions:
            available_utilities[category] = available_functions
    
    return available_utilities


def print_utility_summary():
    """Print a summary of available utilities"""
    print("\n=== Nautilus Trader Engine Utilities ===")
    print(f"Version: {__version__}")
    print(f"Description: {__description__}")
    print("\nAvailable Utility Categories:")
    
    utilities = get_available_utilities()
    for category, functions in utilities.items():
        print(f"\n{category.replace('_', ' ').title()}:")
        for func in functions:
            print(f"  - {func}")
    
    print(f"\nTotal functions available: {sum(len(funcs) for funcs in utilities.values())}")
    print("\nFor detailed documentation, use help() on any function.")


if __name__ == "__main__":
    print_utility_summary()