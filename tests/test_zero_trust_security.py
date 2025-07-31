"""
Tests for Zero-Trust Security System
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from nautilus_trader_engine.security.zero_trust_security import (
    ZeroTrustSecurityManager,
    IdentityManager,
    AccessControlManager,
    EncryptionManager,
    BehavioralAnalytics,
    User,
    Session,
    SecurityEvent,
    SecurityLevel,
    AuthenticationMethod,
    AccessAction
)


class TestIdentityManager:
    """Test identity management"""
    
    @pytest.fixture
    def identity_manager(self):
        return IdentityManager()
    
    def test_create_user(self, identity_manager):
        """Test user creation"""
        user = identity_manager.create_user(
            "testuser", "test@example.com", "Test User",
            "password123", SecurityLevel.INTERNAL
        )
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.security_level == SecurityLevel.INTERNAL
        assert user.is_active
        assert user.user_id in identity_manager.users
        assert user.user_id in identity_manager.password_hashes
    
    def test_authenticate_user_success(self, identity_manager):
        """Test successful user authentication"""
        user = identity_manager.create_user(
            "testuser", "test@example.com", "Test User", "password123"
        )
        
        session = identity_manager.authenticate_user(
            "testuser", "password123", "192.168.1.1", "Mozilla/5.0"
        )
        
        assert session is not None
        assert session.user_id == user.user_id
        assert session.ip_address == "192.168.1.1"
        assert session.user_agent == "Mozilla/5.0"
        assert session.is_active
        assert user.failed_login_attempts == 0
        assert user.last_login is not None
    
    def test_authenticate_user_failure(self, identity_manager):
        """Test failed user authentication"""
        identity_manager.create_user(
            "testuser", "test@example.com", "Test User", "password123"
        )
        
        # Wrong password
        session = identity_manager.authenticate_user(
            "testuser", "wrongpassword", "192.168.1.1", "Mozilla/5.0"
        )
        
        assert session is None
        
        # Non-existent user
        session = identity_manager.authenticate_user(
            "nonexistent", "password123", "192.168.1.1", "Mozilla/5.0"
        )
        
        assert session is None
    
    @pytest.mark.skipif(True, reason="pyotp library not available")
    def test_setup_mfa(self, identity_manager):
        """Test MFA setup"""
        user = identity_manager.create_user(
            "testuser", "test@example.com", "Test User", "password123"
        )
        
        # Test without MFA library
        uri = identity_manager.setup_mfa(user.user_id)
        assert uri is None
    
    @pytest.mark.skipif(True, reason="pyotp library not available")
    def test_verify_mfa(self, identity_manager):
        """Test MFA verification"""
        user = identity_manager.create_user(
            "testuser", "test@example.com", "Test User", "password123"
        )
        
        # Test without MFA library
        result = identity_manager.verify_mfa(user.user_id, "123456")
        assert result is False


class TestAccessControlManager:
    """Test access control"""
    
    @pytest.fixture
    def access_control(self):
        identity_manager = IdentityManager()
        return AccessControlManager(identity_manager)
    
    def test_check_access_with_permission(self, access_control):
        """Test access check with direct permission"""
        # Create user and session
        user = access_control.identity_manager.create_user(
            "testuser", "test@example.com", "Test User", "password123"
        )
        session = access_control.identity_manager.authenticate_user(
            "testuser", "password123", "192.168.1.1", "Mozilla/5.0"
        )
        
        # Grant permission
        access_control.grant_permission(user.user_id, "trading", AccessAction.READ)
        
        # Check access
        has_access = access_control.check_access(
            session.session_id, "trading", AccessAction.READ
        )
        assert has_access is True
        
        # Check access to different action
        has_access = access_control.check_access(
            session.session_id, "trading", AccessAction.WRITE
        )
        assert has_access is False
    
    def test_check_access_with_role(self, access_control):
        """Test access check with role-based permission"""
        # Create role
        access_control.create_role("trader", ["trading:read", "trading:write"])
        
        # Create user and session
        user = access_control.identity_manager.create_user(
            "testuser", "test@example.com", "Test User", "password123"
        )
        session = access_control.identity_manager.authenticate_user(
            "testuser", "password123", "192.168.1.1", "Mozilla/5.0"
        )
        
        # Assign role
        access_control.assign_role(user.user_id, "trader")
        
        # Check access
        has_access = access_control.check_access(
            session.session_id, "trading", AccessAction.READ
        )
        assert has_access is True
        
        has_access = access_control.check_access(
            session.session_id, "trading", AccessAction.WRITE
        )
        assert has_access is True
        
        has_access = access_control.check_access(
            session.session_id, "admin", AccessAction.READ
        )
        assert has_access is False
    
    def test_expired_session(self, access_control):
        """Test access check with expired session"""
        user = access_control.identity_manager.create_user(
            "testuser", "test@example.com", "Test User", "password123"
        )
        session = access_control.identity_manager.authenticate_user(
            "testuser", "password123", "192.168.1.1", "Mozilla/5.0"
        )
        
        # Grant permission
        access_control.grant_permission(user.user_id, "trading", AccessAction.READ)
        
        # Expire session
        session.expires_at = datetime.now() - timedelta(hours=1)
        
        # Check access
        has_access = access_control.check_access(
            session.session_id, "trading", AccessAction.READ
        )
        assert has_access is False
        assert session.is_active is False


class TestEncryptionManager:
    """Test encryption management"""
    
    @pytest.fixture
    def encryption_manager(self):
        return EncryptionManager()
    
    def test_generate_key(self, encryption_manager):
        """Test key generation"""
        with patch('nautilus_trader_engine.security.zero_trust_security.CRYPTO_AVAILABLE', True):
            with patch('nautilus_trader_engine.security.zero_trust_security.Fernet') as mock_fernet:
                mock_fernet.generate_key.return_value = b'test_key'
                
                key = encryption_manager.generate_key("test_key_id")
                
                assert key == b'test_key'
                assert "test_key_id" in encryption_manager.encryption_keys
    
    def test_encrypt_decrypt_data(self, encryption_manager):
        """Test data encryption and decryption"""
        with patch('nautilus_trader_engine.security.zero_trust_security.CRYPTO_AVAILABLE', True):
            with patch('nautilus_trader_engine.security.zero_trust_security.Fernet') as mock_fernet_class:
                # Mock Fernet instance
                mock_fernet = Mock()
                mock_fernet.encrypt.return_value = b'encrypted_data'
                mock_fernet.decrypt.return_value = b'test data'
                mock_fernet_class.return_value = mock_fernet
                mock_fernet_class.generate_key.return_value = b'test_key'
                
                # Generate key
                encryption_manager.generate_key("test_key")
                
                # Test encryption
                with patch('base64.b64encode') as mock_b64encode:
                    mock_b64encode.return_value = b'base64_encrypted'
                    encrypted = encryption_manager.encrypt_data("test data", "test_key")
                    assert encrypted == "base64_encrypted"
                
                # Test decryption
                with patch('base64.b64decode') as mock_b64decode:
                    mock_b64decode.return_value = b'encrypted_data'
                    decrypted = encryption_manager.decrypt_data("base64_encrypted", "test_key")
                    assert decrypted == "test data"


class TestBehavioralAnalytics:
    """Test behavioral analytics"""
    
    @pytest.fixture
    def behavioral_analytics(self):
        return BehavioralAnalytics()
    
    def test_record_user_activity(self, behavioral_analytics):
        """Test recording user activity"""
        user_id = "test_user"
        timestamp = datetime.now()
        
        behavioral_analytics.record_user_activity(
            user_id, "login", "192.168.1.1", timestamp
        )
        
        assert user_id in behavioral_analytics.user_patterns
        pattern = behavioral_analytics.user_patterns[user_id]
        assert len(pattern['activities']) == 1
        assert pattern['activities'][0]['activity'] == "login"
        assert "192.168.1.1" in pattern['ip_addresses']
        assert timestamp.hour in pattern['login_times']
    
    def test_anomaly_detection_unusual_time(self, behavioral_analytics):
        """Test anomaly detection for unusual login times"""
        user_id = "test_user"
        
        # Record normal login times (9 AM)
        for i in range(6):
            timestamp = datetime.now().replace(hour=9)
            behavioral_analytics.record_user_activity(
                user_id, "login", "192.168.1.1", timestamp
            )
        
        # Record unusual login time (3 AM)
        unusual_timestamp = datetime.now().replace(hour=3)
        behavioral_analytics.record_user_activity(
            user_id, "login", "192.168.1.1", unusual_timestamp
        )
        
        # Check if security event was created
        events = [e for e in behavioral_analytics.security_events 
                 if e.event_type == "unusual_login_time"]
        assert len(events) > 0
    
    def test_anomaly_detection_multiple_ips(self, behavioral_analytics):
        """Test anomaly detection for multiple IP addresses"""
        user_id = "test_user"
        timestamp = datetime.now()
        
        # Record activities from different IPs
        ips = ["192.168.1.1", "10.0.0.1", "172.16.0.1"]
        for ip in ips:
            behavioral_analytics.record_user_activity(
                user_id, "trading", ip, timestamp
            )
        
        # Check if security event was created
        events = [e for e in behavioral_analytics.security_events 
                 if e.event_type == "multiple_ip_addresses"]
        assert len(events) > 0


class TestZeroTrustSecurityManager:
    """Test main security manager"""
    
    @pytest.fixture
    def security_manager(self):
        return ZeroTrustSecurityManager()
    
    def test_default_roles_setup(self, security_manager):
        """Test default roles are set up"""
        roles = security_manager.access_control.role_permissions
        
        assert "trader" in roles
        assert "risk_manager" in roles
        assert "administrator" in roles
        
        assert "trading:read" in roles["trader"]
        assert "risk:read" in roles["risk_manager"]
        assert "system:admin" in roles["administrator"]
    
    @pytest.mark.asyncio
    async def test_authenticate_and_authorize_success(self, security_manager):
        """Test successful authentication and authorization"""
        # Create user
        user = security_manager.identity_manager.create_user(
            "trader1", "trader@example.com", "Trader One", "password123"
        )
        security_manager.access_control.assign_role(user.user_id, "trader")
        
        # Test authentication and authorization
        success, session_id = await security_manager.authenticate_and_authorize(
            "trader1", "password123", "trading", AccessAction.READ,
            "192.168.1.1", "Mozilla/5.0"
        )
        
        assert success is True
        assert session_id is not None
        assert session_id.startswith("session_")
    
    @pytest.mark.asyncio
    async def test_authenticate_and_authorize_mfa_required(self, security_manager):
        """Test authentication with MFA requirement"""
        # Create high-security user
        user = security_manager.identity_manager.create_user(
            "admin1", "admin@example.com", "Admin One", 
            "password123", SecurityLevel.SECRET
        )
        security_manager.access_control.assign_role(user.user_id, "administrator")
        
        # Test without MFA token
        success, message = await security_manager.authenticate_and_authorize(
            "admin1", "password123", "system", AccessAction.ADMIN,
            "192.168.1.1", "Mozilla/5.0"
        )
        
        assert success is False
        assert "MFA token required" in message
        
        # Test with invalid MFA token
        success, message = await security_manager.authenticate_and_authorize(
            "admin1", "password123", "system", AccessAction.ADMIN,
            "192.168.1.1", "Mozilla/5.0", "123456"
        )
        
        assert success is False
        assert "Invalid MFA token" in message
    
    @pytest.mark.asyncio
    async def test_authenticate_and_authorize_access_denied(self, security_manager):
        """Test authentication with access denied"""
        # Create user with limited permissions
        user = security_manager.identity_manager.create_user(
            "trader1", "trader@example.com", "Trader One", "password123"
        )
        security_manager.access_control.assign_role(user.user_id, "trader")
        
        # Try to access admin resource
        success, message = await security_manager.authenticate_and_authorize(
            "trader1", "password123", "system", AccessAction.ADMIN,
            "192.168.1.1", "Mozilla/5.0"
        )
        
        assert success is False
        assert "Access denied" in message
    
    def test_get_security_events(self, security_manager):
        """Test getting security events"""
        # Create some security events
        event1 = SecurityEvent(
            event_id="event1", event_type="login_failure",
            user_id="user1", resource=None, action=None,
            timestamp=datetime.now(), severity="high",
            description="Failed login attempt"
        )
        
        event2 = SecurityEvent(
            event_id="event2", event_type="unusual_activity",
            user_id="user2", resource=None, action=None,
            timestamp=datetime.now(), severity="medium",
            description="Unusual activity detected"
        )
        
        security_manager.behavioral_analytics.security_events = [event1, event2]
        
        # Test getting all events
        all_events = security_manager.get_security_events()
        assert len(all_events) == 2
        
        # Test filtering by severity
        high_events = security_manager.get_security_events(severity="high")
        assert len(high_events) == 1
        assert high_events[0].event_id == "event1"
        
        # Test filtering by user
        user1_events = security_manager.get_security_events(user_id="user1")
        assert len(user1_events) == 1
        assert user1_events[0].event_id == "event1"


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_complete_security_workflow(self):
        """Test complete security workflow"""
        security_manager = ZeroTrustSecurityManager()
        
        # Create users
        trader = security_manager.identity_manager.create_user(
            "trader1", "trader@example.com", "John Trader",
            "secure_password123", SecurityLevel.CONFIDENTIAL
        )
        
        admin = security_manager.identity_manager.create_user(
            "admin1", "admin@example.com", "Jane Admin",
            "admin_password456", SecurityLevel.SECRET
        )
        
        # Assign roles
        security_manager.access_control.assign_role(trader.user_id, "trader")
        security_manager.access_control.assign_role(admin.user_id, "administrator")
        
        # Test trader access
        success, session_id = await security_manager.authenticate_and_authorize(
            "trader1", "secure_password123", "trading", AccessAction.READ,
            "192.168.1.100", "Mozilla/5.0"
        )
        
        assert success is True
        assert session_id is not None
        
        # Test encryption
        key_id = "test_encryption"
        with patch('nautilus_trader_engine.security.zero_trust_security.CRYPTO_AVAILABLE', True):
            with patch('nautilus_trader_engine.security.zero_trust_security.Fernet') as mock_fernet_class:
                mock_fernet = Mock()
                mock_fernet.encrypt.return_value = b'encrypted'
                mock_fernet.decrypt.return_value = b'sensitive data'
                mock_fernet_class.return_value = mock_fernet
                mock_fernet_class.generate_key.return_value = b'key'
                
                security_manager.encryption_manager.generate_key(key_id)
                
                with patch('base64.b64encode', return_value=b'encrypted_b64'):
                    encrypted = security_manager.encryption_manager.encrypt_data(
                        "sensitive data", key_id
                    )
                    assert encrypted == "encrypted_b64"
                
                with patch('base64.b64decode', return_value=b'encrypted'):
                    decrypted = security_manager.encryption_manager.decrypt_data(
                        encrypted, key_id
                    )
                    assert decrypted == "sensitive data"
        
        # Test behavioral analytics
        security_manager.behavioral_analytics.record_user_activity(
            trader.user_id, "trading", "192.168.1.100", datetime.now()
        )
        
        pattern = security_manager.behavioral_analytics.user_patterns[trader.user_id]
        assert len(pattern['activities']) >= 1  # May have multiple activities from auth flow
        assert "192.168.1.100" in pattern['ip_addresses']
        
        print("Complete security workflow test passed!")


if __name__ == "__main__":
    pytest.main([__file__])