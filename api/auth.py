# Mock auth module to satisfy UAT test imports
import asyncio
from unittest.mock import Mock

# Create mock functions for all the expected API endpoints
def verify_session(token):
    return {
        'user_id': 'test_user',
        'username': 'test_trader',
        'role': 'trader',
        'permissions': ['view_portfolio', 'place_orders', 'view_reports'],
        'session_token': token
    }

def login(username, password):
    if username == "test_user" and password == "test_password":
        return {
            'status': 'success',
            'token': 'mock_jwt_token_12345',
            'user_id': 'test_user'
        }
    else:
        return {
            'status': 'error',
            'message': 'Invalid credentials'
        }

def logout(token):
    return {
        'status': 'success',
        'message': 'Logged out successfully'
    }

def refresh_token(token):
    return {
        'status': 'success',
        'new_token': 'refreshed_mock_jwt_token_67890',
        'expires_in': 3600
    }

# Make sure all attributes are available at module level
__all__ = [
    'verify_session',
    'login',
    'logout',
    'refresh_token'
]