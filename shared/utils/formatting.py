"""
Shared formatting utilities for the Algorithmic Trading System.

This module consolidates all formatting functions that were previously duplicated
across multiple components. Provides consistent formatting for currency, numbers,
percentages, and other financial data types.
"""

import re
from decimal import Decimal
from typing import Union, Optional


def format_currency(
    amount: Union[float, int, Decimal, str], 
    currency: str = "USD", 
    decimals: int = 2
) -> str:
    """
    Format currency amount with proper locale and currency symbol.
    
    Args:
        amount: The monetary amount to format
        currency: Currency code (default: USD)
        decimals: Number of decimal places to display
        
    Returns:
        Formatted currency string
        
    Examples:
        >>> format_currency(1234.56, "USD")
        '$1,234.56'
        >>> format_currency(1000, "EUR", 0)
        '€1,000'
    """
    try:
        amount_val = float(amount)
    except (ValueError, TypeError):
        return f"${0:,.{decimals}f}"
    
    if currency == "USD":
        return f"${amount_val:,.{decimals}f}"
    elif currency == "EUR":
        return f"€{amount_val:,.{decimals}f}"
    elif currency == "GBP":
        return f"£{amount_val:,.{decimals}f}"
    elif currency == "JPY":
        return f"¥{amount_val:,.0f}"  # JPY typically has no decimals
    else:
        return f"{amount_val:,.{decimals}f} {currency}"


def format_percentage(value: Union[float, int, Decimal], decimals: int = 2) -> str:
    """
    Format percentage value with consistent display.
    
    Args:
        value: Percentage value (e.g., 0.05 for 5% or 5 for 5%)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
        
    Examples:
        >>> format_percentage(0.0523, 2)
        '5.23%'
        >>> format_percentage(5.23, 1)
        '5.2%'
    """
    try:
        value_float = float(value)
        # Handle both decimal (0.05) and whole number (5) representations
        if abs(value_float) <= 1:
            value_float *= 100
        return f"{value_float:.{decimals}f}%"
    except (ValueError, TypeError):
        return f"{0:.{decimals}f}%"


def format_number(
    num: Union[float, int, Decimal], 
    decimals: int = 2, 
    compact: bool = False
) -> str:
    """
    Format numbers with proper thousand separators and optional compact notation.
    
    Args:
        num: Number to format
        decimals: Number of decimal places
        compact: If True, use compact notation (1.2K, 1.5M, etc.)
        
    Returns:
        Formatted number string
        
    Examples:
        >>> format_number(1234567.89)
        '1,234,567.89'
        >>> format_number(1234567, compact=True)
        '1.23M'
    """
    try:
        num_val = float(num)
    except (ValueError, TypeError):
        return f"{0:,.{decimals}f}"
    
    if compact:
        return format_compact_number(num_val, decimals)
    else:
        return f"{num_val:,.{decimals}f}"


def format_compact_number(value: float, decimals: int = 1) -> str:
    """
    Format large numbers in compact notation (K, M, B, T).
    
    Args:
        value: Number to format
        decimals: Number of decimal places for compact notation
        
    Returns:
        Compact formatted number
        
    Examples:
        >>> format_compact_number(1500)
        '1.5K'
        >>> format_compact_number(2500000)
        '2.5M'
    """
    abs_value = abs(value)
    sign = '-' if value < 0 else ''
    
    if abs_value >= 1e12:  # Trillion
        return f"{sign}{abs_value / 1e12:.{decimals}f}T"
    elif abs_value >= 1e9:  # Billion
        return f"{sign}{abs_value / 1e9:.{decimals}f}B"
    elif abs_value >= 1e6:  # Million
        return f"{sign}{abs_value / 1e6:.{decimals}f}M"
    elif abs_value >= 1e3:  # Thousand
        return f"{sign}{abs_value / 1e3:.{decimals}f}K"
    else:
        return f"{sign}{abs_value:.{decimals}f}"


def format_change_with_sign(
    value: Union[float, int, Decimal], 
    decimals: int = 2,
    as_percentage: bool = False
) -> str:
    """
    Format a change value with appropriate sign (+ or -).
    
    Args:
        value: Change value
        decimals: Number of decimal places
        as_percentage: If True, format as percentage
        
    Returns:
        Formatted change string with sign
        
    Examples:
        >>> format_change_with_sign(5.23)
        '+5.23'
        >>> format_change_with_sign(-2.1, as_percentage=True)
        '-2.10%'
    """
    try:
        value_float = float(value)
        sign = '+' if value_float >= 0 else ''
        
        if as_percentage:
            return f"{sign}{value_float:.{decimals}f}%"
        else:
            return f"{sign}{value_float:.{decimals}f}"
    except (ValueError, TypeError):
        return f"+{0:.{decimals}f}{'%' if as_percentage else ''}"


def format_price(
    price: Union[float, int, Decimal, str], 
    symbol: Optional[str] = None,
    decimals: Optional[int] = None
) -> str:
    """
    Format price with appropriate decimal places based on asset type.
    
    Args:
        price: Price value to format
        symbol: Trading symbol (used to determine decimal places)
        decimals: Override decimal places
        
    Returns:
        Formatted price string
        
    Examples:
        >>> format_price(123.456, "AAPL")
        '123.46'
        >>> format_price(1.23456, "EURUSD")
        '1.2346'
    """
    try:
        price_val = float(price)
    except (ValueError, TypeError):
        return "0.00"
    
    if decimals is not None:
        return f"{price_val:.{decimals}f}"
    
    # Determine decimal places based on asset type
    if symbol:
        symbol = symbol.upper()
        # Forex pairs typically use 4-5 decimal places
        if '/' in symbol or any(fx in symbol for fx in ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD']):
            if 'JPY' in symbol:
                return f"{price_val:.3f}"  # JPY pairs use 3 decimals
            else:
                return f"{price_val:.5f}"  # Other forex pairs use 5 decimals
        # Crypto pairs
        elif any(crypto in symbol for crypto in ['BTC', 'ETH', 'ADA', 'DOT', 'LINK']):
            return f"{price_val:.8f}"  # Crypto typically uses more decimals
    
    # Default to 2 decimal places for stocks
    return f"{price_val:.2f}"


def format_volume(volume: Union[float, int], compact: bool = True) -> str:
    """
    Format trading volume with appropriate scaling.
    
    Args:
        volume: Volume value
        compact: If True, use compact notation
        
    Returns:
        Formatted volume string
        
    Examples:
        >>> format_volume(1500000)
        '1.5M'
        >>> format_volume(1500000, compact=False)
        '1,500,000'
    """
    try:
        volume_val = float(volume)
        if compact:
            return format_compact_number(volume_val, 1)
        else:
            return f"{volume_val:,.0f}"
    except (ValueError, TypeError):
        return "0"


def format_market_cap(market_cap: Union[float, int, Decimal]) -> str:
    """
    Format market capitalization in appropriate scale.
    
    Args:
        market_cap: Market cap value
        
    Returns:
        Formatted market cap string
        
    Examples:
        >>> format_market_cap(2500000000)
        '$2.5B'
        >>> format_market_cap(150000000)
        '$150.0M'
    """
    return format_currency(market_cap, decimals=1) if float(market_cap) < 1e6 else f"${format_compact_number(float(market_cap), 1)}"


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate string to maximum length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to append when truncated
        
    Returns:
        Truncated string
        
    Examples:
        >>> truncate_string("This is a long text", 10)
        'This is...'
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def clean_symbol(symbol: str) -> str:
    """
    Clean and normalize trading symbol.
    
    Args:
        symbol: Raw symbol string
        
    Returns:
        Cleaned symbol
        
    Examples:
        >>> clean_symbol(" aapl ")
        'AAPL'
        >>> clean_symbol("btc-usd")
        'BTCUSD'
    """
    if not symbol:
        return ""
    
    # Remove whitespace and convert to uppercase
    cleaned = symbol.strip().upper()
    
    # Remove common separators for normalization
    cleaned = re.sub(r'[-_./]', '', cleaned)
    
    return cleaned