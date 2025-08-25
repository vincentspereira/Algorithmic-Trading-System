"""
Cache implementation for dependency monitoring data.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import json
import redis

class DependencyCache:
    """TTL-based cache for dependency monitoring data"""
    
    def __init__(
        self,
        host: str = "redis",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None
    ):
        self.redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )
        
        # Default TTLs
        self.ttls = {
            "dependency_status": 300,  # 5 minutes
            "vulnerability_data": 3600,  # 1 hour
            "github_data": 1800,  # 30 minutes
            "historical_data": 86400 * 30,  # 30 days
        }
        
    def _make_key(self, category: str, identifier: str) -> str:
        """Create a cache key"""
        return f"dep:{category}:{identifier}"
        
    def get(
        self,
        category: str,
        identifier: str,
        default: Any = None
    ) -> Any:
        """Get value from cache"""
        key = self._make_key(category, identifier)
        value = self.redis.get(key)
        
        if value is None:
            return default
            
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
            
    def set(
        self,
        category: str,
        identifier: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Set value in cache"""
        key = self._make_key(category, identifier)
        
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
            
        self.redis.set(
            key,
            value,
            ex=ttl or self.ttls.get(category, 300)
        )
        
    def store_historical_data(
        self,
        tier: str,
        dependency: str,
        data: Dict
    ) -> None:
        """Store historical data point"""
        key = self._make_key("historical", f"{tier}:{dependency}")
        timestamp = datetime.utcnow().isoformat()
        
        # Store as a sorted set with timestamp score
        self.redis.zadd(
            key,
            {json.dumps(data): timestamp}
        )
        
        # Keep only last 30 days of data
        threshold = (
            datetime.utcnow() - timedelta(days=30)
        ).isoformat()
        self.redis.zremrangebyscore(key, "-inf", threshold)
        
    def get_historical_data(
        self,
        tier: str,
        dependency: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> list:
        """Get historical data points"""
        key = self._make_key("historical", f"{tier}:{dependency}")
        
        # Convert times to ISO format strings
        start = start_time.isoformat() if start_time else "-inf"
        end = end_time.isoformat() if end_time else "+inf"
        
        # Get data points in time range
        data_points = self.redis.zrangebyscore(
            key,
            start,
            end,
            withscores=True
        )
        
        return [
            {
                "data": json.loads(point),
                "timestamp": score
            }
            for point, score in data_points
        ]
