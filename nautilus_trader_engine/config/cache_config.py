
from typing import Dict, Any

from shared.config import settings

# This file centralizes all caching configurations for the trading system,
# including Redis connection settings and cache expiration times for
# different types of data.

def get_redis_config() -> Dict[str, Any]:
    """Get Redis connection configuration."""
    return {
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
        "password": settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
        "db": settings.REDIS_DB,
        "encoding": "utf-8",
        "decode_responses": True,
    }

def get_cache_profiles() -> Dict[str, int]:
    """Get cache expiration profiles for different data types."""
    return {
        "predictions": settings.CACHE_EXP_PREDICTIONS, # 1 minute
        "risk_calculations": settings.CACHE_EXP_RISK, # 5 minutes
        "market_data": settings.CACHE_EXP_MARKET_DATA, # 10 seconds
    }
