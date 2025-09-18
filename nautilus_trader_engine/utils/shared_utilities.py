"""Shared Utility Functions for Algorithmic Trading System

This module provides common utility functions used across the trading system:
- Data validation and sanitization
- Mathematical calculations
- Time and date utilities
- Configuration management
- Error handling helpers
- Performance monitoring utilities
"""

import os
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
from pathlib import Path
import numpy as np
import pandas as pd


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class ConfigurationError(Exception):
    """Custom exception for configuration errors"""
    pass


# =============================================================================
# DATA VALIDATION UTILITIES
# =============================================================================

def validate_price(price: Union[float, int]) -> float:
    """Validate and sanitize price values
    
    Args:
        price: Price value to validate
        
    Returns:
        float: Validated price
        
    Raises:
        ValidationError: If price is invalid
    """
    if price is None:
        raise ValidationError("Price cannot be None")
    
    try:
        price = float(price)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid price format: {price}")
    
    if price < 0:
        raise ValidationError(f"Price cannot be negative: {price}")
    
    if not np.isfinite(price):
        raise ValidationError(f"Price must be finite: {price}")
    
    return round(price, 8)  # Round to 8 decimal places


def validate_quantity(quantity: Union[float, int]) -> float:
    """Validate and sanitize quantity values
    
    Args:
        quantity: Quantity value to validate
        
    Returns:
        float: Validated quantity
        
    Raises:
        ValidationError: If quantity is invalid
    """
    if quantity is None:
        raise ValidationError("Quantity cannot be None")
    
    try:
        quantity = float(quantity)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid quantity format: {quantity}")
    
    if quantity <= 0:
        raise ValidationError(f"Quantity must be positive: {quantity}")
    
    if not np.isfinite(quantity):
        raise ValidationError(f"Quantity must be finite: {quantity}")
    
    return quantity


def validate_symbol(symbol: str) -> str:
    """Validate and sanitize symbol strings
    
    Args:
        symbol: Symbol string to validate
        
    Returns:
        str: Validated symbol
        
    Raises:
        ValidationError: If symbol is invalid
    """
    if not symbol or not isinstance(symbol, str):
        raise ValidationError(f"Invalid symbol: {symbol}")
    
    symbol = symbol.strip().upper()
    
    if not symbol:
        raise ValidationError("Symbol cannot be empty")
    
    # Basic symbol validation (alphanumeric and common separators)
    if not all(c.isalnum() or c in '.-_/' for c in symbol):
        raise ValidationError(f"Symbol contains invalid characters: {symbol}")
    
    return symbol


# =============================================================================
# MATHEMATICAL UTILITIES
# =============================================================================

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, handling division by zero
    
    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Default value to return if division by zero
        
    Returns:
        float: Result of division or default value
    """
    if denominator == 0 or not np.isfinite(denominator):
        return default
    
    result = numerator / denominator
    return result if np.isfinite(result) else default


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values
    
    Args:
        old_value: Original value
        new_value: New value
        
    Returns:
        float: Percentage change
    """
    if old_value == 0:
        return 0.0 if new_value == 0 else float('inf')
    
    return ((new_value - old_value) / abs(old_value)) * 100


def normalize_value(value: float, min_val: float, max_val: float) -> float:
    """Normalize a value to range [0, 1]
    
    Args:
        value: Value to normalize
        min_val: Minimum value in range
        max_val: Maximum value in range
        
    Returns:
        float: Normalized value
    """
    if max_val == min_val:
        return 0.5  # Return middle value if range is zero
    
    return (value - min_val) / (max_val - min_val)


# =============================================================================
# TIME AND DATE UTILITIES
# =============================================================================

def get_current_utc_timestamp() -> datetime:
    """Get current UTC timestamp
    
    Returns:
        datetime: Current UTC timestamp
    """
    return datetime.now(timezone.utc)


def convert_to_utc(dt: datetime, source_tz: str = 'US/Eastern') -> datetime:
    """Convert datetime to UTC
    
    Args:
        dt: Datetime to convert
        source_tz: Source timezone string
        
    Returns:
        datetime: UTC datetime
    """
    import pytz
    
    if dt.tzinfo is None:
        # Assume source timezone if naive datetime
        source_timezone = pytz.timezone(source_tz)
        dt = source_timezone.localize(dt)
    
    return dt.astimezone(timezone.utc)


def is_market_hours(dt: Optional[datetime] = None, market: str = 'NYSE') -> bool:
    """Check if given time is within market hours
    
    Args:
        dt: Datetime to check (defaults to current time)
        market: Market identifier
        
    Returns:
        bool: True if within market hours
    """
    if dt is None:
        dt = get_current_utc_timestamp()
    
    # Convert to market timezone
    import pytz
    
    market_timezones = {
        'NYSE': 'US/Eastern',
        'NASDAQ': 'US/Eastern',
        'LSE': 'Europe/London',
        'TSE': 'Asia/Tokyo'
    }
    
    tz_str = market_timezones.get(market, 'US/Eastern')
    market_tz = pytz.timezone(tz_str)
    market_time = dt.astimezone(market_tz)
    
    # Check if weekday and within trading hours (9:30 AM - 4:00 PM)
    if market_time.weekday() >= 5:  # Weekend
        return False
    
    market_open = market_time.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = market_time.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= market_time <= market_close


# =============================================================================
# CONFIGURATION UTILITIES
# =============================================================================

def load_config(config_path: Union[str, Path]) -> Dict[str, Any]:
    """Load configuration from JSON file
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Dict: Configuration dictionary
        
    Raises:
        ConfigurationError: If config cannot be loaded
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise ConfigurationError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        raise ConfigurationError(f"Invalid JSON in config file: {e}")
    except Exception as e:
        raise ConfigurationError(f"Error loading config: {e}")


def get_env_var(var_name: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """Get environment variable with validation
    
    Args:
        var_name: Environment variable name
        default: Default value if not found
        required: Whether the variable is required
        
    Returns:
        str: Environment variable value
        
    Raises:
        ConfigurationError: If required variable is missing
    """
    value = os.environ.get(var_name, default)
    
    if required and value is None:
        raise ConfigurationError(f"Required environment variable not set: {var_name}")
    
    return value


# =============================================================================
# ERROR HANDLING UTILITIES
# =============================================================================

def retry_on_exception(max_retries: int = 3, delay: float = 1.0, 
                      exceptions: tuple = (Exception,)) -> Callable:
    """Decorator to retry function on exception
    
    Args:
        max_retries: Maximum number of retries
        delay: Delay between retries in seconds
        exceptions: Tuple of exceptions to catch
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        logging.error(f"All {max_retries + 1} attempts failed")
            
            raise last_exception
        
        return wrapper
    return decorator


def log_execution_time(func: Callable) -> Callable:
    """Decorator to log function execution time
    
    Args:
        func: Function to decorate
        
    Returns:
        Callable: Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logging.info(f"{func.__name__} executed in {execution_time:.4f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logging.error(f"{func.__name__} failed after {execution_time:.4f}s: {e}")
            raise
    
    return wrapper


# =============================================================================
# PERFORMANCE MONITORING UTILITIES
# =============================================================================

class PerformanceMonitor:
    """Simple performance monitoring utility"""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
    
    def start_timer(self, name: str) -> None:
        """Start timing an operation
        
        Args:
            name: Name of the operation
        """
        self.start_times[name] = time.time()
    
    def end_timer(self, name: str) -> float:
        """End timing an operation and record the duration
        
        Args:
            name: Name of the operation
            
        Returns:
            float: Duration in seconds
        """
        if name not in self.start_times:
            logging.warning(f"Timer '{name}' was not started")
            return 0.0
        
        duration = time.time() - self.start_times[name]
        
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append(duration)
        del self.start_times[name]
        
        return duration
    
    def get_stats(self, name: str) -> Dict[str, float]:
        """Get statistics for a metric
        
        Args:
            name: Name of the metric
            
        Returns:
            Dict: Statistics dictionary
        """
        if name not in self.metrics or not self.metrics[name]:
            return {}
        
        values = self.metrics[name]
        return {
            'count': len(values),
            'mean': np.mean(values),
            'median': np.median(values),
            'min': np.min(values),
            'max': np.max(values),
            'std': np.std(values)
        }
    
    def reset(self, name: Optional[str] = None) -> None:
        """Reset metrics
        
        Args:
            name: Name of specific metric to reset (None for all)
        """
        if name is None:
            self.metrics.clear()
            self.start_times.clear()
        else:
            self.metrics.pop(name, None)
            self.start_times.pop(name, None)


# =============================================================================
# DATA PROCESSING UTILITIES
# =============================================================================

def clean_dataframe(df: pd.DataFrame, drop_na: bool = True, 
                   fill_method: Optional[str] = None) -> pd.DataFrame:
    """Clean and preprocess DataFrame
    
    Args:
        df: DataFrame to clean
        drop_na: Whether to drop rows with NaN values
        fill_method: Method to fill NaN values ('forward', 'backward', 'mean')
        
    Returns:
        pd.DataFrame: Cleaned DataFrame
    """
    df_clean = df.copy()
    
    # Remove duplicate rows
    df_clean = df_clean.drop_duplicates()
    
    # Handle NaN values
    if fill_method == 'forward':
        df_clean = df_clean.fillna(method='ffill')
    elif fill_method == 'backward':
        df_clean = df_clean.fillna(method='bfill')
    elif fill_method == 'mean':
        numeric_columns = df_clean.select_dtypes(include=[np.number]).columns
        df_clean[numeric_columns] = df_clean[numeric_columns].fillna(
            df_clean[numeric_columns].mean()
        )
    elif drop_na:
        df_clean = df_clean.dropna()
    
    return df_clean


def calculate_returns(prices: pd.Series, method: str = 'simple') -> pd.Series:
    """Calculate returns from price series
    
    Args:
        prices: Price series
        method: Return calculation method ('simple' or 'log')
        
    Returns:
        pd.Series: Returns series
    """
    if method == 'simple':
        return prices.pct_change().dropna()
    elif method == 'log':
        return np.log(prices / prices.shift(1)).dropna()
    else:
        raise ValueError(f"Unknown return method: {method}")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# =============================================================================
# MODULE INITIALIZATION
# =============================================================================

def initialize_shared_utilities(log_level: str = 'INFO') -> None:
    """Initialize shared utilities module
    
    Args:
        log_level: Logging level
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logging.info("Shared utilities module initialized")


if __name__ == "__main__":
    # Example usage
    initialize_shared_utilities()
    
    # Test validation functions
    try:
        price = validate_price(100.50)
        quantity = validate_quantity(1000)
        symbol = validate_symbol("AAPL")
        print(f"Validated: price={price}, quantity={quantity}, symbol={symbol}")
    except ValidationError as e:
        print(f"Validation error: {e}")
    
    # Test performance monitoring
    performance_monitor.start_timer('test_operation')
    time.sleep(0.1)  # Simulate work
    duration = performance_monitor.end_timer('test_operation')
    print(f"Operation took {duration:.4f} seconds")
    
    stats = performance_monitor.get_stats('test_operation')
    print(f"Performance stats: {stats}")