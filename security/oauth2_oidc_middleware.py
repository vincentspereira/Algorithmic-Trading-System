#!/usr/bin/env python3
"""
OAuth2/OpenID Connect Middleware
Integrates OAuth2/OIDC provider with existing authentication framework
"""

import asyncio
import logging
import sys
import os
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime

# Add the security directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from authentication_framework import AuthenticationManager, Session, User, UserRole
from oauth2_oidc_provider import OAuth2OIDCProvider, OAuth2Token

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class OAuth2Session:
    """OAuth2 session information"""
    session_id: str
    access_token: str
    refresh_token: Optional[str]
    user_id: str
    client_id: str
    scopes: list
    expires_at: datetime
    refresh_expires_at: Optional[datetime] = None

class OAuth2Middleware:
    """OAuth2/OpenID Connect Middleware for Authentication Framework"""
    
    def __init__(self, auth_manager: AuthenticationManager, 
                 oauth2_provider: OAuth2OIDCProvider):
        self.auth_manager = auth_manager
        self.oauth2_provider = oauth2_provider
        self.oauth2_sessions: Dict[str, OAuth2Session] = {}
    
    def create_oauth2_session(self, access_token: str, user_id: str, 
                            client_id: str, scopes: list) -> Optional[str]:
        """Create OAuth2 session from access token"""
        # Validate access token
        token = self.oauth2_provider.validate_access_token(access_token)
        if not token:
            logger.warning("Invalid access token provided for OAuth2 session creation")
            return None
        
        # Create session ID
        session_id = f"oauth2_{access_token[:16]}"
        
        # Create OAuth2 session
        oauth2_session = OAuth2Session(
            session_id=session_id,
            access_token=access_token,
            refresh_token=token.refresh_token,
            user_id=user_id,
            client_id=client_id,
            scopes=scopes,
            expires_at=token.expires_at,
            refresh_expires_at=token.refresh_expires_at
        )
        
        self.oauth2_sessions[session_id] = oauth2_session
        logger.info(f"Created OAuth2 session for user {user_id} with client {client_id}")
        return session_id
    
    def validate_oauth2_session(self, session_id: str) -> Optional[OAuth2Session]:
        """Validate OAuth2 session"""
        oauth2_session = self.oauth2_sessions.get(session_id)
        if not oauth2_session:
            return None
        
        # Check if session is expired
        if datetime.now() > oauth2_session.expires_at:
            del self.oauth2_sessions[session_id]
            logger.warning(f"OAuth2 session expired: {session_id}")
            return None
        
        return oauth2_session
    
    def refresh_oauth2_session(self, session_id: str) -> bool:
        """Refresh OAuth2 session using refresh token"""
        oauth2_session = self.oauth2_sessions.get(session_id)
        if not oauth2_session or not oauth2_session.refresh_token:
            return False
        
        try:
            # Refresh token
            new_token = self.oauth2_provider.refresh_access_token(
                refresh_token=oauth2_session.refresh_token,
                client_id=oauth2_session.client_id,
                client_secret="client_secret_placeholder"  # In practice, this would be retrieved securely
            )
            
            # Update session
            oauth2_session.access_token = new_token.access_token
            oauth2_session.refresh_token = new_token.refresh_token
            oauth2_session.expires_at = new_token.expires_at
            oauth2_session.refresh_expires_at = new_token.refresh_expires_at
            
            logger.info(f"Refreshed OAuth2 session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh OAuth2 session {session_id}: {e}")
            return False
    
    def get_user_from_oauth2_session(self, session_id: str) -> Optional[User]:
        """Get user from OAuth2 session"""
        oauth2_session = self.validate_oauth2_session(session_id)
        if not oauth2_session:
            return None
        
        # Get user from auth manager
        return self.auth_manager.users.get(oauth2_session.user_id)
    
    def check_oauth2_permission(self, session_id: str, permission: str) -> bool:
        """Check permission for OAuth2 session"""
        user = self.get_user_from_oauth2_session(session_id)
        if not user:
            return False
        
        # Check if permission is in user's permissions
        return permission in [p.value for p in user.permissions]
    
    def revoke_oauth2_session(self, session_id: str):
        """Revoke OAuth2 session"""
        oauth2_session = self.oauth2_sessions.get(session_id)
        if not oauth2_session:
            return
        
        # Revoke tokens at provider
        if oauth2_session.access_token:
            try:
                self.oauth2_provider.revoke_token(
                    token_value=oauth2_session.access_token,
                    client_id=oauth2_session.client_id,
                    client_secret="client_secret_placeholder"  # In practice, this would be retrieved securely
                )
            except Exception as e:
                logger.error(f"Failed to revoke access token: {e}")
        
        # Remove session
        del self.oauth2_sessions[session_id]
        logger.info(f"Revoked OAuth2 session: {session_id}")
    
    def integrate_with_auth_manager(self):
        """Integrate OAuth2 middleware with authentication manager"""
        # Add OAuth2 session validation to auth manager
        original_validate_session = self.auth_manager.validate_session
        
        def validate_session_with_oauth2(session_id: str, ip_address: str = "unknown") -> Optional[Session]:
            # First try regular session validation
            session = original_validate_session(session_id, ip_address)
            if session:
                return session
            
            # If not found, try OAuth2 session
            oauth2_session = self.validate_oauth2_session(session_id)
            if oauth2_session:
                # Create a compatible Session object
                user = self.get_user_from_oauth2_session(session_id)
                if user:
                    # Create session object compatible with existing framework
                    return Session(
                        session_id=session_id,
                        user_id=user.user_id,
                        username=user.username,
                        roles=user.roles,
                        permissions=user.permissions,
                        created_at=datetime.now(),
                        last_activity=datetime.now(),
                        expires_at=oauth2_session.expires_at,
                        ip_address=ip_address,
                        user_agent="OAuth2 Client",
                        mfa_verified=True  # OAuth2 is considered verified
                    )
            
            return None
        
        # Replace the validate_session method
        self.auth_manager.validate_session = validate_session_with_oauth2
        
        logger.info("Integrated OAuth2 middleware with authentication manager")

# OIDC Integration
class OIDCMiddleware:
    """OpenID Connect Middleware for User Information"""
    
    def __init__(self, oauth2_provider: OAuth2OIDCProvider):
        self.oauth2_provider = oauth2_provider
    
    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from OIDC provider"""
        try:
            user_info = self.oauth2_provider.get_user_info(access_token)
            if user_info:
                # Convert to dictionary
                return {
                    "sub": user_info.sub,
                    "name": user_info.name,
                    "given_name": user_info.given_name,
                    "family_name": user_info.family_name,
                    "email": user_info.email,
                    "email_verified": user_info.email_verified
                    # Add other fields as needed
                }
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
        
        return None
    
    def create_user_from_oidc(self, access_token: str, 
                            auth_manager: AuthenticationManager) -> Optional[User]:
        """Create user in auth manager from OIDC user info"""
        user_info = self.get_user_info(access_token)
        if not user_info:
            return None
        
        # Check if user already exists
        existing_user = None
        for user in auth_manager.users.values():
            if user.metadata.get("oidc_sub") == user_info['sub']:
                existing_user = user
                break
        
        if existing_user:
            return existing_user
        
        # Create new user
        try:
            # Generate a secure password for OIDC users (they won't use it)
            import secrets
            import string
            # Ensure password meets all requirements: uppercase, lowercase, digit, symbol
            uppercase = secrets.choice(string.ascii_uppercase)
            lowercase = secrets.choice(string.ascii_lowercase)
            digit = secrets.choice(string.digits)
            symbol = secrets.choice("!@#$%^&*")
            
            # Fill the rest with random characters
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            remaining_chars = ''.join(secrets.choice(alphabet) for _ in range(16))
            
            # Combine and shuffle
            secure_password = uppercase + lowercase + digit + symbol + remaining_chars
            
            # In a real implementation, you would map OIDC roles to system roles
            # For now, we'll create a basic user
            user = auth_manager.create_user(
                username=user_info.get('preferred_username') or user_info['sub'],
                email=user_info.get('email', ''),
                password=secure_password,  # OIDC users don't have passwords in our system
                roles={UserRole.VIEWER},  # Default role for OIDC users
                metadata={"oidc_sub": user_info['sub']}
            )
            
            logger.info(f"Created user from OIDC: {user.username}")
            return user
            
        except Exception as e:
            logger.error(f"Failed to create user from OIDC: {e}")
            return None

# Integration example
def integrate_oauth2_oidc_with_security_framework():
    """Example of how to integrate OAuth2/OIDC with the existing security framework"""
    
    # This would typically be done in the application initialization
    # For demonstration, we'll show how the integration would work
    
    print("OAuth2/OIDC integration example:")
    print("1. Initialize OAuth2/OIDC provider")
    print("2. Initialize authentication manager")
    print("3. Create OAuth2 middleware")
    print("4. Integrate middleware with authentication manager")
    print("5. Use integrated system for authentication and authorization")

if __name__ == "__main__":
    integrate_oauth2_oidc_with_security_framework()