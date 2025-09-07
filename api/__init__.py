"""API module - Root level API access

This module provides access to the nautilus_trader_engine API components
for testing and external integration purposes.
"""

# Simple mock implementation for testing environments
class MockAuth:
    @staticmethod
    def verify_session(session_token: str) -> dict:
        """Mock verify_session for testing."""
        return {
            'user_id': 'test_user',
            'username': 'test_trader',
            'role': 'trader',
            'permissions': ['view_portfolio', 'place_orders', 'view_reports'],
            'session_token': session_token
        }

# Create auth instance
auth = MockAuth()

# Expose the verify_session function at module level for easier patching
verify_session = auth.verify_session

__all__ = [
    "auth",
    "verify_session",
]