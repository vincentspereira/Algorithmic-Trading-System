"""Core module for the algorithmic trading system.

This module provides fundamental data types, events, and utilities
used throughout the trading system.
"""

__version__ = "1.0.0"

# Import core components for easy access
from .events import Event, EventType
from .data_types import MarketData, Trade, Position, Order
from .risk_management import RiskManager
from .portfolio import Portfolio

__all__ = [
    "Event",
    "EventType", 
    "MarketData",
    "Trade",
    "Position",
    "Order",
    "RiskManager",
    "Portfolio"
]