
from typing import Dict, Any
from datetime import datetime

class ServiceStatus:
    """Service status tracking with better organization"""

    def __init__(self):
        self.kafka_connected = False
        self.kafka_streaming = False
        self.postgres_connected = False
        self.clickhouse_connected = False
        self.duckdb_connected = False
        self.ib_connected = False
        self.redis_connected = False
        self.last_health_check = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "kafka_connected": self.kafka_connected,
            "kafka_streaming": self.kafka_streaming,
            "postgres_connected": self.postgres_connected,
            "clickhouse_connected": self.clickhouse_connected,
            "duckdb_connected": self.duckdb_connected,
            "ib_connected": self.ib_connected,
            "redis_connected": self.redis_connected,
            "last_health_check": self.last_health_check
        }

    def is_healthy(self) -> bool:
        """Check if all critical services are connected"""
        return all([
            self.kafka_connected,
            self.postgres_connected,
            self.clickhouse_connected,
            self.duckdb_connected,
            self.ib_connected
        ])
