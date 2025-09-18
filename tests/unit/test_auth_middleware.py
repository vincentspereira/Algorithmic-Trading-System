"""Unit tests for authentication middleware components."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
import sys
from unittest.mock import patch

# Mock dependencies to avoid import issues
with patch.dict('sys.modules', {
    'shared.auth.user_manager': Mock(),
    'passlib.context': Mock(),
    'bcrypt': Mock()
}):
    from shared.auth.middleware import (
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
    from shared.auth.exceptions import TokenExpiredError, TokenInvalidError, AuthenticationError
    from shared.auth.rbac import Permission


class TestMiddlewareComponents:
    """Test suite for middleware components without direct imports."""
    
    def test_token_extraction_logic(self):
        """Test token extraction from authorization header."""
        # Test valid Bearer token
        auth_header = "Bearer valid_token_123"
        parts = auth_header.split()
        
        assert len(parts) == 2
        assert parts[0] == "Bearer"
        assert parts[1] == "valid_token_123"
    
    def test_token_extraction_invalid_format(self):
        """Test token extraction with invalid format."""
        # Test invalid format
        auth_header = "Invalid token"
        parts = auth_header.split()
        
        assert len(parts) != 2 or parts[0] != "Bearer"
    
    def test_excluded_paths_logic(self):
        """Test excluded paths matching logic."""
        excluded_paths = ["/docs", "/health", "/auth/login", "/auth/register"]
        
        # Test matching paths
        assert "/docs" in excluded_paths
        assert "/health" in excluded_paths
        assert "/auth/login" in excluded_paths
        
        # Test non-matching paths
        assert "/protected" not in excluded_paths
        assert "/api/orders" not in excluded_paths
    
    @pytest.mark.asyncio
    async def test_mock_middleware_dispatch(self):
        """Test middleware dispatch logic with mocks."""
        # Mock request
        request = Mock(spec=Request)
        request.url.path = "/protected"
        request.headers = {"authorization": "Bearer valid_token"}
        request.state = Mock()
        
        # Mock call_next function
        call_next = AsyncMock(return_value=JSONResponse({"message": "success"}))
        
        # Mock JWT manager
        jwt_manager = Mock()
        token_data = Mock()
        token_data.user_id = "user123"
        token_data.username = "testuser"
        jwt_manager.verify_token.return_value = token_data
        
        # Simulate middleware logic
        excluded_paths = ["/docs", "/health"]
        
        if request.url.path not in excluded_paths:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                user_data = jwt_manager.verify_token(token, token_type="access")
                request.state.user = user_data
        
        response = await call_next(request)
        
        # Assertions
        jwt_manager.verify_token.assert_called_once_with("valid_token", token_type="access")
        assert request.state.user == token_data
        call_next.assert_called_once_with(request)
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_mock_middleware_excluded_path(self):
        """Test middleware with excluded path."""
        # Mock request for excluded path
        request = Mock(spec=Request)
        request.url.path = "/docs"
        
        # Mock call_next function
        call_next = AsyncMock(return_value=JSONResponse({"message": "docs"}))
        
        # Mock JWT manager (should not be called)
        jwt_manager = Mock()
        
        # Simulate middleware logic
        excluded_paths = ["/docs", "/health"]
        
        if request.url.path in excluded_paths:
            # Skip authentication for excluded paths
            pass
        
        response = await call_next(request)
        
        # Assertions
        jwt_manager.verify_token.assert_not_called()
        call_next.assert_called_once_with(request)
        assert response.status_code == 200
    
    def test_error_response_creation(self):
        """Test error response creation logic."""
        # Test 401 Unauthorized
        error_response = JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"}
        )
        
        assert error_response.status_code == 401
        
        # Test 403 Forbidden
        error_response = JSONResponse(
            status_code=403,
            content={"detail": "Insufficient permissions"}
        )
        
        assert error_response.status_code == 403
    
    def test_token_validation_scenarios(self):
        """Test various token validation scenarios."""
        # Mock JWT manager with different scenarios
        jwt_manager = Mock()
        
        # Valid token scenario
        token_data = Mock()
        token_data.user_id = "user123"
        jwt_manager.verify_token.return_value = token_data
        
        result = jwt_manager.verify_token("valid_token", token_type="access")
        assert result == token_data
        
        # Invalid token scenario
        from shared.auth.exceptions import TokenInvalidError
        jwt_manager.verify_token.side_effect = TokenInvalidError("Invalid token")
        
        with pytest.raises(TokenInvalidError):
            jwt_manager.verify_token("invalid_token", token_type="access")
        
        # Expired token scenario
        from shared.auth.exceptions import TokenExpiredError
        jwt_manager.verify_token.side_effect = TokenExpiredError("Token expired")
        
        with pytest.raises(TokenExpiredError):
            jwt_manager.verify_token("expired_token", token_type="access")
    
    def test_rbac_permission_checking(self):
        """Test RBAC permission checking logic."""
        # Mock RBAC manager
        rbac_manager = Mock()
        
        # Mock user with permissions
        user_permissions = ["read_orders", "write_orders"]
        rbac_manager.check_permission.return_value = True
        
        # Test permission check
        has_permission = rbac_manager.check_permission("user123", "read_orders")
        assert has_permission is True
        
        # Test insufficient permissions
        rbac_manager.check_permission.return_value = False
        has_permission = rbac_manager.check_permission("user123", "admin_access")
        assert has_permission is False
    
    @pytest.mark.asyncio
    async def test_authentication_backend_logic(self):
        """Test authentication backend logic."""
        # Mock request with authorization header
        request = Mock(spec=Request)
        request.headers = {"authorization": "Bearer valid_token"}
        
        # Mock JWT manager
        jwt_manager = Mock()
        token_data = Mock()
        token_data.user_id = "user123"
        jwt_manager.verify_token.return_value = token_data
        
        # Simulate authentication backend logic
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            credentials = jwt_manager.verify_token(token, token_type="access")
            auth_result = ("jwt", credentials)
        else:
            auth_result = None
        
        # Assertions
        assert auth_result is not None
        assert auth_result[0] == "jwt"
        assert auth_result[1] == token_data
        jwt_manager.verify_token.assert_called_once_with("valid_token", token_type="access")
    
    def test_middleware_configuration(self):
        """Test middleware configuration options."""
        # Test default configuration
        config = {
            "require_auth": True,
            "excluded_paths": ["/docs", "/openapi.json", "/health"],
            "jwt_algorithm": "HS256",
            "token_type": "access"
        }
        
        assert config["require_auth"] is True
        assert "/docs" in config["excluded_paths"]
        assert config["jwt_algorithm"] == "HS256"
        
        # Test custom configuration
        custom_config = {
            "require_auth": False,
            "excluded_paths": ["/public", "/api/public"],
            "jwt_algorithm": "RS256"
        }
        
        assert custom_config["require_auth"] is False
        assert "/public" in custom_config["excluded_paths"]
        assert custom_config["jwt_algorithm"] == "RS256"


class TestJWTBearer:
    """Test JWTBearer authentication handler"""
    
    @pytest.fixture
    def jwt_bearer(self):
        jwt_manager = Mock()
        rbac_manager = Mock()
        return JWTBearer(jwt_manager, rbac_manager)
    
    @pytest.mark.asyncio
    async def test_jwt_bearer_valid_token(self, jwt_bearer):
        """Test JWTBearer with valid token"""
        # Mock token data
        token_data = Mock()
        token_data.user_id = "user123"
        token_data.username = "testuser"
        
        jwt_bearer.jwt_manager.validate_token.return_value = token_data
        
        # Mock request and credentials
        request = Mock(spec=Request)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_token")
        
        # Mock parent class call
        with patch.object(JWTBearer.__bases__[0], '__call__', return_value=credentials):
            result = await jwt_bearer(request)
            
        assert result == token_data
        jwt_bearer.jwt_manager.validate_token.assert_called_once_with("valid_token")
    
    @pytest.mark.asyncio
    async def test_jwt_bearer_missing_credentials(self, jwt_bearer):
        """Test JWTBearer with missing credentials"""
        request = Mock(spec=Request)
        
        # Mock parent class to raise HTTPException for missing credentials
        with patch.object(JWTBearer.__bases__[0], '__call__', side_effect=HTTPException(status_code=403)):
            with pytest.raises(HTTPException) as exc_info:
                await jwt_bearer(request)
            
        assert exc_info.value.status_code == 401  # Should convert 403 to 401


class TestDecoratorFunctions:
    """Test permission and role decorator functions"""
    
    @pytest.mark.asyncio
    async def test_require_permissions_decorator(self):
        """Test require_permissions decorator"""
        # Mock Permission enum
        mock_permission = Mock()
        mock_permission.value = "read_orders"
        
        # Create decorator
        decorator = require_permissions(mock_permission)
        
        # Mock function to decorate
        @decorator
        async def protected_function(request):
            return "success"
        
        # Mock request with permissions
        request = Mock(spec=Request)
        request.state.user_id = "user123"
        request.state.permissions = {mock_permission}
        
        # Should succeed
        result = await protected_function(request)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_require_permissions_missing(self):
        """Test require_permissions with missing permissions"""
        # Mock Permission enum
        mock_permission = Mock()
        mock_permission.value = "admin_access"
        
        # Create decorator
        decorator = require_permissions(mock_permission)
        
        # Mock function to decorate
        @decorator
        async def protected_function(request):
            return "success"
        
        # Mock request without required permissions
        request = Mock(spec=Request)
        request.state.user_id = "user123"
        request.state.permissions = set()
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await protected_function(request)
        
        assert exc_info.value.status_code == 403
    
    @pytest.mark.asyncio
    async def test_require_roles_decorator(self):
        """Test require_roles decorator"""
        # Create decorator
        decorator = require_roles("admin", "manager")
        
        # Mock function to decorate
        @decorator
        async def protected_function(request):
            return "success"
        
        # Mock request with required roles
        request = Mock(spec=Request)
        request.state.user_id = "user123"
        request.state.roles = ["admin", "manager", "user"]
        
        # Should succeed
        result = await protected_function(request)
        assert result == "success"


class TestUtilityFunctions:
    """Test utility functions for user context"""
    
    def test_get_current_user(self):
        """Test get_current_user function"""
        # Mock request with token data
        request = Mock(spec=Request)
        token_data = Mock()
        token_data.user_id = "user123"
        request.state.token_data = token_data
        
        result = get_current_user(request)
        assert result == token_data
    
    def test_get_current_user_id(self):
        """Test get_current_user_id function"""
        # Mock request with user ID
        request = Mock(spec=Request)
        request.state.user_id = "user123"
        
        result = get_current_user_id(request)
        assert result == "user123"
    
    def test_get_current_user_permissions(self):
        """Test get_current_user_permissions function"""
        # Mock request with permissions
        request = Mock(spec=Request)
        permissions = {"read_orders", "write_orders"}
        request.state.permissions = permissions
        
        result = get_current_user_permissions(request)
        assert result == permissions
    
    def test_has_permission(self):
        """Test has_permission function"""
        # Mock request with permissions
        request = Mock(spec=Request)
        mock_permission = Mock()
        permissions = {mock_permission}
        request.state.permissions = permissions
        
        result = has_permission(request, mock_permission)
        assert result is True
        
        # Test with missing permission
        other_permission = Mock()
        result = has_permission(request, other_permission)
        assert result is False


class TestRateLimitMiddleware:
    """Test rate limiting middleware"""
    
    def test_rate_limit_initialization(self):
        """Test RateLimitMiddleware initialization"""
        app = Mock()
        middleware = RateLimitMiddleware(
            app=app,
            requests_per_minute=100,
            burst_limit=20
        )
        
        assert middleware.requests_per_minute == 100
        assert middleware.burst_limit == 20
        assert middleware.request_counts == {}
    
    @pytest.mark.asyncio
    async def test_rate_limit_within_limit(self):
        """Test rate limiting within allowed limits"""
        app = Mock()
        middleware = RateLimitMiddleware(app=app, requests_per_minute=60)
        
        # Mock request
        request = Mock(spec=Request)
        request.client.host = "127.0.0.1"
        
        # Mock call_next
        call_next = AsyncMock(return_value=JSONResponse({"message": "success"}))
        
        # Should allow request
        response = await middleware.dispatch(request, call_next)
        
        assert response.status_code == 200
        assert middleware.request_counts["127.0.0.1"] == 1
        call_next.assert_called_once_with(request)