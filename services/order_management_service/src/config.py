"""Order Service Configuration

Configuration management for the order management service.
"""

import os
from typing import Optional
from pydantic import BaseModel


class KafkaConfig(BaseModel):
    """Kafka configuration"""
    bootstrap_servers: str = "localhost:9092"
    topic_prefix: str = "trading"
    consumer_group: str = "order_service"
    auto_offset_reset: str = "latest"


class DatabaseConfig(BaseModel):
    """Database configuration"""
    url: str = "sqlite:///orders.db"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20


class OrderServiceConfig(BaseModel):
    """Order service configuration"""
    service_name: str = "order_management_service"
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False
    
    # Sub-configurations
    kafka_config: KafkaConfig = KafkaConfig()
    database_config: DatabaseConfig = DatabaseConfig()
    
    # JWT Configuration
    jwt_secret_key: str = "your-secret-key-here"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    
    @classmethod
    def from_env(cls) -> "OrderServiceConfig":
        """Create configuration from environment variables"""
        return cls(
            service_name=os.getenv("SERVICE_NAME", "order_management_service"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8001")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            kafka_config=KafkaConfig(
                bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
                topic_prefix=os.getenv("KAFKA_TOPIC_PREFIX", "trading"),
                consumer_group=os.getenv("KAFKA_CONSUMER_GROUP", "order_service"),
                auto_offset_reset=os.getenv("KAFKA_AUTO_OFFSET_RESET", "latest")
            ),
            database_config=DatabaseConfig(
                url=os.getenv("DATABASE_URL", "sqlite:///orders.db"),
                echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
                pool_size=int(os.getenv("DATABASE_POOL_SIZE", "10")),
                max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
            ),
            jwt_secret_key=os.getenv("JWT_SECRET_KEY", "your-secret-key-here"),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            jwt_access_token_expire_minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        )