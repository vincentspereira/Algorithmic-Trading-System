
from typing import Dict

class ServiceConfiguration:
    """Service configuration management"""

    def __init__(self):
        self.title = "Nautilus Trader Engine"
        self.description = "High-performance algorithmic trading engine for Phase 1 infrastructure"
        self.version = "1.0.0"
        self.docs_url = "/docs"
        self.redoc_url = "/redoc"

    def get_cors_config(self) -> dict:
        """Get CORS configuration"""
        return {
            "allow_origins": ["*"],  # Configure appropriately for production
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }
