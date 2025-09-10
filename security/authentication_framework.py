#!/usr/bin/env python3
"""
Advanced Authentication and Authorization Framework
Provides comprehensive security features including multi-factor authentication,
role-based access control, session management, and audit logging.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict
import jwt
import bcrypt
import pyotp
import qrcode
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserRole(Enum):
    """User roles with hierarchical permissions"""
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    RISK_MANAGER = "RISK_MANAGER"
    TRADER = "TRADER"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"
    API_USER = "API_USER"
    SYSTEM = "SYSTEM"

class Permission(Enum):
    """System permissions"""
    # Order Management
    ORDER_CREATE = "ORDER_CREATE"
    ORDER_MODIFY = "ORDER_MODIFY"
    ORDER_CANCEL = "ORDER_CANCEL"
    ORDER_VIEW = "ORDER_VIEW"
    ORDER_APPROVE = "ORDER_APPROVE"
    
    # Risk Management
    RISK_VIEW = "RISK_VIEW"
    RISK_MODIFY = "RISK_MODIFY"
    RISK_OVERRIDE = "RISK_OVERRIDE"
    
    # System Administration
    USER_MANAGE = "USER_MANAGE"
    SYSTEM_CONFIG = "SYSTEM_CONFIG"
    AUDIT_VIEW = "AUDIT_VIEW"
    
    # Data Access
    DATA_VIEW = "DATA_VIEW"
    DATA_EXPORT = "DATA_EXPORT"
    SENSITIVE_DATA_VIEW = "SENSITIVE_DATA_VIEW"
    
    # API Access
    API_READ = "API_READ"
    API_WRITE = "API_WRITE"
    API_ADMIN = "API_ADMIN"

class AuthenticationMethod(Enum):
    """Authentication methods"""
    PASSWORD = "PASSWORD"
    MFA_TOTP = "MFA_TOTP"
    MFA_SMS = "MFA_SMS"
    MFA_BIOMETRIC = "MFA_BIOMETRIC"
    API_KEY = "API_KEY"
    JWT_TOKEN = "JWT_TOKEN"
    CERTIFICATE = "CERTIFICATE"

class SessionStatus(Enum):
    """Session status"""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"
    LOCKED = "LOCKED"

class AuditEventType(Enum):
    """Audit event types"""
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    LOGOUT = "LOGOUT"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    MFA_SETUP = "MFA_SETUP"
    MFA_DISABLE = "MFA_DISABLE"
    PERMISSION_GRANTED = "PERMISSION_GRANTED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    ACCOUNT_UNLOCKED = "ACCOUNT_UNLOCKED"
    SENSITIVE_DATA_ACCESS = "SENSITIVE_DATA_ACCESS"
    SYSTEM_CONFIG_CHANGE = "SYSTEM_CONFIG_CHANGE"

class PermissionCategory(Enum):
    """Permission categories for granular access control"""
    ORDER_MANAGEMENT = "ORDER_MANAGEMENT"
    RISK_MANAGEMENT = "RISK_MANAGEMENT"
    PORTFOLIO_MANAGEMENT = "PORTFOLIO_MANAGEMENT"
    MARKET_DATA = "MARKET_DATA"
    ANALYTICS = "ANALYTICS"
    SYSTEM_ADMINISTRATION = "SYSTEM_ADMINISTRATION"
    COMPLIANCE = "COMPLIANCE"
    API_ACCESS = "API_ACCESS"
    FINANCIAL_OPERATIONS = "FINANCIAL_OPERATIONS"
    RESEARCH = "RESEARCH"

class GranularPermission(Enum):
    """Granular system permissions"""
    # Order Management
    ORDER_CREATE_EQUITY = "ORDER_CREATE_EQUITY"
    ORDER_CREATE_FUTURES = "ORDER_CREATE_FUTURES"
    ORDER_CREATE_OPTIONS = "ORDER_CREATE_OPTIONS"
    ORDER_CREATE_FOREX = "ORDER_CREATE_FOREX"
    ORDER_CREATE_CRYPTOCURRENCY = "ORDER_CREATE_CRYPTOCURRENCY"
    ORDER_MODIFY_ANY = "ORDER_MODIFY_ANY"
    ORDER_CANCEL_ANY = "ORDER_CANCEL_ANY"
    ORDER_VIEW_OWN = "ORDER_VIEW_OWN"
    ORDER_VIEW_TEAM = "ORDER_VIEW_TEAM"
    ORDER_VIEW_ALL = "ORDER_VIEW_ALL"
    ORDER_APPROVE_LIMIT_1M = "ORDER_APPROVE_LIMIT_1M"
    ORDER_APPROVE_LIMIT_10M = "ORDER_APPROVE_LIMIT_10M"
    ORDER_APPROVE_LIMIT_ANY = "ORDER_APPROVE_LIMIT_ANY"
    
    # Risk Management
    RISK_VIEW_OWN = "RISK_VIEW_OWN"
    RISK_VIEW_TEAM = "RISK_VIEW_TEAM"
    RISK_VIEW_ALL = "RISK_VIEW_ALL"
    RISK_MODIFY_OWN = "RISK_MODIFY_OWN"
    RISK_MODIFY_TEAM = "RISK_MODIFY_TEAM"
    RISK_OVERRIDE_ANY = "RISK_OVERRIDE_ANY"
    
    # Portfolio Management
    PORTFOLIO_CREATE = "PORTFOLIO_CREATE"
    PORTFOLIO_MODIFY_OWN = "PORTFOLIO_MODIFY_OWN"
    PORTFOLIO_MODIFY_ANY = "PORTFOLIO_MODIFY_ANY"
    PORTFOLIO_VIEW_OWN = "PORTFOLIO_VIEW_OWN"
    PORTFOLIO_VIEW_TEAM = "PORTFOLIO_VIEW_TEAM"
    PORTFOLIO_VIEW_ALL = "PORTFOLIO_VIEW_ALL"
    
    # Market Data
    MARKET_DATA_REALTIME = "MARKET_DATA_REALTIME"
    MARKET_DATA_HISTORICAL = "MARKET_DATA_HISTORICAL"
    MARKET_DATA_DELAYED = "MARKET_DATA_DELAYED"
    
    # Analytics
    ANALYTICS_VIEW_BASIC = "ANALYTICS_VIEW_BASIC"
    ANALYTICS_VIEW_ADVANCED = "ANALYTICS_VIEW_ADVANCED"
    ANALYTICS_EXPORT = "ANALYTICS_EXPORT"
    
    # System Administration
    USER_MANAGE_OWN = "USER_MANAGE_OWN"
    USER_MANAGE_TEAM = "USER_MANAGE_TEAM"
    USER_MANAGE_ALL = "USER_MANAGE_ALL"
    SYSTEM_CONFIG_VIEW = "SYSTEM_CONFIG_VIEW"
    SYSTEM_CONFIG_MODIFY = "SYSTEM_CONFIG_MODIFY"
    AUDIT_VIEW_OWN = "AUDIT_VIEW_OWN"
    AUDIT_VIEW_TEAM = "AUDIT_VIEW_TEAM"
    AUDIT_VIEW_ALL = "AUDIT_VIEW_ALL"
    
    # Compliance
    COMPLIANCE_VIEW = "COMPLIANCE_VIEW"
    COMPLIANCE_EXPORT = "COMPLIANCE_EXPORT"
    COMPLIANCE_OVERRIDE = "COMPLIANCE_OVERRIDE"
    SENSITIVE_DATA_VIEW = "SENSITIVE_DATA_VIEW"
    
    # API Access
    API_READ_BASIC = "API_READ_BASIC"
    API_READ_SENSITIVE = "API_READ_SENSITIVE"
    API_WRITE_BASIC = "API_WRITE_BASIC"
    API_WRITE_SENSITIVE = "API_WRITE_SENSITIVE"
    API_ADMIN = "API_ADMIN"
    
    # Financial Operations
    FINANCIAL_DEPOSIT = "FINANCIAL_DEPOSIT"
    FINANCIAL_WITHDRAW = "FINANCIAL_WITHDRAW"
    FINANCIAL_TRANSFER_INTERNAL = "FINANCIAL_TRANSFER_INTERNAL"
    FINANCIAL_TRANSFER_EXTERNAL = "FINANCIAL_TRANSFER_EXTERNAL"
    
    # Research
    RESEARCH_VIEW = "RESEARCH_VIEW"
    RESEARCH_CREATE = "RESEARCH_CREATE"
    RESEARCH_MODIFY_OWN = "RESEARCH_MODIFY_OWN"
    RESEARCH_MODIFY_ANY = "RESEARCH_MODIFY_ANY"

@dataclass
class TemporaryRole:
    """Temporary role assignment with time constraints"""
    role: UserRole
    start_time: datetime
    end_time: datetime
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ConditionalRole:
    """Conditional role assignment based on specific conditions"""
    role: UserRole
    conditions: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class User:
    """User account information"""
    user_id: str
    username: str
    email: str
    password_hash: str
    salt: str
    roles: Set[UserRole]
    permissions: Set[Permission] = field(default_factory=set)
    granular_permissions: Set[GranularPermission] = field(default_factory=set)
    is_active: bool = True
    is_locked: bool = False
    failed_login_attempts: int = 0
    last_login: Optional[datetime] = None
    password_changed_at: datetime = field(default_factory=datetime.now)
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    mfa_phone_number: Optional[str] = None  # For SMS MFA
    mfa_biometric_template: Optional[str] = None  # For biometric MFA
    api_keys: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)  # User attributes for ABAC
    temporary_roles: List[TemporaryRole] = field(default_factory=list)
    conditional_roles: List[ConditionalRole] = field(default_factory=list)
    
    def __post_init__(self):
        # Auto-assign permissions based on roles
        self.permissions.update(self._get_role_permissions())
        # Auto-assign granular permissions based on roles
        self.granular_permissions.update(self._get_role_granular_permissions())
    
    def _get_role_permissions(self) -> Set[Permission]:
        """Get permissions based on user roles"""
        role_permissions = {
            UserRole.SUPER_ADMIN: set(Permission),  # All permissions
            UserRole.ADMIN: {
                Permission.ORDER_VIEW, Permission.ORDER_CREATE, Permission.ORDER_MODIFY,
                Permission.ORDER_CANCEL, Permission.RISK_VIEW, Permission.RISK_MODIFY,
                Permission.USER_MANAGE, Permission.SYSTEM_CONFIG, Permission.AUDIT_VIEW,
                Permission.DATA_VIEW, Permission.DATA_EXPORT, Permission.API_READ,
                Permission.API_WRITE
            },
            UserRole.RISK_MANAGER: {
                Permission.ORDER_VIEW, Permission.ORDER_APPROVE, Permission.RISK_VIEW,
                Permission.RISK_MODIFY, Permission.RISK_OVERRIDE, Permission.DATA_VIEW,
                Permission.SENSITIVE_DATA_VIEW, Permission.AUDIT_VIEW
            },
            UserRole.TRADER: {
                Permission.ORDER_CREATE, Permission.ORDER_MODIFY, Permission.ORDER_CANCEL,
                Permission.ORDER_VIEW, Permission.RISK_VIEW, Permission.DATA_VIEW,
                Permission.API_READ, Permission.API_WRITE
            },
            UserRole.ANALYST: {
                Permission.ORDER_VIEW, Permission.RISK_VIEW, Permission.DATA_VIEW,
                Permission.DATA_EXPORT, Permission.API_READ
            },
            UserRole.VIEWER: {
                Permission.ORDER_VIEW, Permission.RISK_VIEW, Permission.DATA_VIEW
            },
            UserRole.API_USER: {
                Permission.API_READ, Permission.API_WRITE, Permission.ORDER_VIEW,
                Permission.DATA_VIEW
            },
            UserRole.SYSTEM: set(Permission)  # System accounts have all permissions
        }
        
        permissions = set()
        for role in self.roles:
            permissions.update(role_permissions.get(role, set()))
        
        return permissions
    
    def _get_role_granular_permissions(self) -> Set[GranularPermission]:
        """Get granular permissions based on user roles"""
        role_granular_permissions = {
            UserRole.SUPER_ADMIN: set(GranularPermission),  # All granular permissions
            UserRole.ADMIN: {
                GranularPermission.ORDER_VIEW_ALL, GranularPermission.ORDER_CREATE_EQUITY,
                GranularPermission.ORDER_CREATE_FUTURES, GranularPermission.ORDER_MODIFY_ANY,
                GranularPermission.ORDER_CANCEL_ANY, GranularPermission.RISK_VIEW_ALL,
                GranularPermission.RISK_MODIFY_TEAM, GranularPermission.USER_MANAGE_TEAM,
                GranularPermission.SYSTEM_CONFIG_VIEW, GranularPermission.AUDIT_VIEW_ALL,
                GranularPermission.MARKET_DATA_REALTIME, GranularPermission.ANALYTICS_EXPORT,
                GranularPermission.API_READ_BASIC, GranularPermission.API_WRITE_BASIC
            },
            UserRole.RISK_MANAGER: {
                GranularPermission.ORDER_VIEW_TEAM, GranularPermission.ORDER_APPROVE_LIMIT_10M,
                GranularPermission.RISK_VIEW_ALL, GranularPermission.RISK_MODIFY_TEAM,
                GranularPermission.RISK_OVERRIDE_ANY, GranularPermission.MARKET_DATA_REALTIME,
                GranularPermission.SENSITIVE_DATA_VIEW, GranularPermission.AUDIT_VIEW_TEAM
            },
            UserRole.TRADER: {
                GranularPermission.ORDER_CREATE_EQUITY, GranularPermission.ORDER_CREATE_FUTURES,
                GranularPermission.ORDER_MODIFY_ANY, GranularPermission.ORDER_CANCEL_ANY,
                GranularPermission.ORDER_VIEW_OWN, GranularPermission.RISK_VIEW_OWN,
                GranularPermission.MARKET_DATA_REALTIME, GranularPermission.API_READ_BASIC,
                GranularPermission.API_WRITE_BASIC
            },
            UserRole.ANALYST: {
                GranularPermission.ORDER_VIEW_OWN, GranularPermission.RISK_VIEW_OWN,
                GranularPermission.MARKET_DATA_REALTIME, GranularPermission.ANALYTICS_EXPORT,
                GranularPermission.ANALYTICS_VIEW_BASIC, GranularPermission.API_READ_BASIC
            },
            UserRole.VIEWER: {
                GranularPermission.ORDER_VIEW_OWN, GranularPermission.RISK_VIEW_OWN,
                GranularPermission.MARKET_DATA_REALTIME
            },
            UserRole.API_USER: {
                GranularPermission.API_READ_BASIC, GranularPermission.API_WRITE_BASIC,
                GranularPermission.ORDER_VIEW_OWN, GranularPermission.MARKET_DATA_REALTIME
            },
            UserRole.SYSTEM: set(GranularPermission)  # System accounts have all granular permissions
        }
        
        permissions = set()
        for role in self.roles:
            permissions.update(role_granular_permissions.get(role, set()))
        
        # Add permissions from temporary roles
        now = datetime.now()
        for temp_role in self.temporary_roles:
            if temp_role.start_time <= now <= temp_role.end_time:
                permissions.update(role_granular_permissions.get(temp_role.role, set()))
        
        # Add permissions from conditional roles (simplified check)
        for cond_role in self.conditional_roles:
            # In a real implementation, this would evaluate the conditions
            # For now, we'll assume conditions are met
            permissions.update(role_granular_permissions.get(cond_role.role, set()))
        
        return permissions
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions
    
    def has_granular_permission(self, permission: GranularPermission, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if user has specific granular permission with context"""
        # Check if user has the permission at all
        if permission not in self.granular_permissions:
            return False
        
        # Check based on context (simplified implementation)
        if context:
            # Example context-based checks
            if permission == GranularPermission.ORDER_CREATE_EQUITY and context.get('asset_class') != 'EQUITY':
                return False
            if permission == GranularPermission.ORDER_APPROVE_LIMIT_10M and context.get('order_value', 0) > 10000000:
                # Check if user has higher approval limit
                return GranularPermission.ORDER_APPROVE_LIMIT_ANY in self.granular_permissions
        
        return True
    
    def has_role(self, role: UserRole) -> bool:
        """Check if user has specific role"""
        if role in self.roles:
            return True
        
        # Check temporary roles
        now = datetime.now()
        for temp_role in self.temporary_roles:
            if temp_role.role == role and temp_role.start_time <= now <= temp_role.end_time:
                return True
        
        # Check conditional roles (simplified)
        for cond_role in self.conditional_roles:
            if cond_role.role == role:
                # In a real implementation, this would evaluate the conditions
                return True
        
        return False

@dataclass
class Session:
    """User session information"""
    session_id: str
    user_id: str
    username: str
    roles: Set[UserRole]
    permissions: Set[Permission]
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    ip_address: str
    user_agent: str
    status: SessionStatus = SessionStatus.ACTIVE
    mfa_verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.now() > self.expires_at
    
    @property
    def is_active(self) -> bool:
        """Check if session is active"""
        return self.status == SessionStatus.ACTIVE and not self.is_expired
    
    def extend_session(self, duration: timedelta = timedelta(hours=8)):
        """Extend session expiration"""
        self.expires_at = datetime.now() + duration
        self.last_activity = datetime.now()

@dataclass
class AuditEvent:
    """Security audit event"""
    event_id: str
    event_type: AuditEventType
    user_id: Optional[str]
    username: Optional[str]
    session_id: Optional[str]
    timestamp: datetime
    ip_address: str
    user_agent: str
    resource: Optional[str]
    action: Optional[str]
    result: str  # SUCCESS, FAILURE, ERROR
    details: Dict[str, Any]
    risk_score: int = 0  # 0-100 risk score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'user_id': self.user_id,
            'username': self.username,
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'resource': self.resource,
            'action': self.action,
            'result': self.result,
            'details': self.details,
            'risk_score': self.risk_score
        }

class SecurityConfig:
    """Security configuration settings"""
    
    def __init__(self):
        # Password policy
        self.password_min_length = 12
        self.password_require_uppercase = True
        self.password_require_lowercase = True
        self.password_require_numbers = True
        self.password_require_symbols = True
        self.password_history_count = 5
        self.password_max_age_days = 90
        
        # Account lockout policy
        self.max_failed_login_attempts = 5
        self.lockout_duration_minutes = 30
        self.lockout_escalation_enabled = True
        
        # Session management
        self.session_timeout_minutes = 480  # 8 hours
        self.session_idle_timeout_minutes = 60
        self.max_concurrent_sessions = 3
        self.session_ip_validation = True
        
        # MFA settings
        self.mfa_required_for_roles = {UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.RISK_MANAGER}
        self.mfa_backup_codes_count = 10
        self.mfa_window_seconds = 30
        self.mfa_sms_provider = "twilio"  # Default SMS provider
        self.mfa_sms_template = "Your verification code is: {code}"
        self.mfa_biometric_threshold = 0.85  # Biometric matching threshold
        
        # API security
        self.api_key_length = 64
        self.api_key_expiry_days = 365
        self.api_rate_limit_per_minute = 1000
        
        # JWT settings
        self.jwt_secret_key = os.environ.get('JWT_SECRET_KEY', secrets.token_urlsafe(64))
        self.jwt_algorithm = 'HS256'
        self.jwt_expiry_hours = 24
        
        # Audit settings
        self.audit_retention_days = 2555  # 7 years
        self.audit_sensitive_operations = True
        self.audit_failed_attempts = True

class AuthenticationManager:
    """Advanced authentication and authorization manager"""
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, Session] = {}
        self.audit_events: List[AuditEvent] = []
        self.failed_login_tracking: Dict[str, List[datetime]] = defaultdict(list)
        self.api_keys: Dict[str, str] = {}  # api_key -> user_id
        self.password_history: Dict[str, List[str]] = defaultdict(list)
        self.mfa_backup_codes: Dict[str, Set[str]] = defaultdict(set)
        self.mfa_sms_codes: Dict[str, Tuple[str, datetime]] = {}  # user_id -> (code, expiry)
        self.mfa_biometric_data: Dict[str, str] = {}  # user_id -> biometric_template
        
        # OAuth2/OIDC integration
        self.oauth2_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Initialize encryption for sensitive data
        self._init_encryption()
        
        # Create default admin user
        self._create_default_admin()
        
        logger.info("Authentication Manager initialized")
    
    def _init_encryption(self):
        """Initialize encryption for sensitive data"""
        # Generate or load encryption key
        key = os.environ.get('ENCRYPTION_KEY')
        if not key:
            key = Fernet.generate_key()
            logger.warning("Generated new encryption key. Set ENCRYPTION_KEY environment variable for production.")
        else:
            key = key.encode()
        
        self.cipher_suite = Fernet(key)
    
    def _create_default_admin(self):
        """Create default admin user if none exists"""
        admin_username = os.environ.get('DEFAULT_ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'TradingSystem2024!')
        
        if not any(UserRole.SUPER_ADMIN in user.roles for user in self.users.values()):
            admin_user = self.create_user(
                username=admin_username,
                email='admin@tradingsystem.com',
                password=admin_password,
                roles={UserRole.SUPER_ADMIN}
            )
            logger.info(f"Created default admin user: {admin_username}")
    
    def _hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hash password with salt"""
        if salt is None:
            salt = bcrypt.gensalt().decode('utf-8')
        
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt.encode('utf-8')).decode('utf-8')
        return password_hash, salt
    
    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def _validate_password_policy(self, password: str) -> Tuple[bool, List[str]]:
        """Validate password against security policy"""
        errors = []
        
        if len(password) < self.config.password_min_length:
            errors.append(f"Password must be at least {self.config.password_min_length} characters long")
        
        if self.config.password_require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.config.password_require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.config.password_require_numbers and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
        
        if self.config.password_require_symbols and not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            errors.append("Password must contain at least one special character")
        
        return len(errors) == 0, errors
    
    def _generate_api_key(self) -> str:
        """Generate secure API key"""
        return secrets.token_urlsafe(self.config.api_key_length)
    
    def _generate_mfa_secret(self) -> str:
        """Generate MFA secret"""
        return pyotp.random_base32()
    
    def _generate_backup_codes(self) -> Set[str]:
        """Generate MFA backup codes"""
        codes = set()
        for _ in range(self.config.mfa_backup_codes_count):
            code = ''.join(secrets.choice('0123456789') for _ in range(8))
            codes.add(code)
        return codes
    
    def _generate_sms_code(self) -> str:
        """Generate SMS verification code"""
        return ''.join(secrets.choice('0123456789') for _ in range(6))
    
    def _send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS message (placeholder implementation)"""
        # In a real implementation, this would integrate with an SMS provider like Twilio
        logger.info(f"Sending SMS to {phone_number}: {message}")
        # Simulate SMS sending
        return True
    
    def _hash_biometric_data(self, biometric_data: str) -> str:
        """Hash biometric data for storage"""
        # In a real implementation, this would use a secure hashing algorithm appropriate for biometric data
        return hashlib.sha256(biometric_data.encode()).hexdigest()
    
    def _compare_biometric_data(self, stored_template: str, provided_data: str) -> bool:
        """Compare biometric data with stored template"""
        # In a real implementation, this would use a proper biometric matching algorithm
        # For this implementation, we'll use a simple similarity check
        provided_hash = self._hash_biometric_data(provided_data)
        # Simulate matching with a threshold
        return provided_hash == stored_template  # Simplified for demonstration
    
    def _log_audit_event(self, event_type: AuditEventType, user_id: Optional[str] = None,
                        username: Optional[str] = None, session_id: Optional[str] = None,
                        ip_address: str = "unknown", user_agent: str = "unknown",
                        resource: Optional[str] = None, action: Optional[str] = None,
                        result: str = "SUCCESS", details: Optional[Dict[str, Any]] = None,
                        risk_score: int = 0):
        """Log security audit event"""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            user_id=user_id,
            username=username,
            session_id=session_id,
            timestamp=datetime.now(),
            ip_address=ip_address,
            user_agent=user_agent,
            resource=resource,
            action=action,
            result=result,
            details=details or {},
            risk_score=risk_score
        )
        
        self.audit_events.append(event)
        
        # Log to system logger
        log_level = logging.WARNING if result == "FAILURE" else logging.INFO
        logger.log(log_level, f"Security Event: {event_type.value} - {result} - User: {username} - IP: {ip_address}")
        
        # Clean up old audit events
        cutoff_date = datetime.now() - timedelta(days=self.config.audit_retention_days)
        self.audit_events = [e for e in self.audit_events if e.timestamp > cutoff_date]
    
    def create_user(self, username: str, email: str, password: str, 
                   roles: Set[UserRole], **kwargs) -> User:
        """Create new user account"""
        # Validate password
        is_valid, errors = self._validate_password_policy(password)
        if not is_valid:
            raise ValueError(f"Password policy violation: {'; '.join(errors)}")
        
        # Check if username already exists
        if any(user.username == username for user in self.users.values()):
            raise ValueError(f"Username '{username}' already exists")
        
        # Hash password
        password_hash, salt = self._hash_password(password)
        
        # Create user
        user_id = str(uuid.uuid4())
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            salt=salt,
            roles=roles,
            **kwargs
        )
        
        self.users[user_id] = user
        
        # Store password in history
        self.password_history[user_id].append(password_hash)
        
        self._log_audit_event(
            AuditEventType.SYSTEM_CONFIG_CHANGE,
            details={'action': 'user_created', 'username': username, 'roles': [r.value for r in roles]}
        )
        
        logger.info(f"Created user: {username} with roles: {[r.value for r in roles]}")
        return user
    
    def authenticate_user(self, username: str, password: str, ip_address: str = "unknown",
                         user_agent: str = "unknown", mfa_code: Optional[str] = None) -> Optional[Session]:
        """Authenticate user and create session"""
        # Find user
        user = None
        for u in self.users.values():
            if u.username == username:
                user = u
                break
        
        if not user:
            self._log_audit_event(
                AuditEventType.LOGIN_FAILURE,
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                result="FAILURE",
                details={'reason': 'user_not_found'},
                risk_score=30
            )
            return None
        
        # Check if account is locked
        if user.is_locked:
            self._log_audit_event(
                AuditEventType.LOGIN_FAILURE,
                user_id=user.user_id,
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                result="FAILURE",
                details={'reason': 'account_locked'},
                risk_score=50
            )
            return None
        
        # Check if account is active
        if not user.is_active:
            self._log_audit_event(
                AuditEventType.LOGIN_FAILURE,
                user_id=user.user_id,
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                result="FAILURE",
                details={'reason': 'account_inactive'},
                risk_score=40
            )
            return None
        
        # Verify password
        if not self._verify_password(password, user.password_hash, user.salt):
            # Track failed login attempt
            user.failed_login_attempts += 1
            self.failed_login_tracking[user.user_id].append(datetime.now())
            
            # Check if account should be locked
            if user.failed_login_attempts >= self.config.max_failed_login_attempts:
                user.is_locked = True
                self._log_audit_event(
                    AuditEventType.ACCOUNT_LOCKED,
                    user_id=user.user_id,
                    username=username,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={'failed_attempts': user.failed_login_attempts},
                    risk_score=70
                )
            
            self._log_audit_event(
                AuditEventType.LOGIN_FAILURE,
                user_id=user.user_id,
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                result="FAILURE",
                details={'reason': 'invalid_password', 'attempt': user.failed_login_attempts},
                risk_score=40
            )
            return None
        
        # Check MFA if enabled
        mfa_verified = True
        if user.mfa_enabled:
            if not mfa_code:
                self._log_audit_event(
                    AuditEventType.LOGIN_FAILURE,
                    user_id=user.user_id,
                    username=username,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    result="FAILURE",
                    details={'reason': 'mfa_required'},
                    risk_score=20
                )
                return None
            
            if not self.verify_mfa_code(user.user_id, mfa_code):
                self._log_audit_event(
                    AuditEventType.LOGIN_FAILURE,
                    user_id=user.user_id,
                    username=username,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    result="FAILURE",
                    details={'reason': 'invalid_mfa_code'},
                    risk_score=60
                )
                return None
        
        # Reset failed login attempts on successful authentication
        user.failed_login_attempts = 0
        user.last_login = datetime.now()
        
        # Create session
        session = self._create_session(user, ip_address, user_agent, mfa_verified)
        
        self._log_audit_event(
            AuditEventType.LOGIN_SUCCESS,
            user_id=user.user_id,
            username=username,
            session_id=session.session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={'mfa_used': user.mfa_enabled}
        )
        
        logger.info(f"User authenticated: {username} from {ip_address}")
        return session
    
    def _create_session(self, user: User, ip_address: str, user_agent: str, mfa_verified: bool) -> Session:
        """Create user session"""
        session_id = str(uuid.uuid4())
        now = datetime.now()
        expires_at = now + timedelta(minutes=self.config.session_timeout_minutes)
        
        session = Session(
            session_id=session_id,
            user_id=user.user_id,
            username=user.username,
            roles=user.roles,
            permissions=user.permissions,
            created_at=now,
            last_activity=now,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            mfa_verified=mfa_verified
        )
        
        # Check concurrent session limit
        active_sessions = [s for s in self.sessions.values() 
                          if s.user_id == user.user_id and s.is_active]
        
        if len(active_sessions) >= self.config.max_concurrent_sessions:
            # Terminate oldest session
            oldest_session = min(active_sessions, key=lambda s: s.created_at)
            self.terminate_session(oldest_session.session_id, "concurrent_limit_exceeded")
        
        self.sessions[session_id] = session
        return session
    
    def integrate_oauth2_session(self, session_id: str, access_token: str, 
                               user_id: str, client_id: str, scopes: List[str],
                               expires_at: datetime, refresh_expires_at: Optional[datetime] = None):
        """Integrate OAuth2 session with authentication manager"""
        self.oauth2_sessions[session_id] = {
            'access_token': access_token,
            'user_id': user_id,
            'client_id': client_id,
            'scopes': scopes,
            'expires_at': expires_at,
            'refresh_expires_at': refresh_expires_at,
            'created_at': datetime.now()
        }
        
        self._log_audit_event(
            AuditEventType.LOGIN_SUCCESS,
            user_id=user_id,
            username=self.users.get(user_id).username if user_id in self.users else "unknown",
            session_id=session_id,
            details={'auth_method': 'OAuth2', 'client_id': client_id}
        )
        
        logger.info(f"Integrated OAuth2 session: {session_id}")
    
    def validate_session(self, session_id: str, ip_address: str = "unknown") -> Optional[Session]:
        """Validate and refresh session (enhanced with OAuth2 support)"""
        # First check regular sessions
        session = self.sessions.get(session_id)
        
        if session:
            # Check if session is expired
            if session.is_expired:
                session.status = SessionStatus.EXPIRED
                self._log_audit_event(
                    AuditEventType.SESSION_EXPIRED,
                    user_id=session.user_id,
                    username=session.username,
                    session_id=session_id,
                    ip_address=ip_address
                )
                return None
            
            # Check IP validation if enabled
            if self.config.session_ip_validation and session.ip_address != ip_address:
                self._log_audit_event(
                    AuditEventType.LOGIN_FAILURE,
                    user_id=session.user_id,
                    username=session.username,
                    session_id=session_id,
                    ip_address=ip_address,
                    result="FAILURE",
                    details={'reason': 'ip_mismatch', 'original_ip': session.ip_address},
                    risk_score=80
                )
                return None
            
            # Check idle timeout
            idle_time = datetime.now() - session.last_activity
            if idle_time > timedelta(minutes=self.config.session_idle_timeout_minutes):
                session.status = SessionStatus.EXPIRED
                self._log_audit_event(
                    AuditEventType.SESSION_EXPIRED,
                    user_id=session.user_id,
                    username=session.username,
                    session_id=session_id,
                    ip_address=ip_address,
                    details={'reason': 'idle_timeout'}
                )
                return None
            
            # Update last activity
            session.last_activity = datetime.now()
            return session
        
        # If not found, check OAuth2 sessions
        oauth2_session = self.oauth2_sessions.get(session_id)
        if oauth2_session:
            # Check if OAuth2 session is expired
            if datetime.now() > oauth2_session['expires_at']:
                del self.oauth2_sessions[session_id]
                self._log_audit_event(
                    AuditEventType.SESSION_EXPIRED,
                    user_id=oauth2_session['user_id'],
                    session_id=session_id
                )
                return None
            
            # Get user information
            user = self.users.get(oauth2_session['user_id'])
            if not user:
                return None
            
            # Create compatible Session object
            return Session(
                session_id=session_id,
                user_id=user.user_id,
                username=user.username,
                roles=user.roles,
                permissions=user.permissions,
                created_at=oauth2_session['created_at'],
                last_activity=datetime.now(),
                expires_at=oauth2_session['expires_at'],
                ip_address=ip_address,
                user_agent="OAuth2 Client",
                mfa_verified=True,  # OAuth2 is considered verified
                metadata={'oauth2_scopes': oauth2_session['scopes']}
            )
        
        return None
    
    def terminate_session(self, session_id: str, reason: str = "user_logout"):
        """Terminate user session"""
        session = self.sessions.get(session_id)
        if session:
            session.status = SessionStatus.TERMINATED
            self._log_audit_event(
                AuditEventType.LOGOUT,
                user_id=session.user_id,
                username=session.username,
                session_id=session_id,
                details={'reason': reason}
            )
    
    def setup_sms_mfa(self, user_id: str, phone_number: str) -> bool:
        """Setup SMS MFA for user"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Validate phone number format
        if not phone_number or len(phone_number) < 10:
            raise ValueError("Invalid phone number")
        
        # Store phone number
        user.mfa_phone_number = phone_number
        user.mfa_enabled = True
        
        self._log_audit_event(
            AuditEventType.MFA_SETUP,
            user_id=user_id,
            username=user.username,
            details={'mfa_type': 'SMS', 'phone_number': phone_number[-4:]}  # Only log last 4 digits
        )
        
        return True
    
    def setup_biometric_mfa(self, user_id: str, biometric_template: str) -> bool:
        """Setup biometric MFA for user"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Store biometric template (hashed for security)
        hashed_template = self._hash_biometric_data(biometric_template)
        user.mfa_biometric_template = hashed_template
        user.mfa_enabled = True
        
        self._log_audit_event(
            AuditEventType.MFA_SETUP,
            user_id=user_id,
            username=user.username,
            details={'mfa_type': 'BIOMETRIC'}
        )
        
        return True
    
    def send_sms_mfa_code(self, user_id: str) -> bool:
        """Send SMS MFA code to user"""
        user = self.users.get(user_id)
        if not user or not user.mfa_phone_number:
            return False
        
        # Generate code
        code = self._generate_sms_code()
        expiry = datetime.now() + timedelta(minutes=5)  # Code expires in 5 minutes
        
        # Store code with expiry
        self.mfa_sms_codes[user_id] = (code, expiry)
        
        # Send SMS
        message = self.config.mfa_sms_template.format(code=code)
        return self._send_sms(user.mfa_phone_number, message)
    
    def verify_sms_mfa_code(self, user_id: str, code: str) -> bool:
        """Verify SMS MFA code"""
        user = self.users.get(user_id)
        if not user or not user.mfa_enabled:
            return False
        
        # Check if code exists and is not expired
        if user_id not in self.mfa_sms_codes:
            return False
        
        stored_code, expiry = self.mfa_sms_codes[user_id]
        
        # Check if code is expired
        if datetime.now() > expiry:
            del self.mfa_sms_codes[user_id]
            return False
        
        # Check if code matches
        if stored_code == code:
            # Remove used code
            del self.mfa_sms_codes[user_id]
            return True
        
        return False
    
    def verify_biometric_mfa(self, user_id: str, biometric_data: str) -> bool:
        """Verify biometric MFA data"""
        user = self.users.get(user_id)
        if not user or not user.mfa_enabled or not user.mfa_biometric_template:
            return False
        
        # Compare biometric data with stored template
        return self._compare_biometric_data(user.mfa_biometric_template, biometric_data)
    
    def setup_mfa(self, user_id: str) -> Tuple[str, str]:
        """Setup TOTP MFA for user"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Generate MFA secret
        secret = self._generate_mfa_secret()
        user.mfa_secret = secret
        user.mfa_enabled = True
        
        # Generate backup codes
        backup_codes = self._generate_backup_codes()
        self.mfa_backup_codes[user_id] = backup_codes
        
        # Generate QR code for authenticator app
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="Trading System"
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        self._log_audit_event(
            AuditEventType.MFA_SETUP,
            user_id=user_id,
            username=user.username,
            details={'mfa_type': 'TOTP', 'backup_codes_generated': len(backup_codes)}
        )
        
        return secret, provisioning_uri
    
    def verify_mfa_code(self, user_id: str, code: str, mfa_type: AuthenticationMethod = AuthenticationMethod.MFA_TOTP) -> bool:
        """Verify MFA code based on the specified MFA type"""
        user = self.users.get(user_id)
        if not user or not user.mfa_enabled:
            return False
        
        if mfa_type == AuthenticationMethod.MFA_TOTP:
            # Check if it's a backup code
            if code in self.mfa_backup_codes.get(user_id, set()):
                self.mfa_backup_codes[user_id].remove(code)
                return True
            
            # Verify TOTP code
            if user.mfa_secret:
                totp = pyotp.TOTP(user.mfa_secret)
                return totp.verify(code, valid_window=self.config.mfa_window_seconds // 30)
        
        elif mfa_type == AuthenticationMethod.MFA_SMS:
            # Verify SMS code
            return self.verify_sms_mfa_code(user_id, code)
        
        elif mfa_type == AuthenticationMethod.MFA_BIOMETRIC:
            # For biometric, the "code" parameter is actually the biometric data
            return self.verify_biometric_mfa(user_id, code)
        
        return False
    
    def disable_mfa(self, user_id: str):
        """Disable MFA for user"""
        user = self.users.get(user_id)
        if user:
            user.mfa_enabled = False
            user.mfa_secret = None
            self.mfa_backup_codes.pop(user_id, None)
            
            self._log_audit_event(
                AuditEventType.MFA_DISABLE,
                user_id=user_id,
                username=user.username
            )
    
    def generate_api_key(self, user_id: str, description: str = "") -> str:
        """Generate API key for user"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")
        
        api_key = self._generate_api_key()
        self.api_keys[api_key] = user_id
        user.api_keys.append(api_key)
        
        self._log_audit_event(
            AuditEventType.SYSTEM_CONFIG_CHANGE,
            user_id=user_id,
            username=user.username,
            details={'action': 'api_key_generated', 'description': description}
        )
        
        return api_key
    
    def revoke_api_key(self, api_key: str):
        """Revoke API key"""
        user_id = self.api_keys.pop(api_key, None)
        if user_id:
            user = self.users.get(user_id)
            if user and api_key in user.api_keys:
                user.api_keys.remove(api_key)
                
                self._log_audit_event(
                    AuditEventType.SYSTEM_CONFIG_CHANGE,
                    user_id=user_id,
                    username=user.username,
                    details={'action': 'api_key_revoked'}
                )
    
    def authenticate_api_key(self, api_key: str) -> Optional[User]:
        """Authenticate using API key"""
        user_id = self.api_keys.get(api_key)
        if user_id:
            user = self.users.get(user_id)
            if user and user.is_active and not user.is_locked:
                return user
        return None
    
    def generate_jwt_token(self, user_id: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """Generate JWT token for user"""
        user = self.users.get(user_id)
        if not user:
            raise ValueError("User not found")
        
        now = datetime.now()
        payload = {
            'user_id': user_id,
            'username': user.username,
            'roles': [role.value for role in user.roles],
            'permissions': [perm.value for perm in user.permissions],
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(hours=self.config.jwt_expiry_hours)).timestamp()),
            'iss': 'trading-system'
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.config.jwt_secret_key, algorithm=self.config.jwt_algorithm)
        return token
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.config.jwt_secret_key, algorithms=[self.config.jwt_algorithm])
            
            # Check if user still exists and is active
            user = self.users.get(payload.get('user_id'))
            if not user or not user.is_active or user.is_locked:
                return None
            
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """Change user password"""
        user = self.users.get(user_id)
        if not user:
            return False
        
        # Verify old password
        if not self._verify_password(old_password, user.password_hash, user.salt):
            return False
        
        # Validate new password
        is_valid, errors = self._validate_password_policy(new_password)
        if not is_valid:
            raise ValueError(f"Password policy violation: {'; '.join(errors)}")
        
        # Check password history
        new_hash, _ = self._hash_password(new_password, user.salt)
        if new_hash in self.password_history.get(user_id, []):
            raise ValueError("Password has been used recently")
        
        # Update password
        user.password_hash, user.salt = self._hash_password(new_password)
        user.password_changed_at = datetime.now()
        
        # Update password history
        history = self.password_history[user_id]
        history.append(user.password_hash)
        if len(history) > self.config.password_history_count:
            history.pop(0)
        
        self._log_audit_event(
            AuditEventType.PASSWORD_CHANGE,
            user_id=user_id,
            username=user.username
        )
        
        return True
    
    def check_permission(self, session_id: str, permission: Permission, 
                        resource: Optional[str] = None) -> bool:
        """Check if session has permission for resource"""
        session = self.sessions.get(session_id)
        if not session or not session.is_active:
            self._log_audit_event(
                AuditEventType.PERMISSION_DENIED,
                session_id=session_id,
                resource=resource,
                action=permission.value,
                result="FAILURE",
                details={'reason': 'invalid_session'},
                risk_score=40
            )
            return False
        
        user = self.users.get(session.user_id)
        if not user or not user.is_active or user.is_locked:
            self._log_audit_event(
                AuditEventType.PERMISSION_DENIED,
                user_id=session.user_id,
                username=session.username,
                session_id=session_id,
                resource=resource,
                action=permission.value,
                result="FAILURE",
                details={'reason': 'user_inactive'},
                risk_score=50
            )
            return False
        
        has_permission = user.has_permission(permission)
        
        # Log permission check
        event_type = AuditEventType.PERMISSION_GRANTED if has_permission else AuditEventType.PERMISSION_DENIED
        self._log_audit_event(
            event_type,
            user_id=session.user_id,
            username=session.username,
            session_id=session_id,
            resource=resource,
            action=permission.value,
            result="SUCCESS" if has_permission else "FAILURE",
            risk_score=0 if has_permission else 30
        )
        
        # Log sensitive data access
        if has_permission and permission == Permission.SENSITIVE_DATA_VIEW:
            self._log_audit_event(
                AuditEventType.SENSITIVE_DATA_ACCESS,
                user_id=session.user_id,
                username=session.username,
                session_id=session_id,
                resource=resource,
                action=permission.value,
                details={'data_type': resource}
            )
        
        return has_permission
    
    def check_granular_permission(self, session_id: str, permission: GranularPermission,
                                resource: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if session has granular permission for resource with context"""
        session = self.sessions.get(session_id)
        if not session or not session.is_active:
            self._log_audit_event(
                AuditEventType.PERMISSION_DENIED,
                session_id=session_id,
                resource=resource,
                action=permission.value,
                result="FAILURE",
                details={'reason': 'invalid_session', 'permission_type': 'granular'},
                risk_score=40
            )
            return False
        
        user = self.users.get(session.user_id)
        if not user or not user.is_active or user.is_locked:
            self._log_audit_event(
                AuditEventType.PERMISSION_DENIED,
                user_id=session.user_id,
                username=session.username,
                session_id=session_id,
                resource=resource,
                action=permission.value,
                result="FAILURE",
                details={'reason': 'user_inactive', 'permission_type': 'granular'},
                risk_score=50
            )
            return False
        
        has_permission = user.has_granular_permission(permission, context)
        
        # Log permission check
        event_type = AuditEventType.PERMISSION_GRANTED if has_permission else AuditEventType.PERMISSION_DENIED
        self._log_audit_event(
            event_type,
            user_id=session.user_id,
            username=session.username,
            session_id=session_id,
            resource=resource,
            action=permission.value,
            result="SUCCESS" if has_permission else "FAILURE",
            risk_score=0 if has_permission else 30,
            details={'permission_type': 'granular', 'context': context}
        )
        
        # Log sensitive data access
        if has_permission and permission in [
            GranularPermission.MARKET_DATA_REALTIME,
            GranularPermission.API_READ_SENSITIVE,
            GranularPermission.FINANCIAL_TRANSFER_EXTERNAL
        ]:
            self._log_audit_event(
                AuditEventType.SENSITIVE_DATA_ACCESS,
                user_id=session.user_id,
                username=session.username,
                session_id=session_id,
                resource=resource,
                action=permission.value,
                details={'data_type': resource, 'permission_type': 'granular'}
            )
        
        return has_permission
    
    def check_oauth2_permission(self, session_id: str, permission: Permission) -> bool:
        """Check if OAuth2 session has specific permission"""
        oauth2_session = self.oauth2_sessions.get(session_id)
        if not oauth2_session:
            return False
        
        # Check if session is expired
        if datetime.now() > oauth2_session['expires_at']:
            return False
        
        # Get user
        user = self.users.get(oauth2_session['user_id'])
        if not user:
            return False
        
        # Check permission
        return user.has_permission(permission)
    
    def unlock_account(self, user_id: str, admin_user_id: str):
        """Unlock user account (admin function)"""
        user = self.users.get(user_id)
        admin_user = self.users.get(admin_user_id)
        
        if not user or not admin_user:
            return False
        
        if not admin_user.has_permission(Permission.USER_MANAGE):
            return False
        
        user.is_locked = False
        user.failed_login_attempts = 0
        
        self._log_audit_event(
            AuditEventType.ACCOUNT_UNLOCKED,
            user_id=user_id,
            username=user.username,
            details={'unlocked_by': admin_user.username}
        )
        
        return True
    
    def assign_temporary_role(self, user_id: str, role: UserRole,
                             start_time: datetime, end_time: datetime) -> bool:
        """Assign a role for a specific time period"""
        user = self.users.get(user_id)
        if not user:
            return False
        
        temp_role = TemporaryRole(role=role, start_time=start_time, end_time=end_time)
        user.temporary_roles.append(temp_role)
        
        # Update user's granular permissions
        user.granular_permissions.update(user._get_role_granular_permissions())
        
        self._log_audit_event(
            AuditEventType.SYSTEM_CONFIG_CHANGE,
            user_id=user_id,
            username=user.username,
            details={'action': 'temporary_role_assigned', 'role': role.value,
                    'start_time': start_time.isoformat(), 'end_time': end_time.isoformat()}
        )
        
        return True
    
    def assign_conditional_role(self, user_id: str, role: UserRole,
                               conditions: Dict[str, Any]) -> bool:
        """Assign a role based on specific conditions"""
        user = self.users.get(user_id)
        if not user:
            return False
        
        cond_role = ConditionalRole(role=role, conditions=conditions)
        user.conditional_roles.append(cond_role)
        
        # Update user's granular permissions
        user.granular_permissions.update(user._get_role_granular_permissions())
        
        self._log_audit_event(
            AuditEventType.SYSTEM_CONFIG_CHANGE,
            user_id=user_id,
            username=user.username,
            details={'action': 'conditional_role_assigned', 'role': role.value,
                    'conditions': conditions}
        )
        
        return True
    
    def get_audit_events(self, user_id: Optional[str] = None, 
                        event_type: Optional[AuditEventType] = None,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None,
                        limit: int = 1000) -> List[AuditEvent]:
        """Get audit events with filtering"""
        events = self.audit_events
        
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if start_date:
            events = [e for e in events if e.timestamp >= start_date]
        
        if end_date:
            events = [e for e in events if e.timestamp <= end_date]
        
        # Sort by timestamp (newest first) and limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics and statistics"""
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        
        recent_events = [e for e in self.audit_events if e.timestamp >= last_24h]
        weekly_events = [e for e in self.audit_events if e.timestamp >= last_7d]
        
        return {
            'total_users': len(self.users),
            'active_users': len([u for u in self.users.values() if u.is_active]),
            'locked_users': len([u for u in self.users.values() if u.is_locked]),
            'mfa_enabled_users': len([u for u in self.users.values() if u.mfa_enabled]),
            'active_sessions': len([s for s in self.sessions.values() if s.is_active]),
            'total_api_keys': len(self.api_keys),
            'events_24h': len(recent_events),
            'events_7d': len(weekly_events),
            'failed_logins_24h': len([e for e in recent_events if e.event_type == AuditEventType.LOGIN_FAILURE]),
            'successful_logins_24h': len([e for e in recent_events if e.event_type == AuditEventType.LOGIN_SUCCESS]),
            'high_risk_events_24h': len([e for e in recent_events if e.risk_score >= 70]),
            'permission_denials_24h': len([e for e in recent_events if e.event_type == AuditEventType.PERMISSION_DENIED]),
            'sensitive_data_access_24h': len([e for e in recent_events if e.event_type == AuditEventType.SENSITIVE_DATA_ACCESS])
        }
    
    def revoke_oauth2_session(self, session_id: str):
        """Revoke OAuth2 session"""
        if session_id in self.oauth2_sessions:
            oauth2_session = self.oauth2_sessions[session_id]
            user_id = oauth2_session['user_id']
            username = self.users.get(user_id).username if user_id in self.users else "unknown"
            
            del self.oauth2_sessions[session_id]
            
            self._log_audit_event(
                AuditEventType.LOGOUT,
                user_id=user_id,
                username=username,
                session_id=session_id,
                details={'auth_method': 'OAuth2'}
            )
            
            logger.info(f"Revoked OAuth2 session: {session_id}")

# Example usage and testing
if __name__ == "__main__":
    # Initialize authentication manager
    auth_manager = AuthenticationManager()
    
    # Create test users
    trader_user = auth_manager.create_user(
        username="trader1",
        email="trader1@example.com",
        password="SecureTrader123!",
        roles={UserRole.TRADER}
    )
    
    admin_user = auth_manager.create_user(
        username="admin1",
        email="admin1@example.com",
        password="SecureAdmin123!",
        roles={UserRole.ADMIN}
    )
    
    # Test authentication
    session = auth_manager.authenticate_user(
        username="trader1",
        password="SecureTrader123!",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0..."
    )
    
    if session:
        print(f"Authentication successful: {session.session_id}")
        
        # Test permission checking
        can_create_order = auth_manager.check_permission(
            session.session_id,
            Permission.ORDER_CREATE,
            "equity_order"
        )
        print(f"Can create order: {can_create_order}")
        
        # Test MFA setup
        secret, qr_uri = auth_manager.setup_mfa(trader_user.user_id)
        print(f"MFA Secret: {secret}")
        
        # Get security metrics
        metrics = auth_manager.get_security_metrics()
        print(f"Security metrics: {metrics}")
    
    else:
        print("Authentication failed")