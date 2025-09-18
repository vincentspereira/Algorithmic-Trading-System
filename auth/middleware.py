#!/usr/bin/env python3
"""
Authentication Middleware for API endpoints
Handles JWT token validation for both local and OIDC tokens
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from functools import wraps
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# FastAPI/Starlette imports (if using FastAPI)
try:
    from fastapi import HTTPException, status, Request, Depends
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    HTTPException = None
    status = None
    Request = None
    Depends = None
    HTTPBearer = None
    HTTPAuthorizationCredentials = None

# Flask imports (if using Flask)
try:
    from flask import request, jsonify, g
    from functools import wraps as flask_wraps
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    request = None
    jsonify = None
    g = None
    flask_wraps = None

from .oauth_service import OAuthService, Permission, UserRole
from .keycloak_client import KeycloakConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AuthContext:
    """Authentication context for requests"""
    user_id: str
    username: str
    email: str = ""
    roles: List[UserRole] = None
    permissions: List[str] = None
    is_authenticated: bool = False
    is_oidc: bool = False
    token_payload: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = []
        if self.permissions is None:
            self.permissions = []
        if self.token_payload is None:
            self.token_payload = {}

class AuthMiddleware:
    """Authentication middleware for API endpoints"""
    
    def __init__(self, oauth_service: OAuthService = None, keycloak_config: KeycloakConfig = None):
        self.oauth_service = oauth_service or OAuthService(keycloak_config=keycloak_config)
        self._security = HTTPBearer() if FASTAPI_AVAILABLE else None
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.oauth_service.close()
    
    def extract_token_from_header(self, authorization_header: str) -> Optional[str]:
        """Extract JWT token from Authorization header"""
        if not authorization_header:
            return None
        
        parts = authorization_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None
        
        return parts[1]
    
    async def authenticate_request(self, token: str) -> Optional[AuthContext]:
        """Authenticate request using JWT token"""
        if not token:
            return None
        
        try:
            # Verify token (handles both local and OIDC tokens)
            payload = await self.oauth_service.verify_token(token)
            if not payload:
                return None
            
            # Extract user information from token payload
            user_id = payload.get('sub') or payload.get('user_id', '')
            username = payload.get('preferred_username') or payload.get('username', '')
            email = payload.get('email', '')
            
            # Extract roles and permissions
            roles = []
            permissions = []
            
            # Handle OIDC token structure
            if 'realm_access' in payload:
                # Keycloak OIDC token
                realm_roles = payload.get('realm_access', {}).get('roles', [])
                client_roles = payload.get('resource_access', {}).get(
                    self.oauth_service.keycloak_config.client_id, {}
                ).get('roles', [])
                
                all_roles = realm_roles + client_roles
                
                # Map to system roles
                for role in all_roles:
                    if role == 'admin':
                        roles.append(UserRole.ADMIN)
                    elif role == 'trader':
                        roles.append(UserRole.TRADER)
                    elif role == 'analyst':
                        roles.append(UserRole.ANALYST)
                    elif role == 'viewer':
                        roles.append(UserRole.VIEWER)
                    elif role == 'risk_manager':
                        roles.append(UserRole.RISK_MANAGER)
                    elif role == 'compliance_officer':
                        roles.append(UserRole.COMPLIANCE_OFFICER)
                
                # Map roles to permissions
                for role in roles:
                    role_permissions = self.oauth_service.role_permissions.get(role, [])
                    permissions.extend([perm.value for perm in role_permissions])
                
                is_oidc = True
            else:
                # Local token structure
                roles_data = payload.get('roles', [])
                permissions_data = payload.get('permissions', [])
                
                # Convert role strings to UserRole enums
                for role_str in roles_data:
                    try:
                        roles.append(UserRole(role_str))
                    except ValueError:
                        logger.warning(f"Unknown role: {role_str}")
                
                # Convert permission strings
                permissions = [perm.value if hasattr(perm, 'value') else str(perm) for perm in permissions_data]
                
                is_oidc = False
            
            return AuthContext(
                user_id=user_id,
                username=username,
                email=email,
                roles=roles,
                permissions=list(set(permissions)),  # Remove duplicates
                is_authenticated=True,
                is_oidc=is_oidc,
                token_payload=payload
            )
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    def require_auth(self, required_permissions: List[str] = None, required_roles: List[UserRole] = None):
        """Decorator to require authentication and optionally specific permissions/roles"""
        def decorator(func):
            if FASTAPI_AVAILABLE:
                return self._fastapi_auth_decorator(func, required_permissions, required_roles)
            elif FLASK_AVAILABLE:
                return self._flask_auth_decorator(func, required_permissions, required_roles)
            else:
                raise RuntimeError("No supported web framework found (FastAPI or Flask)")
        return decorator
    
    def _fastapi_auth_decorator(self, func, required_permissions: List[str] = None, required_roles: List[UserRole] = None):
        """FastAPI authentication decorator"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if hasattr(arg, 'headers'):
                    request = arg
                    break
            
            if not request:
                for value in kwargs.values():
                    if hasattr(value, 'headers'):
                        request = value
                        break
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )
            
            # Extract token
            auth_header = request.headers.get('Authorization')
            token = self.extract_token_from_header(auth_header)
            
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Authenticate
            auth_context = await self.authenticate_request(token)
            if not auth_context or not auth_context.is_authenticated:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Check permissions
            if required_permissions:
                if not any(perm in auth_context.permissions for perm in required_permissions):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions"
                    )
            
            # Check roles
            if required_roles:
                if not any(role in auth_context.roles for role in required_roles):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient role privileges"
                    )
            
            # Add auth context to kwargs
            kwargs['auth_context'] = auth_context
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    def _flask_auth_decorator(self, func, required_permissions: List[str] = None, required_roles: List[UserRole] = None):
        """Flask authentication decorator"""
        @flask_wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract token from Flask request
            auth_header = request.headers.get('Authorization')
            token = self.extract_token_from_header(auth_header)
            
            if not token:
                return jsonify({"error": "Authentication required"}), 401
            
            # Authenticate
            auth_context = await self.authenticate_request(token)
            if not auth_context or not auth_context.is_authenticated:
                return jsonify({"error": "Invalid or expired token"}), 401
            
            # Check permissions
            if required_permissions:
                if not any(perm in auth_context.permissions for perm in required_permissions):
                    return jsonify({"error": "Insufficient permissions"}), 403
            
            # Check roles
            if required_roles:
                if not any(role in auth_context.roles for role in required_roles):
                    return jsonify({"error": "Insufficient role privileges"}), 403
            
            # Store auth context in Flask's g object
            g.auth_context = auth_context
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    # FastAPI dependency injection
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> AuthContext:
        """FastAPI dependency to get current authenticated user"""
        if not FASTAPI_AVAILABLE:
            raise RuntimeError("FastAPI not available")
        
        auth_context = await self.authenticate_request(credentials.credentials)
        if not auth_context or not auth_context.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return auth_context
    
    async def get_admin_user(self, auth_context: AuthContext = Depends(get_current_user)) -> AuthContext:
        """FastAPI dependency to get current admin user"""
        if UserRole.ADMIN not in auth_context.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required"
            )
        return auth_context
    
    async def get_trader_user(self, auth_context: AuthContext = Depends(get_current_user)) -> AuthContext:
        """FastAPI dependency to get current trader user"""
        allowed_roles = [UserRole.ADMIN, UserRole.TRADER]
        if not any(role in auth_context.roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Trader privileges required"
            )
        return auth_context

# Convenience functions for common permission checks
def require_permission(*permissions: str):
    """Decorator to require specific permissions"""
    def decorator(middleware_instance):
        return middleware_instance.require_auth(required_permissions=list(permissions))
    return decorator

def require_role(*roles: UserRole):
    """Decorator to require specific roles"""
    def decorator(middleware_instance):
        return middleware_instance.require_auth(required_roles=list(roles))
    return decorator

def require_admin(middleware_instance):
    """Decorator to require admin role"""
    return middleware_instance.require_auth(required_roles=[UserRole.ADMIN])

def require_trader(middleware_instance):
    """Decorator to require trader or admin role"""
    return middleware_instance.require_auth(required_roles=[UserRole.ADMIN, UserRole.TRADER])

# Example usage
if __name__ == "__main__":
    async def main():
        # Initialize middleware
        async with AuthMiddleware() as auth_middleware:
            
            # Example FastAPI endpoint
            if FASTAPI_AVAILABLE:
                @auth_middleware.require_auth(required_permissions=["read:portfolio"])
                async def get_portfolio(request: Request, auth_context: AuthContext):
                    return {
                        "message": f"Portfolio for user {auth_context.username}",
                        "user_id": auth_context.user_id,
                        "permissions": auth_context.permissions
                    }
            
            # Example Flask endpoint
            if FLASK_AVAILABLE:
                @auth_middleware.require_auth(required_roles=[UserRole.TRADER])
                async def execute_trade():
                    auth_context = g.auth_context
                    return jsonify({
                        "message": f"Trade executed by {auth_context.username}",
                        "user_id": auth_context.user_id
                    })
            
            logger.info("Authentication middleware initialized successfully")
    
    asyncio.run(main())