"""
Nautilus Trader SDK Utilities

Utility functions for the Nautilus Trader Python SDK.
"""

import re
from datetime import datetime
from typing import Optional, Union, Any
from decimal import Decimal

def format_currency(amount: float, currency: str = "USD", decimals: int = 2) -> str:
    """Format currency amount"""
    if currency == "USD":
        return f"${amount:,.{decimals}f}"
    else:
        return f"{amount:,.{decimals}f} {currency}"

def parse_timestamp(timestamp: Union[str, int, float, datetime]) -> datetime:
    """Parse various timestamp formats to datetime"""
    if isinstance(timestamp, datetime):
        return timestamp
    elif isinstance(timestamp, str):
        # Try ISO format first
        try:
            return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            pass
        
        # Try other common formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse timestamp: {timestamp}")
    
    elif isinstance(timestamp, (int, float)):
        # Assume Unix timestamp
        return datetime.fromtimestamp(timestamp)
    
    else:
        raise ValueError(f"Invalid timestamp type: {type(timestamp)}")

def validate_symbol(symbol: str) -> bool:
    """Validate trading symbol format"""
    if not symbol or not isinstance(symbol, str):
        return False
    
    # Basic validation - alphanumeric characters, possibly with dots or dashes
    pattern = r'^[A-Z0-9._-]+$'
    return bool(re.match(pattern, symbol.upper()))

def validate_price(price: Union[float, int, str, Decimal]) -> bool:
    """Validate price value"""
    try:
        price_val = float(price)
        return price_val > 0
    except (ValueError, TypeError):
        return False

def validate_quantity(quantity: Union[float, int, str, Decimal]) -> bool:
    """Validate quantity value"""
    try:
        qty_val = float(quantity)
        return qty_val > 0
    except (ValueError, TypeError):
        return False

def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values"""
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / old_value) * 100

def round_to_tick_size(price: float, tick_size: float) -> float:
    """Round price to nearest tick size"""
    if tick_size <= 0:
        return price
    return round(price / tick_size) * tick_size

def format_percentage(value: float, decimals: int = 2) -> str:
    """Format percentage value"""
    return f"{value:.{decimals}f}%"

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division with default value for zero denominator"""
    if denominator == 0:
        return default
    return numerator / denominator

def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def normalize_symbol(symbol: str) -> str:
    """Normalize trading symbol"""
    return symbol.upper().strip()

def is_market_hours(market: str = "NYSE") -> bool:
    """Check if market is currently open (simplified)"""
    # This is a simplified implementation
    # In reality, you'd check actual market hours and holidays
    now = datetime.now()
    weekday = now.weekday()  # 0 = Monday, 6 = Sunday
    hour = now.hour
    
    # Basic NYSE hours (9:30 AM - 4:00 PM ET, Monday-Friday)
    if market.upper() == "NYSE":
        if weekday >= 5:  # Weekend
            return False
        return 9 <= hour < 16  # Simplified - doesn't account for timezone
    
    # Default to always open for other markets
    return True

def calculate_position_size(
    account_balance: float,
    risk_percentage: float,
    entry_price: float,
    stop_loss_price: float
) -> float:
    """Calculate position size based on risk management"""
    if entry_price <= 0 or stop_loss_price <= 0:
        return 0.0
    
    risk_amount = account_balance * (risk_percentage / 100)
    price_difference = abs(entry_price - stop_loss_price)
    
    if price_difference == 0:
        return 0.0
    
    return risk_amount / price_difference

def format_order_summary(order) -> str:
    """Format order for display"""
    return (
        f"{order.side.upper()} {order.quantity} {order.symbol} "
        f"@ {order.price or 'MARKET'} ({order.status.value})"
    )

def format_position_summary(position) -> str:
    """Format position for display"""
    pnl_sign = "+" if position.unrealized_pnl >= 0 else ""
    return (
        f"{position.symbol}: {position.quantity} @ {position.average_price:.2f} "
        f"(P&L: {pnl_sign}{position.unrealized_pnl:.2f})"
    )

class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    def can_make_call(self) -> bool:
        """Check if a call can be made within rate limits"""
        now = datetime.now()
        
        # Remove old calls outside the time window
        cutoff_time = now.timestamp() - self.time_window
        self.calls = [call_time for call_time in self.calls if call_time > cutoff_time]
        
        return len(self.calls) < self.max_calls
    
    def record_call(self):
        """Record a new API call"""
        self.calls.append(datetime.now().timestamp())

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying failed operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                    else:
                        break
            
            raise last_exception
        
        return wrapper
    return decorator