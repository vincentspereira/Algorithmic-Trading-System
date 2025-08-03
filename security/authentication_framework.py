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
    is_active: bool = True
    is_locked: bool = False
    failed_login_attempts: int = 0
    last_login: Optional[datetime] = None
    password_changed_at: datetime = field(default_factory=datetime.now)
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    api_keys: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Auto-assign permissions based on roles
        self.permissions.update(self._get_role_permissions())
    
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
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions
    
    def has_role(self, role: UserRole) -> bool:
        """Check if user has specific role"""
        return role in self.roles

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
    
    def validate_session(self, session_id: str, ip_address: str = "unknown") -> Optional[Session]:
        """Validate and refresh session"""
        session = self.sessions.get(session_id)
        
        if not session:
            return None
        
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
    
    def setup_mfa(self, user_id: str) -> Tuple[str, str]:
        """Setup MFA for user"""
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
            details={'backup_codes_generated': len(backup_codes)}
        )
        
        return secret, provisioning_uri
    
    def verify_mfa_code(self, user_id: str, code: str) -> bool:
        """Verify MFA code"""
        user = self.users.get(user_id)
        if not user or not user.mfa_enabled or not user.mfa_secret:
            return False
        
        # Check if it's a backup code
        if code in self.mfa_backup_codes.get(user_id, set()):
            self.mfa_backup_codes[user_id].remove(code)
            return True
        
        # Verify TOTP code
        totp = pyotp.TOTP(user.mfa_secret)
        return totp.verify(code, valid_window=self.config.mfa_window_seconds // 30)
    
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
            'iat': now,
            'exp': now + timedelta(hours=self.config.jwt_expiry_hours),
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