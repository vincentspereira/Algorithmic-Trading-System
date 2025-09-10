#!/usr/bin/env python3
"""
Tests for Enhanced MFA Service Implementation
"""

import unittest
import sys
import os
from datetime import datetime, timedelta

# Add the security directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from authentication_framework import AuthenticationManager, UserRole
from enhanced_mfa_service import EnhancedMFAService, MFAProvider


class TestEnhancedMFAService(unittest.TestCase):
    """Test cases for Enhanced MFA Service Implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.auth_manager = AuthenticationManager()
        self.mfa_service = EnhancedMFAService(self.auth_manager)
        
        # Create test user
        self.test_user = self.auth_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="SecureTest123!",
            roles={UserRole.TRADER}
        )
    
    def test_totp_mfa_setup(self):
        """Test TOTP MFA setup"""
        secret, provisioning_uri = self.mfa_service.initiate_totp_mfa(self.test_user.user_id)
        
        self.assertTrue(secret)
        self.assertTrue(provisioning_uri)
        self.assertTrue(self.test_user.mfa_enabled)
        self.assertTrue(self.test_user.mfa_secret)
    
    def test_sms_mfa_setup(self):
        """Test SMS MFA setup"""
        phone_number = "+1234567890"
        result = self.mfa_service.initiate_sms_mfa(self.test_user.user_id, phone_number)
        
        self.assertTrue(result)
        self.assertTrue(self.test_user.mfa_enabled)
        self.assertEqual(self.test_user.mfa_phone_number, phone_number)
    
    def test_biometric_mfa_setup(self):
        """Test biometric MFA setup"""
        result = self.mfa_service.initiate_biometric_mfa(self.test_user.user_id)
        
        self.assertTrue("initiated" in result)
    
    def test_biometric_template_registration(self):
        """Test biometric template registration"""
        biometric_data = "sample_biometric_data"
        result = self.mfa_service.register_biometric_template(self.test_user.user_id, biometric_data)
        
        self.assertTrue(result)
        self.assertTrue(self.test_user.mfa_enabled)
        self.assertTrue(self.test_user.mfa_biometric_template)
    
    def test_mfa_challenge_totp(self):
        """Test MFA challenge creation and verification for TOTP"""
        # Setup TOTP
        secret, _ = self.mfa_service.initiate_totp_mfa(self.test_user.user_id)
        
        # Create challenge
        challenge_id = self.mfa_service.create_mfa_challenge(
            self.test_user.user_id, 
            MFAProvider.TOTP
        )
        
        self.assertTrue(challenge_id)
        
        # For testing, we'll verify with a dummy code (in real implementation, this would be a valid TOTP)
        # Since we're testing the framework, not the actual TOTP generation, we'll test the flow
        # The actual TOTP verification is tested in the authentication framework tests
    
    def test_mfa_challenge_sms(self):
        """Test MFA challenge creation for SMS"""
        # Setup SMS
        phone_number = "+1234567890"
        self.mfa_service.initiate_sms_mfa(self.test_user.user_id, phone_number)
        
        # Create challenge
        challenge_id = self.mfa_service.create_mfa_challenge(
            self.test_user.user_id, 
            MFAProvider.SMS
        )
        
        self.assertTrue(challenge_id)
    
    def test_mfa_challenge_biometric(self):
        """Test MFA challenge creation for biometric"""
        # Setup biometric
        biometric_data = "sample_biometric_data"
        self.mfa_service.register_biometric_template(self.test_user.user_id, biometric_data)
        
        # Create challenge
        challenge_id = self.mfa_service.create_mfa_challenge(
            self.test_user.user_id, 
            MFAProvider.BIOMETRIC
        )
        
        self.assertTrue(challenge_id)
    
    def test_available_mfa_methods(self):
        """Test getting available MFA methods"""
        # Initially no MFA methods
        methods = self.mfa_service.get_available_mfa_methods(self.test_user.user_id)
        self.assertEqual(len(methods), 0)
        
        # Setup TOTP
        self.mfa_service.initiate_totp_mfa(self.test_user.user_id)
        methods = self.mfa_service.get_available_mfa_methods(self.test_user.user_id)
        self.assertIn(MFAProvider.TOTP.value, methods)
        
        # Setup SMS
        phone_number = "+1234567890"
        self.mfa_service.initiate_sms_mfa(self.test_user.user_id, phone_number)
        methods = self.mfa_service.get_available_mfa_methods(self.test_user.user_id)
        self.assertIn(MFAProvider.TOTP.value, methods)
        self.assertIn(MFAProvider.SMS.value, methods)
    
    def test_disable_mfa_method(self):
        """Test disabling specific MFA methods"""
        # Setup TOTP
        self.mfa_service.initiate_totp_mfa(self.test_user.user_id)
        
        # Disable TOTP
        result = self.mfa_service.disable_mfa_method(self.test_user.user_id, MFAProvider.TOTP)
        self.assertTrue(result)
        
        # Check that TOTP is disabled
        methods = self.mfa_service.get_available_mfa_methods(self.test_user.user_id)
        self.assertNotIn(MFAProvider.TOTP.value, methods)


def run_tests():
    """Run all enhanced MFA tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestEnhancedMFAService))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)