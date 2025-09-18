"""Authentication and Authorization Exceptions

Defines custom exceptions for the authentication and authorization system
with detailed error messages and proper HTTP status code mappings.
"""

from typing import Optional, Dict, Any


class AuthError(Exception):
    """Base authentication/authorization error"""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


class AuthenticationError(AuthError):
    """Authentication failed - user identity could not be verified"""
    pass


class AuthorizationError(AuthError):
    """Authorization failed - user lacks required permissions"""
    pass


class TokenError(AuthError):
    """Base token-related error"""
    pass


class TokenExpiredError(TokenError):
    """JWT token has expired"""
    
    def __init__(self, message: str = "Token has expired", **kwargs):
        super().__init__(message, **kwargs)


class TokenInvalidError(TokenError):
    """JWT token is invalid or malformed"""
    
    def __init__(self, message: str = "Invalid token", **kwargs):
        super().__init__(message, **kwargs)


class TokenRevokedError(TokenError):
    """JWT token has been revoked"""
    
    def __init__(self, message: str = "Token has been revoked", **kwargs):
        super().__init__(message, **kwargs)


class TokenMissingError(TokenError):
    """JWT token is missing from request"""
    
    def __init__(self, message: str = "Authentication token is required", **kwargs):
        super().__init__(message, **kwargs)


class UserError(AuthError):
    """Base user-related error"""
    pass


class UserNotFoundError(UserError):
    """User does not exist"""
    
    def __init__(self, message: str = "User not found", **kwargs):
        super().__init__(message, **kwargs)


class UserAlreadyExistsError(UserError):
    """User already exists (duplicate username/email)"""
    
    def __init__(self, message: str = "User already exists", **kwargs):
        super().__init__(message, **kwargs)


class UserInactiveError(UserError):
    """User account is inactive"""
    
    def __init__(self, message: str = "User account is inactive", **kwargs):
        super().__init__(message, **kwargs)


class UserSuspendedError(UserError):
    """User account is suspended"""
    
    def __init__(self, message: str = "User account is suspended", **kwargs):
        super().__init__(message, **kwargs)


class UserLockedError(UserError):
    """User account is locked due to failed login attempts"""
    
    def __init__(self, message: str = "User account is locked", **kwargs):
        super().__init__(message, **kwargs)


class InvalidCredentialsError(AuthenticationError):
    """Invalid username/password combination"""
    
    def __init__(self, message: str = "Invalid credentials", **kwargs):
        super().__init__(message, **kwargs)


class PasswordError(AuthError):
    """Base password-related error"""
    pass


class WeakPasswordError(PasswordError):
    """Password does not meet security requirements"""
    
    def __init__(self, message: str = "Password does not meet security requirements", **kwargs):
        super().__init__(message, **kwargs)


class PasswordExpiredError(PasswordError):
    """Password has expired and must be changed"""
    
    def __init__(self, message: str = "Password has expired", **kwargs):
        super().__init__(message, **kwargs)


class PasswordReuseError(PasswordError):
    """Password has been used recently and cannot be reused"""
    
    def __init__(self, message: str = "Password has been used recently", **kwargs):
        super().__init__(message, **kwargs)


class RoleError(AuthError):
    """Base role-related error"""
    pass


class RoleNotFoundError(RoleError):
    """Role does not exist"""
    
    def __init__(self, message: str = "Role not found", **kwargs):
        super().__init__(message, **kwargs)


class RoleAlreadyExistsError(RoleError):
    """Role already exists"""
    
    def __init__(self, message: str = "Role already exists", **kwargs):
        super().__init__(message, **kwargs)


class PermissionError(AuthError):
    """Base permission-related error"""
    pass


class PermissionDeniedError(PermissionError):
    """User does not have required permission"""
    
    def __init__(self, message: str = "Permission denied", **kwargs):
        super().__init__(message, **kwargs)


class InsufficientPermissionsError(PermissionError):
    """User has some but not all required permissions"""
    
    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(message, **kwargs)


class SessionError(AuthError):
    """Base session-related error"""
    pass


class SessionExpiredError(SessionError):
    """User session has expired"""
    
    def __init__(self, message: str = "Session has expired", **kwargs):
        super().__init__(message, **kwargs)


class SessionInvalidError(SessionError):
    """User session is invalid"""
    
    def __init__(self, message: str = "Invalid session", **kwargs):
        super().__init__(message, **kwargs)


class RateLimitError(AuthError):
    """Rate limit exceeded"""
    
    def __init__(self, message: str = "Rate limit exceeded", **kwargs):
        super().__init__(message, **kwargs)


class TwoFactorError(AuthError):
    """Base two-factor authentication error"""
    pass


class TwoFactorRequiredError(TwoFactorError):
    """Two-factor authentication is required"""
    
    def __init__(self, message: str = "Two-factor authentication required", **kwargs):
        super().__init__(message, **kwargs)


class TwoFactorInvalidError(TwoFactorError):
    """Two-factor authentication code is invalid"""
    
    def __init__(self, message: str = "Invalid two-factor authentication code", **kwargs):
        super().__init__(message, **kwargs)


class ConfigurationError(AuthError):
    """Authentication system configuration error"""
    
    def __init__(self, message: str = "Authentication configuration error", **kwargs):
        super().__init__(message, **kwargs)


class CryptoError(AuthError):
    """Cryptographic operation error"""
    
    def __init__(self, message: str = "Cryptographic operation failed", **kwargs):
        super().__init__(message, **kwargs)


class ValidationError(AuthError):
    """Input validation error"""
    
    def __init__(self, message: str = "Validation failed", **kwargs):
        super().__init__(message, **kwargs)


# HTTP Status Code Mappings
HTTP_STATUS_MAPPINGS = {
    # 400 Bad Request
    ValidationError: 400,
    WeakPasswordError: 400,
    PasswordReuseError: 400,
    
    # 401 Unauthorized
    AuthenticationError: 401,
    InvalidCredentialsError: 401,
    TokenExpiredError: 401,
    TokenInvalidError: 401,
    TokenRevokedError: 401,
    TokenMissingError: 401,
    SessionExpiredError: 401,
    SessionInvalidError: 401,
    TwoFactorRequiredError: 401,
    TwoFactorInvalidError: 401,
    
    # 403 Forbidden
    AuthorizationError: 403,
    PermissionDeniedError: 403,
    InsufficientPermissionsError: 403,
    UserInactiveError: 403,
    UserSuspendedError: 403,
    UserLockedError: 403,
    
    # 404 Not Found
    UserNotFoundError: 404,
    RoleNotFoundError: 404,
    
    # 409 Conflict
    UserAlreadyExistsError: 409,
    RoleAlreadyExistsError: 409,
    
    # 429 Too Many Requests
    RateLimitError: 429,
    
    # 500 Internal Server Error
    ConfigurationError: 500,
    CryptoError: 500,
}


def get_http_status_code(exception: AuthError) -> int:
    """Get HTTP status code for authentication exception
    
    Args:
        exception: Authentication exception
        
    Returns:
        HTTP status code
    """
    return HTTP_STATUS_MAPPINGS.get(type(exception), 500)


def create_error_response(exception: AuthError) -> Dict[str, Any]:
    """Create standardized error response for authentication exception
    
    Args:
        exception: Authentication exception
        
    Returns:
        Error response dictionary
    """
    return {
        "error": exception.error_code,
        "message": exception.message,
        "details": exception.details,
        "status_code": get_http_status_code(exception)
    }