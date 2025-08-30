"""
Simple Configuration Module for Phase 1 API Testing
Provides default settings without complex validation
"""

import os
from typing import List, Optional

class SimpleSettings:
    """Simplified settings for Phase 1 API testing"""
    
    def __init__(self):
        # Core settings with defaults
        self.SECRET_KEY = os.getenv("SECRET_KEY", "phase1-test-secret-key-for-development")
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "phase1-jwt-secret-key")
        self.ALGORITHM = os.getenv("ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        
        # Database settings
        self.POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
        self.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
        self.POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
        self.POSTGRES_DB = os.getenv("POSTGRES_DB", "trading_system")
        self.DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}")
        
        # API settings
        self.API_V1_STR = os.getenv("API_V1_STR", "/api/v1")
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.DEBUG = os.getenv("DEBUG", "true").lower() == "true"
        
        # CORS settings
        cors_origins = os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")
        self.BACKEND_CORS_ORIGINS = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
        
        # Feature flags
        self.FEATURE_REAL_TIME_TRADING = os.getenv("FEATURE_REAL_TIME_TRADING", "false").lower() == "true"
        self.FEATURE_BACKTESTING = os.getenv("FEATURE_BACKTESTING", "true").lower() == "true"
        self.FEATURE_OPTIMIZATION = os.getenv("FEATURE_OPTIMIZATION", "true").lower() == "true"
        self.FEATURE_PAPER_TRADING = os.getenv("FEATURE_PAPER_TRADING", "true").lower() == "true"

# Global settings instance
settings = SimpleSettings()