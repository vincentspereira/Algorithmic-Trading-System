"""Authentication and Authorization Module

Provides comprehensive authentication and authorization functionality for the
algorithmic trading system including JWT token management, role-based access
control (RBAC), user management, and security middleware.

Components:
- JWT Manager: Token generation, validation, and refresh
- RBAC System: Role and permission management
- User Manager: User account management and authentication
- Security Middleware: FastAPI middleware for request authentication
- Exceptions: Custom authentication/authorization exceptions

Usage:
    from shared.auth import JWTManager, RBACManager, UserManager
    from shared.auth.middleware import SecurityMiddleware
    from shared.auth.exceptions import AuthenticationError
"""

from .jwt_manager import JWTManager, TokenData
from .rbac import RBACManager, Role, Permission
from .user_manager import (
    UserManager, 
    UserProfile, 
    UserCreateRequest, 
    UserUpdateRequest,
    PasswordChangeRequest,
    UserStatus,
    LoginAttemptResult
)
from .middleware import (
    SecurityMiddleware, 
    JWTBearer, 
    RateLimitMiddleware,
    require_permissions,
    require_any_permission,
    require_roles,
    get_current_user,
    get_current_user_id,
    get_current_user_permissions,
    has_permission
)
from .exceptions import (
    AuthError,
    AuthenticationError,
    AuthorizationError,
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
    TokenMissingError,
    UserError,
    UserNotFoundError,
    UserAlreadyExistsError,
    UserInactiveError,
    UserSuspendedError,
    UserLockedError,
    InvalidCredentialsError,
    PasswordError,
    WeakPasswordError,
    PasswordExpiredError,
    RoleError,
    RoleNotFoundError,
    PermissionError,
    PermissionDeniedError,
    RateLimitError,
    get_http_status_code,
    create_error_response
)

__all__ = [
    # Core managers
    "JWTManager",
    "RBACManager", 
    "UserManager",
    
    # Data models
    "TokenData",
    "Role",
    "Permission",
    "UserProfile",
    "UserCreateRequest",
    "UserUpdateRequest",
    "PasswordChangeRequest",
    "UserStatus",
    "LoginAttemptResult",
    
    # Middleware and decorators
    "SecurityMiddleware",
    "JWTBearer",
    "RateLimitMiddleware",
    "require_permissions",
    "require_any_permission",
    "require_roles",
    "get_current_user",
    "get_current_user_id",
    "get_current_user_permissions",
    "has_permission",
    "require_permissions",
    "require_roles",
    
    # Exceptions
    "AuthError",
    "AuthenticationError",
    "AuthorizationError",
    "TokenError",
    "TokenExpiredError",
    "TokenInvalidError",
    "TokenRevokedError",
    "TokenMissingError",
    "UserError",
    "UserNotFoundError",
    "UserAlreadyExistsError",
    "UserInactiveError",
    "UserSuspendedError",
    "UserLockedError",
    "InvalidCredentialsError",
    "PasswordError",
    "WeakPasswordError",
    "PasswordExpiredError",
    "RoleError",
    "RoleNotFoundError",
    "PermissionError",
    "PermissionDeniedError",
    "RateLimitError",
    "get_http_status_code",
    "create_error_response"
]