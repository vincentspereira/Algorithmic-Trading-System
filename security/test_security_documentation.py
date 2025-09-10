#!/usr/bin/env python3
"""
Test script to verify security documentation examples
"""

import sys
import os
from datetime import datetime, timedelta

# Add the security directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from authentication_framework import AuthenticationManager, UserRole, Permission, GranularPermission
from enhanced_audit_logger import AuditLoggerConfig, integrate_audit_logger
from enhanced_mfa_service import EnhancedMFAService, MFAProvider
from oauth2_oidc_provider import OAuth2OIDCProvider, OAuth2GrantType, OIDCScope
from api_security_middleware import SecurityMiddleware
from secure_session_manager import SecureSessionManager

def test_authentication_framework():
    """Test authentication framework examples from documentation"""
    print("Testing Authentication Framework...")
    
    # Initialize authentication manager
    auth_manager = AuthenticationManager()
    
    # Create a new user
    user = auth_manager.create_user(
        username="trader1",
        email="trader1@example.com",
        password="SecurePassword123!",
        roles={UserRole.TRADER}
    )
    
    # Authenticate user (creates session)
    session = auth_manager.authenticate_user(
        username="trader1",
        password="SecurePassword123!",
        ip_address="192.168.1.100"
    )
    
    assert session is not None, "Authentication failed"
    
    # Validate session
    valid_session = auth_manager.validate_session(session.session_id, "192.168.1.100")
    assert valid_session is not None, "Session validation failed"
    
    # Check traditional permission
    can_create_order = auth_manager.check_permission(
        session.session_id,
        Permission.ORDER_CREATE
    )
    assert isinstance(can_create_order, bool), "Permission check failed"
    
    # Check granular permission with context
    can_create_equity_order = auth_manager.check_granular_permission(
        session.session_id,
        GranularPermission.ORDER_CREATE_EQUITY,
        context={"asset_class": "EQUITY"}
    )
    assert isinstance(can_create_equity_order, bool), "Granular permission check failed"
    
    print("Authentication Framework tests passed!")

def test_enhanced_audit_logger():
    """Test enhanced audit logger examples from documentation"""
    print("Testing Enhanced Audit Logger...")
    
    # Initialize authentication manager
    auth_manager = AuthenticationManager()
    
    # Create a test user
    user = auth_manager.create_user(
        username="testuser",
        email="test@example.com",
        password="SecureTest123!",
        roles={UserRole.TRADER}
    )
    
    # Configure audit logger
    config = AuditLoggerConfig()
    config.log_file_path = "test_security_audit.log"
    config.database_path = "test_security_audit.db"
    
    # Integrate with authentication manager
    audit_logger = integrate_audit_logger(auth_manager, config)
    
    # Authenticate user to generate audit events
    session = auth_manager.authenticate_user(
        username="testuser",
        password="SecureTest123!",
        ip_address="192.168.1.100"
    )
    
    assert session is not None, "Authentication failed"
    
    # Close audit logger to flush data
    audit_logger.close()
    
    # Clean up test files
    import os
    if os.path.exists("test_security_audit.log"):
        os.remove("test_security_audit.log")
    if os.path.exists("test_security_audit.db"):
        os.remove("test_security_audit.db")
    
    print("Enhanced Audit Logger tests passed!")

def test_oauth2_oidc_provider():
    """Test OAuth2/OIDC provider examples from documentation"""
    print("Testing OAuth2/OIDC Provider...")
    
    # Initialize provider
    provider = OAuth2OIDCProvider("https://trading-system.example.com")
    
    # Register client application
    client_data = {
        "client_name": "Trading Dashboard",
        "redirect_uris": ["https://dashboard.example.com/callback"],
        "grant_types": ["authorization_code", "refresh_token"],
        "scopes": ["openid", "profile", "email"]
    }
    
    client = provider.register_client(client_data)
    assert client is not None, "Client registration failed"
    assert client.client_name == "Trading Dashboard", "Client name mismatch"
    
    print("OAuth2/OIDC Provider tests passed!")

def test_enhanced_mfa_service():
    """Test enhanced MFA service examples from documentation"""
    print("Testing Enhanced MFA Service...")
    
    # Initialize authentication manager
    auth_manager = AuthenticationManager()
    
    # Create a test user
    user = auth_manager.create_user(
        username="mfauser",
        email="mfa@example.com",
        password="SecureMFA123!",
        roles={UserRole.TRADER}
    )
    
    # Initialize MFA service
    mfa_service = EnhancedMFAService(auth_manager)
    
    # Setup TOTP MFA
    secret, provisioning_uri = mfa_service.initiate_totp_mfa(user.user_id)
    assert secret is not None, "TOTP setup failed"
    assert provisioning_uri is not None, "Provisioning URI generation failed"
    
    print("Enhanced MFA Service tests passed!")

def test_api_security_middleware():
    """Test API security middleware examples from documentation"""
    print("Testing API Security Middleware...")
    
    # Initialize authentication manager
    auth_manager = AuthenticationManager()
    
    # Initialize middleware
    api_middleware = SecurityMiddleware(auth_manager)
    assert api_middleware is not None, "API middleware initialization failed"
    
    print("API Security Middleware tests passed!")

def test_secure_session_manager():
    """Test secure session manager examples from documentation"""
    print("Testing Secure Session Manager...")
    
    # Initialize authentication manager
    auth_manager = AuthenticationManager()
    
    # Create a test user and session
    user = auth_manager.create_user(
        username="sessionuser",
        email="session@example.com",
        password="SecureSession123!",
        roles={UserRole.TRADER}
    )
    
    session = auth_manager.authenticate_user(
        username="sessionuser",
        password="SecureSession123!",
        ip_address="192.168.1.100"
    )
    
    assert session is not None, "Authentication failed"
    
    # Initialize secure session manager
    secure_session_manager = SecureSessionManager(auth_manager)
    assert secure_session_manager is not None, "Secure session manager initialization failed"
    
    # Create secure session token
    access_token, refresh_token = secure_session_manager.create_secure_session(session)
    assert access_token is not None, "Access token creation failed"
    
    # Validate secure token
    secure_session = secure_session_manager.validate_secure_token(access_token, "192.168.1.100")
    assert secure_session is not None, "Secure token validation failed"
    
    print("Secure Session Manager tests passed!")

def main():
    """Run all security documentation tests"""
    print("Running Security Documentation Tests...")
    print("=" * 50)
    
    try:
        test_authentication_framework()
        test_enhanced_audit_logger()
        test_oauth2_oidc_provider()
        test_enhanced_mfa_service()
        test_api_security_middleware()
        test_secure_session_manager()
        
        print("=" * 50)
        print("All Security Documentation Tests Passed!")
        return True
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)