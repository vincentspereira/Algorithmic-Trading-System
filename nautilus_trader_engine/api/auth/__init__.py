"""Authentication modules
"""

from .dependencies import get_current_user

def verify_session(session_token: str) -> bool:
    """Verify if a session token is valid.
    
    Args:
        session_token: The session token to verify
        
    Returns:
        bool: True if session is valid, False otherwise
    """
    # Mock implementation for testing
    return session_token is not None and len(session_token) > 0

__all__ = [
    "dependencies",
    "jwt",
    "middleware",
    "utils",
    "verify_session",
    "get_current_user",
]