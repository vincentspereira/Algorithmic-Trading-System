"""Comprehensive Test Suite for Authentication System

Tests JWT authentication, RBAC, user management, and security middleware.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

# Import authentication components
from shared.auth import (
    JWTManager,
    RBACManager,
    UserManager,
    JWTBearer,
    TokenData,
    UserProfile,
    UserCreateRequest,
    UserUpdateRequest,
    PasswordChangeRequest,
    Permission,
    Role,
    UserStatus,
    LoginAttemptResult,
    AuthenticationError,
    AuthorizationError,
    TokenError,
    TokenInvalidError,
    TokenExpiredError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
    PermissionDeniedError
)


class TestJWTManager:
    """Test JWT token management functionality"""
    
    @pytest.fixture
    def jwt_manager(self):
        """Create JWT manager instance for testing"""
        return JWTManager(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7
        )
    
    def test_create_access_token(self, jwt_manager):
        """Test access token creation"""
        user_id = "user123"
        username = "testuser"
        email = "test@example.com"
        roles = ["trader"]
        permissions = ["read_portfolio", "execute_trades"]
        
        token = jwt_manager.create_access_token(user_id, username, email, roles, permissions)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token can be decoded
        token_data = jwt_manager.verify_token(token)
        assert token_data.user_id == user_id
        assert token_data.username == username
        assert token_data.roles == roles
        assert token_data.permissions == permissions
    
    def test_create_refresh_token(self, jwt_manager):
        """Test refresh token creation"""
        user_id = "user123"
        username = "testuser"
        
        token = jwt_manager.create_refresh_token(user_id, username)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token can be decoded
        token_data = jwt_manager.verify_token(token, token_type="refresh")
        assert token_data.user_id == user_id
        assert token_data.username == username
        assert token_data.token_type == "refresh"
    
    def test_verify_valid_token(self, jwt_manager):
        """Test token verification with valid token"""
        user_id = "user123"
        username = "testuser"
        roles = ["trader"]
        
        token = jwt_manager.create_access_token(user_id, username, "test@example.com", roles, [])
        token_data = jwt_manager.verify_token(token)
        
        assert token_data.user_id == user_id
        assert token_data.username == username
        assert token_data.roles == roles
        assert token_data.token_type == "access"
    
    def test_verify_invalid_token(self, jwt_manager):
        """Test token verification with invalid token"""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(TokenError):
            jwt_manager.verify_token(invalid_token)
    
    def test_verify_expired_token(self, jwt_manager):
        """Test token verification with expired token"""
        # Create JWT manager with very short expiration
        short_jwt_manager = JWTManager(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=-1  # Already expired
        )
        
        token = short_jwt_manager.create_access_token("user123", "testuser", "test@example.com", [], [])
        
        with pytest.raises(TokenError):
            short_jwt_manager.verify_token(token)
    
    def test_refresh_access_token(self, jwt_manager):
        """Test access token refresh"""
        user_id = "user123"
        username = "testuser"
        
        refresh_token = jwt_manager.create_refresh_token(user_id, username)
        token_response = jwt_manager.refresh_access_token(refresh_token)
        
        assert isinstance(token_response, dict)
        assert "access_token" in token_response
        assert "refresh_token" in token_response
        assert "token_type" in token_response
        
        new_access_token = token_response["access_token"]
        assert isinstance(new_access_token, str)
        assert len(new_access_token) > 0
        
        # Verify new token is valid
        token_data = jwt_manager.verify_token(new_access_token)
        assert token_data.user_id == user_id
        assert token_data.username == username
        assert token_data.token_type == "access"
    
    def test_revoke_token(self, jwt_manager):
        """Test token revocation"""
        token = jwt_manager.create_access_token("user123", "testuser", "test@example.com", [], [])
        token_data = jwt_manager.verify_token(token)
        
        # Revoke token
        jwt_manager.revoke_token(token)
        
        # Verify token is revoked
        assert jwt_manager.is_token_revoked(token)
        
        # Verify revoked token raises exception
        with pytest.raises(TokenError):
            jwt_manager.verify_token(token)


class TestRBACManager:
    """Test Role-Based Access Control functionality"""
    
    @pytest.fixture
    def rbac_manager(self):
        """Create RBAC manager instance for testing"""
        manager = RBACManager()
        return manager
    
    def test_initialize_default_roles(self, rbac_manager):
        """Test default roles initialization"""
        # Check that default roles exist
        assert "super_admin" in rbac_manager.roles
        assert "trader" in rbac_manager.roles
        assert "analyst" in rbac_manager.roles
        assert "viewer" in rbac_manager.roles
        
        # Check admin has all permissions
        admin_permissions = rbac_manager.get_role_permissions("super_admin")
        assert len(admin_permissions) > 0
        assert Permission.MANAGE_USERS in admin_permissions
    
    def test_assign_user_role(self, rbac_manager):
        """Test user role assignment"""
        user_id = "user123"
        role = "trader"
        
        rbac_manager.assign_user_role(user_id, role)
        user_roles = rbac_manager.get_user_roles(user_id)
        
        assert role in user_roles
    
    def test_remove_user_role(self, rbac_manager):
        """Test user role removal"""
        user_id = "user123"
        role = "trader"
        
        # Assign then remove role
        rbac_manager.assign_user_role(user_id, role)
        rbac_manager.remove_user_role(user_id, role)
        
        user_roles = rbac_manager.get_user_roles(user_id)
        assert role not in user_roles
    
    def test_check_user_permission(self, rbac_manager):
        """Test user permission checking"""
        user_id = "user123"
        
        # Assign trader role
        rbac_manager.assign_user_role(user_id, "trader")
        
        # Check trader permissions
        assert rbac_manager.check_user_permission(user_id, Permission.CREATE_ORDERS)
        assert rbac_manager.check_user_permission(user_id, Permission.READ_ORDERS)
        
        # Check admin-only permission
        assert not rbac_manager.check_user_permission(user_id, Permission.MANAGE_USERS)
    
    def test_check_user_role(self, rbac_manager):
        """Test user role checking"""
        user_id = "user123"
        
        # Assign trader role
        rbac_manager.assign_user_role(user_id, "trader")
        
        # Check role
        assert rbac_manager.check_user_role(user_id, "trader")
        assert not rbac_manager.check_user_role(user_id, "super_admin")


class TestUserManager:
    """Test user management functionality"""
    
    @pytest.fixture
    def user_manager(self):
        """Create user manager instance for testing"""
        rbac_manager = RBACManager()
        # Default roles are automatically initialized in constructor
        
        jwt_manager = JWTManager(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7
        )
        
        return UserManager(rbac_manager, jwt_manager)
    
    def test_create_user(self, user_manager):
        """Test user creation"""
        request = UserCreateRequest(
            username="testuser",
            email="test@example.com",
            password="Password123",
            first_name="Test",
            last_name="User",
            roles=["trader"]
        )
        
        user = user_manager.create_user(request)
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.status == UserStatus.ACTIVE
        assert isinstance(user.user_id, str)
        assert len(user.user_id) > 0
    
    def test_create_duplicate_user(self, user_manager):
        """Test creating duplicate user raises exception"""
        request = UserCreateRequest(
            username="testuser",
            email="test@example.com",
            password="Password123"
        )
        
        # Create first user
        user_manager.create_user(request)
        
        # Try to create duplicate
        with pytest.raises(UserAlreadyExistsError):
            user_manager.create_user(request)
    
    def test_authenticate_user_success(self, user_manager):
        """Test successful user authentication"""
        # Create user
        request = UserCreateRequest(
            username="testuser",
            email="test@example.com",
            password="Password123"
        )
        user_manager.create_user(request)
        
        # Authenticate
        user, result = user_manager.authenticate_user(
            "testuser", "Password123", "127.0.0.1", "test-agent"
        )
        
        assert user is not None
        assert user.username == "testuser"
        assert result == LoginAttemptResult.SUCCESS
    
    def test_authenticate_user_invalid_credentials(self, user_manager):
        """Test authentication with invalid credentials"""
        # Create user
        request = UserCreateRequest(
            username="testuser",
            email="test@example.com",
            password="Password123"
        )
        user_manager.create_user(request)
        
        # Try invalid password
        user, result = user_manager.authenticate_user(
            "testuser", "wrongpassword", "127.0.0.1", "test-agent"
        )
        
        assert user is None
        assert result == LoginAttemptResult.INVALID_CREDENTIALS
    
    def test_authenticate_nonexistent_user(self, user_manager):
        """Test authentication with nonexistent user"""
        user, result = user_manager.authenticate_user(
            "nonexistent", "password123", "127.0.0.1", "test-agent"
        )
        
        assert user is None
        assert result == LoginAttemptResult.INVALID_CREDENTIALS
    
    def test_get_user_by_id(self, user_manager):
        """Test getting user by ID"""
        # Create user
        request = UserCreateRequest(
            username="testuser",
            email="test@example.com",
            password="Password123"
        )
        created_user = user_manager.create_user(request)
        
        # Get user by ID
        retrieved_user = user_manager.get_user_by_id(created_user.user_id)
        
        assert retrieved_user is not None
        assert retrieved_user.user_id == created_user.user_id
        assert retrieved_user.username == "testuser"
    
    def test_update_user(self, user_manager):
        """Test user profile update"""
        # Create user
        request = UserCreateRequest(
            username="testuser",
            email="test@example.com",
            password="Password123",
            first_name="Test",
            last_name="User"
        )
        user = user_manager.create_user(request)
        
        # Update user
        update_request = UserUpdateRequest(
            first_name="Updated",
            last_name="Name",
            email="updated@example.com"
        )
        updated_user = user_manager.update_user(user.user_id, update_request)
        
        assert updated_user.first_name == "Updated"
        assert updated_user.last_name == "Name"
        assert updated_user.email == "updated@example.com"
    
    def test_change_password(self, user_manager):
        """Test password change"""
        # Create user
        request = UserCreateRequest(
            username="testuser",
            email="test@example.com",
            password="OldPassword123"
        )
        user = user_manager.create_user(request)
        
        # Change password
        change_request = PasswordChangeRequest(
            current_password="OldPassword123",
            new_password="NewPassword123"
        )
        success = user_manager.change_password(user.user_id, change_request)
        
        assert success
        
        # Verify old password doesn't work
        user_auth, result = user_manager.authenticate_user(
            "testuser", "OldPassword123", "127.0.0.1", "test-agent"
        )
        assert result == LoginAttemptResult.INVALID_CREDENTIALS
        
        # Verify new password works
        user_auth, result = user_manager.authenticate_user(
            "testuser", "NewPassword123", "127.0.0.1", "test-agent"
        )
        assert result == LoginAttemptResult.SUCCESS


class TestJWTBearer:
    """Test JWT Bearer authentication middleware"""
    
    @pytest.fixture
    def jwt_bearer(self):
        """Create JWT Bearer instance for testing"""
        jwt_manager = JWTManager(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7
        )
        
        rbac_manager = RBACManager()
        # Default roles are automatically initialized in constructor
        
        return JWTBearer(jwt_manager, rbac_manager)
    
    @pytest.mark.asyncio
    async def test_valid_token_authentication(self, jwt_bearer):
        """Test authentication with valid token"""
        # Create valid token
        token = jwt_bearer.jwt_manager.create_access_token(
            "user123", "testuser", "test@example.com", ["trader"], ["read_portfolio"]
        )
        
        # Mock FastAPI Request object
        from fastapi import Request
        from fastapi.security import HTTPAuthorizationCredentials
        
        mock_request = Mock(spec=Request)
        mock_request.headers = {"authorization": f"Bearer {token}"}
        
        # Mock the parent HTTPBearer call to return credentials
        with patch.object(jwt_bearer.__class__.__bases__[0], '__call__', 
                         return_value=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)):
            token_data = await jwt_bearer(mock_request)
        
        assert token_data.user_id == "user123"
        assert token_data.username == "testuser"
        assert "trader" in token_data.roles
    
    @pytest.mark.asyncio
    async def test_missing_token_authentication(self, jwt_bearer):
        """Test authentication with missing token"""
        from fastapi import Request
        
        # Mock FastAPI Request object
        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        
        # Mock the parent HTTPBearer call to raise 403 (which should be converted to 401)
        with patch.object(jwt_bearer.__class__.__bases__[0], '__call__', 
                         side_effect=HTTPException(status_code=403, detail="Forbidden")):
            with pytest.raises(HTTPException) as exc_info:
                await jwt_bearer(mock_request)
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_invalid_token_authentication(self, jwt_bearer):
        """Test authentication with invalid token"""
        from fastapi import Request
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Mock FastAPI Request object
        mock_request = Mock(spec=Request)
        mock_request.headers = {"authorization": "Bearer invalid.token.here"}
        
        # Mock the parent HTTPBearer call to return invalid credentials
        with patch.object(jwt_bearer.__class__.__bases__[0], '__call__', 
                         return_value=HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.token.here")):
            with pytest.raises(HTTPException) as exc_info:
                await jwt_bearer(mock_request)
            assert exc_info.value.status_code == 401


class TestAuthenticationIntegration:
    """Integration tests for the complete authentication system"""
    
    @pytest.fixture
    def auth_system(self):
        """Create complete authentication system for testing"""
        jwt_manager = JWTManager(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7
        )
        
        rbac_manager = RBACManager()
        # Default roles are automatically initialized in constructor
        
        user_manager = UserManager(rbac_manager, jwt_manager)
        jwt_bearer = JWTBearer(jwt_manager, rbac_manager)
        
        return {
            "jwt_manager": jwt_manager,
            "rbac_manager": rbac_manager,
            "user_manager": user_manager,
            "jwt_bearer": jwt_bearer
        }
    
    def test_complete_user_workflow(self, auth_system):
        """Test complete user registration and authentication workflow"""
        user_manager = auth_system["user_manager"]
        rbac_manager = auth_system["rbac_manager"]
        jwt_manager = auth_system["jwt_manager"]
        
        # 1. Create user
        request = UserCreateRequest(
            username="trader1",
            email="trader1@example.com",
            password="Password123",
            first_name="John",
            last_name="Trader",
            roles=["trader"]
        )
        user = user_manager.create_user(request)
        
        # 2. Authenticate user
        auth_user, result = user_manager.authenticate_user(
            "trader1", "Password123", "127.0.0.1", "test-agent"
        )
        assert result == LoginAttemptResult.SUCCESS
        assert auth_user.user_id == user.user_id
        
        # 3. Generate tokens
        access_token = jwt_manager.create_access_token(
            user.user_id, user.username, user.email, ["trader"], ["read_portfolio"]
        )
        refresh_token = jwt_manager.create_refresh_token(
            user.user_id, user.username
        )
        
        # 4. Verify tokens
        access_token_data = jwt_manager.verify_token(access_token, "access")
        refresh_token_data = jwt_manager.verify_token(refresh_token, "refresh")
        
        assert access_token_data.user_id == user.user_id
        assert refresh_token_data.user_id == user.user_id
        
        # 5. Check permissions
        assert rbac_manager.check_user_permission(user.user_id, Permission.CREATE_ORDERS)
        assert rbac_manager.check_user_permission(user.user_id, Permission.READ_ORDERS)
        assert not rbac_manager.check_user_permission(user.user_id, Permission.MANAGE_USERS)
        
        # 6. Refresh access token
        token_response = jwt_manager.refresh_access_token(refresh_token)
        new_access_token = token_response["access_token"]
        new_token_data = jwt_manager.verify_token(new_access_token, "access")
        assert new_token_data.user_id == user.user_id
    
    def test_permission_based_access_control(self, auth_system):
        """Test permission-based access control"""
        user_manager = auth_system["user_manager"]
        rbac_manager = auth_system["rbac_manager"]
        
        # Create users with different roles
        admin_request = UserCreateRequest(
            username="test_admin",
            email="test_admin@example.com",
            password="Password123",
            roles=["super_admin"]
        )
        admin_user = user_manager.create_user(admin_request)
        
        trader_request = UserCreateRequest(
            username="trader",
            email="trader@example.com",
            password="Password123",
            roles=["trader"]
        )
        trader_user = user_manager.create_user(trader_request)
        
        viewer_request = UserCreateRequest(
            username="viewer",
            email="viewer@example.com",
            password="Password123",
            roles=["viewer"]
        )
        viewer_user = user_manager.create_user(viewer_request)
        
        # Test admin permissions
        assert rbac_manager.check_user_permission(admin_user.user_id, Permission.MANAGE_USERS)
        assert rbac_manager.check_user_permission(admin_user.user_id, Permission.CREATE_ORDERS)
        assert rbac_manager.check_user_permission(admin_user.user_id, Permission.VIEW_METRICS)
        
        # Test trader permissions
        assert not rbac_manager.check_user_permission(trader_user.user_id, Permission.MANAGE_USERS)
        assert rbac_manager.check_user_permission(trader_user.user_id, Permission.CREATE_ORDERS)
        assert rbac_manager.check_user_permission(trader_user.user_id, Permission.READ_ORDERS)
        
        # Test viewer permissions
        assert not rbac_manager.check_user_permission(viewer_user.user_id, Permission.MANAGE_USERS)
        assert not rbac_manager.check_user_permission(viewer_user.user_id, Permission.CREATE_ORDERS)
        assert rbac_manager.check_user_permission(viewer_user.user_id, Permission.READ_ORDERS)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])