#!/usr/bin/env python3
"""
Comprehensive tests for OAuth2/OpenID Connect implementation
"""

import unittest
import sys
import os
from datetime import datetime, timedelta

# Add the security directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from oauth2_oidc_provider import OAuth2OIDCProvider, OAuth2Client, OIDCUserInfo
from oauth2_oidc_middleware import OAuth2Middleware, OIDCMiddleware
from authentication_framework import AuthenticationManager, UserRole, Permission


class TestOAuth2OIDCProvider(unittest.TestCase):
    """Test cases for OAuth2/OIDC Provider"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.issuer = "https://test.example.com"
        self.provider = OAuth2OIDCProvider(self.issuer)
        
        # Register a test client
        self.client_data = {
            "client_name": "Test Client",
            "redirect_uris": ["https://test.example.com/callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "scopes": ["openid", "profile", "email"]
        }
        self.client = self.provider.register_client(self.client_data)
        
        # Set up user info
        self.user_info = OIDCUserInfo(
            sub="user123",
            name="Test User",
            email="test@example.com",
            email_verified=True
        )
        self.provider.set_user_info("user123", self.user_info)
    
    def test_client_registration(self):
        """Test OAuth2 client registration"""
        self.assertIsInstance(self.client, OAuth2Client)
        self.assertEqual(self.client.client_name, "Test Client")
        self.assertTrue(self.client.client_id)
        self.assertTrue(self.client.client_secret)
        self.assertTrue(self.client.is_active)
    
    def test_client_authentication(self):
        """Test OAuth2 client authentication"""
        # Valid authentication
        result = self.provider.authenticate_client(
            self.client.client_id, 
            self.client.client_secret
        )
        self.assertTrue(result)
        
        # Invalid client ID
        result = self.provider.authenticate_client(
            "invalid_client_id", 
            self.client.client_secret
        )
        self.assertFalse(result)
    
    def test_authorization_code_flow(self):
        """Test OAuth2 authorization code flow"""
        # Create authorization code
        auth_code = self.provider.create_authorization_code(
            client_id=self.client.client_id,
            user_id="user123",
            redirect_uri="https://test.example.com/callback",
            scopes=["openid", "profile"]
        )
        self.assertTrue(auth_code)
        
        # Exchange for tokens
        token = self.provider.exchange_authorization_code(
            code=auth_code,
            client_id=self.client.client_id,
            client_secret=self.client.client_secret,
            redirect_uri="https://test.example.com/callback"
        )
        
        self.assertTrue(token.access_token)
        self.assertTrue(token.refresh_token)
        self.assertEqual(token.user_id, "user123")
        self.assertIn("openid", token.scopes)
    
    def test_token_refresh(self):
        """Test token refresh functionality"""
        # Create authorization code and exchange for tokens
        auth_code = self.provider.create_authorization_code(
            client_id=self.client.client_id,
            user_id="user123",
            redirect_uri="https://test.example.com/callback",
            scopes=["openid", "profile"]
        )
        
        token = self.provider.exchange_authorization_code(
            code=auth_code,
            client_id=self.client.client_id,
            client_secret=self.client.client_secret,
            redirect_uri="https://test.example.com/callback"
        )
        
        # Refresh token
        new_token = self.provider.refresh_access_token(
            refresh_token=token.refresh_token,
            client_id=self.client.client_id,
            client_secret=self.client.client_secret
        )
        
        self.assertTrue(new_token.access_token)
        self.assertTrue(new_token.refresh_token)
        self.assertNotEqual(token.access_token, new_token.access_token)
    
    def test_token_validation(self):
        """Test token validation"""
        # Create and exchange tokens
        auth_code = self.provider.create_authorization_code(
            client_id=self.client.client_id,
            user_id="user123",
            redirect_uri="https://test.example.com/callback",
            scopes=["openid", "profile"]
        )
        
        token = self.provider.exchange_authorization_code(
            code=auth_code,
            client_id=self.client.client_id,
            client_secret=self.client.client_secret,
            redirect_uri="https://test.example.com/callback"
        )
        
        # Validate token
        validated_token = self.provider.validate_access_token(token.access_token)
        self.assertIsNotNone(validated_token)
        self.assertEqual(validated_token.access_token, token.access_token)
    
    def test_token_revocation(self):
        """Test token revocation"""
        # Create and exchange tokens
        auth_code = self.provider.create_authorization_code(
            client_id=self.client.client_id,
            user_id="user123",
            redirect_uri="https://test.example.com/callback",
            scopes=["openid", "profile"]
        )
        
        token = self.provider.exchange_authorization_code(
            code=auth_code,
            client_id=self.client.client_id,
            client_secret=self.client.client_secret,
            redirect_uri="https://test.example.com/callback"
        )
        
        # Revoke token
        self.provider.revoke_token(
            token_value=token.access_token,
            client_id=self.client.client_id,
            client_secret=self.client.client_secret
        )
        
        # Try to validate revoked token
        validated_token = self.provider.validate_access_token(token.access_token)
        self.assertIsNone(validated_token)
    
    def test_user_info_retrieval(self):
        """Test OpenID Connect user info retrieval"""
        # Create and exchange tokens
        auth_code = self.provider.create_authorization_code(
            client_id=self.client.client_id,
            user_id="user123",
            redirect_uri="https://test.example.com/callback",
            scopes=["openid", "profile"]
        )
        
        token = self.provider.exchange_authorization_code(
            code=auth_code,
            client_id=self.client.client_id,
            client_secret=self.client.client_secret,
            redirect_uri="https://test.example.com/callback"
        )
        
        # Get user info
        user_info = self.provider.get_user_info(token.access_token)
        self.assertIsNotNone(user_info)
        self.assertEqual(user_info.sub, "user123")
        self.assertEqual(user_info.name, "Test User")
        self.assertEqual(user_info.email, "test@example.com")


class TestOAuth2Middleware(unittest.TestCase):
    """Test cases for OAuth2 Middleware"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.auth_manager = AuthenticationManager()
        self.provider = OAuth2OIDCProvider("https://test.example.com")
        self.middleware = OAuth2Middleware(self.auth_manager, self.provider)
        
        # Register a test client
        self.client_data = {
            "client_name": "Test Client",
            "redirect_uris": ["https://test.example.com/callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "scopes": ["openid", "profile", "email"]
        }
        self.client = self.provider.register_client(self.client_data)
        
        # Create a test user
        self.user = self.auth_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="SecurePassword123!",
            roles={UserRole.TRADER}
        )
        
        # Set up user info
        self.user_info = OIDCUserInfo(
            sub=self.user.user_id,
            name="Test User",
            email="test@example.com",
            email_verified=True
        )
        self.provider.set_user_info(self.user.user_id, self.user_info)
    
    def test_oauth2_session_creation(self):
        """Test OAuth2 session creation"""
        # Create authorization code and exchange for tokens
        auth_code = self.provider.create_authorization_code(
            client_id=self.client.client_id,
            user_id=self.user.user_id,
            redirect_uri="https://test.example.com/callback",
            scopes=["openid", "profile"]
        )
        
        token = self.provider.exchange_authorization_code(
            code=auth_code,
            client_id=self.client.client_id,
            client_secret=self.client.client_secret,
            redirect_uri="https://test.example.com/callback"
        )
        
        # Create OAuth2 session
        session_id = self.middleware.create_oauth2_session(
            access_token=token.access_token,
            user_id=self.user.user_id,
            client_id=self.client.client_id,
            scopes=token.scopes
        )
        
        self.assertTrue(session_id)
        self.assertIn(session_id, self.middleware.oauth2_sessions)
    
    def test_oauth2_session_validation(self):
        """Test OAuth2 session validation"""
        # Create authorization code and exchange for tokens
        auth_code = self.provider.create_authorization_code(
            client_id=self.client.client_id,
            user_id=self.user.user_id,
            redirect_uri="https://test.example.com/callback",
            scopes=["openid", "profile"]
        )
        
        token = self.provider.exchange_authorization_code(
            code=auth_code,
            client_id=self.client.client_id,
            client_secret=self.client.client_secret,
            redirect_uri="https://test.example.com/callback"
        )
        
        # Create OAuth2 session
        session_id = self.middleware.create_oauth2_session(
            access_token=token.access_token,
            user_id=self.user.user_id,
            client_id=self.client.client_id,
            scopes=token.scopes
        )
        
        # Validate session
        oauth2_session = self.middleware.validate_oauth2_session(session_id)
        self.assertIsNotNone(oauth2_session)
        self.assertEqual(oauth2_session.user_id, self.user.user_id)
    
    def test_user_retrieval_from_oauth2_session(self):
        """Test user retrieval from OAuth2 session"""
        # Create authorization code and exchange for tokens
        auth_code = self.provider.create_authorization_code(
            client_id=self.client.client_id,
            user_id=self.user.user_id,
            redirect_uri="https://test.example.com/callback",
            scopes=["openid", "profile"]
        )
        
        token = self.provider.exchange_authorization_code(
            code=auth_code,
            client_id=self.client.client_id,
            client_secret=self.client.client_secret,
            redirect_uri="https://test.example.com/callback"
        )
        
        # Create OAuth2 session
        session_id = self.middleware.create_oauth2_session(
            access_token=token.access_token,
            user_id=self.user.user_id,
            client_id=self.client.client_id,
            scopes=token.scopes
        )
        
        # Get user from session
        user = self.middleware.get_user_from_oauth2_session(session_id)
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, self.user.user_id)
        self.assertEqual(user.username, "testuser")


class TestOIDCMiddleware(unittest.TestCase):
    """Test cases for OIDC Middleware"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.provider = OAuth2OIDCProvider("https://test.example.com")
        self.middleware = OIDCMiddleware(self.provider)
        self.auth_manager = AuthenticationManager()
        
        # Register a test client
        self.client_data = {
            "client_name": "Test Client",
            "redirect_uris": ["https://test.example.com/callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "scopes": ["openid", "profile", "email"]
        }
        self.client = self.provider.register_client(self.client_data)
        
        # Set up user info
        self.user_info = OIDCUserInfo(
            sub="oidc_user_123",
            name="OIDC Test User",
            email="oidc_test@example.com",
            email_verified=True
        )
        self.provider.set_user_info("oidc_user_123", self.user_info)
    
    def test_user_info_retrieval(self):
        """Test user info retrieval from OIDC"""
        # Create authorization code and exchange for tokens
        auth_code = self.provider.create_authorization_code(
            client_id=self.client.client_id,
            user_id="oidc_user_123",
            redirect_uri="https://test.example.com/callback",
            scopes=["openid", "profile", "email"]
        )
        
        token = self.provider.exchange_authorization_code(
            code=auth_code,
            client_id=self.client.client_id,
            client_secret=self.client.client_secret,
            redirect_uri="https://test.example.com/callback"
        )
        
        # Get user info
        user_info = self.middleware.get_user_info(token.access_token)
        self.assertIsNotNone(user_info)
        self.assertEqual(user_info["sub"], "oidc_user_123")
        self.assertEqual(user_info["name"], "OIDC Test User")
        self.assertEqual(user_info["email"], "oidc_test@example.com")
    
    def test_user_creation_from_oidc(self):
        """Test user creation from OIDC user info"""
        # Create authorization code and exchange for tokens
        auth_code = self.provider.create_authorization_code(
            client_id=self.client.client_id,
            user_id="oidc_user_123",
            redirect_uri="https://test.example.com/callback",
            scopes=["openid", "profile", "email"]
        )
        
        token = self.provider.exchange_authorization_code(
            code=auth_code,
            client_id=self.client.client_id,
            client_secret=self.client.client_secret,
            redirect_uri="https://test.example.com/callback"
        )
        
        # Create user from OIDC
        user = self.middleware.create_user_from_oidc(token.access_token, self.auth_manager)
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "oidc_test@example.com")
        # Check that OIDC sub is stored in metadata
        self.assertEqual(user.metadata.get("oidc_sub"), "oidc_user_123")


def run_tests():
    """Run all OAuth2/OIDC tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestOAuth2OIDCProvider))
    suite.addTests(loader.loadTestsFromTestCase(TestOAuth2Middleware))
    suite.addTests(loader.loadTestsFromTestCase(TestOIDCMiddleware))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)