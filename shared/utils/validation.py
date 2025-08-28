"""
Shared validation utilities for the Algorithmic Trading System.

This module consolidates all validation functions that were previously duplicated
across multiple components. Provides consistent validation for trading symbols,
prices, quantities, and other financial data.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Union, Optional, Tuple, List
from datetime import datetime, time


def validate_symbol(symbol: str) -> bool:
    """
    Validate trading symbol format.
    
    Args:
        symbol: Trading symbol to validate
        
    Returns:
        True if symbol is valid, False otherwise
        
    Examples:
        >>> validate_symbol("AAPL")
        True
        >>> validate_symbol("BTC/USD")
        True
        >>> validate_symbol("")
        False
    """
    if not symbol or not isinstance(symbol, str):
        return False
    
    # Remove whitespace and convert to uppercase
    symbol = symbol.strip().upper()
    
    # Basic validation patterns
    patterns = [
        r'^[A-Z0-9._-]+$',           # Basic alphanumeric with separators
        r'^[A-Z]{1,5}$',             # Simple stock symbols (1-5 chars)
        r'^[A-Z]{1,5}/[A-Z]{1,5}$',  # Forex pairs (EUR/USD)
        r'^[A-Z]{1,10}-[A-Z]{1,10}$', # Crypto pairs (BTC-USD)
        r'^[A-Z]{1,10}\.[A-Z]{1,5}$'  # Dotted notation (AAPL.O)
    ]
    
    return any(re.match(pattern, symbol) for pattern in patterns)


def validate_price(price: Union[float, int, str, Decimal]) -> bool:
    """
    Validate price value.
    
    Args:
        price: Price value to validate
        
    Returns:
        True if price is valid, False otherwise
        
    Examples:
        >>> validate_price(100.50)
        True
        >>> validate_price(-50)
        False
        >>> validate_price("invalid")
        False
    """
    try:
        if isinstance(price, str):
            # Remove currency symbols and whitespace
            price_clean = re.sub(r'[^0-9.-]', '', price.strip())
            price_val = float(price_clean)
        else:
            price_val = float(price)
        
        return price_val > 0 and not (price_val != price_val)  # Check for NaN
    except (ValueError, TypeError, InvalidOperation):
        return False


def validate_quantity(quantity: Union[float, int, str, Decimal]) -> bool:
    """
    Validate quantity value.
    
    Args:
        quantity: Quantity value to validate
        
    Returns:
        True if quantity is valid, False otherwise
        
    Examples:
        >>> validate_quantity(100)
        True
        >>> validate_quantity(0)
        False
        >>> validate_quantity(-50)
        False
    """
    try:
        qty_val = float(quantity)
        return qty_val > 0 and not (qty_val != qty_val)  # Check for NaN
    except (ValueError, TypeError, InvalidOperation):
        return False


def validate_order_side(side: str) -> bool:
    """
    Validate order side.
    
    Args:
        side: Order side (buy/sell)
        
    Returns:
        True if side is valid, False otherwise
        
    Examples:
        >>> validate_order_side("buy")
        True
        >>> validate_order_side("SELL")
        True
        >>> validate_order_side("invalid")
        False
    """
    if not isinstance(side, str):
        return False
    
    return side.lower() in ['buy', 'sell', 'long', 'short']


def validate_order_type(order_type: str) -> bool:
    """
    Validate order type.
    
    Args:
        order_type: Order type to validate
        
    Returns:
        True if order type is valid, False otherwise
        
    Examples:
        >>> validate_order_type("market")
        True
        >>> validate_order_type("LIMIT")
        True
        >>> validate_order_type("invalid")
        False
    """
    if not isinstance(order_type, str):
        return False
    
    valid_types = [
        'market', 'limit', 'stop', 'stop_limit', 'stop_loss', 
        'take_profit', 'trailing_stop', 'iceberg', 'twap', 'vwap'
    ]
    
    return order_type.lower() in valid_types


def validate_time_in_force(tif: str) -> bool:
    """
    Validate time in force parameter.
    
    Args:
        tif: Time in force value
        
    Returns:
        True if TIF is valid, False otherwise
        
    Examples:
        >>> validate_time_in_force("day")
        True
        >>> validate_time_in_force("GTC")
        True
        >>> validate_time_in_force("invalid")
        False
    """
    if not isinstance(tif, str):
        return False
    
    valid_tifs = ['day', 'gtc', 'ioc', 'fok', 'gtd', 'at_open', 'at_close']
    return tif.lower() in valid_tifs


def validate_currency_code(currency: str) -> bool:
    """
    Validate currency code format.
    
    Args:
        currency: Currency code to validate
        
    Returns:
        True if currency code is valid, False otherwise
        
    Examples:
        >>> validate_currency_code("USD")
        True
        >>> validate_currency_code("BTC")
        True
        >>> validate_currency_code("invalid")
        False
    """
    if not isinstance(currency, str):
        return False
    
    currency = currency.upper().strip()
    
    # Standard 3-letter currency codes or crypto symbols
    return re.match(r'^[A-Z]{3,10}$', currency) is not None


def validate_percentage(percentage: Union[float, int, str]) -> bool:
    """
    Validate percentage value.
    
    Args:
        percentage: Percentage value to validate
        
    Returns:
        True if percentage is valid, False otherwise
        
    Examples:
        >>> validate_percentage(25.5)
        True
        >>> validate_percentage(-10)
        True
        >>> validate_percentage(150)
        True
    """
    try:
        pct_val = float(percentage)
        # Allow negative percentages (for losses) and values over 100% (for gains)
        return not (pct_val != pct_val)  # Check for NaN
    except (ValueError, TypeError):
        return False


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email is valid, False otherwise
        
    Examples:
        >>> validate_email("user@example.com")
        True
        >>> validate_email("invalid-email")
        False
    """
    if not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email.strip()) is not None


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        True if phone number is valid, False otherwise
        
    Examples:
        >>> validate_phone_number("+1-555-123-4567")
        True
        >>> validate_phone_number("5551234567")
        True
        >>> validate_phone_number("invalid")
        False
    """
    if not isinstance(phone, str):
        return False
    
    # Remove all non-digit characters except +
    clean_phone = re.sub(r'[^\d+]', '', phone.strip())
    
    # Valid phone number should have 10-15 digits (with optional + prefix)
    pattern = r'^\+?[1-9]\d{9,14}$'
    return re.match(pattern, clean_phone) is not None


def validate_date_range(start_date: datetime, end_date: datetime) -> bool:
    """
    Validate date range.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        True if date range is valid, False otherwise
        
    Examples:
        >>> from datetime import datetime
        >>> validate_date_range(datetime(2023, 1, 1), datetime(2023, 12, 31))
        True
        >>> validate_date_range(datetime(2023, 12, 31), datetime(2023, 1, 1))
        False
    """
    if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
        return False
    
    return start_date <= end_date


def validate_market_hours(current_time: time, market_open: time, market_close: time) -> bool:
    """
    Check if current time is within market hours.
    
    Args:
        current_time: Current time
        market_open: Market opening time
        market_close: Market closing time
        
    Returns:
        True if within market hours, False otherwise
        
    Examples:
        >>> from datetime import time
        >>> validate_market_hours(time(10, 30), time(9, 30), time(16, 0))
        True
        >>> validate_market_hours(time(18, 0), time(9, 30), time(16, 0))
        False
    """
    if not all(isinstance(t, time) for t in [current_time, market_open, market_close]):
        return False
    
    return market_open <= current_time <= market_close


def validate_order_parameters(
    symbol: str,
    side: str,
    quantity: Union[float, int],
    order_type: str,
    price: Optional[Union[float, int]] = None,
    stop_price: Optional[Union[float, int]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Comprehensive order parameter validation.
    
    Args:
        symbol: Trading symbol
        side: Order side (buy/sell)
        quantity: Order quantity
        order_type: Order type
        price: Limit price (for limit orders)
        stop_price: Stop price (for stop orders)
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Examples:
        >>> validate_order_parameters("AAPL", "buy", 100, "limit", 150.0)
        (True, None)
        >>> validate_order_parameters("", "buy", 100, "market")
        (False, "Invalid symbol")
    """
    # Validate symbol
    if not validate_symbol(symbol):
        return False, "Invalid symbol"
    
    # Validate side
    if not validate_order_side(side):
        return False, "Invalid order side. Must be 'buy' or 'sell'"
    
    # Validate quantity
    if not validate_quantity(quantity):
        return False, "Invalid quantity. Must be positive"
    
    # Validate order type
    if not validate_order_type(order_type):
        return False, "Invalid order type"
    
    # Validate price for limit orders
    if order_type.lower() in ['limit', 'stop_limit']:
        if price is None:
            return False, f"{order_type} orders require a price"
        if not validate_price(price):
            return False, "Invalid price"
    
    # Validate stop price for stop orders
    if order_type.lower() in ['stop', 'stop_limit', 'stop_loss']:
        if stop_price is None:
            return False, f"{order_type} orders require a stop price"
        if not validate_price(stop_price):
            return False, "Invalid stop price"
    
    return True, None


def validate_portfolio_allocation(allocations: List[Tuple[str, float]]) -> Tuple[bool, Optional[str]]:
    """
    Validate portfolio allocation percentages.
    
    Args:
        allocations: List of (symbol, percentage) tuples
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Examples:
        >>> validate_portfolio_allocation([("AAPL", 50.0), ("GOOGL", 30.0), ("CASH", 20.0)])
        (True, None)
        >>> validate_portfolio_allocation([("AAPL", 60.0), ("GOOGL", 50.0)])
        (False, "Allocations exceed 100%")
    """
    if not allocations:
        return False, "No allocations provided"
    
    total_allocation = 0
    seen_symbols = set()
    
    for symbol, percentage in allocations:
        # Validate symbol
        if not validate_symbol(symbol) and symbol.upper() != 'CASH':
            return False, f"Invalid symbol: {symbol}"
        
        # Check for duplicates
        if symbol in seen_symbols:
            return False, f"Duplicate symbol: {symbol}"
        seen_symbols.add(symbol)
        
        # Validate percentage
        if not validate_percentage(percentage):
            return False, f"Invalid percentage for {symbol}"
        
        if percentage < 0:
            return False, f"Negative allocation not allowed for {symbol}"
        
        total_allocation += percentage
    
    # Check total allocation
    if abs(total_allocation - 100.0) > 0.01:  # Allow small rounding errors
        return False, f"Allocations total {total_allocation:.2f}%, must equal 100%"
    
    return True, None


def sanitize_input(input_str: str, max_length: int = 255) -> str:
    """
    Sanitize user input by removing potentially harmful characters.
    
    Args:
        input_str: Input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
        
    Examples:
        >>> sanitize_input("Hello <script>alert('xss')</script>")
        'Hello scriptalert(xss)/script'
    """
    if not isinstance(input_str, str):
        return ""
    
    # Remove HTML tags and script content
    sanitized = re.sub(r'<[^>]*>', '', input_str)
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\';\\]', '', sanitized)
    
    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()


def validate_api_key(api_key: str) -> bool:
    """
    Validate API key format.
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if API key format is valid, False otherwise
        
    Examples:
        >>> validate_api_key("abc123def456")
        True
        >>> validate_api_key("short")
        False
    """
    if not isinstance(api_key, str):
        return False
    
    # API key should be alphanumeric and at least 8 characters
    return re.match(r'^[a-zA-Z0-9]{8,}$', api_key.strip()) is not None