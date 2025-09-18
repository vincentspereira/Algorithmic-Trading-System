"""Security Middleware for FastAPI Applications

Provides authentication and authorization middleware with JWT token validation,
RBAC integration, and comprehensive security features.
"""

import logging
from typing import Optional, List, Callable, Any
from datetime import datetime

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .jwt_manager import JWTManager, TokenData
from .rbac import RBACManager, Permission
from .exceptions import (
    AuthenticationError, 
    AuthorizationError, 
    TokenExpiredError,
    TokenInvalidError
)

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for authentication and authorization"""
    
    def __init__(
        self,
        app,
        jwt_manager: JWTManager,
        rbac_manager: RBACManager,
        excluded_paths: Optional[List[str]] = None,
        require_auth: bool = True
    ):
        super().__init__(app)
        self.jwt_manager = jwt_manager
        self.rbac_manager = rbac_manager
        self.excluded_paths = excluded_paths or [
            "/docs", "/redoc", "/openapi.json", "/health", "/metrics",
            "/auth/login", "/auth/register", "/auth/refresh"
        ]
        self.require_auth = require_auth
    
    async def dispatch(self, request: Request, call_next):
        """Process request through security middleware"""
        
        # Skip authentication for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Skip authentication if not required
        if not self.require_auth:
            return await call_next(request)
        
        try:
            # Extract and validate token
            token = self._extract_token(request)
            if not token:
                return self._unauthorized_response("Missing authentication token")
            
            # Validate JWT token
            token_data = self.jwt_manager.validate_token(token)
            if not token_data:
                return self._unauthorized_response("Invalid authentication token")
            
            # Add user context to request
            request.state.user_id = token_data.user_id
            request.state.username = token_data.username
            request.state.roles = token_data.roles
            request.state.permissions = self.rbac_manager.get_user_permissions(token_data.user_id)
            request.state.token_data = token_data
            
            # Log successful authentication
            logger.info(
                f"Authenticated user: {token_data.username} ({token_data.user_id}) "
                f"for {request.method} {request.url.path}"
            )
            
            response = await call_next(request)
            return response
            
        except TokenExpiredError:
            return self._unauthorized_response("Token has expired")
        except TokenInvalidError:
            return self._unauthorized_response("Invalid token")
        except AuthenticationError as e:
            return self._unauthorized_response(str(e))
        except Exception as e:
            logger.error(f"Security middleware error: {str(e)}")
            return self._server_error_response("Authentication service unavailable")
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request headers"""
        # Try Authorization header first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix
        
        # Try cookie as fallback
        return request.cookies.get("access_token")
    
    def _unauthorized_response(self, message: str) -> JSONResponse:
        """Return unauthorized response"""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Unauthorized",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    def _server_error_response(self, message: str) -> JSONResponse:
        """Return server error response"""
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


class JWTBearer(HTTPBearer):
    """Custom JWT Bearer token handler for FastAPI dependency injection"""
    
    def __init__(
        self,
        jwt_manager: JWTManager,
        rbac_manager: RBACManager,
        auto_error: bool = True
    ):
        super().__init__(auto_error=auto_error)
        self.jwt_manager = jwt_manager
        self.rbac_manager = rbac_manager
    
    async def __call__(self, request: Request) -> TokenData:
        """Validate JWT token and return token data"""
        try:
            credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        except HTTPException as e:
            # Convert parent class 403 to 401 for consistency
            if e.status_code == 403:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            raise
        
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        try:
            token_data = self.jwt_manager.validate_token(credentials.credentials)
            if not token_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            return token_data
            
        except TokenExpiredError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except TokenInvalidError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            logger.error(f"JWT validation error: {str(e)} (type: {type(e).__name__})")
            # For debugging - convert all token-related errors to 401
            if "token" in str(e).lower() or "jwt" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service unavailable"
            )


def require_permissions(*permissions: Permission):
    """Decorator factory for requiring specific permissions
    
    Args:
        *permissions: Required permissions
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # Try to get from kwargs
                request = kwargs.get('request')
            
            if not request or not hasattr(request.state, 'user_id'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check permissions
            user_permissions = getattr(request.state, 'permissions', set())
            missing_permissions = []
            
            for permission in permissions:
                if permission not in user_permissions:
                    missing_permissions.append(permission.value)
            
            if missing_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permissions: {missing_permissions}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_any_permission(*permissions: Permission):
    """Decorator factory for requiring any of the specified permissions
    
    Args:
        *permissions: Permissions (user needs at least one)
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                request = kwargs.get('request')
            
            if not request or not hasattr(request.state, 'user_id'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check if user has any of the required permissions
            user_permissions = getattr(request.state, 'permissions', set())
            has_permission = any(perm in user_permissions for perm in permissions)
            
            if not has_permission:
                perm_names = [p.value for p in permissions]
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires at least one of: {perm_names}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_roles(*roles: str):
    """Decorator factory for requiring specific roles
    
    Args:
        *roles: Required role names
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                request = kwargs.get('request')
            
            if not request or not hasattr(request.state, 'user_id'):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check roles
            user_roles = getattr(request.state, 'roles', [])
            missing_roles = []
            
            for role in roles:
                if role not in user_roles:
                    missing_roles.append(role)
            
            if missing_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required roles: {missing_roles}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def get_current_user(request: Request) -> Optional[TokenData]:
    """Get current authenticated user from request state
    
    Args:
        request: FastAPI request object
        
    Returns:
        TokenData if user is authenticated, None otherwise
    """
    return getattr(request.state, 'token_data', None)


def get_current_user_id(request: Request) -> Optional[str]:
    """Get current user ID from request state
    
    Args:
        request: FastAPI request object
        
    Returns:
        User ID if authenticated, None otherwise
    """
    return getattr(request.state, 'user_id', None)


def get_current_user_permissions(request: Request) -> set:
    """Get current user permissions from request state
    
    Args:
        request: FastAPI request object
        
    Returns:
        Set of user permissions
    """
    return getattr(request.state, 'permissions', set())


def has_permission(request: Request, permission: Permission) -> bool:
    """Check if current user has a specific permission
    
    Args:
        request: FastAPI request object
        permission: Permission to check
        
    Returns:
        True if user has permission, False otherwise
    """
    user_permissions = get_current_user_permissions(request)
    return permission in user_permissions


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_limit: int = 10
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.request_counts = {}  # In production, use Redis
        self.last_reset = datetime.utcnow()
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting"""
        client_ip = request.client.host
        current_time = datetime.utcnow()
        
        # Reset counters every minute
        if (current_time - self.last_reset).seconds >= 60:
            self.request_counts.clear()
            self.last_reset = current_time
        
        # Check rate limit
        current_count = self.request_counts.get(client_ip, 0)
        if current_count >= self.requests_per_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_minute} requests per minute",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Increment counter
        self.request_counts[client_ip] = current_count + 1
        
        response = await call_next(request)
        return response