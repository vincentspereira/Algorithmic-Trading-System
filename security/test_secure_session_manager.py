#!/usr/bin/env python3
"""
Tests for Secure Session Manager Implementation
"""

import unittest
import sys
import os
from datetime import datetime, timedelta

# Add the security directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from authentication_framework import AuthenticationManager, UserRole
from secure_session_manager import SecureSessionManager


class TestSecureSessionManager(unittest.TestCase):
    """Test cases for Secure Session Manager Implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.auth_manager = AuthenticationManager()
        self.secure_manager = SecureSessionManager(self.auth_manager)
        
        # Create test user
        self.test_user = self.auth_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="SecureTest123!",
            roles={UserRole.TRADER}
        )
    
    def test_create_secure_session(self):
        """Test creating secure session"""
        # Create session
        session = self.auth_manager.authenticate_user(
            username="testuser",
            password="SecureTest123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        
        # Create secure session
        access_token, refresh_token = self.secure_manager.create_secure_session(session)
        
        self.assertIsNotNone(access_token)
        self.assertIsNotNone(refresh_token)
        self.assertIn('.', access_token)
    
    def test_validate_secure_token(self):
        """Test validating secure token"""
        # Create session
        session = self.auth_manager.authenticate_user(
            username="testuser",
            password="SecureTest123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        
        # Create secure session
        access_token, refresh_token = self.secure_manager.create_secure_session(session)
        
        # Validate secure token
        validated_session = self.secure_manager.validate_secure_token(
            access_token, 
            "192.168.1.100"
        )
        
        self.assertIsNotNone(validated_session)
        self.assertEqual(validated_session.session_id, session.session_id)
        self.assertEqual(validated_session.user_id, session.user_id)
    
    def test_validate_secure_token_invalid_ip(self):
        """Test validating secure token with invalid IP"""
        # Create session
        session = self.auth_manager.authenticate_user(
            username="testuser",
            password="SecureTest123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        
        # Create secure session
        access_token, refresh_token = self.secure_manager.create_secure_session(session)
        
        # Validate secure token with different IP (should fail)
        validated_session = self.secure_manager.validate_secure_token(
            access_token, 
            "10.0.0.1"
        )
        
        self.assertIsNone(validated_session)
    
    def test_validate_expired_token(self):
        """Test validating expired secure token"""
        # Create session
        session = self.auth_manager.authenticate_user(
            username="testuser",
            password="SecureTest123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        
        # Create secure session
        access_token, refresh_token = self.secure_manager.create_secure_session(session)
        
        # Manually expire the token
        token_id = access_token.split('.')[0]
        secure_token = self.secure_manager.secure_tokens[token_id]
        secure_token.expires_at = datetime.now() - timedelta(hours=1)
        
        # Validate expired token (should fail)
        validated_session = self.secure_manager.validate_secure_token(
            access_token, 
            "192.168.1.100"
        )
        
        self.assertIsNone(validated_session)
    
    def test_refresh_secure_token(self):
        """Test refreshing secure token"""
        # Create session
        session = self.auth_manager.authenticate_user(
            username="testuser",
            password="SecureTest123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        
        # Create secure session
        access_token, refresh_token = self.secure_manager.create_secure_session(session)
        
        # Refresh token
        new_access_token, new_refresh_token = self.secure_manager.refresh_secure_token(refresh_token)
        
        self.assertIsNotNone(new_access_token)
        self.assertIsNotNone(new_refresh_token)
        self.assertNotEqual(access_token, new_access_token)
        self.assertNotEqual(refresh_token, new_refresh_token)
    
    def test_refresh_expired_token(self):
        """Test refreshing expired refresh token"""
        # Create session
        session = self.auth_manager.authenticate_user(
            username="testuser",
            password="SecureTest123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        
        # Create secure session
        access_token, refresh_token = self.secure_manager.create_secure_session(session)
        
        # Manually expire the refresh token
        token_id = access_token.split('.')[0]
        secure_token = self.secure_manager.secure_tokens[token_id]
        secure_token.refresh_expires_at = datetime.now() - timedelta(hours=1)
        
        # Try to refresh expired token (should fail)
        result = self.secure_manager.refresh_secure_token(refresh_token)
        
        self.assertIsNone(result)
    
    def test_revoke_secure_token(self):
        """Test revoking secure token"""
        # Create session
        session = self.auth_manager.authenticate_user(
            username="testuser",
            password="SecureTest123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        
        # Create secure session
        access_token, refresh_token = self.secure_manager.create_secure_session(session)
        
        # Verify token exists
        token_id = access_token.split('.')[0]
        self.assertIn(token_id, self.secure_manager.secure_tokens)
        self.assertIn(refresh_token, self.secure_manager.refresh_tokens)
        
        # Revoke token
        self.secure_manager.revoke_secure_token(access_token)
        
        # Verify token is revoked
        self.assertNotIn(token_id, self.secure_manager.secure_tokens)
        self.assertNotIn(refresh_token, self.secure_manager.refresh_tokens)
    
    def test_cleanup_expired_tokens(self):
        """Test cleaning up expired tokens"""
        # Create session
        session = self.auth_manager.authenticate_user(
            username="testuser",
            password="SecureTest123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        
        # Create secure session
        access_token, refresh_token = self.secure_manager.create_secure_session(session)
        
        # Manually expire the token
        token_id = access_token.split('.')[0]
        secure_token = self.secure_manager.secure_tokens[token_id]
        secure_token.expires_at = datetime.now() - timedelta(hours=1)
        
        # Verify token exists before cleanup
        self.assertIn(token_id, self.secure_manager.secure_tokens)
        self.assertIn(refresh_token, self.secure_manager.refresh_tokens)
        
        # Clean up expired tokens
        self.secure_manager.cleanup_expired_tokens()
        
        # Verify token is cleaned up
        self.assertNotIn(token_id, self.secure_manager.secure_tokens)
        self.assertNotIn(refresh_token, self.secure_manager.refresh_tokens)
    
    def test_session_metrics(self):
        """Test getting session metrics"""
        # Create session
        session = self.auth_manager.authenticate_user(
            username="testuser",
            password="SecureTest123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        
        # Create secure session
        access_token, refresh_token = self.secure_manager.create_secure_session(session)
        
        # Get metrics
        metrics = self.secure_manager.get_session_metrics()
        
        self.assertIsInstance(metrics, dict)
        self.assertIn("active_sessions", metrics)
        self.assertIn("secure_tokens", metrics)
        self.assertIn("refresh_tokens", metrics)
        self.assertGreater(metrics["active_sessions"], 0)
        self.assertGreater(metrics["secure_tokens"], 0)
        self.assertGreater(metrics["refresh_tokens"], 0)


def run_tests():
    """Run all secure session manager tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestSecureSessionManager))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)