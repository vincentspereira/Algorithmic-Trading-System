#!/usr/bin/env python3
"""
API Security Middleware
Provides comprehensive authentication and authorization for API endpoints
"""

import logging
import json
import secrets
from typing import Dict, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from authentication_framework import (
    AuthenticationManager, Session, User, UserRole, Permission, 
    GranularPermission, AuthenticationMethod
)
from oauth2_oidc_provider import OAuth2OIDCProvider
from oauth2_oidc_middleware import OAuth2Middleware

logger = logging.getLogger(__name__)

class AuthTokenType(Enum):
    """Authentication token types"""
    JWT = "jwt"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    SESSION = "session"

@dataclass
class AuthContext:
    """Authentication context for request"""
    user_id: str
    username: str
    roles: set
    permissions: set
    granular_permissions: set
    auth_method: AuthenticationMethod
    token_type: AuthTokenType
    session_id: Optional[str] = None
    client_id: Optional[str] = None
    scopes: list = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class SecurityMiddleware:
    """Comprehensive API Security Middleware"""
    
    def __init__(self, auth_manager: AuthenticationManager, 
                 oauth2_provider: Optional[OAuth2OIDCProvider] = None):
        self.auth_manager = auth_manager
        self.oauth2_provider = oauth2_provider
        self.oauth2_middleware = OAuth2Middleware(auth_manager, oauth2_provider) if oauth2_provider else None
        
        # Rate limiting
        self.rate_limits = {}  # user_id -> {endpoint: [timestamps]}
        self.rate_limit_window = timedelta(minutes=1)
        self.rate_limit_max_requests = 1000
        
        # IP tracking
        self.ip_tracking = {}  # ip -> [timestamps]
        
        logger.info("Security Middleware initialized")
    
    def authenticate_request(self, headers: Dict[str, str], 
                           ip_address: str = "unknown") -> Optional[AuthContext]:
        """
        Authenticate request based on headers
        Supports JWT, API Key, OAuth2 Bearer tokens, and session cookies
        """
        # Check rate limiting
        if not self._check_rate_limit(ip_address):
            logger.warning(f"Rate limit exceeded for IP: {ip_address}")
            return None
        
        # Track IP
        self._track_ip(ip_address)
        
        # Try different authentication methods
        auth_header = headers.get("Authorization", "")
        
        # Try JWT first for Bearer tokens
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            # Try JWT first
            jwt_payload = self.auth_manager.verify_jwt_token(token)
            if jwt_payload:
                return self._create_auth_context_from_jwt(jwt_payload, token)
            
            # Try OAuth2 access token
            if self.oauth2_provider:
                user_info = self.oauth2_provider.get_user_info(token)
                if user_info:
                    return self._create_auth_context_from_oauth2(user_info, token)
        
        # API Key authentication
        api_key = headers.get("X-API-Key") or headers.get("Authorization", "").replace("ApiKey ", "")
        if api_key:
            user = self.auth_manager.authenticate_api_key(api_key)
            if user:
                return self._create_auth_context_from_api_key(user, api_key)
        
        # Session cookie authentication
        session_id = headers.get("X-Session-ID") or self._extract_session_from_cookie(headers)
        if session_id:
            session = self.auth_manager.validate_session(session_id, ip_address)
            if session:
                return self._create_auth_context_from_session(session)
        
        logger.warning("Authentication failed for request")
        return None
    
    def _extract_session_from_cookie(self, headers: Dict[str, str]) -> Optional[str]:
        """Extract session ID from cookie header"""
        cookie_header = headers.get("Cookie", "")
        if "session_id=" in cookie_header:
            # Simple cookie parsing (in production, use a proper cookie parser)
            cookies = cookie_header.split(";")
            for cookie in cookies:
                if "session_id=" in cookie:
                    return cookie.split("=")[1].strip()
        return None
    
    def _create_auth_context_from_jwt(self, payload: Dict[str, Any], token: str) -> AuthContext:
        """Create auth context from JWT payload"""
        return AuthContext(
            user_id=payload.get("user_id"),
            username=payload.get("username"),
            roles=set(UserRole(role) for role in payload.get("roles", [])),
            permissions=set(Permission(perm) for perm in payload.get("permissions", [])),
            granular_permissions=set(),  # JWT doesn't contain granular permissions
            auth_method=AuthenticationMethod.JWT_TOKEN,
            token_type=AuthTokenType.JWT,
            metadata={"token": token, "payload": payload}
        )
    
    def _create_auth_context_from_oauth2(self, user_info: Any, token: str) -> AuthContext:
        """Create auth context from OAuth2 user info"""
        user = self.auth_manager.users.get(user_info.sub)
        if not user:
            return None
            
        return AuthContext(
            user_id=user_info.sub,
            username=getattr(user_info, "name", "") or "",
            roles=user.roles,
            permissions=user.permissions,
            granular_permissions=user.granular_permissions,
            auth_method=AuthenticationMethod.JWT_TOKEN,  # OAuth2 uses JWT tokens
            token_type=AuthTokenType.OAUTH2,
            metadata={"token": token, "user_info": {
                "sub": user_info.sub,
                "name": getattr(user_info, "name", ""),
                "email": getattr(user_info, "email", "")
            }}
        )
    
    def _create_auth_context_from_api_key(self, user: User, api_key: str) -> AuthContext:
        """Create auth context from API key"""
        return AuthContext(
            user_id=user.user_id,
            username=user.username,
            roles=user.roles,
            permissions=user.permissions,
            granular_permissions=user.granular_permissions,
            auth_method=AuthenticationMethod.API_KEY,
            token_type=AuthTokenType.API_KEY,
            metadata={"api_key": api_key}
        )
    
    def _create_auth_context_from_session(self, session: Session) -> AuthContext:
        """Create auth context from session"""
        user = self.auth_manager.users.get(session.user_id)
        if not user:
            return None
            
        return AuthContext(
            user_id=session.user_id,
            username=session.username,
            roles=session.roles,
            permissions=session.permissions,
            granular_permissions=user.granular_permissions,  # Get from user as session may not have granular permissions
            auth_method=AuthenticationMethod.PASSWORD,  # Sessions typically created from password auth
            token_type=AuthTokenType.SESSION,
            session_id=session.session_id,
            metadata={"session": session}
        )
    
    def authorize_request(self, auth_context: AuthContext, 
                         required_permission: Union[Permission, GranularPermission, str],
                         resource: Optional[str] = None,
                         context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Authorize request based on required permissions
        """
        if not auth_context:
            return False
        
        # Check if user has the required permission
        if isinstance(required_permission, Permission):
            return required_permission in auth_context.permissions
        elif isinstance(required_permission, GranularPermission):
            # For granular permissions, we need to check against the user directly
            user = self.auth_manager.users.get(auth_context.user_id)
            if user:
                return user.has_granular_permission(required_permission, context)
            return False
        elif isinstance(required_permission, str):
            # String permission check
            return (required_permission in [p.value for p in auth_context.permissions] or
                   required_permission in [p.value for p in auth_context.granular_permissions])
        
        return False
    
    def _check_rate_limit(self, identifier: str) -> bool:
        """Check if request is within rate limits"""
        now = datetime.now()
        window_start = now - self.rate_limit_window
        
        if identifier not in self.rate_limits:
            self.rate_limits[identifier] = []
        
        # Remove old timestamps
        self.rate_limits[identifier] = [
            timestamp for timestamp in self.rate_limits[identifier]
            if timestamp > window_start
        ]
        
        # Check if limit exceeded
        if len(self.rate_limits[identifier]) >= self.rate_limit_max_requests:
            return False
        
        # Add current request
        self.rate_limits[identifier].append(now)
        return True
    
    def _track_ip(self, ip_address: str):
        """Track IP address for security monitoring"""
        now = datetime.now()
        window_start = now - timedelta(hours=1)
        
        if ip_address not in self.ip_tracking:
            self.ip_tracking[ip_address] = []
        
        # Remove old timestamps
        self.ip_tracking[ip_address] = [
            timestamp for timestamp in self.ip_tracking[ip_address]
            if timestamp > window_start
        ]
        
        # Add current request
        self.ip_tracking[ip_address].append(now)
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics and statistics"""
        now = datetime.now()
        last_hour = now - timedelta(hours=1)
        
        # Count active rate limit entries
        active_rate_limits = {
            identifier: len(timestamps) 
            for identifier, timestamps in self.rate_limits.items()
            if any(ts > last_hour for ts in timestamps)
        }
        
        # Count active IP tracking entries
        active_ips = {
            ip: len(timestamps)
            for ip, timestamps in self.ip_tracking.items()
            if any(ts > last_hour for ts in timestamps)
        }
        
        return {
            "active_rate_limit_entries": len(active_rate_limits),
            "active_ips": len(active_ips),
            "total_requests_last_hour": sum(active_rate_limits.values()),
            "unique_ips_last_hour": len(active_ips)
        }
    
    def log_security_event(self, event_type: str, auth_context: Optional[AuthContext] = None,
                          details: Optional[Dict[str, Any]] = None):
        """Log security events"""
        logger.info(f"Security Event: {event_type}", extra={
            "user_id": auth_context.user_id if auth_context else None,
            "username": auth_context.username if auth_context else None,
            "auth_method": auth_context.auth_method.value if auth_context else None,
            "details": details or {}
        })

# Example usage and integration
def create_security_middleware():
    """Factory function to create security middleware"""
    # In a real application, these would be injected dependencies
    auth_manager = AuthenticationManager()
    oauth2_provider = OAuth2OIDCProvider("https://trading-system.example.com")
    
    return SecurityMiddleware(auth_manager, oauth2_provider)

if __name__ == "__main__":
    # Example usage
    middleware = create_security_middleware()
    print("API Security Middleware initialized")