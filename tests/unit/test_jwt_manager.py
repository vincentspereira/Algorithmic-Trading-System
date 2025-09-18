"""Unit tests for JWT manager."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import jwt
import secrets

from shared.auth.jwt_manager import JWTManager
from shared.auth.exceptions import (
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError
)


class TestJWTManager:
    """Test JWT manager functionality"""
    
    @pytest.fixture
    def jwt_manager(self):
        """Create JWT manager instance for testing"""
        return JWTManager(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7
        )
    
    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for token creation"""
        return {
            "user_id": "123",
            "username": "testuser",
            "email": "test@example.com",
            "roles": ["user", "admin"],
            "permissions": ["read", "write"]
        }
    
    def test_jwt_manager_initialization_with_secret(self):
        """Test JWT manager initialization with provided secret"""
        secret = "my-secret-key"
        manager = JWTManager(secret_key=secret)
        
        assert manager.secret_key == secret
        assert manager.algorithm == "HS256"
        assert manager.access_token_expire_delta == timedelta(minutes=30)
        assert manager.refresh_token_expire_delta == timedelta(days=7)
    
    def test_jwt_manager_initialization_without_secret(self):
        """Test JWT manager initialization without secret (auto-generated)"""
        with patch('secrets.token_urlsafe') as mock_token:
            mock_token.return_value = "generated-secret"
            manager = JWTManager()
            
            assert manager.secret_key == "generated-secret"
            mock_token.assert_called_once_with(32)
    
    def test_create_access_token_default_expiry(self, jwt_manager, sample_user_data):
        """Test creating access token with default expiry"""
        token = jwt_manager.create_access_token(**sample_user_data)
        
        # Decode token to verify contents
        payload = jwt.decode(token, jwt_manager.secret_key, algorithms=["HS256"])
        
        assert payload["user_id"] == "123"
        assert payload["username"] == "testuser"
        assert payload["email"] == "test@example.com"
        assert payload["roles"] == ["user", "admin"]
        assert payload["permissions"] == ["read", "write"]
        assert payload["token_type"] == "access"
        assert "jti" in payload
        assert "iat" in payload
        assert "exp" in payload
    
    def test_create_access_token_custom_expiry(self, jwt_manager, sample_user_data):
        """Test creating access token with custom expiry"""
        custom_delta = timedelta(hours=2)
        token = jwt_manager.create_access_token(
            expires_delta=custom_delta,
            **sample_user_data
        )
        
        payload = jwt.decode(token, jwt_manager.secret_key, algorithms=["HS256"])
        
        # Check that expiry is approximately 2 hours from now
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_exp = datetime.now(timezone.utc) + custom_delta
        
        # Allow 1 minute tolerance
        assert abs((exp_time - expected_exp).total_seconds()) < 60
    
    def test_create_refresh_token(self, jwt_manager, sample_user_data):
        """Test creating refresh token"""
        token = jwt_manager.create_refresh_token(
            sample_user_data["user_id"],
            sample_user_data["username"]
        )
        
        payload = jwt.decode(token, jwt_manager.secret_key, algorithms=["HS256"])
        
        assert payload["user_id"] == "123"
        assert payload["username"] == "testuser"
        assert payload["token_type"] == "refresh"
        assert "jti" in payload
        assert "iat" in payload
        assert "exp" in payload
    
    def test_verify_token_valid(self, jwt_manager, sample_user_data):
        """Test verifying valid token"""
        token = jwt_manager.create_access_token(**sample_user_data)
        
        token_data = jwt_manager.verify_token(token)
        
        assert token_data.user_id == "123"
        assert token_data.username == "testuser"
    
    def test_verify_token_expired(self, jwt_manager, sample_user_data):
        """Test verifying expired token"""
        # Create token that expires immediately
        expired_delta = timedelta(seconds=-1)
        token = jwt_manager.create_access_token(
            expires_delta=expired_delta,
            **sample_user_data
        )
        
        with pytest.raises(TokenError, match="Token has expired"):
            jwt_manager.verify_token(token)
    
    def test_verify_token_invalid_signature(self, jwt_manager, sample_user_data):
        """Test verifying token with invalid signature"""
        # Create token with different secret
        other_manager = JWTManager(secret_key="different-secret")
        token = other_manager.create_access_token(**sample_user_data)
        
        with pytest.raises(TokenError, match="Invalid token"):
            jwt_manager.verify_token(token)
    
    def test_verify_token_malformed(self, jwt_manager):
        """Test verifying malformed token"""
        with pytest.raises(TokenError, match="Invalid token"):
            jwt_manager.verify_token("invalid.token.format")
    
    def test_verify_token_revoked(self, jwt_manager, sample_user_data):
        """Test verifying revoked token"""
        token = jwt_manager.create_access_token(**sample_user_data)
        
        # Revoke the token
        jwt_manager.revoke_token(token)
        
        with pytest.raises(TokenError, match="Token has been revoked"):
            jwt_manager.verify_token(token)
    
    def test_refresh_token_valid(self, jwt_manager, sample_user_data):
        """Test refreshing valid refresh token"""
        refresh_token = jwt_manager.create_refresh_token(
            sample_user_data["user_id"],
            sample_user_data["username"]
        )
        
        result = jwt_manager.refresh_access_token(refresh_token)
        
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"
        
        # Verify new tokens are valid
        access_token_data = jwt_manager.verify_token(result["access_token"])
        assert access_token_data.user_id == "123"
    
    def test_refresh_token_invalid(self, jwt_manager, sample_user_data):
        """Test refreshing invalid token"""
        with pytest.raises(TokenError):
            jwt_manager.refresh_access_token("invalid.token")
    
    def test_refresh_token_access_type(self, jwt_manager, sample_user_data):
        """Test refreshing access token (should fail)"""
        access_token = jwt_manager.create_access_token(**sample_user_data)
        
        with pytest.raises(TokenError):
            jwt_manager.refresh_access_token(access_token)
    
    def test_refresh_token_exception_handling(self, jwt_manager, sample_user_data):
        """Test refresh token exception handling"""
        refresh_token = jwt_manager.create_refresh_token(
            sample_user_data["user_id"],
            sample_user_data["username"]
        )
        
        # Mock jwt.decode to raise an exception
        with patch('jwt.decode') as mock_decode:
            mock_decode.side_effect = Exception("Decode error")
            
            with pytest.raises(TokenError):
                jwt_manager.refresh_access_token(refresh_token)
    
    def test_revoke_token_valid(self, jwt_manager, sample_user_data):
        """Test revoking valid token"""
        token = jwt_manager.create_access_token(**sample_user_data)
        
        # Token should not be revoked initially
        assert not jwt_manager.is_token_revoked(token)
        
        # Revoke token
        jwt_manager.revoke_token(token)
        
        # Token should now be revoked
        assert jwt_manager.is_token_revoked(token)
    
    def test_revoke_token_invalid(self, jwt_manager):
        """Test revoking invalid token (should not raise exception)"""
        # Should not raise exception
        jwt_manager.revoke_token("invalid.token")
    
    def test_revoke_token_expired(self, jwt_manager, sample_user_data):
        """Test revoking expired token"""
        # Create expired token
        expired_delta = timedelta(seconds=-1)
        token = jwt_manager.create_access_token(
            expires_delta=expired_delta,
            **sample_user_data
        )
        
        # Should be able to revoke expired token
        jwt_manager.revoke_token(token)
        assert jwt_manager.is_token_revoked(token)
    
    def test_is_token_revoked_invalid_token(self, jwt_manager):
        """Test checking revocation status of invalid token"""
        # Invalid tokens should be considered revoked
        assert jwt_manager.is_token_revoked("invalid.token")
    
    def test_get_token_claims_valid(self, jwt_manager, sample_user_data):
        """Test getting token claims from valid token"""
        token = jwt_manager.create_access_token(**sample_user_data)
        
        claims = jwt_manager.get_token_claims(token)
        
        assert claims["user_id"] == "123"
        assert claims["username"] == "testuser"
        assert claims["token_type"] == "access"
    
    def test_get_token_claims_invalid(self, jwt_manager):
        """Test getting claims from invalid token"""
        with pytest.raises(TokenError, match="Cannot decode token"):
            jwt_manager.get_token_claims("completely.invalid.token")
    
    def test_get_token_claims_expired(self, jwt_manager, sample_user_data):
        """Test getting claims from expired token (should still work)"""
        # Create expired token
        expired_delta = timedelta(seconds=-1)
        token = jwt_manager.create_access_token(
            expires_delta=expired_delta,
            **sample_user_data
        )
        
        # Should still be able to get claims without verification
        claims = jwt_manager.get_token_claims(token)
        assert claims["user_id"] == "123"
    
    def test_token_jti_uniqueness(self, jwt_manager, sample_user_data):
        """Test that each token gets a unique JTI"""
        token1 = jwt_manager.create_access_token(**sample_user_data)
        token2 = jwt_manager.create_access_token(**sample_user_data)
        
        payload1 = jwt.decode(token1, jwt_manager.secret_key, algorithms=["HS256"])
        payload2 = jwt.decode(token2, jwt_manager.secret_key, algorithms=["HS256"])
        
        assert payload1["jti"] != payload2["jti"]
    
    def test_revoked_tokens_persistence(self, jwt_manager, sample_user_data):
        """Test that revoked tokens remain revoked"""
        token1 = jwt_manager.create_access_token(**sample_user_data)
        token2 = jwt_manager.create_access_token(**sample_user_data)
        
        # Revoke first token
        jwt_manager.revoke_token(token1)
        
        # First should be revoked, second should not
        assert jwt_manager.is_token_revoked(token1)
        assert not jwt_manager.is_token_revoked(token2)
        
        # Revoke second token
        jwt_manager.revoke_token(token2)
        
        # Both should now be revoked
        assert jwt_manager.is_token_revoked(token1)
        assert jwt_manager.is_token_revoked(token2)