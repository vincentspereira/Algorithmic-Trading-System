"""
Data Feeds Module - Re-export for compatibility
"""

from nautilus_trader_engine.core.data_feeds import (
    DataFeedManager,
    AssetClass,
    DataSource,
    DataRequest,
    DataResponse,
    get_data,
    RateLimitManager,
)

__all__ = [
    "DataFeedManager",
    "AssetClass",
    "DataSource",
    "DataRequest",
    "DataResponse",
    "get_data",
    "RateLimitManager",
]