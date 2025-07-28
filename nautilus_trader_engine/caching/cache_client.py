"""
Cache Client for Redis Integration

This module provides a client for interacting with a Redis server,
including connection management and caching operations.

Author: Vincent Pereira
Version: 1.0.0
"""

import redis.asyncio as redis
from fastapi import Request
from nautilus_trader_engine.config.cache_config import get_redis_config, get_cache_profiles

async def get_cache_client(request: Request) -> redis.Redis:
    """
    Dependency injection function to get a Redis client.
    This manages the connection pool and ensures a single client
    instance per application lifecycle.
    """
    if not hasattr(request.app.state, "redis_client"):
        redis_config = get_redis_config()
        request.app.state.redis_client = redis.from_url(
            redis_config["url"],
            encoding=redis_config["encoding"],
            decode_responses=redis_config["decode_responses"]
        )
    return request.app.state.redis_client

class CacheClient:
    """
    A wrapper for the Redis client to provide a clean interface for caching.
    """
    def __init__(self, client: redis.Redis):
        self._client = client
        self._cache_profiles = get_cache_profiles()

    async def get(self, key: str):
        return await self._client.get(key)

    async def set(self, key: str, value: str, profile: str = None):
        """Set a key with an optional expiration profile."""
        if profile and profile in self._cache_profiles:
            await self.setex(key, self._cache_profiles[profile], value)
        else:
            await self._client.set(key, value)
        
    async def setex(self, key: str, seconds: int, value: str):
        await self._client.setex(key, seconds, value)