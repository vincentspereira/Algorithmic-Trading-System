"""Unit tests for authentication exceptions."""

import pytest
from shared.auth.exceptions import (
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
    PasswordReuseError,
    RoleError,
    RoleNotFoundError,
    RoleAlreadyExistsError,
    PermissionError,
    PermissionDeniedError,
    InsufficientPermissionsError,
    SessionError,
    SessionExpiredError,
    SessionInvalidError,
    RateLimitError,
    TwoFactorError,
    TwoFactorRequiredError,
    TwoFactorInvalidError,
    ConfigurationError,
    CryptoError,
    ValidationError,
    HTTP_STATUS_MAPPINGS,
    get_http_status_code,
    create_error_response
)


class TestBaseAuthError:
    """Test base AuthError class"""
    
    def test_auth_error_basic_initialization(self):
        """Test basic AuthError initialization"""
        error = AuthError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.error_code == "AuthError"
        assert error.details == {}
    
    def test_auth_error_full_initialization(self):
        """Test AuthError with all parameters"""
        details = {"field": "username", "value": "invalid"}
        error = AuthError(
            message="Custom error",
            error_code="CUSTOM_ERROR",
            details=details
        )
        
        assert error.message == "Custom error"
        assert error.error_code == "CUSTOM_ERROR"
        assert error.details == details
    
    def test_auth_error_to_dict(self):
        """Test AuthError to_dict method"""
        details = {"user_id": "123"}
        error = AuthError(
            message="Test error",
            error_code="TEST_ERROR",
            details=details
        )
        
        result = error.to_dict()
        expected = {
            "error": "TEST_ERROR",
            "message": "Test error",
            "details": details
        }
        
        assert result == expected


class TestTokenErrors:
    """Test token-related exceptions"""
    
    def test_token_expired_error_default(self):
        """Test TokenExpiredError with default message"""
        error = TokenExpiredError()
        
        assert error.message == "Token has expired"
        assert error.error_code == "TokenExpiredError"
    
    def test_token_expired_error_custom(self):
        """Test TokenExpiredError with custom message"""
        error = TokenExpiredError("Custom expiry message")
        
        assert error.message == "Custom expiry message"
        assert error.error_code == "TokenExpiredError"
    
    def test_token_invalid_error_default(self):
        """Test TokenInvalidError with default message"""
        error = TokenInvalidError()
        
        assert error.message == "Invalid token"
        assert error.error_code == "TokenInvalidError"
    
    def test_token_revoked_error_default(self):
        """Test TokenRevokedError with default message"""
        error = TokenRevokedError()
        
        assert error.message == "Token has been revoked"
        assert error.error_code == "TokenRevokedError"
    
    def test_token_missing_error_default(self):
        """Test TokenMissingError with default message"""
        error = TokenMissingError()
        
        assert error.message == "Authentication token is required"
        assert error.error_code == "TokenMissingError"


class TestUserErrors:
    """Test user-related exceptions"""
    
    def test_user_not_found_error(self):
        """Test UserNotFoundError"""
        error = UserNotFoundError()
        assert error.message == "User not found"
        
        error_custom = UserNotFoundError("User 'john' not found")
        assert error_custom.message == "User 'john' not found"
    
    def test_user_already_exists_error(self):
        """Test UserAlreadyExistsError"""
        error = UserAlreadyExistsError()
        assert error.message == "User already exists"
    
    def test_user_inactive_error(self):
        """Test UserInactiveError"""
        error = UserInactiveError()
        assert error.message == "User account is inactive"
    
    def test_user_suspended_error(self):
        """Test UserSuspendedError"""
        error = UserSuspendedError()
        assert error.message == "User account is suspended"
    
    def test_user_locked_error(self):
        """Test UserLockedError"""
        error = UserLockedError()
        assert error.message == "User account is locked"


class TestPasswordErrors:
    """Test password-related exceptions"""
    
    def test_weak_password_error(self):
        """Test WeakPasswordError"""
        error = WeakPasswordError()
        assert error.message == "Password does not meet security requirements"
    
    def test_password_expired_error(self):
        """Test PasswordExpiredError"""
        error = PasswordExpiredError()
        assert error.message == "Password has expired"
    
    def test_password_reuse_error(self):
        """Test PasswordReuseError"""
        error = PasswordReuseError()
        assert error.message == "Password has been used recently"


class TestRoleErrors:
    """Test role-related exceptions"""
    
    def test_role_not_found_error(self):
        """Test RoleNotFoundError"""
        error = RoleNotFoundError()
        assert error.message == "Role not found"
    
    def test_role_already_exists_error(self):
        """Test RoleAlreadyExistsError"""
        error = RoleAlreadyExistsError()
        assert error.message == "Role already exists"


class TestPermissionErrors:
    """Test permission-related exceptions"""
    
    def test_permission_denied_error(self):
        """Test PermissionDeniedError"""
        error = PermissionDeniedError()
        assert error.message == "Permission denied"
    
    def test_insufficient_permissions_error(self):
        """Test InsufficientPermissionsError"""
        error = InsufficientPermissionsError()
        assert error.message == "Insufficient permissions"


class TestSessionErrors:
    """Test session-related exceptions"""
    
    def test_session_expired_error(self):
        """Test SessionExpiredError"""
        error = SessionExpiredError()
        assert error.message == "Session has expired"
    
    def test_session_invalid_error(self):
        """Test SessionInvalidError"""
        error = SessionInvalidError()
        assert error.message == "Invalid session"


class TestTwoFactorErrors:
    """Test two-factor authentication exceptions"""
    
    def test_two_factor_required_error(self):
        """Test TwoFactorRequiredError"""
        error = TwoFactorRequiredError()
        assert error.message == "Two-factor authentication required"
    
    def test_two_factor_invalid_error(self):
        """Test TwoFactorInvalidError"""
        error = TwoFactorInvalidError()
        assert error.message == "Invalid two-factor authentication code"


class TestOtherErrors:
    """Test other authentication exceptions"""
    
    def test_rate_limit_error(self):
        """Test RateLimitError"""
        error = RateLimitError()
        assert error.message == "Rate limit exceeded"
    
    def test_configuration_error(self):
        """Test ConfigurationError"""
        error = ConfigurationError()
        assert error.message == "Authentication configuration error"
    
    def test_crypto_error(self):
        """Test CryptoError"""
        error = CryptoError()
        assert error.message == "Cryptographic operation failed"
    
    def test_validation_error(self):
        """Test ValidationError"""
        error = ValidationError()
        assert error.message == "Validation failed"
    
    def test_invalid_credentials_error(self):
        """Test InvalidCredentialsError"""
        error = InvalidCredentialsError()
        assert error.message == "Invalid credentials"


class TestHTTPStatusMappings:
    """Test HTTP status code mappings and utility functions"""
    
    def test_http_status_mappings_exist(self):
        """Test that HTTP_STATUS_MAPPINGS contains expected mappings"""
        # Test 401 mappings
        assert HTTP_STATUS_MAPPINGS[TokenExpiredError] == 401
        assert HTTP_STATUS_MAPPINGS[TokenInvalidError] == 401
        assert HTTP_STATUS_MAPPINGS[AuthenticationError] == 401
        
        # Test 403 mappings
        assert HTTP_STATUS_MAPPINGS[AuthorizationError] == 403
        assert HTTP_STATUS_MAPPINGS[PermissionDeniedError] == 403
        assert HTTP_STATUS_MAPPINGS[UserInactiveError] == 403
        
        # Test 404 mappings
        assert HTTP_STATUS_MAPPINGS[UserNotFoundError] == 404
        assert HTTP_STATUS_MAPPINGS[RoleNotFoundError] == 404
        
        # Test 409 mappings
        assert HTTP_STATUS_MAPPINGS[UserAlreadyExistsError] == 409
        assert HTTP_STATUS_MAPPINGS[RoleAlreadyExistsError] == 409
        
        # Test 429 mappings
        assert HTTP_STATUS_MAPPINGS[RateLimitError] == 429
        
        # Test 500 mappings
        assert HTTP_STATUS_MAPPINGS[ConfigurationError] == 500
        assert HTTP_STATUS_MAPPINGS[CryptoError] == 500
    
    def test_get_http_status_code_known_exception(self):
        """Test get_http_status_code with known exception"""
        error = TokenExpiredError()
        status_code = get_http_status_code(error)
        assert status_code == 401
    
    def test_get_http_status_code_unknown_exception(self):
        """Test get_http_status_code with unknown exception"""
        error = AuthError("Unknown error")
        status_code = get_http_status_code(error)
        assert status_code == 500  # Default for unknown exceptions
    
    def test_create_error_response(self):
        """Test create_error_response function"""
        details = {"field": "username"}
        error = TokenExpiredError(
            message="Token expired",
            error_code="TOKEN_EXPIRED",
            details=details
        )
        
        response = create_error_response(error)
        expected = {
            "error": "TOKEN_EXPIRED",
            "message": "Token expired",
            "details": details,
            "status_code": 401
        }
        
        assert response == expected
    
    def test_create_error_response_default_values(self):
        """Test create_error_response with default values"""
        error = ValidationError()
        response = create_error_response(error)
        
        assert response["error"] == "ValidationError"
        assert response["message"] == "Validation failed"
        assert response["details"] == {}
        assert response["status_code"] == 400


class TestExceptionInheritance:
    """Test exception inheritance hierarchy"""
    
    def test_token_error_inheritance(self):
        """Test that token errors inherit from TokenError and AuthError"""
        error = TokenExpiredError()
        
        assert isinstance(error, TokenError)
        assert isinstance(error, AuthError)
        assert isinstance(error, Exception)
    
    def test_user_error_inheritance(self):
        """Test that user errors inherit from UserError and AuthError"""
        error = UserNotFoundError()
        
        assert isinstance(error, UserError)
        assert isinstance(error, AuthError)
        assert isinstance(error, Exception)
    
    def test_authentication_error_inheritance(self):
        """Test AuthenticationError inheritance"""
        error = InvalidCredentialsError()
        
        assert isinstance(error, AuthenticationError)
        assert isinstance(error, AuthError)
        assert isinstance(error, Exception)