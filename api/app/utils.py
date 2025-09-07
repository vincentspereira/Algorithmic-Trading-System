
import json
from typing import Optional, Any

import redis
import structlog

from api.app.core.config import api_settings

logger = structlog.get_logger()

def get_cache_key(prefix: str, **kwargs) -> str:
    """Generate cache key from parameters"""
    key_parts = [prefix]
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}:{v}")
    return ":".join(key_parts)

async def get_cached_data(key: str) -> Optional[Any]:
    """Get data from cache"""
    if not api_settings.REDIS_HOST:
        return None

    try:
        redis_client = redis.Redis(host=api_settings.REDIS_HOST, port=api_settings.REDIS_PORT, decode_responses=True)
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.error("Cache read error", key=key, error=str(e))
        return None

async def set_cached_data(key: str, data: Any, ttl: int = 300):
    """Set data in cache with TTL"""
    if not api_settings.REDIS_HOST:
        return

    try:
        redis_client = redis.Redis(host=api_settings.REDIS_HOST, port=api_settings.REDIS_PORT, decode_responses=True)
        redis_client.setex(key, ttl, json.dumps(data, default=str))
    except Exception as e:
        logger.error("Cache write error", key=key, error=str(e))
