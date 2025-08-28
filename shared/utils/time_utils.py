"""
Shared time utilities for the Algorithmic Trading System.

This module consolidates all time and timestamp handling functions that were
previously duplicated across multiple components. Provides consistent handling
for timestamps, market hours, and time zone conversions.
"""

import pytz
from datetime import datetime, time, timedelta, timezone
from typing import Union, Optional, Dict, Any
import re
from enum import Enum


class MarketSession(Enum):
    """Market session types"""
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"
    CLOSED = "closed"


class TimeZone(Enum):
    """Common trading time zones"""
    UTC = "UTC"
    NEW_YORK = "America/New_York"
    LONDON = "Europe/London"
    TOKYO = "Asia/Tokyo"
    HONG_KONG = "Asia/Hong_Kong"
    SYDNEY = "Australia/Sydney"


def parse_timestamp(timestamp: Union[str, int, float, datetime]) -> datetime:
    """
    Parse various timestamp formats to datetime object.
    
    Args:
        timestamp: Timestamp in various formats
        
    Returns:
        Parsed datetime object
        
    Raises:
        ValueError: If timestamp cannot be parsed
        
    Examples:
        >>> parse_timestamp("2023-12-25T10:30:00Z")
        datetime(2023, 12, 25, 10, 30, tzinfo=timezone.utc)
        >>> parse_timestamp(1703505000)
        datetime(2023, 12, 25, 10, 30, tzinfo=timezone.utc)
    """
    if isinstance(timestamp, datetime):
        # Ensure timezone awareness
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)
        return timestamp
    
    elif isinstance(timestamp, str):
        timestamp = timestamp.strip()
        
        # Try ISO format first
        try:
            # Handle various ISO formats
            if timestamp.endswith('Z'):
                timestamp = timestamp[:-1] + '+00:00'
            elif '+' not in timestamp and timestamp.count(':') >= 2:
                # Add UTC timezone if missing
                timestamp += '+00:00'
            
            return datetime.fromisoformat(timestamp)
        except ValueError:
            pass
        
        # Try other common formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%d',
            '%m/%d/%Y %H:%M:%S',
            '%m/%d/%Y',
            '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y',
            '%Y%m%d %H:%M:%S',
            '%Y%m%d'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse timestamp: {timestamp}")
    
    elif isinstance(timestamp, (int, float)):
        # Handle Unix timestamps (seconds since epoch)
        try:
            # Check if timestamp is in milliseconds
            if timestamp > 1e10:  # Likely milliseconds
                timestamp = timestamp / 1000
            
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (ValueError, OSError):
            raise ValueError(f"Invalid Unix timestamp: {timestamp}")
    
    else:
        raise ValueError(f"Invalid timestamp type: {type(timestamp)}")


def format_timestamp(
    dt: datetime, 
    format_type: str = "iso", 
    timezone_name: Optional[str] = None
) -> str:
    """
    Format datetime to string representation.
    
    Args:
        dt: Datetime object to format
        format_type: Format type ('iso', 'readable', 'date_only', 'time_only')
        timezone_name: Target timezone name
        
    Returns:
        Formatted timestamp string
        
    Examples:
        >>> dt = datetime(2023, 12, 25, 10, 30, tzinfo=timezone.utc)
        >>> format_timestamp(dt, "iso")
        '2023-12-25T10:30:00+00:00'
        >>> format_timestamp(dt, "readable")
        '2023-12-25 10:30:00 UTC'
    """
    if timezone_name:
        tz = pytz.timezone(timezone_name)
        dt = dt.astimezone(tz)
    
    if format_type == "iso":
        return dt.isoformat()
    elif format_type == "readable":
        return dt.strftime('%Y-%m-%d %H:%M:%S %Z')
    elif format_type == "date_only":
        return dt.strftime('%Y-%m-%d')
    elif format_type == "time_only":
        return dt.strftime('%H:%M:%S')
    elif format_type == "compact":
        return dt.strftime('%Y%m%d_%H%M%S')
    else:
        return dt.isoformat()


def convert_timezone(
    dt: datetime, 
    from_tz: str, 
    to_tz: str
) -> datetime:
    """
    Convert datetime between time zones.
    
    Args:
        dt: Datetime object
        from_tz: Source timezone name
        to_tz: Target timezone name
        
    Returns:
        Datetime in target timezone
        
    Examples:
        >>> dt = datetime(2023, 12, 25, 10, 30)
        >>> convert_timezone(dt, "UTC", "America/New_York")
        datetime(2023, 12, 25, 5, 30, tzinfo=...)
    """
    from_timezone = pytz.timezone(from_tz)
    to_timezone = pytz.timezone(to_tz)
    
    # Localize if naive
    if dt.tzinfo is None:
        dt = from_timezone.localize(dt)
    
    return dt.astimezone(to_timezone)


def get_market_hours(market: str = "NYSE") -> Dict[str, time]:
    """
    Get market hours for specified market.
    
    Args:
        market: Market name (NYSE, NASDAQ, LSE, TSE, etc.)
        
    Returns:
        Dictionary with market hours
        
    Examples:
        >>> hours = get_market_hours("NYSE")
        >>> hours["regular_open"]
        time(9, 30)
    """
    market_hours_map = {
        "NYSE": {
            "pre_market_open": time(4, 0),
            "pre_market_close": time(9, 30),
            "regular_open": time(9, 30),
            "regular_close": time(16, 0),
            "after_hours_open": time(16, 0),
            "after_hours_close": time(20, 0),
            "timezone": "America/New_York"
        },
        "NASDAQ": {
            "pre_market_open": time(4, 0),
            "pre_market_close": time(9, 30),
            "regular_open": time(9, 30),
            "regular_close": time(16, 0),
            "after_hours_open": time(16, 0),
            "after_hours_close": time(20, 0),
            "timezone": "America/New_York"
        },
        "LSE": {
            "regular_open": time(8, 0),
            "regular_close": time(16, 30),
            "timezone": "Europe/London"
        },
        "TSE": {
            "regular_open": time(9, 0),
            "regular_close": time(15, 0),
            "timezone": "Asia/Tokyo"
        },
        "ASX": {
            "regular_open": time(10, 0),
            "regular_close": time(16, 0),
            "timezone": "Australia/Sydney"
        },
        "FOREX": {
            "regular_open": time(0, 0),  # 24/5 market
            "regular_close": time(23, 59),
            "timezone": "UTC"
        }
    }
    
    return market_hours_map.get(market.upper(), market_hours_map["NYSE"])


def is_market_open(
    market: str = "NYSE", 
    current_time: Optional[datetime] = None
) -> bool:
    """
    Check if market is currently open.
    
    Args:
        market: Market name
        current_time: Time to check (defaults to now)
        
    Returns:
        True if market is open, False otherwise
        
    Examples:
        >>> is_market_open("NYSE")  # depends on current time
        True
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    hours = get_market_hours(market)
    market_tz = pytz.timezone(hours["timezone"])
    
    # Convert to market timezone
    market_time = current_time.astimezone(market_tz)
    current_time_only = market_time.time()
    current_weekday = market_time.weekday()
    
    # Check if it's a weekday (Monday = 0, Sunday = 6)
    if market == "FOREX":
        # Forex is open 24/5 (Sunday 5 PM EST to Friday 5 PM EST)
        if current_weekday == 6:  # Sunday
            return current_time_only >= time(17, 0)  # 5 PM EST
        elif current_weekday == 5:  # Saturday
            return current_time_only < time(17, 0)  # Before 5 PM EST
        else:
            return True  # Monday-Friday
    else:
        # Stock markets are typically closed on weekends
        if current_weekday >= 5:  # Saturday or Sunday
            return False
    
    # Check regular market hours
    regular_open = hours.get("regular_open")
    regular_close = hours.get("regular_close")
    
    if regular_open and regular_close:
        return regular_open <= current_time_only <= regular_close
    
    return False


def get_market_session(
    market: str = "NYSE", 
    current_time: Optional[datetime] = None
) -> MarketSession:
    """
    Determine current market session.
    
    Args:
        market: Market name
        current_time: Time to check (defaults to now)
        
    Returns:
        Current market session
        
    Examples:
        >>> get_market_session("NYSE")
        MarketSession.REGULAR
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    hours = get_market_hours(market)
    market_tz = pytz.timezone(hours["timezone"])
    
    # Convert to market timezone
    market_time = current_time.astimezone(market_tz)
    current_time_only = market_time.time()
    current_weekday = market_time.weekday()
    
    # Check if it's a weekday
    if current_weekday >= 5:  # Weekend
        return MarketSession.CLOSED
    
    # Check pre-market
    pre_open = hours.get("pre_market_open")
    pre_close = hours.get("pre_market_close")
    if pre_open and pre_close and pre_open <= current_time_only < pre_close:
        return MarketSession.PRE_MARKET
    
    # Check regular hours
    regular_open = hours.get("regular_open")
    regular_close = hours.get("regular_close")
    if regular_open and regular_close and regular_open <= current_time_only <= regular_close:
        return MarketSession.REGULAR
    
    # Check after hours
    after_open = hours.get("after_hours_open")
    after_close = hours.get("after_hours_close")
    if after_open and after_close and after_open < current_time_only <= after_close:
        return MarketSession.AFTER_HOURS
    
    return MarketSession.CLOSED


def get_next_market_open(
    market: str = "NYSE", 
    current_time: Optional[datetime] = None
) -> datetime:
    """
    Get the next market open time.
    
    Args:
        market: Market name
        current_time: Reference time (defaults to now)
        
    Returns:
        Next market open datetime
        
    Examples:
        >>> next_open = get_next_market_open("NYSE")
        >>> isinstance(next_open, datetime)
        True
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    hours = get_market_hours(market)
    market_tz = pytz.timezone(hours["timezone"])
    regular_open = hours.get("regular_open")
    
    if not regular_open:
        raise ValueError(f"No regular hours defined for market: {market}")
    
    # Convert to market timezone
    market_time = current_time.astimezone(market_tz)
    
    # Try today first
    today_open = market_time.replace(
        hour=regular_open.hour,
        minute=regular_open.minute,
        second=0,
        microsecond=0
    )
    
    # If market already opened today or it's weekend, find next business day
    if (market_time.time() > regular_open or 
        market_time.weekday() >= 5):  # Weekend
        
        # Move to next business day
        days_ahead = 1
        if market_time.weekday() == 5:  # Saturday
            days_ahead = 2
        elif market_time.weekday() == 6:  # Sunday
            days_ahead = 1
        
        next_open = today_open + timedelta(days=days_ahead)
        
        # Skip weekends
        while next_open.weekday() >= 5:
            next_open += timedelta(days=1)
    else:
        next_open = today_open
    
    return next_open.astimezone(timezone.utc)


def calculate_trading_days(
    start_date: datetime, 
    end_date: datetime, 
    market: str = "NYSE"
) -> int:
    """
    Calculate number of trading days between two dates.
    
    Args:
        start_date: Start date
        end_date: End date
        market: Market to check holidays for
        
    Returns:
        Number of trading days
        
    Examples:
        >>> start = datetime(2023, 12, 1)
        >>> end = datetime(2023, 12, 8)
        >>> calculate_trading_days(start, end)
        5
    """
    if start_date > end_date:
        return 0
    
    trading_days = 0
    current_date = start_date.date()
    end_date = end_date.date()
    
    while current_date <= end_date:
        # Skip weekends
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            # TODO: Add holiday checking for specific markets
            trading_days += 1
        current_date += timedelta(days=1)
    
    return trading_days


def round_to_nearest_minute(dt: datetime, minutes: int = 1) -> datetime:
    """
    Round datetime to nearest specified minutes.
    
    Args:
        dt: Datetime to round
        minutes: Minutes to round to
        
    Returns:
        Rounded datetime
        
    Examples:
        >>> dt = datetime(2023, 12, 25, 10, 32, 45)
        >>> round_to_nearest_minute(dt, 5)
        datetime(2023, 12, 25, 10, 30)
    """
    # Calculate seconds to round to
    seconds = minutes * 60
    
    # Round to nearest interval
    rounded_timestamp = round(dt.timestamp() / seconds) * seconds
    
    return datetime.fromtimestamp(rounded_timestamp, tz=dt.tzinfo)


def get_trading_calendar(
    year: int, 
    market: str = "NYSE"
) -> Dict[str, Any]:
    """
    Get trading calendar for specified year and market.
    
    Args:
        year: Year to get calendar for
        market: Market name
        
    Returns:
        Trading calendar information
        
    Examples:
        >>> calendar = get_trading_calendar(2023)
        >>> "holidays" in calendar
        True
    """
    # Common US market holidays (simplified)
    holidays = [
        f"{year}-01-01",  # New Year's Day
        f"{year}-07-04",  # Independence Day
        f"{year}-12-25",  # Christmas Day
        # TODO: Add more holidays and market-specific holidays
    ]
    
    # Calculate total trading days
    start_of_year = datetime(year, 1, 1)
    end_of_year = datetime(year, 12, 31)
    total_trading_days = calculate_trading_days(start_of_year, end_of_year, market)
    
    return {
        "year": year,
        "market": market,
        "holidays": holidays,
        "total_trading_days": total_trading_days,
        "market_hours": get_market_hours(market)
    }