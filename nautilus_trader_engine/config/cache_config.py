import os
from typing import Dict, Any

# This file centralizes all caching configurations for the trading system,
# including Redis connection settings and cache expiration times for
# different types of data.

def get_redis_config() -> Dict[str, Any]:
    """Get Redis connection configuration."""
    return {
        "url": os.getenv("REDIS_URL", "redis://localhost:6379"),
        "encoding": "utf-8",
        "decode_responses": True,
    }

def get_cache_profiles() -> Dict[str, int]:
    """Get cache expiration profiles for different data types."""
    return {
        "predictions": int(os.getenv("CACHE_EXP_PREDICTIONS", 60)), # 1 minute
        "risk_calculations": int(os.getenv("CACHE_EXP_RISK", 300)), # 5 minutes
        "market_data": int(os.getenv("CACHE_EXP_MARKET_DATA", 10)), # 10 seconds
    }