"""Integration Tests for Authentication API Endpoints

Tests the FastAPI authentication endpoints with real HTTP requests.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

# Import the FastAPI app and authentication components
from services.order_management_service.src.main import app
from services.order_management_service.src.auth_api import router as auth_router
from shared.auth import (
    UserCreateRequest,
    UserUpdateRequest,
    PasswordChangeRequest,
    LoginRequest,
    TokenRefreshRequest,
    UserManager,
    JWTManager,
    RBACManager,
    UserStatus,
    LoginAttemptResult
)


class TestAuthAPIEndpoints:
    """Test authentication API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_auth_managers(self):
        """Mock authentication managers for testing"""
        jwt_manager = Mock(spec=JWTManager)
        rbac_manager = Mock(spec=RBACManager)
        user_manager = Mock(spec=UserManager)
        
        return {
            "jwt_manager": jwt_manager,
            "rbac_manager": rbac_manager,
            "user_manager": user_manager
        }
    
    def test_register_user_success(self, client, mock_auth_managers):
        """Test successful user registration"""
        with patch('services.order_management_service.src.main.user_manager', mock_auth_managers["user_manager"]):
            # Mock successful user creation
            mock_user = Mock()
            mock_user.user_id = "user123"
            mock_user.username = "testuser"
            mock_user.email = "test@example.com"
            mock_user.first_name = "Test"
            mock_user.last_name = "User"
            mock_user.status = UserStatus.ACTIVE
            mock_user.created_at = "2024-01-01T00:00:00Z"
            
            mock_auth_managers["user_manager"].create_user.return_value = mock_user
            
            # Test registration
            response = client.post("/auth/register", json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123",
                "first_name": "Test",
                "last_name": "User",
                "roles": ["trader"]
            })
            
            assert response.status_code == 201
            data = response.json()
            assert data["message"] == "User registered successfully"
            assert data["user"]["username"] == "testuser"
            assert data["user"]["email"] == "test@example.com"
    
    def test_register_user_duplicate(self, client, mock_auth_managers):
        """Test user registration with duplicate username"""
        with patch('services.order_management_service.src.main.user_manager', mock_auth_managers["user_manager"]):
            from shared.auth.exceptions import UserAlreadyExistsError
            
            # Mock duplicate user error
            mock_auth_managers["user_manager"].create_user.side_effect = UserAlreadyExistsError("Username already exists")
            
            # Test registration
            response = client.post("/auth/register", json={
                "username": "existinguser",
                "email": "test@example.com",
                "password": "password123"
            })
            
            assert response.status_code == 409
            data = response.json()
            assert "already exists" in data["detail"].lower()
    
    def test_login_success(self, client, mock_auth_managers):
        """Test successful user login"""
        with patch('services.order_management_service.src.main.user_manager', mock_auth_managers["user_manager"]), \
             patch('services.order_management_service.src.main.jwt_manager', mock_auth_managers["jwt_manager"]):
            
            # Mock successful authentication
            mock_user = Mock()
            mock_user.user_id = "user123"
            mock_user.username = "testuser"
            mock_user.email = "test@example.com"
            
            mock_auth_managers["user_manager"].authenticate_user.return_value = (
                mock_user, LoginAttemptResult.SUCCESS
            )
            mock_auth_managers["user_manager"].get_user_roles.return_value = ["trader"]
            
            # Mock token generation
            mock_auth_managers["jwt_manager"].create_access_token.return_value = "access_token_123"
            mock_auth_managers["jwt_manager"].create_refresh_token.return_value = "refresh_token_123"
            
            # Test login
            response = client.post("/auth/login", json={
                "username": "testuser",
                "password": "password123"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "access_token_123"
            assert data["refresh_token"] == "refresh_token_123"
            assert data["token_type"] == "bearer"
            assert data["user"]["username"] == "testuser"
    
    def test_login_invalid_credentials(self, client, mock_auth_managers):
        """Test login with invalid credentials"""
        with patch('services.order_management_service.src.main.user_manager', mock_auth_managers["user_manager"]):
            # Mock failed authentication
            mock_auth_managers["user_manager"].authenticate_user.return_value = (
                None, LoginAttemptResult.INVALID_CREDENTIALS
            )
            
            # Test login
            response = client.post("/auth/login", json={
                "username": "testuser",
                "password": "wrongpassword"
            })
            
            assert response.status_code == 401
            data = response.json()
            assert "invalid credentials" in data["detail"].lower()
    
    def test_refresh_token_success(self, client, mock_auth_managers):
        """Test successful token refresh"""
        with patch('services.order_management_service.src.main.jwt_manager', mock_auth_managers["jwt_manager"]):
            # Mock successful token refresh
            mock_auth_managers["jwt_manager"].refresh_access_token.return_value = "new_access_token_123"
            
            # Test token refresh
            response = client.post("/auth/refresh", json={
                "refresh_token": "valid_refresh_token"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "new_access_token_123"
            assert data["token_type"] == "bearer"
    
    def test_refresh_token_invalid(self, client, mock_auth_managers):
        """Test token refresh with invalid token"""
        with patch('services.order_management_service.src.main.jwt_manager', mock_auth_managers["jwt_manager"]):
            from shared.auth.exceptions import InvalidTokenError
            
            # Mock invalid token error
            mock_auth_managers["jwt_manager"].refresh_access_token.side_effect = InvalidTokenError("Invalid refresh token")
            
            # Test token refresh
            response = client.post("/auth/refresh", json={
                "refresh_token": "invalid_refresh_token"
            })
            
            assert response.status_code == 401
            data = response.json()
            assert "invalid" in data["detail"].lower()
    
    def test_logout_success(self, client, mock_auth_managers):
        """Test successful logout"""
        with patch('services.order_management_service.src.main.jwt_manager', mock_auth_managers["jwt_manager"]):
            # Mock token data
            mock_token_data = Mock()
            mock_token_data.jti = "token_jti_123"
            
            # Mock JWT bearer dependency
            with patch('services.order_management_service.src.auth_api.jwt_bearer') as mock_jwt_bearer:
                mock_jwt_bearer.return_value = mock_token_data
                
                # Test logout
                response = client.post("/auth/logout", headers={
                    "Authorization": "Bearer valid_token"
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Successfully logged out"
                
                # Verify token was revoked
                mock_auth_managers["jwt_manager"].revoke_token.assert_called_once_with("token_jti_123")
    
    def test_get_profile_success(self, client, mock_auth_managers):
        """Test successful profile retrieval"""
        with patch('services.order_management_service.src.main.user_manager', mock_auth_managers["user_manager"]):
            # Mock user data
            mock_user = Mock()
            mock_user.user_id = "user123"
            mock_user.username = "testuser"
            mock_user.email = "test@example.com"
            mock_user.first_name = "Test"
            mock_user.last_name = "User"
            mock_user.status = UserStatus.ACTIVE
            mock_user.created_at = "2024-01-01T00:00:00Z"
            
            mock_auth_managers["user_manager"].get_user_by_id.return_value = mock_user
            mock_auth_managers["user_manager"].get_user_roles.return_value = ["trader"]
            
            # Mock token data
            mock_token_data = Mock()
            mock_token_data.user_id = "user123"
            
            # Mock JWT bearer dependency
            with patch('services.order_management_service.src.auth_api.jwt_bearer') as mock_jwt_bearer:
                mock_jwt_bearer.return_value = mock_token_data
                
                # Test profile retrieval
                response = client.get("/auth/profile", headers={
                    "Authorization": "Bearer valid_token"
                })
                
                assert response.status_code == 200
                data = response.json()
                assert data["username"] == "testuser"
                assert data["email"] == "test@example.com"
                assert "trader" in data["roles"]
    
    def test_update_profile_success(self, client, mock_auth_managers):
        """Test successful profile update"""
        with patch('services.order_management_service.src.main.user_manager', mock_auth_managers["user_manager"]):
            # Mock updated user data
            mock_updated_user = Mock()
            mock_updated_user.user_id = "user123"
            mock_updated_user.username = "testuser"
            mock_updated_user.email = "updated@example.com"
            mock_updated_user.first_name = "Updated"
            mock_updated_user.last_name = "User"
            mock_updated_user.status = UserStatus.ACTIVE
            
            mock_auth_managers["user_manager"].update_user.return_value = mock_updated_user
            
            # Mock token data
            mock_token_data = Mock()
            mock_token_data.user_id = "user123"
            
            # Mock JWT bearer dependency
            with patch('services.order_management_service.src.auth_api.jwt_bearer') as mock_jwt_bearer:
                mock_jwt_bearer.return_value = mock_token_data
                
                # Test profile update
                response = client.put("/auth/profile", 
                    headers={"Authorization": "Bearer valid_token"},
                    json={
                        "first_name": "Updated",
                        "email": "updated@example.com"
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Profile updated successfully"
                assert data["user"]["first_name"] == "Updated"
                assert data["user"]["email"] == "updated@example.com"
    
    def test_change_password_success(self, client, mock_auth_managers):
        """Test successful password change"""
        with patch('services.order_management_service.src.main.user_manager', mock_auth_managers["user_manager"]):
            # Mock successful password change
            mock_auth_managers["user_manager"].change_password.return_value = True
            
            # Mock token data
            mock_token_data = Mock()
            mock_token_data.user_id = "user123"
            
            # Mock JWT bearer dependency
            with patch('services.order_management_service.src.auth_api.jwt_bearer') as mock_jwt_bearer:
                mock_jwt_bearer.return_value = mock_token_data
                
                # Test password change
                response = client.post("/auth/change-password",
                    headers={"Authorization": "Bearer valid_token"},
                    json={
                        "current_password": "oldpassword",
                        "new_password": "newpassword123"
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Password changed successfully"
    
    def test_validate_token_success(self, client, mock_auth_managers):
        """Test successful token validation"""
        with patch('services.order_management_service.src.main.jwt_manager', mock_auth_managers["jwt_manager"]):
            # Mock token data
            mock_token_data = Mock()
            mock_token_data.user_id = "user123"
            mock_token_data.username = "testuser"
            mock_token_data.roles = ["trader"]
            mock_token_data.exp = 1234567890
            
            mock_auth_managers["jwt_manager"].verify_token.return_value = mock_token_data
            
            # Test token validation
            response = client.post("/auth/validate-token", json={
                "token": "valid_token_123"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["user_id"] == "user123"
            assert data["username"] == "testuser"
            assert "trader" in data["roles"]
    
    def test_validate_token_invalid(self, client, mock_auth_managers):
        """Test token validation with invalid token"""
        with patch('services.order_management_service.src.main.jwt_manager', mock_auth_managers["jwt_manager"]):
            from shared.auth.exceptions import InvalidTokenError
            
            # Mock invalid token error
            mock_auth_managers["jwt_manager"].verify_token.side_effect = InvalidTokenError("Invalid token")
            
            # Test token validation
            response = client.post("/auth/validate-token", json={
                "token": "invalid_token_123"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert "error" in data
    
    def test_health_check(self, client):
        """Test authentication service health check"""
        response = client.get("/auth/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "authentication"
        assert "timestamp" in data


class TestAuthenticationMiddleware:
    """Test authentication middleware integration"""
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app"""
        return TestClient(app)
    
    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get("/orders")
        
        # Should return 401 Unauthorized
        assert response.status_code == 401
    
    def test_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token"""
        response = client.get("/orders", headers={
            "Authorization": "Bearer invalid_token"
        })
        
        # Should return 401 Unauthorized
        assert response.status_code == 401
    
    def test_protected_endpoint_with_valid_token(self, client):
        """Test accessing protected endpoint with valid token"""
        with patch('services.order_management_service.src.main.jwt_manager') as mock_jwt_manager, \
             patch('services.order_management_service.src.main.rbac_manager') as mock_rbac_manager:
            
            # Mock token verification
            mock_token_data = Mock()
            mock_token_data.user_id = "user123"
            mock_token_data.username = "testuser"
            mock_token_data.roles = ["trader"]
            mock_token_data.jti = "token_jti"
            
            mock_jwt_manager.verify_token.return_value = mock_token_data
            mock_jwt_manager.is_token_revoked.return_value = False
            
            # Mock permission check
            mock_rbac_manager.check_user_permission.return_value = True
            
            # Mock JWT bearer middleware
            with patch('shared.auth.middleware.JWTBearer.__call__') as mock_jwt_bearer:
                mock_jwt_bearer.return_value = mock_token_data
                
                response = client.get("/orders", headers={
                    "Authorization": "Bearer valid_token"
                })
                
                # Should return 200 OK (or appropriate response for orders endpoint)
                # The exact status code depends on the orders endpoint implementation
                assert response.status_code in [200, 404]  # 404 if no orders found


if __name__ == "__main__":
    pytest.main([__file__, "-v"])