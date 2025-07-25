"""
Core configuration settings for the API
"""

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Nautilus Trader Engine API"
    VERSION: str = "2.0.0"
    DESCRIPTION: str = "Enhanced API with OAuth2/JWT authentication and backtesting capabilities"
    
    # Security Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = ["*"]  # Configure appropriately for production
    
    # Database Configuration (inherited from Phase 1)
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "trading_system")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
    
    # Kafka Configuration (inherited from Phase 1)
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    class Config:
        case_sensitive = True


# Global settings instance
settings = Settings()