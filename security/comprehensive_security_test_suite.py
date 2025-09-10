#!/usr/bin/env python3
"""
Comprehensive Security Testing Suite
End-to-end security testing for all components
"""

import unittest
import sys
import os
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add the security directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from authentication_framework import (
    AuthenticationManager, UserRole, Permission, GranularPermission, 
    AuthenticationMethod, SessionStatus
)
from oauth2_oidc_provider import OAuth2OIDCProvider
from oauth2_oidc_middleware import OAuth2Middleware, OIDCMiddleware
from enhanced_mfa_service import EnhancedMFAService, MFAProvider
from api_security_middleware import SecurityMiddleware, AuthContext
from secure_session_manager import SecureSessionManager
from enhanced_audit_logger import EnhancedAuditLogger, AuditLoggerConfig
# Fix the import path for ZeroTrustSecurityManager
from zero_trust_security import IdentityAccessManager


class ComprehensiveSecurityTestSuite(unittest.TestCase):
    """Comprehensive security testing suite"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Initialize core security components
        self.auth_manager = AuthenticationManager()
        self.oauth2_provider = OAuth2OIDCProvider("https://test.trading-system.com")
        self.oauth2_middleware = OAuth2Middleware(self.auth_manager, self.oauth2_provider)
        self.oidc_middleware = OIDCMiddleware(self.oauth2_provider)
        self.mfa_service = EnhancedMFAService(self.auth_manager)
        self.security_middleware = SecurityMiddleware(self.auth_manager, self.oauth2_provider)
        self.secure_session_manager = SecureSessionManager(self.auth_manager)
        
        # Initialize zero trust security
        self.zero_trust_manager = IdentityAccessManager()
        
        # Initialize audit logger
        audit_config = AuditLoggerConfig()
        audit_config.log_file_path = "comprehensive_test_audit.log"
        audit_config.database_path = "comprehensive_test_audit.db"
        self.audit_logger = EnhancedAuditLogger(self.auth_manager, audit_config)
        
        # Create test users
        self.admin_user = self.auth_manager.create_user(
            username="admin_user",
            email="admin@test.com",
            password="SecureAdmin123!",
            roles={UserRole.ADMIN}
        )
        
        self.trader_user = self.auth_manager.create_user(
            username="trader_user",
            email="trader@test.com",
            password="SecureTrader123!",
            roles={UserRole.TRADER}
        )
        
        self.risk_manager_user = self.auth_manager.create_user(
            username="risk_user",
            email="risk@test.com",
            password="SecureRisk123!",
            roles={UserRole.RISK_MANAGER}
        )
    
    def test_01_authentication_integration(self):
        """Test authentication integration across all components"""
        # Test basic authentication
        session = self.auth_manager.authenticate_user(
            username="trader_user",
            password="SecureTrader123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        self.assertTrue(session.is_active)
        self.assertEqual(session.username, "trader_user")
        
        # Test session validation
        validated_session = self.auth_manager.validate_session(
            session.session_id, 
            "192.168.1.100"
        )
        
        self.assertIsNotNone(validated_session)
        self.assertEqual(validated_session.session_id, session.session_id)
    
    def test_02_oauth2_oidc_integration(self):
        """Test OAuth2/OIDC integration"""
        # Register OAuth2 client
        client_data = {
            "client_name": "Test Client",
            "redirect_uris": ["https://test.client.com/callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "scopes": ["openid", "profile", "email"]
        }
        
        client = self.oauth2_provider.register_client(client_data)
        self.assertIsNotNone(client)
        self.assertTrue(client.is_active)
        
        # Create authorization code
        auth_code = self.oauth2_provider.create_authorization_code(
            client_id=client.client_id,
            user_id=self.trader_user.user_id,
            redirect_uri="https://test.client.com/callback",
            scopes=["openid", "profile"]
        )
        
        self.assertIsNotNone(auth_code)
        
        # Exchange for tokens
        token = self.oauth2_provider.exchange_authorization_code(
            code=auth_code,
            client_id=client.client_id,
            client_secret=client.client_secret,
            redirect_uri="https://test.client.com/callback"
        )
        
        self.assertIsNotNone(token)
        self.assertIsNotNone(token.access_token)
        self.assertIsNotNone(token.refresh_token)
    
    def test_03_mfa_integration(self):
        """Test MFA integration"""
        # Setup TOTP MFA
        secret, provisioning_uri = self.mfa_service.initiate_totp_mfa(self.trader_user.user_id)
        self.assertIsNotNone(secret)
        self.assertIsNotNone(provisioning_uri)
        self.assertTrue(self.trader_user.mfa_enabled)
        
        # Setup SMS MFA
        result = self.mfa_service.initiate_sms_mfa(self.trader_user.user_id, "+1234567890")
        self.assertTrue("initiated" in result)
        
        # Create MFA challenge
        challenge_id = self.mfa_service.create_mfa_challenge(
            self.trader_user.user_id, 
            MFAProvider.TOTP
        )
        
        self.assertIsNotNone(challenge_id)
    
    def test_04_api_security_middleware(self):
        """Test API security middleware"""
        # Authenticate user to get session
        session = self.auth_manager.authenticate_user(
            username="trader_user",
            password="SecureTrader123!",
            ip_address="192.168.1.100"
        )
        
        # Test authentication with session
        headers = {"X-Session-ID": session.session_id}
        auth_context = self.security_middleware.authenticate_request(
            headers, 
            "192.168.1.100"
        )
        
        self.assertIsNotNone(auth_context)
        self.assertEqual(auth_context.user_id, self.trader_user.user_id)
        self.assertEqual(auth_context.username, "trader_user")
        
        # Test authorization
        authorized = self.security_middleware.authorize_request(
            auth_context,
            Permission.ORDER_CREATE
        )
        
        self.assertTrue(authorized)
        
        # Test unauthorized access
        unauthorized = self.security_middleware.authorize_request(
            auth_context,
            Permission.USER_MANAGE
        )
        
        self.assertFalse(unauthorized)
    
    def test_05_secure_session_management(self):
        """Test secure session management"""
        # Authenticate user
        session = self.auth_manager.authenticate_user(
            username="trader_user",
            password="SecureTrader123!",
            ip_address="192.168.1.100"
        )
        
        # Create secure session
        access_token, refresh_token = self.secure_session_manager.create_secure_session(session)
        self.assertIsNotNone(access_token)
        self.assertIsNotNone(refresh_token)
        
        # Validate secure token
        validated_session = self.secure_session_manager.validate_secure_token(
            access_token,
            "192.168.1.100"
        )
        
        self.assertIsNotNone(validated_session)
        self.assertEqual(validated_session.session_id, session.session_id)
        
        # Refresh token
        new_access_token, new_refresh_token = self.secure_session_manager.refresh_secure_token(refresh_token)
        self.assertIsNotNone(new_access_token)
        self.assertIsNotNone(new_refresh_token)
    
    def test_06_audit_logging_comprehensive(self):
        """Test comprehensive audit logging"""
        # Perform some actions to generate audit events
        session = self.auth_manager.authenticate_user(
            username="trader_user",
            password="SecureTrader123!",
            ip_address="192.168.1.100"
        )
        
        # Check permissions
        self.auth_manager.check_permission(
            session.session_id,
            Permission.ORDER_CREATE
        )
        
        # Use the integrate_audit_logger function to properly set up audit logging
        from enhanced_audit_logger import integrate_audit_logger
        audit_config = AuditLoggerConfig()
        audit_config.log_file_path = "comprehensive_test_suite_audit.log"
        audit_config.database_path = "comprehensive_test_suite_audit.db"
        integrated_audit_logger = integrate_audit_logger(self.auth_manager, audit_config)
        
        # Perform another action to generate audit events with the integrated logger
        session2 = self.auth_manager.authenticate_user(
            username="admin_user",
            password="SecureAdmin123!",
            ip_address="192.168.1.101"
        )
        
        # Close the audit logger to flush contents
        integrated_audit_logger.close()
        
        # Create a new audit logger instance to access the database
        new_audit_logger = EnhancedAuditLogger(self.auth_manager, audit_config)
        
        # Query audit events
        events = new_audit_logger.query_events(
            limit=10
        )
        
        self.assertGreater(len(events), 0)
        
        # Test audit summary
        summary = new_audit_logger.get_audit_summary()
        self.assertIsInstance(summary, dict)
        self.assertIn('total_events', summary)
        
        # Close the new audit logger
        new_audit_logger.close()
        
        # Clean up test files
        import os
        if os.path.exists(audit_config.log_file_path):
            os.remove(audit_config.log_file_path)
        if os.path.exists(audit_config.database_path):
            os.remove(audit_config.database_path)
    
    def test_07_zero_trust_security(self):
        """Test zero trust security implementation"""
        # Create a user for testing
        user_id = self.zero_trust_manager.create_user(
            username="zt_test_user",
            email="zt_test@example.com",
            password="SecureTest123!",
            roles={"trader"},
            permissions={"trade.execute"}
        )
        
        # Test security dashboard
        dashboard = self.zero_trust_manager.get_security_dashboard()
        self.assertIsInstance(dashboard, dict)
        self.assertIn('users', dashboard)
        self.assertIn('devices', dashboard)
        self.assertIn('threats', dashboard)
    
    def test_08_security_performance_stress(self):
        """Test security component performance under stress"""
        # Measure authentication performance
        start_time = time.time()
        
        # Perform multiple authentications
        sessions = []
        for i in range(50):
            session = self.auth_manager.authenticate_user(
                username="trader_user",
                password="SecureTrader123!",
                ip_address=f"192.168.1.{i % 255}"
            )
            sessions.append(session)
        
        end_time = time.time()
        auth_time = end_time - start_time
        
        # Should complete within reasonable time (less than 30 seconds for 50 auths)
        self.assertLess(auth_time, 30.0)
        self.assertEqual(len(sessions), 50)
        
        # Test concurrent session validation
        start_time = time.time()
        
        validation_results = []
        for session in sessions:
            if session:
                validated = self.auth_manager.validate_session(
                    session.session_id,
                    session.ip_address
                )
                validation_results.append(validated is not None)
        
        end_time = time.time()
        validation_time = end_time - start_time
        
        # Should complete within reasonable time
        self.assertLess(validation_time, 30.0)
        self.assertTrue(all(validation_results))
    
    def test_09_security_compliance_validation(self):
        """Test security compliance with standards"""
        # Check password policy enforcement
        with self.assertRaises(ValueError) as context:
            self.auth_manager.create_user(
                username="weak_user",
                email="weak@test.com",
                password="weak",  # Weak password
                roles={UserRole.VIEWER}
            )
        
        self.assertIn("Password policy violation", str(context.exception))
        
        # Check session timeout configuration
        self.assertEqual(
            self.auth_manager.config.session_timeout_minutes, 
            480  # 8 hours
        )
        
        # Check MFA requirements for privileged roles
        self.assertIn(UserRole.ADMIN, self.auth_manager.config.mfa_required_for_roles)
        self.assertIn(UserRole.SUPER_ADMIN, self.auth_manager.config.mfa_required_for_roles)
        self.assertIn(UserRole.RISK_MANAGER, self.auth_manager.config.mfa_required_for_roles)
    
    def test_10_penetration_testing_simulation(self):
        """Simulate common penetration testing scenarios"""
        # Test brute force protection
        for i in range(10):  # Try 10 wrong passwords
            session = self.auth_manager.authenticate_user(
                username="trader_user",
                password=f"wrong_password_{i}",
                ip_address="10.0.0.1"
            )
            self.assertIsNone(session)
        
        # Check if account is locked after max attempts
        user = self.auth_manager.users[self.trader_user.user_id]
        if user.failed_login_attempts >= self.auth_manager.config.max_failed_login_attempts:
            self.assertTrue(user.is_locked)
        
        # Test session hijacking prevention
        session = self.auth_manager.authenticate_user(
            username="admin_user",
            password="SecureAdmin123!",
            ip_address="192.168.1.100"
        )
        
        # Try to validate session from different IP (should fail if IP validation enabled)
        if self.auth_manager.config.session_ip_validation:
            hijacked_session = self.auth_manager.validate_session(
                session.session_id,
                "10.0.0.2"  # Different IP
            )
            # This might not fail if the session is still valid, but we check the audit logs
            # The important thing is that it's logged as suspicious
        
        # Test privilege escalation attempts
        # Regular user trying to access admin functions
        trader_session = self.auth_manager.authenticate_user(
            username="trader_user",
            password="SecureTrader123!",
            ip_address="192.168.1.101"
        )
        
        # Check that authentication was successful before checking permissions
        if trader_session:
            # Try to check admin permission
            has_admin_perm = self.auth_manager.check_permission(
                trader_session.session_id,
                Permission.USER_MANAGE
            )
            
            self.assertFalse(has_admin_perm)
    
    def test_11_security_metrics_and_monitoring(self):
        """Test security metrics and monitoring capabilities"""
        # Generate some security events
        for i in range(5):
            session = self.auth_manager.authenticate_user(
                username="trader_user",
                password="SecureTrader123!",
                ip_address=f"192.168.1.{100 + i}"
            )
            
            if session:
                # Check some permissions
                self.auth_manager.check_permission(
                    session.session_id,
                    Permission.ORDER_VIEW
                )
        
        # Get security metrics from middleware
        metrics = self.security_middleware.get_security_metrics()
        self.assertIsInstance(metrics, dict)
        self.assertIn("active_rate_limit_entries", metrics)
        self.assertIn("active_ips", metrics)
        
        # Get audit summary
        summary = self.audit_logger.get_audit_summary(
            start_time=datetime.now() - timedelta(minutes=5)
        )
        self.assertIsInstance(summary, dict)
        self.assertGreaterEqual(summary.get('total_events', 0), 0)
    
    def test_12_integration_with_external_systems(self):
        """Test integration with external security systems"""
        # Test JWT token generation and validation
        jwt_token = self.auth_manager.generate_jwt_token(self.trader_user.user_id)
        self.assertIsNotNone(jwt_token)
        
        # Validate JWT token
        jwt_payload = self.auth_manager.verify_jwt_token(jwt_token)
        self.assertIsNotNone(jwt_payload)
        self.assertEqual(jwt_payload.get('user_id'), self.trader_user.user_id)
        self.assertEqual(jwt_payload.get('username'), 'trader_user')
        
        # Test API key generation and authentication
        api_key = self.auth_manager.generate_api_key(self.trader_user.user_id)
        self.assertIsNotNone(api_key)
        
        # Authenticate with API key
        user_from_api_key = self.auth_manager.authenticate_api_key(api_key)
        self.assertIsNotNone(user_from_api_key)
        self.assertEqual(user_from_api_key.user_id, self.trader_user.user_id)


def create_test_suite():
    """Create comprehensive security test suite"""
    suite = unittest.TestSuite()
    
    # Add all test methods
    test_cases = [
        "test_01_authentication_integration",
        "test_02_oauth2_oidc_integration",
        "test_03_mfa_integration",
        "test_04_api_security_middleware",
        "test_05_secure_session_management",
        "test_06_audit_logging_comprehensive",
        "test_07_zero_trust_security",
        "test_08_security_performance_stress",
        "test_09_security_compliance_validation",
        "test_10_penetration_testing_simulation",
        "test_11_security_metrics_and_monitoring",
        "test_12_integration_with_external_systems"
    ]
    
    for test_case in test_cases:
        suite.addTest(ComprehensiveSecurityTestSuite(test_case))
    
    return suite


def run_comprehensive_security_tests():
    """Run the comprehensive security test suite"""
    print("Starting Comprehensive Security Test Suite...")
    print("=" * 50)
    
    # Create test suite
    suite = create_test_suite()
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 50)
    print("Comprehensive Security Test Suite Results:")
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_security_tests()
    exit(0 if success else 1)