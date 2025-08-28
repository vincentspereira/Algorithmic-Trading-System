"""
Shared components package for the Algorithmic Trading System.

This package contains shared components, utilities, models, and configurations
that are used across multiple services in the trading system. It promotes
code reuse and maintains consistency across the entire platform.

Subpackages:
    utils: Common utility functions for formatting, validation, etc.
    models: Shared data models and schemas
    config: Centralized configuration management

Usage:
    from shared.utils import format_currency, validate_symbol
    from shared.models import BaseModel, TradingModel
    from shared.config import get_settings
"""

__version__ = "1.0.0"
__author__ = "Algorithmic Trading System Team"

# Import key utilities for easy access
from .utils import (
    format_currency,
    format_percentage,
    validate_symbol,
    validate_price,
    parse_timestamp,
    is_market_open,
    TradingSystemError,
    retry
)

__all__ = [
    'format_currency',
    'format_percentage',
    'validate_symbol', 
    'validate_price',
    'parse_timestamp',
    'is_market_open',
    'TradingSystemError',
    'retry'
]