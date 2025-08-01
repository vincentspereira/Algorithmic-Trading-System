"""
Nautilus Trader Python SDK

A comprehensive Python SDK for interacting with the Nautilus Trader Engine.
Provides easy access to REST APIs, GraphQL, WebSocket connections, and webhook management.
"""

__version__ = "1.0.0"
__author__ = "Nautilus Trader Team"
__email__ = "support@nautilus-trader.com"

from .client import NautilusTraderClient
from .models import *
from .exceptions import *
from .utils import *

__all__ = [
    'NautilusTraderClient',
    # Models
    'Order', 'Position', 'Trade', 'Portfolio', 'MarketData',
    'Strategy', 'Backtest', 'RiskMetrics', 'Analytics',
    # Exceptions
    'NautilusTraderError', 'APIError', 'AuthenticationError',
    'ValidationError', 'NetworkError', 'RateLimitError',
    # Utils
    'format_currency', 'parse_timestamp', 'validate_symbol'
]