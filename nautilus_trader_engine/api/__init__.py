"""Nautilus Trader Engine API - Phase 2
Enhanced FastAPI application with OAuth2/JWT authentication and backtesting capabilities
"""

from . import auth
from .session_manager import RealtimeSessionManager

# Create a mock router for testing purposes
class MockRouter:
    def get_all_routes(self):
        return []

router = MockRouter()

# Create a mock validation module for testing purposes
class MockValidation:
    def validate_parameters(self, path, method):
        return []

validation = MockValidation()

__version__ = "2.0.0"
__author__ = "Vincent S. Pereira"
__description__ = "Enhanced API with OAuth2/JWT authentication and backtesting capabilities"

__all__ = [
    "auth",
    "router",
    "validation",
    "RealtimeSessionManager"
]