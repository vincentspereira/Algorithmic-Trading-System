"""
Zero-Trust Security Implementation

This module provides comprehensive zero-trust security capabilities including:
- Identity and access management
- Multi-factor authentication
- End-to-end encryption
- Behavioral analytics for anomaly detection
"""

import logging
import asyncio
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import base64

# Try to import optional dependencies
try:
    import cryptography
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

try:
    import pyotp
    import qrcode
    MFA_AVAILABLE = True
except ImportError:
    MFA_AVAILABLE = False

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False


class SecurityLevel(Enum):
    """Security clearance levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"
    TOP_SECRET = "top_secret"


class AuthenticationMethod(Enum):
    """Authentication methods"""
    PASSWORD = "password"
    MFA_TOTP = "mfa_totp"
    MFA_SMS = "mfa_sms"
    BIOMETRIC = "biometric"
    CERTIFICATE = "certificate"
    API_KEY = "api_key"


class AccessAction(Enum):
    """Access actions"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"


@dataclass
class User:
    """User identity"""
    user_id: str
    username: str
    email: str
    full_name: str
    security_level: SecurityLevel
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """User session"""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    ip_address: str
    user_agent: str
    is_active: bool = True
    last_activity: datetime = field(default_factory=datetime.now)
    security_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessRequest:
    """Access request"""
    request_id: str
    user_id: str
    resource: str
    action: AccessAction
    timestamp: datetime
    ip_address: str
    user_agent: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityEvent:
    """Security event"""
    event_id: str
    event_type: str
    user_id: Optional[str]
    resource: Optional[str]
    action: Optional[str]
    timestamp: datetime
    severity: str
    description: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class IdentityManager:
    """Manages user identities and authentication"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, Session] = {}
        self.password_hashes: Dict[str, str] = {}
        self.mfa_secrets: Dict[str, str] = {}
        
    def create_user(self, username: str, email: str, full_name: str,
                   password: str, security_level: SecurityLevel = SecurityLevel.INTERNAL) -> User:
        """Create a new user"""
        try:
            user_id = self._generate_user_id()
            
            # Hash password
            password_hash = self._hash_password(password)
            
            user = User(
                user_id=user_id,
                username=username,
                email=email,
                full_name=full_name,
                security_level=security_level
            )
            
            self.users[user_id] = user
            self.password_hashes[user_id] = password_hash
            
            self.logger.info(f"Created user: {username} ({user_id})")
            return user
            
        except Exception as e:
            self.logger.error(f"Error creating user: {e}")
            raise
    
    def authenticate_user(self, username: str, password: str,
                         ip_address: str, user_agent: str) -> Optional[Session]:
        """Authenticate user with password"""
        try:
            # Find user by username
            user = self._find_user_by_username(username)
            if not user:
                self.logger.warning(f"Authentication failed: user not found - {username}")
                return None
            
            # Check if user is active
            if not user.is_active:
                self.logger.warning(f"Authentication failed: user inactive - {username}")
                return None
            
            # Check password
            if not self._verify_password(user.user_id, password):
                user.failed_login_attempts += 1
                self.logger.warning(f"Authentication failed: invalid password - {username}")
                return None
            
            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.last_login = datetime.now()
            
            # Create session
            session = self._create_session(user.user_id, ip_address, user_agent)
            
            self.logger.info(f"User authenticated: {username}")
            return session
            
        except Exception as e:
            self.logger.error(f"Error authenticating user: {e}")
            return None
    
    def setup_mfa(self, user_id: str) -> Optional[str]:
        """Setup multi-factor authentication for user"""
        try:
            if not MFA_AVAILABLE:
                self.logger.error("MFA libraries not available")
                return None
            
            user = self.users.get(user_id)
            if not user:
                return None
            
            # Generate secret
            secret = pyotp.random_base32()
            self.mfa_secrets[user_id] = secret
            
            # Generate QR code URL
            totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=user.email,
                issuer_name="Nautilus Trader"
            )
            
            self.logger.info(f"MFA setup for user: {user.username}")
            return totp_uri
            
        except Exception as e:
            self.logger.error(f"Error setting up MFA: {e}")
            return None
    
    def verify_mfa(self, user_id: str, token: str) -> bool:
        """Verify MFA token"""
        try:
            if not MFA_AVAILABLE:
                return False
            
            secret = self.mfa_secrets.get(user_id)
            if not secret:
                return False
            
            totp = pyotp.TOTP(secret)
            return totp.verify(token)
            
        except Exception as e:
            self.logger.error(f"Error verifying MFA: {e}")
            return False
    
    def _generate_user_id(self) -> str:
        """Generate unique user ID"""
        return f"user_{secrets.token_hex(16)}"
    
    def _hash_password(self, password: str) -> str:
        """Hash password using secure method"""
        salt = secrets.token_hex(32)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{password_hash.hex()}"
    
    def _verify_password(self, user_id: str, password: str) -> bool:
        """Verify password against stored hash"""
        try:
            stored_hash = self.password_hashes.get(user_id)
            if not stored_hash:
                return False
            
            salt, hash_hex = stored_hash.split(':')
            password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return password_hash.hex() == hash_hex
            
        except Exception:
            return False
    
    def _find_user_by_username(self, username: str) -> Optional[User]:
        """Find user by username"""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    def _create_session(self, user_id: str, ip_address: str, user_agent: str) -> Session:
        """Create user session"""
        session_id = f"session_{secrets.token_hex(32)}"
        expires_at = datetime.now() + timedelta(hours=8)  # 8 hour session
        
        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.now(),
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.sessions[session_id] = session
        return session


class AccessControlManager:
    """Manages access control and authorization"""
    
    def __init__(self, identity_manager: IdentityManager):
        self.identity_manager = identity_manager
        self.logger = logging.getLogger(__name__)
        self.permissions: Dict[str, List[str]] = {}
        self.role_permissions: Dict[str, List[str]] = {}
        
    def check_access(self, session_id: str, resource: str, action: AccessAction) -> bool:
        """Check if user has access to resource"""
        try:
            session = self.identity_manager.sessions.get(session_id)
            if not session or not session.is_active:
                return False
            
            # Check session expiry
            if datetime.now() > session.expires_at:
                session.is_active = False
                return False
            
            user = self.identity_manager.users.get(session.user_id)
            if not user or not user.is_active:
                return False
            
            # Check permissions
            required_permission = f"{resource}:{action.value}"
            
            # Check direct permissions
            if required_permission in user.permissions:
                return True
            
            # Check role-based permissions
            for role in user.roles:
                role_perms = self.role_permissions.get(role, [])
                if required_permission in role_perms:
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking access: {e}")
            return False
    
    def grant_permission(self, user_id: str, resource: str, action: AccessAction):
        """Grant permission to user"""
        try:
            user = self.identity_manager.users.get(user_id)
            if not user:
                return
            
            permission = f"{resource}:{action.value}"
            if permission not in user.permissions:
                user.permissions.append(permission)
                self.logger.info(f"Granted permission {permission} to user {user.username}")
                
        except Exception as e:
            self.logger.error(f"Error granting permission: {e}")
    
    def create_role(self, role_name: str, permissions: List[str]):
        """Create role with permissions"""
        self.role_permissions[role_name] = permissions
        self.logger.info(f"Created role: {role_name}")
    
    def assign_role(self, user_id: str, role_name: str):
        """Assign role to user"""
        try:
            user = self.identity_manager.users.get(user_id)
            if not user:
                return
            
            if role_name not in user.roles:
                user.roles.append(role_name)
                self.logger.info(f"Assigned role {role_name} to user {user.username}")
                
        except Exception as e:
            self.logger.error(f"Error assigning role: {e}")


class EncryptionManager:
    """Manages encryption and decryption"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.encryption_keys: Dict[str, bytes] = {}
        
    def generate_key(self, key_id: str) -> Optional[bytes]:
        """Generate encryption key"""
        try:
            if not CRYPTO_AVAILABLE:
                self.logger.error("Cryptography libraries not available")
                return None
            
            key = Fernet.generate_key()
            self.encryption_keys[key_id] = key
            return key
            
        except Exception as e:
            self.logger.error(f"Error generating key: {e}")
            return None
    
    def encrypt_data(self, data: str, key_id: str) -> Optional[str]:
        """Encrypt data"""
        try:
            if not CRYPTO_AVAILABLE:
                return None
            
            key = self.encryption_keys.get(key_id)
            if not key:
                return None
            
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(data.encode())
            return base64.b64encode(encrypted_data).decode()
            
        except Exception as e:
            self.logger.error(f"Error encrypting data: {e}")
            return None
    
    def decrypt_data(self, encrypted_data: str, key_id: str) -> Optional[str]:
        """Decrypt data"""
        try:
            if not CRYPTO_AVAILABLE:
                return None
            
            key = self.encryption_keys.get(key_id)
            if not key:
                return None
            
            fernet = Fernet(key)
            decoded_data = base64.b64decode(encrypted_data.encode())
            decrypted_data = fernet.decrypt(decoded_data)
            return decrypted_data.decode()
            
        except Exception as e:
            self.logger.error(f"Error decrypting data: {e}")
            return None


class BehavioralAnalytics:
    """Analyzes user behavior for anomaly detection"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.user_patterns: Dict[str, Dict[str, Any]] = {}
        self.security_events: List[SecurityEvent] = []
        
    def record_user_activity(self, user_id: str, activity: str, 
                           ip_address: str, timestamp: datetime):
        """Record user activity for analysis"""
        try:
            if user_id not in self.user_patterns:
                self.user_patterns[user_id] = {
                    'login_times': [],
                    'ip_addresses': set(),
                    'activities': [],
                    'last_activity': None
                }
            
            pattern = self.user_patterns[user_id]
            pattern['activities'].append({
                'activity': activity,
                'timestamp': timestamp,
                'ip_address': ip_address
            })
            pattern['ip_addresses'].add(ip_address)
            pattern['last_activity'] = timestamp
            
            if activity == 'login':
                pattern['login_times'].append(timestamp.hour)
            
            # Check for anomalies
            self._check_anomalies(user_id)
            
        except Exception as e:
            self.logger.error(f"Error recording user activity: {e}")
    
    def _check_anomalies(self, user_id: str):
        """Check for behavioral anomalies"""
        try:
            pattern = self.user_patterns.get(user_id)
            if not pattern:
                return
            
            # Check for unusual login times
            if len(pattern['login_times']) > 5:
                avg_login_hour = sum(pattern['login_times']) / len(pattern['login_times'])
                recent_login = pattern['login_times'][-1]
                
                if abs(recent_login - avg_login_hour) > 3:  # 3 hour difference
                    self._create_security_event(
                        user_id, "unusual_login_time",
                        f"Login at unusual time: {recent_login}:00"
                    )
            
            # Check for new IP addresses
            if len(pattern['ip_addresses']) > 1:
                recent_activities = pattern['activities'][-5:]  # Last 5 activities
                recent_ips = {act['ip_address'] for act in recent_activities}
                
                if len(recent_ips) > 1:
                    self._create_security_event(
                        user_id, "multiple_ip_addresses",
                        f"Activity from multiple IPs: {recent_ips}"
                    )
                    
        except Exception as e:
            self.logger.error(f"Error checking anomalies: {e}")
    
    def _create_security_event(self, user_id: str, event_type: str, description: str):
        """Create security event"""
        event = SecurityEvent(
            event_id=f"event_{secrets.token_hex(16)}",
            event_type=event_type,
            user_id=user_id,
            resource=None,
            action=None,
            timestamp=datetime.now(),
            severity="medium",
            description=description
        )
        
        self.security_events.append(event)
        self.logger.warning(f"Security event: {event_type} - {description}")


class ZeroTrustSecurityManager:
    """Main zero-trust security manager"""
    
    def __init__(self):
        self.identity_manager = IdentityManager()
        self.access_control = AccessControlManager(self.identity_manager)
        self.encryption_manager = EncryptionManager()
        self.behavioral_analytics = BehavioralAnalytics()
        self.logger = logging.getLogger(__name__)
        
        # Initialize default roles
        self._setup_default_roles()
    
    def _setup_default_roles(self):
        """Setup default security roles"""
        # Trader role
        self.access_control.create_role("trader", [
            "trading:read",
            "trading:write",
            "portfolio:read",
            "market_data:read"
        ])
        
        # Risk Manager role
        self.access_control.create_role("risk_manager", [
            "trading:read",
            "portfolio:read",
            "risk:read",
            "risk:write",
            "compliance:read"
        ])
        
        # Administrator role
        self.access_control.create_role("administrator", [
            "trading:admin",
            "portfolio:admin",
            "risk:admin",
            "compliance:admin",
            "system:admin"
        ])
    
    async def authenticate_and_authorize(self, username: str, password: str,
                                       resource: str, action: AccessAction,
                                       ip_address: str, user_agent: str,
                                       mfa_token: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Complete authentication and authorization flow"""
        try:
            # Step 1: Authenticate user
            session = self.identity_manager.authenticate_user(
                username, password, ip_address, user_agent
            )
            
            if not session:
                return False, "Authentication failed"
            
            # Step 2: Check MFA if required
            user = self.identity_manager.users[session.user_id]
            if user.security_level in [SecurityLevel.SECRET, SecurityLevel.TOP_SECRET]:
                if not mfa_token:
                    return False, "MFA token required"
                
                if not self.identity_manager.verify_mfa(session.user_id, mfa_token):
                    return False, "Invalid MFA token"
            
            # Step 3: Check authorization
            if not self.access_control.check_access(session.session_id, resource, action):
                return False, "Access denied"
            
            # Step 4: Record activity for behavioral analysis
            self.behavioral_analytics.record_user_activity(
                session.user_id, f"{resource}:{action.value}",
                ip_address, datetime.now()
            )
            
            return True, session.session_id
            
        except Exception as e:
            self.logger.error(f"Error in authentication/authorization: {e}")
            return False, "Internal error"
    
    def get_security_events(self, severity: Optional[str] = None,
                          user_id: Optional[str] = None) -> List[SecurityEvent]:
        """Get security events"""
        events = self.behavioral_analytics.security_events
        
        if severity:
            events = [e for e in events if e.severity == severity]
        
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        return events


# Example usage
async def example_usage():
    """Demonstrate zero-trust security"""
    print("=== Zero-Trust Security Demo ===")
    
    # Create security manager
    security_manager = ZeroTrustSecurityManager()
    
    # Create users
    user1 = security_manager.identity_manager.create_user(
        "trader1", "trader1@example.com", "John Trader",
        "secure_password123", SecurityLevel.CONFIDENTIAL
    )
    
    user2 = security_manager.identity_manager.create_user(
        "risk_mgr", "risk@example.com", "Jane Risk",
        "secure_password456", SecurityLevel.SECRET
    )
    
    # Assign roles
    security_manager.access_control.assign_role(user1.user_id, "trader")
    security_manager.access_control.assign_role(user2.user_id, "risk_manager")
    
    # Setup MFA for high-security user
    mfa_uri = security_manager.identity_manager.setup_mfa(user2.user_id)
    print(f"MFA setup URI: {mfa_uri}")
    
    # Test authentication and authorization
    success, session_id = await security_manager.authenticate_and_authorize(
        "trader1", "secure_password123",
        "trading", AccessAction.WRITE,
        "192.168.1.100", "Mozilla/5.0"
    )
    
    print(f"Authentication result: {success}")
    if success:
        print(f"Session ID: {session_id}")
    
    # Test encryption
    key_id = "test_key"
    security_manager.encryption_manager.generate_key(key_id)
    
    sensitive_data = "This is sensitive trading data"
    encrypted = security_manager.encryption_manager.encrypt_data(sensitive_data, key_id)
    decrypted = security_manager.encryption_manager.decrypt_data(encrypted, key_id)
    
    print(f"Original: {sensitive_data}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")
    
    print("\\nZero-trust security demo completed!")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run example
    asyncio.run(example_usage())