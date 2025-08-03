#!/usr/bin/env python3
"""
Comprehensive Test Suite for Zero-Trust Security Implementation
Tests authentication, authorization, behavioral analytics, and threat detection
"""

import asyncio
import json
import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Any
import os
import sys

# Add the parent directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security.zero_trust_security import (
    IdentityAccessManager, UserIdentity, AuthenticationContext, AccessRequest,
    AuthenticationMethod, ThreatLevel, AccessDecision, DeviceFingerprint,
    BehavioralProfile, ThreatIntelligence
)
from security.behavioral_analytics_engine import (
    BehavioralAnalyticsEngine, BehavioralEvent, AnomalyType, RiskLevel
)
from security.authentication_framework import (
    AuthenticationManager, SecurityConfig, UserRole, Permission
)

class TestZeroTrustSecurity:
    """Test suite for zero-trust security implementation"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.iam = IdentityAccessManager()
        self.analytics = BehavioralAnalyticsEngine(model_path=os.path.join(self.temp_dir, "models"))
        self.auth_manager = AuthenticationManager()
        
    def teardown_method(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.asyncio
    async def test_user_creation_and_authentication(self):
        """Test user creation and basic authentication"""
        # Create a test user
        user_id = await self.iam.create_user(
            username="testuser",
            email="test@example.com",
            password="SecurePassword123!",
            roles={"trader"},
            permissions={"trade.execute", "report.view"}
        )
        
        assert user_id is not None
        assert user_id in self.iam.users
        
        user = self.iam.users[user_id]
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert "trader" in user.roles
        assert "trade.execute" in user.permissions
        
        # Test authentication
        context = AuthenticationContext(
            user_id="",
            session_id="",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 Test Browser",
            device_fingerprint="test_device_123",
            location="New York"
        )
        
        session_id = await self.iam.authenticate_user("testuser", "SecurePassword123!", context)
        assert session_id is not None
        assert session_id in self.iam.sessions
        
        session = self.iam.sessions[session_id]
        assert session.user_id == user_id
        assert session.ip_address == "192.168.1.100"
    
    @pytest.mark.asyncio
    async def test_failed_authentication(self):
        """Test failed authentication scenarios"""
        # Create a test user
        user_id = await self.iam.create_user(
            username="testuser",
            email="test@example.com",
            password="SecurePassword123!",
            roles={"trader"},
            permissions={"trade.execute"}
        )
        
        context = AuthenticationContext(
            user_id="",
            session_id="",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 Test Browser",
            device_fingerprint="test_device_123"
        )
        
        # Test wrong password
        session_id = await self.iam.authenticate_user("testuser", "WrongPassword", context)
        assert session_id is None
        
        # Test non-existent user
        session_id = await self.iam.authenticate_user("nonexistent", "password", context)
        assert session_id is None
        
        # Test account lockout after multiple failed attempts
        for i in range(5):
            session_id = await self.iam.authenticate_user("testuser", "WrongPassword", context)
            assert session_id is None
        
        # User should be locked now
        user = self.iam.users[user_id]
        assert user.account_locked is True
        
        # Even correct password should fail for locked account
        session_id = await self.iam.authenticate_user("testuser", "SecurePassword123!", context)
        assert session_id is None
    
    @pytest.mark.asyncio
    async def test_mfa_functionality(self):
        """Test multi-factor authentication"""
        # Create a test user
        user_id = await self.iam.create_user(
            username="testuser",
            email="test@example.com",
            password="SecurePassword123!",
            roles={"trader"},
            permissions={"trade.execute"}
        )
        
        # Enable MFA
        mfa_secret = await self.iam.enable_mfa(user_id, AuthenticationMethod.MULTI_FACTOR)
        assert mfa_secret is not None
        
        user = self.iam.users[user_id]
        assert user.mfa_enabled is True
        
        # Authenticate and get session
        context = AuthenticationContext(
            user_id="",
            session_id="",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 Test Browser",
            device_fingerprint="test_device_123"
        )
        
        session_id = await self.iam.authenticate_user("testuser", "SecurePassword123!", context)
        assert session_id is not None
        
        # Verify MFA with valid code (using demo logic)
        mfa_result = await self.iam.verify_mfa(session_id, "123456")
        assert mfa_result is True
        
        session = self.iam.sessions[session_id]
        assert AuthenticationMethod.MULTI_FACTOR in session.authentication_methods
        
        # Test invalid MFA code
        session_id2 = await self.iam.authenticate_user("testuser", "SecurePassword123!", context)
        mfa_result = await self.iam.verify_mfa(session_id2, "invalid")
        assert mfa_result is False
    
    @pytest.mark.asyncio
    async def test_access_control(self):
        """Test access control policies"""
        # Create users with different roles
        trader_id = await self.iam.create_user(
            username="trader",
            email="trader@example.com",
            password="SecurePassword123!",
            roles={"trader"},
            permissions={"trade.execute", "report.view"}
        )
        
        analyst_id = await self.iam.create_user(
            username="analyst",
            email="analyst@example.com",
            password="SecurePassword123!",
            roles={"analyst"},
            permissions={"report.view"}
        )
        
        # Authenticate users
        trader_context = AuthenticationContext(
            user_id=trader_id,
            session_id="trader_session",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 Test Browser",
            device_fingerprint="trader_device"
        )
        
        analyst_context = AuthenticationContext(
            user_id=analyst_id,
            session_id="analyst_session",
            ip_address="192.168.1.101",
            user_agent="Mozilla/5.0 Test Browser",
            device_fingerprint="analyst_device"
        )
        
        self.iam.sessions["trader_session"] = trader_context
        self.iam.sessions["analyst_session"] = analyst_context
        
        # Test trading access
        trading_request = AccessRequest(
            request_id="req_1",
            user_id=trader_id,
            resource="trading",
            action="execute_trade",
            context=trader_context
        )
        
        decision = await self.iam.check_access(trading_request)
        assert decision == AccessDecision.CHALLENGE  # Should require MFA
        
        # Enable MFA for trader and verify
        await self.iam.enable_mfa(trader_id, AuthenticationMethod.MULTI_FACTOR)
        await self.iam.verify_mfa("trader_session", "123456")
        
        decision = await self.iam.check_access(trading_request)
        assert decision == AccessDecision.ALLOW
        
        # Test analyst trying to access trading (should be denied)
        analyst_trading_request = AccessRequest(
            request_id="req_2",
            user_id=analyst_id,
            resource="trading",
            action="execute_trade",
            context=analyst_context
        )
        
        decision = await self.iam.check_access(analyst_trading_request)
        assert decision == AccessDecision.DENY
        
        # Test analyst accessing reports (should be allowed)
        report_request = AccessRequest(
            request_id="req_3",
            user_id=analyst_id,
            resource="reporting",
            action="view_report",
            context=analyst_context
        )
        
        decision = await self.iam.check_access(report_request)
        assert decision == AccessDecision.ALLOW
    
    def test_device_fingerprinting(self):
        """Test device fingerprinting functionality"""
        # Create device fingerprint
        fingerprint_data = {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'screen_resolution': '1920x1080',
            'timezone': 'America/New_York',
            'language': 'en-US',
            'plugins': ['Chrome PDF Plugin', 'Native Client'],
            'fonts': ['Arial', 'Times New Roman', 'Helvetica'],
            'canvas_fingerprint': 'abc123def456',
            'webgl_fingerprint': 'webgl789xyz',
            'audio_fingerprint': 'audio456abc',
            'hardware_concurrency': 8,
            'memory': 16384,
            'platform': 'Win32'
        }
        
        device_id = "test_device_123"
        fingerprint_hash = self.iam.register_device_fingerprint(device_id, fingerprint_data)
        
        assert fingerprint_hash is not None
        assert device_id in self.iam.device_fingerprints
        
        # Test fingerprint verification with same data
        is_verified, similarity = self.iam.verify_device_fingerprint(device_id, fingerprint_data)
        assert is_verified is True
        assert similarity == 1.0
        
        # Test fingerprint verification with slightly different data
        modified_data = fingerprint_data.copy()
        modified_data['screen_resolution'] = '1366x768'
        
        is_verified, similarity = self.iam.verify_device_fingerprint(device_id, modified_data)
        assert similarity < 1.0
        assert similarity > 0.8  # Should still be similar
    
    def test_threat_intelligence(self):
        """Test threat intelligence functionality"""
        # Add threat intelligence
        self.iam.add_threat_intelligence(
            indicator="192.168.100.50",
            indicator_type="ip",
            threat_level=ThreatLevel.HIGH,
            description="Known malicious IP",
            source="internal_analysis",
            confidence=0.9,
            tags=["malware", "botnet"]
        )
        
        assert "192.168.100.50" in self.iam.threat_intelligence
        
        threat_info = self.iam.threat_intelligence["192.168.100.50"]
        assert threat_info.threat_level == ThreatLevel.HIGH
        assert threat_info.confidence == 0.9
        assert "malware" in threat_info.tags
        
        # Test threat detection
        malicious_context = AuthenticationContext(
            user_id="test_user",
            session_id="test_session",
            ip_address="192.168.100.50",  # Malicious IP
            user_agent="Mozilla/5.0 Test Browser",
            device_fingerprint="test_device"
        )
        
        threat_analysis = self.iam.check_threat_intelligence(malicious_context)
        assert threat_analysis['threat_detected'] is True
        assert threat_analysis['threat_score'] > 0.5
        assert len(threat_analysis['threats']) > 0
    
    @pytest.mark.asyncio
    async def test_enhanced_access_control(self):
        """Test enhanced access control with behavioral analysis"""
        # Create a test user
        user_id = await self.iam.create_user(
            username="testuser",
            email="test@example.com",
            password="SecurePassword123!",
            roles={"trader"},
            permissions={"trade.execute"}
        )
        
        # Create behavioral profile
        initial_behavior = {
            'location': 'New York',
            'device_id': 'trusted_device',
            'session_duration': 3600,
            'actions_count': 50
        }
        
        self.iam.create_behavioral_profile(user_id, initial_behavior)
        
        # Test normal access
        normal_context = AuthenticationContext(
            user_id=user_id,
            session_id="test_session",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 Test Browser",
            device_fingerprint="trusted_device",
            location="New York"
        )
        
        self.iam.sessions["test_session"] = normal_context
        
        normal_request = AccessRequest(
            request_id="req_1",
            user_id=user_id,
            resource="trading",
            action="execute_trade",
            context=normal_context
        )
        
        decision, analysis = await self.iam.enhanced_check_access(normal_request)
        assert analysis['basic_decision'] == AccessDecision.CHALLENGE  # Requires MFA
        
        # Test anomalous access (different location)
        anomalous_context = AuthenticationContext(
            user_id=user_id,
            session_id="test_session_2",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 Test Browser",
            device_fingerprint="new_device",  # Different device
            location="London"  # Different location
        )
        
        self.iam.sessions["test_session_2"] = anomalous_context
        
        anomalous_request = AccessRequest(
            request_id="req_2",
            user_id=user_id,
            resource="trading",
            action="execute_trade",
            context=anomalous_context
        )
        
        decision, analysis = await self.iam.enhanced_check_access(anomalous_request)
        assert len(analysis['risk_factors']) > 0
        # Should require additional verification due to anomalies
    
    def test_behavioral_analytics(self):
        """Test behavioral analytics engine"""
        # Create sample events
        user_id = "test_user_123"
        events = [
            BehavioralEvent(
                event_id=f"event_{i}",
                user_id=user_id,
                event_type="login",
                timestamp=datetime.now() - timedelta(hours=i),
                location="New York",
                device_id="device_abc",
                ip_address="192.168.1.100",
                resource_accessed="dashboard",
                action_performed="view",
                data_volume=1024
            )
            for i in range(10)
        ]
        
        # Record events
        for event in events:
            self.analytics.record_event(event)
        
        # Check if profile was created
        assert user_id in self.analytics.user_profiles
        
        profile = self.analytics.user_profiles[user_id]
        assert profile.user_id == user_id
        assert len(profile.typical_locations) > 0
        assert "New York" in profile.typical_locations
        
        # Test anomaly detection with unusual event
        anomalous_event = BehavioralEvent(
            event_id="anomaly_event",
            user_id=user_id,
            event_type="login",
            timestamp=datetime.now(),
            location="Tokyo",  # Different location
            device_id="new_device",  # Different device
            ip_address="192.168.1.200",
            resource_accessed="admin_panel",  # Different resource
            action_performed="config_change",
            data_volume=100000  # High volume
        )
        
        # Record anomalous event
        initial_anomaly_count = len(self.analytics.anomaly_detections)
        self.analytics.record_event(anomalous_event)
        
        # Should detect anomalies
        assert len(self.analytics.anomaly_detections) > initial_anomaly_count
        
        # Analyze user behavior
        analysis = self.analytics.analyze_user_behavior(user_id, days=7)
        assert analysis['user_id'] == user_id
        assert analysis['total_events'] > 0
        assert 'patterns' in analysis
        assert 'risk_assessment' in analysis
    
    def test_security_dashboard(self):
        """Test security dashboard functionality"""
        # Get IAM dashboard
        iam_dashboard = self.iam.get_security_dashboard()
        
        assert 'timestamp' in iam_dashboard
        assert 'users' in iam_dashboard
        assert 'devices' in iam_dashboard
        assert 'threats' in iam_dashboard
        assert 'security_events' in iam_dashboard
        
        # Get analytics dashboard
        analytics_dashboard = self.analytics.get_analytics_dashboard()
        
        assert 'timestamp' in analytics_dashboard
        assert 'events' in analytics_dashboard
        assert 'profiles' in analytics_dashboard
        assert 'anomalies' in analytics_dashboard
        assert 'ml_models' in analytics_dashboard
    
    def test_authentication_framework_integration(self):
        """Test integration with authentication framework"""
        # Create user with authentication framework
        trader_user = self.auth_manager.create_user(
            username="trader1",
            email="trader1@example.com",
            password="SecureTrader123!",
            roles={UserRole.TRADER}
        )
        
        assert trader_user.user_id is not None
        assert trader_user.username == "trader1"
        assert UserRole.TRADER in trader_user.roles
        assert trader_user.has_permission(Permission.ORDER_CREATE)
        
        # Test authentication
        session = self.auth_manager.authenticate_user(
            username="trader1",
            password="SecureTrader123!",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 Test Browser"
        )
        
        assert session is not None
        assert session.user_id == trader_user.user_id
        assert session.is_active
        
        # Test permission checking
        can_create_order = self.auth_manager.check_permission(
            session.session_id,
            Permission.ORDER_CREATE,
            "equity_order"
        )
        assert can_create_order is True
        
        # Test permission denial
        can_manage_users = self.auth_manager.check_permission(
            session.session_id,
            Permission.USER_MANAGE,
            "user_management"
        )
        assert can_manage_users is False
    
    def test_jwt_token_functionality(self):
        """Test JWT token generation and verification"""
        # Create user
        trader_user = self.auth_manager.create_user(
            username="trader1",
            email="trader1@example.com",
            password="SecureTrader123!",
            roles={UserRole.TRADER}
        )
        
        # Generate JWT token
        token = self.auth_manager.generate_jwt_token(
            trader_user.user_id,
            additional_claims={'custom_claim': 'test_value'}
        )
        
        assert token is not None
        assert isinstance(token, str)
        
        # Verify JWT token
        payload = self.auth_manager.verify_jwt_token(token)
        assert payload is not None
        assert payload['user_id'] == trader_user.user_id
        assert payload['username'] == trader_user.username
        assert 'custom_claim' in payload
        assert payload['custom_claim'] == 'test_value'
        
        # Test invalid token
        invalid_payload = self.auth_manager.verify_jwt_token("invalid_token")
        assert invalid_payload is None
    
    def test_api_key_functionality(self):
        """Test API key generation and authentication"""
        # Create user
        trader_user = self.auth_manager.create_user(
            username="trader1",
            email="trader1@example.com",
            password="SecureTrader123!",
            roles={UserRole.TRADER}
        )
        
        # Generate API key
        api_key = self.auth_manager.generate_api_key(
            trader_user.user_id,
            description="Test API key"
        )
        
        assert api_key is not None
        assert len(api_key) > 0
        assert api_key in trader_user.api_keys
        
        # Authenticate with API key
        authenticated_user = self.auth_manager.authenticate_api_key(api_key)
        assert authenticated_user is not None
        assert authenticated_user.user_id == trader_user.user_id
        
        # Revoke API key
        self.auth_manager.revoke_api_key(api_key)
        assert api_key not in trader_user.api_keys
        
        # Should not authenticate with revoked key
        authenticated_user = self.auth_manager.authenticate_api_key(api_key)
        assert authenticated_user is None
    
    def test_security_metrics(self):
        """Test security metrics collection"""
        # Create some test data
        trader_user = self.auth_manager.create_user(
            username="trader1",
            email="trader1@example.com",
            password="SecureTrader123!",
            roles={UserRole.TRADER}
        )
        
        # Authenticate user
        session = self.auth_manager.authenticate_user(
            username="trader1",
            password="SecureTrader123!",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 Test Browser"
        )
        
        # Get security metrics
        metrics = self.auth_manager.get_security_metrics()
        
        assert 'total_users' in metrics
        assert 'active_users' in metrics
        assert 'active_sessions' in metrics
        assert 'events_24h' in metrics
        assert 'successful_logins_24h' in metrics
        
        assert metrics['total_users'] >= 1
        assert metrics['active_users'] >= 1
        assert metrics['active_sessions'] >= 1

def run_comprehensive_test():
    """Run comprehensive test suite"""
    print("Starting Zero-Trust Security Test Suite...")
    
    # Create test instance
    test_suite = TestZeroTrustSecurity()
    
    try:
        # Run all tests
        test_methods = [
            method for method in dir(test_suite) 
            if method.startswith('test_') and callable(getattr(test_suite, method))
        ]
        
        passed_tests = 0
        failed_tests = 0
        
        for test_method in test_methods:
            try:
                print(f"\nRunning {test_method}...")
                test_suite.setup_method()
                
                method = getattr(test_suite, test_method)
                if asyncio.iscoroutinefunction(method):
                    asyncio.run(method())
                else:
                    method()
                
                print(f"✓ {test_method} PASSED")
                passed_tests += 1
                
            except Exception as e:
                print(f"✗ {test_method} FAILED: {str(e)}")
                failed_tests += 1
            
            finally:
                test_suite.teardown_method()
        
        print(f"\n{'='*60}")
        print(f"Test Results: {passed_tests} passed, {failed_tests} failed")
        print(f"Success Rate: {(passed_tests / (passed_tests + failed_tests)) * 100:.1f}%")
        
        if failed_tests == 0:
            print("🎉 All tests passed! Zero-Trust Security implementation is working correctly.")
        else:
            print("⚠️  Some tests failed. Please review the implementation.")
        
        return failed_tests == 0
        
    except Exception as e:
        print(f"Test suite execution failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_comprehensive_test()
    exit(0 if success else 1)