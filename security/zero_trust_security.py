#!/usr/bin/env python3
"""
Zero-Trust Security Architecture Implementation
Provides comprehensive identity and access management with behavioral analytics
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
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import jwt
import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthenticationMethod(Enum):
    """Authentication methods"""
    PASSWORD = "PASSWORD"
    BIOMETRIC = "BIOMETRIC"
    TOKEN = "TOKEN"
    CERTIFICATE = "CERTIFICATE"
    MULTI_FACTOR = "MULTI_FACTOR"

class ThreatLevel(Enum):
    """Threat levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AccessDecision(Enum):
    """Access control decisions"""
    ALLOW = "ALLOW"
    DENY = "DENY"
    CHALLENGE = "CHALLENGE"
    MONITOR = "MONITOR"

@dataclass
class UserIdentity:
    """User identity information"""
    user_id: str
    username: str
    email: str
    roles: Set[str]
    permissions: Set[str]
    created_at: datetime
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    account_locked: bool = False
    mfa_enabled: bool = False
    biometric_enrolled: bool = False
    risk_score: float = 0.0
    
@dataclass
class AuthenticationContext:
    """Authentication context"""
    user_id: str
    session_id: str
    ip_address: str
    user_agent: str
    device_fingerprint: str
    location: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    authentication_methods: List[AuthenticationMethod] = field(default_factory=list)
    risk_factors: Dict[str, float] = field(default_factory=dict)
    
@dataclass
class AccessRequest:
    """Access request information"""
    request_id: str
    user_id: str
    resource: str
    action: str
    context: AuthenticationContext
    timestamp: datetime = field(default_factory=datetime.now)
    
@dataclass
class SecurityEvent:
    """Security event"""
    event_id: str
    event_type: str
    user_id: Optional[str]
    severity: ThreatLevel
    description: str
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False

@dataclass
class DeviceFingerprint:
    """Device fingerprinting data for enhanced security"""
    device_id: str
    user_agent: str
    screen_resolution: str
    timezone: str
    language: str
    plugins: List[str]
    fonts: List[str]
    canvas_fingerprint: str
    webgl_fingerprint: str
    audio_fingerprint: str
    hardware_concurrency: int
    memory: int
    platform: str
    created_at: datetime = field(default_factory=datetime.now)
    
    def generate_hash(self) -> str:
        """Generate unique hash for device fingerprint"""
        fingerprint_data = {
            'user_agent': self.user_agent,
            'screen_resolution': self.screen_resolution,
            'timezone': self.timezone,
            'language': self.language,
            'plugins': sorted(self.plugins),
            'fonts': sorted(self.fonts),
            'canvas_fingerprint': self.canvas_fingerprint,
            'webgl_fingerprint': self.webgl_fingerprint,
            'audio_fingerprint': self.audio_fingerprint,
            'hardware_concurrency': self.hardware_concurrency,
            'memory': self.memory,
            'platform': self.platform
        }
        
        fingerprint_str = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()

@dataclass
class BehavioralProfile:
    """User behavioral profile for anomaly detection"""
    user_id: str
    typical_login_hours: List[int]
    typical_locations: List[str]
    typical_devices: List[str]
    typical_session_duration: float
    typical_actions_per_session: int
    typical_data_access_patterns: Dict[str, int]
    risk_tolerance: float
    last_updated: datetime = field(default_factory=datetime.now)
    
    def calculate_anomaly_score(self, current_behavior: Dict[str, Any]) -> float:
        """Calculate anomaly score for current behavior"""
        score = 0.0
        
        # Time-based anomaly
        current_hour = datetime.now().hour
        if current_hour not in self.typical_login_hours:
            score += 0.3
        
        # Location-based anomaly
        current_location = current_behavior.get('location', 'unknown')
        if current_location not in self.typical_locations:
            score += 0.4
        
        # Device-based anomaly
        current_device = current_behavior.get('device_id', 'unknown')
        if current_device not in self.typical_devices:
            score += 0.2
        
        # Session duration anomaly
        session_duration = current_behavior.get('session_duration', 0)
        if abs(session_duration - self.typical_session_duration) > self.typical_session_duration * 0.5:
            score += 0.1
        
        return min(score, 1.0)

@dataclass
class ThreatIntelligence:
    """Threat intelligence data"""
    indicator: str
    indicator_type: str  # ip, domain, hash, etc.
    threat_level: ThreatLevel
    description: str
    source: str
    confidence: float
    first_seen: datetime
    last_seen: datetime
    tags: List[str] = field(default_factory=list)
    
    def is_expired(self, max_age_days: int = 30) -> bool:
        """Check if threat intelligence is expired"""
        return (datetime.now() - self.last_seen).days > max_age_days

class IdentityAccessManager:
    """Identity and Access Management system"""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.users: Dict[str, UserIdentity] = {}
        self.sessions: Dict[str, AuthenticationContext] = {}
        self.access_policies: Dict[str, Dict[str, Any]] = {}
        self.security_events: List[SecurityEvent] = []
        self.failed_attempts: Dict[str, List[datetime]] = defaultdict(list)
        self.device_registry: Dict[str, Dict[str, Any]] = {}
        self.device_fingerprints: Dict[str, DeviceFingerprint] = {}
        self.behavioral_profiles: Dict[str, BehavioralProfile] = {}
        self.threat_intelligence: Dict[str, ThreatIntelligence] = {}
        self.encryption_key = self._generate_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Initialize default policies
        self._initialize_default_policies()
        
        # Initialize threat intelligence with some common indicators
        self._initialize_threat_intelligence()
        
        logger.info("Enhanced Identity and Access Manager initialized")
    
    def _generate_encryption_key(self) -> bytes:
        """Generate encryption key from secret"""
        password = self.secret_key.encode()
        salt = b'salt_'  # In production, use a proper random salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def _initialize_default_policies(self):
        """Initialize default access policies"""
        self.access_policies = {
            "trading": {
                "required_roles": ["trader", "admin"],
                "required_permissions": ["trade.execute"],
                "mfa_required": True,
                "max_risk_score": 0.7,
                "allowed_locations": [],  # Empty means all locations allowed
                "time_restrictions": {},  # Empty means no time restrictions
                "device_trust_required": True,
                "behavioral_analysis": True
            },
            "admin": {
                "required_roles": ["admin"],
                "required_permissions": ["admin.access"],
                "mfa_required": True,
                "max_risk_score": 0.3,
                "allowed_locations": [],
                "time_restrictions": {},
                "device_trust_required": True,
                "behavioral_analysis": True
            },
            "reporting": {
                "required_roles": ["trader", "analyst", "admin"],
                "required_permissions": ["report.view"],
                "mfa_required": False,
                "max_risk_score": 0.8,
                "allowed_locations": [],
                "time_restrictions": {},
                "device_trust_required": False,
                "behavioral_analysis": True
            },
            "sensitive_data": {
                "required_roles": ["admin", "risk_manager"],
                "required_permissions": ["data.sensitive.view"],
                "mfa_required": True,
                "max_risk_score": 0.2,
                "allowed_locations": ["US", "UK"],
                "time_restrictions": {"start_hour": 8, "end_hour": 18},
                "device_trust_required": True,
                "behavioral_analysis": True
            }
        }
    
    def _initialize_threat_intelligence(self):
        """Initialize threat intelligence with common indicators"""
        # Add some common malicious IP ranges and patterns
        common_threats = [
            {
                "indicator": "192.168.100.0/24",
                "type": "ip_range",
                "level": ThreatLevel.HIGH,
                "description": "Known botnet command and control range",
                "source": "internal_analysis"
            },
            {
                "indicator": "tor-exit-node",
                "type": "network_type",
                "level": ThreatLevel.MEDIUM,
                "description": "Tor exit node detected",
                "source": "network_analysis"
            }
        ]
        
        for threat in common_threats:
            self.add_threat_intelligence(
                threat["indicator"],
                threat["type"],
                threat["level"],
                threat["description"],
                threat["source"]
            )
    
    async def create_user(self, username: str, email: str, password: str, 
                         roles: Set[str], permissions: Set[str]) -> str:
        """Create a new user"""
        user_id = str(uuid.uuid4())
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        user = UserIdentity(
            user_id=user_id,
            username=username,
            email=email,
            roles=roles,
            permissions=permissions,
            created_at=datetime.now()
        )
        
        self.users[user_id] = user
        
        # Store encrypted password separately (in production, use proper user store)
        self.users[user_id].__dict__['password_hash'] = password_hash
        
        logger.info(f"User created: {username} ({user_id})")
        return user_id
    
    async def authenticate_user(self, username: str, password: str, 
                              context: AuthenticationContext) -> Optional[str]:
        """Authenticate user with password"""
        # Find user by username
        user = None
        for uid, u in self.users.items():
            if u.username == username:
                user = u
                break
        
        if not user:
            await self._log_security_event(
                "AUTHENTICATION_FAILED",
                None,
                ThreatLevel.MEDIUM,
                f"Authentication failed for unknown user: {username}",
                {"username": username, "ip": context.ip_address}
            )
            return None
        
        # Check if account is locked
        if user.account_locked:
            await self._log_security_event(
                "ACCOUNT_LOCKED_ACCESS_ATTEMPT",
                user.user_id,
                ThreatLevel.HIGH,
                f"Access attempt on locked account: {username}",
                {"username": username, "ip": context.ip_address}
            )
            return None
        
        # Verify password
        stored_hash = user.__dict__.get('password_hash')
        if not stored_hash or not bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            # Record failed attempt
            user.failed_login_attempts += 1
            self.failed_attempts[user.user_id].append(datetime.now())
            
            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.account_locked = True
                await self._log_security_event(
                    "ACCOUNT_LOCKED",
                    user.user_id,
                    ThreatLevel.HIGH,
                    f"Account locked due to failed attempts: {username}",
                    {"username": username, "attempts": user.failed_login_attempts}
                )
            
            await self._log_security_event(
                "AUTHENTICATION_FAILED",
                user.user_id,
                ThreatLevel.MEDIUM,
                f"Authentication failed for user: {username}",
                {"username": username, "ip": context.ip_address, "attempts": user.failed_login_attempts}
            )
            return None
        
        # Reset failed attempts on successful authentication
        user.failed_login_attempts = 0
        user.last_login = datetime.now()
        
        # Calculate risk score
        risk_score = await self._calculate_risk_score(user, context)
        user.risk_score = risk_score
        context.risk_factors['authentication_risk'] = risk_score
        
        # Create session
        session_id = str(uuid.uuid4())
        context.user_id = user.user_id
        context.session_id = session_id
        context.authentication_methods.append(AuthenticationMethod.PASSWORD)
        
        self.sessions[session_id] = context
        
        await self._log_security_event(
            "AUTHENTICATION_SUCCESS",
            user.user_id,
            ThreatLevel.LOW,
            f"User authenticated successfully: {username}",
            {"username": username, "ip": context.ip_address, "risk_score": risk_score}
        )
        
        return session_id
    
    async def _calculate_risk_score(self, user: UserIdentity, context: AuthenticationContext) -> float:
        """Calculate risk score based on various factors"""
        risk_score = 0.0
        
        # Time-based risk (unusual login times)
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:  # Outside business hours
            risk_score += 0.2
        
        # Location-based risk (would integrate with GeoIP in production)
        # For now, just check if it's a new location
        if context.location and context.location not in ["US", "UK", "EU"]:
            risk_score += 0.3
        
        # Device-based risk
        if context.device_fingerprint not in self.device_registry:
            risk_score += 0.4  # New device
            # Register device
            self.device_registry[context.device_fingerprint] = {
                "first_seen": datetime.now(),
                "user_id": user.user_id,
                "trusted": False
            }
        
        # Failed attempt history
        recent_failures = [
            attempt for attempt in self.failed_attempts[user.user_id]
            if attempt > datetime.now() - timedelta(hours=24)
        ]
        if len(recent_failures) > 0:
            risk_score += min(0.3, len(recent_failures) * 0.1)
        
        # Account age (newer accounts are riskier)
        account_age_days = (datetime.now() - user.created_at).days
        if account_age_days < 30:
            risk_score += 0.2
        
        return min(1.0, risk_score)  # Cap at 1.0
    
    async def enable_mfa(self, user_id: str, method: AuthenticationMethod) -> str:
        """Enable multi-factor authentication"""
        if user_id not in self.users:
            raise ValueError("User not found")
        
        user = self.users[user_id]
        user.mfa_enabled = True
        
        if method == AuthenticationMethod.BIOMETRIC:
            user.biometric_enrolled = True
        
        # Generate MFA secret (in production, use proper TOTP library)
        mfa_secret = secrets.token_urlsafe(32)
        user.__dict__['mfa_secret'] = mfa_secret
        
        await self._log_security_event(
            "MFA_ENABLED",
            user_id,
            ThreatLevel.LOW,
            f"MFA enabled for user: {user.username}",
            {"method": method.value}
        )
        
        return mfa_secret
    
    async def verify_mfa(self, session_id: str, mfa_code: str) -> bool:
        """Verify MFA code"""
        if session_id not in self.sessions:
            return False
        
        context = self.sessions[session_id]
        user = self.users[context.user_id]
        
        # In production, implement proper TOTP verification
        # For demo, accept any 6-digit code
        if len(mfa_code) == 6 and mfa_code.isdigit():
            context.authentication_methods.append(AuthenticationMethod.MULTI_FACTOR)
            
            await self._log_security_event(
                "MFA_SUCCESS",
                user.user_id,
                ThreatLevel.LOW,
                f"MFA verification successful: {user.username}",
                {"session_id": session_id}
            )
            return True
        
        await self._log_security_event(
            "MFA_FAILED",
            user.user_id,
            ThreatLevel.MEDIUM,
            f"MFA verification failed: {user.username}",
            {"session_id": session_id}
        )
        return False
    
    async def check_access(self, request: AccessRequest) -> AccessDecision:
        """Check access based on zero-trust principles"""
        # Verify session exists
        if request.context.session_id not in self.sessions:
            return AccessDecision.DENY
        
        user = self.users[request.user_id]
        policy = self.access_policies.get(request.resource)
        
        if not policy:
            # No policy defined - default deny
            await self._log_security_event(
                "ACCESS_DENIED_NO_POLICY",
                request.user_id,
                ThreatLevel.MEDIUM,
                f"Access denied - no policy for resource: {request.resource}",
                {"resource": request.resource, "action": request.action}
            )
            return AccessDecision.DENY
        
        # Check role requirements
        required_roles = set(policy.get("required_roles", []))
        if required_roles and not required_roles.intersection(user.roles):
            await self._log_security_event(
                "ACCESS_DENIED_INSUFFICIENT_ROLES",
                request.user_id,
                ThreatLevel.MEDIUM,
                f"Access denied - insufficient roles for: {request.resource}",
                {"required_roles": list(required_roles), "user_roles": list(user.roles)}
            )
            return AccessDecision.DENY
        
        # Check permission requirements
        required_permissions = set(policy.get("required_permissions", []))
        if required_permissions and not required_permissions.intersection(user.permissions):
            await self._log_security_event(
                "ACCESS_DENIED_INSUFFICIENT_PERMISSIONS",
                request.user_id,
                ThreatLevel.MEDIUM,
                f"Access denied - insufficient permissions for: {request.resource}",
                {"required_permissions": list(required_permissions), "user_permissions": list(user.permissions)}
            )
            return AccessDecision.DENY
        
        # Check MFA requirement
        if policy.get("mfa_required", False):
            if AuthenticationMethod.MULTI_FACTOR not in request.context.authentication_methods:
                await self._log_security_event(
                    "ACCESS_CHALLENGE_MFA_REQUIRED",
                    request.user_id,
                    ThreatLevel.MEDIUM,
                    f"MFA challenge required for: {request.resource}",
                    {"resource": request.resource}
                )
                return AccessDecision.CHALLENGE
        
        # Check risk score
        max_risk_score = policy.get("max_risk_score", 1.0)
        if user.risk_score > max_risk_score:
            await self._log_security_event(
                "ACCESS_DENIED_HIGH_RISK",
                request.user_id,
                ThreatLevel.HIGH,
                f"Access denied - high risk score for: {request.resource}",
                {"risk_score": user.risk_score, "max_allowed": max_risk_score}
            )
            return AccessDecision.DENY
        
        # Access granted
        await self._log_security_event(
            "ACCESS_GRANTED",
            request.user_id,
            ThreatLevel.LOW,
            f"Access granted to: {request.resource}",
            {"resource": request.resource, "action": request.action}
        )
        
        return AccessDecision.ALLOW
    
    async def _log_security_event(self, event_type: str, user_id: Optional[str], 
                                 severity: ThreatLevel, description: str, 
                                 context: Dict[str, Any]):
        """Log security event"""
        event = SecurityEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            user_id=user_id,
            severity=severity,
            description=description,
            context=context
        )
        
        self.security_events.append(event)
        
        # Log to system logger
        log_level = {
            ThreatLevel.LOW: logging.INFO,
            ThreatLevel.MEDIUM: logging.WARNING,
            ThreatLevel.HIGH: logging.ERROR,
            ThreatLevel.CRITICAL: logging.CRITICAL
        }[severity]
        
        logger.log(log_level, f"Security Event [{event_type}]: {description}")
    
    def get_user_sessions(self, user_id: str) -> List[AuthenticationContext]:
        """Get active sessions for user"""
        return [context for context in self.sessions.values() if context.user_id == user_id]
    
    def revoke_session(self, session_id: str) -> bool:
        """Revoke a session"""
        if session_id in self.sessions:
            context = self.sessions[session_id]
            del self.sessions[session_id]
            
            asyncio.create_task(self._log_security_event(
                "SESSION_REVOKED",
                context.user_id,
                ThreatLevel.LOW,
                f"Session revoked: {session_id}",
                {"session_id": session_id}
            ))
            return True
        return False
    
    def get_security_events(self, user_id: Optional[str] = None, 
                           severity: Optional[ThreatLevel] = None,
                           limit: int = 100) -> List[SecurityEvent]:
        """Get security events with optional filtering"""
        events = self.security_events
        
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        if severity:
            events = [e for e in events if e.severity == severity]
        
        # Sort by timestamp (newest first) and limit
        events.sort(key=lambda x: x.timestamp, reverse=True)
        return events[:limit]
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    def generate_jwt_token(self, user_id: str, session_id: str, 
                          expires_in: int = 3600) -> str:
        """Generate JWT token for API access"""
        payload = {
            'user_id': user_id,
            'session_id': session_id,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # Check if session is still active
            session_id = payload.get('session_id')
            if session_id not in self.sessions:
                return None
            
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def register_device_fingerprint(self, device_id: str, fingerprint_data: Dict[str, Any]) -> str:
        """Register device fingerprint for enhanced security"""
        fingerprint = DeviceFingerprint(
            device_id=device_id,
            user_agent=fingerprint_data.get('user_agent', ''),
            screen_resolution=fingerprint_data.get('screen_resolution', ''),
            timezone=fingerprint_data.get('timezone', ''),
            language=fingerprint_data.get('language', ''),
            plugins=fingerprint_data.get('plugins', []),
            fonts=fingerprint_data.get('fonts', []),
            canvas_fingerprint=fingerprint_data.get('canvas_fingerprint', ''),
            webgl_fingerprint=fingerprint_data.get('webgl_fingerprint', ''),
            audio_fingerprint=fingerprint_data.get('audio_fingerprint', ''),
            hardware_concurrency=fingerprint_data.get('hardware_concurrency', 0),
            memory=fingerprint_data.get('memory', 0),
            platform=fingerprint_data.get('platform', '')
        )
        
        fingerprint_hash = fingerprint.generate_hash()
        self.device_fingerprints[device_id] = fingerprint
        
        # Update device registry with fingerprint
        if device_id in self.device_registry:
            self.device_registry[device_id]['fingerprint_hash'] = fingerprint_hash
            self.device_registry[device_id]['fingerprint_verified'] = True
        
        logger.info(f"Device fingerprint registered: {device_id}")
        return fingerprint_hash
    
    def verify_device_fingerprint(self, device_id: str, current_fingerprint: Dict[str, Any]) -> Tuple[bool, float]:
        """Verify device fingerprint consistency"""
        stored_fingerprint = self.device_fingerprints.get(device_id)
        if not stored_fingerprint:
            return False, 0.0
        
        # Create current fingerprint object
        current_fp = DeviceFingerprint(
            device_id=device_id,
            user_agent=current_fingerprint.get('user_agent', ''),
            screen_resolution=current_fingerprint.get('screen_resolution', ''),
            timezone=current_fingerprint.get('timezone', ''),
            language=current_fingerprint.get('language', ''),
            plugins=current_fingerprint.get('plugins', []),
            fonts=current_fingerprint.get('fonts', []),
            canvas_fingerprint=current_fingerprint.get('canvas_fingerprint', ''),
            webgl_fingerprint=current_fingerprint.get('webgl_fingerprint', ''),
            audio_fingerprint=current_fingerprint.get('audio_fingerprint', ''),
            hardware_concurrency=current_fingerprint.get('hardware_concurrency', 0),
            memory=current_fingerprint.get('memory', 0),
            platform=current_fingerprint.get('platform', '')
        )
        
        # Compare fingerprints
        stored_hash = stored_fingerprint.generate_hash()
        current_hash = current_fp.generate_hash()
        
        if stored_hash == current_hash:
            return True, 1.0
        else:
            # Calculate similarity score
            similarity = self._calculate_fingerprint_similarity(stored_fingerprint, current_fp)
            return similarity > 0.8, similarity
    
    def _calculate_fingerprint_similarity(self, fp1: DeviceFingerprint, fp2: DeviceFingerprint) -> float:
        """Calculate similarity between two device fingerprints"""
        similarity_score = 0.0
        
        # Compare individual components with weights
        components = [
            ('user_agent', 0.2),
            ('screen_resolution', 0.1),
            ('timezone', 0.1),
            ('language', 0.1),
            ('canvas_fingerprint', 0.15),
            ('webgl_fingerprint', 0.15),
            ('audio_fingerprint', 0.1),
            ('platform', 0.1)
        ]
        
        for component, weight in components:
            val1 = getattr(fp1, component, '')
            val2 = getattr(fp2, component, '')
            
            if val1 == val2:
                similarity_score += weight
        
        # Special handling for lists (plugins, fonts)
        plugins_similarity = len(set(fp1.plugins) & set(fp2.plugins)) / max(len(set(fp1.plugins) | set(fp2.plugins)), 1)
        fonts_similarity = len(set(fp1.fonts) & set(fp2.fonts)) / max(len(set(fp1.fonts) | set(fp2.fonts)), 1)
        
        similarity_score += plugins_similarity * 0.05
        similarity_score += fonts_similarity * 0.05
        
        return min(similarity_score, 1.0)
    
    def create_behavioral_profile(self, user_id: str, initial_behavior: Dict[str, Any]) -> BehavioralProfile:
        """Create behavioral profile for user"""
        current_hour = datetime.now().hour
        
        profile = BehavioralProfile(
            user_id=user_id,
            typical_login_hours=[current_hour],
            typical_locations=[initial_behavior.get('location', 'unknown')],
            typical_devices=[initial_behavior.get('device_id', 'unknown')],
            typical_session_duration=initial_behavior.get('session_duration', 3600.0),
            typical_actions_per_session=initial_behavior.get('actions_count', 50),
            typical_data_access_patterns={},
            risk_tolerance=0.5
        )
        
        self.behavioral_profiles[user_id] = profile
        logger.info(f"Behavioral profile created for user: {user_id}")
        return profile
    
    def update_behavioral_profile(self, user_id: str, session_data: Dict[str, Any]):
        """Update user behavioral profile with session data"""
        profile = self.behavioral_profiles.get(user_id)
        if not profile:
            profile = self.create_behavioral_profile(user_id, session_data)
        
        # Update profile with new data
        current_hour = datetime.now().hour
        if current_hour not in profile.typical_login_hours:
            profile.typical_login_hours.append(current_hour)
            # Keep only recent patterns (last 30 days worth)
            if len(profile.typical_login_hours) > 24:
                profile.typical_login_hours = profile.typical_login_hours[-24:]
        
        location = session_data.get('location', 'unknown')
        if location not in profile.typical_locations:
            profile.typical_locations.append(location)
            if len(profile.typical_locations) > 10:
                profile.typical_locations = profile.typical_locations[-10:]
        
        device_id = session_data.get('device_id', 'unknown')
        if device_id not in profile.typical_devices:
            profile.typical_devices.append(device_id)
            if len(profile.typical_devices) > 5:
                profile.typical_devices = profile.typical_devices[-5:]
        
        # Update session duration (moving average)
        session_duration = session_data.get('session_duration', 3600)
        profile.typical_session_duration = (profile.typical_session_duration * 0.8) + (session_duration * 0.2)
        
        profile.last_updated = datetime.now()
    
    def add_threat_intelligence(self, indicator: str, indicator_type: str, 
                              threat_level: ThreatLevel, description: str, 
                              source: str, confidence: float = 1.0, tags: List[str] = None):
        """Add threat intelligence indicator"""
        threat_info = ThreatIntelligence(
            indicator=indicator,
            indicator_type=indicator_type,
            threat_level=threat_level,
            description=description,
            source=source,
            confidence=confidence,
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            tags=tags or []
        )
        
        self.threat_intelligence[indicator] = threat_info
        logger.info(f"Added threat intelligence: {indicator} ({threat_level.value})")
    
    def check_threat_intelligence(self, context: AuthenticationContext) -> Dict[str, Any]:
        """Check context against threat intelligence"""
        threat_score = 0.0
        threats_found = []
        
        ip_address = context.ip_address
        user_agent = context.user_agent
        
        # Check IP against threat intelligence
        for indicator, threat_info in self.threat_intelligence.items():
            if threat_info.is_expired():
                continue
            
            if threat_info.indicator_type == 'ip' and threat_info.indicator == ip_address:
                threat_level_scores = {
                    ThreatLevel.LOW: 0.2,
                    ThreatLevel.MEDIUM: 0.5,
                    ThreatLevel.HIGH: 0.8,
                    ThreatLevel.CRITICAL: 1.0
                }
                score = threat_level_scores.get(threat_info.threat_level, 0.5)
                threat_score = max(threat_score, score * threat_info.confidence)
                threats_found.append({
                    'indicator': threat_info.indicator,
                    'type': threat_info.indicator_type,
                    'level': threat_info.threat_level.value,
                    'description': threat_info.description
                })
        
        # Check for known malicious user agents
        malicious_patterns = ['bot', 'crawler', 'scanner', 'exploit']
        if any(pattern in user_agent.lower() for pattern in malicious_patterns):
            threat_score = max(threat_score, 0.6)
            threats_found.append({
                'indicator': user_agent,
                'type': 'user_agent',
                'level': 'MEDIUM',
                'description': 'Suspicious user agent pattern'
            })
        
        return {
            'threat_detected': threat_score > 0.3,
            'threat_score': threat_score,
            'threats': threats_found,
            'critical_threat': threat_score > 0.8
        }
    
    async def enhanced_check_access(self, request: AccessRequest) -> Tuple[AccessDecision, Dict[str, Any]]:
        """Enhanced access check with behavioral analysis and threat intelligence"""
        # Start with basic access check
        basic_decision = await self.check_access(request)
        
        analysis_results = {
            'basic_decision': basic_decision,
            'threat_analysis': {},
            'behavioral_analysis': {},
            'device_analysis': {},
            'final_decision': basic_decision,
            'risk_factors': [],
            'recommendations': []
        }
        
        if basic_decision == AccessDecision.DENY:
            return basic_decision, analysis_results
        
        user = self.users[request.user_id]
        policy = self.access_policies.get(request.resource, {})
        
        # Threat intelligence check
        threat_analysis = self.check_threat_intelligence(request.context)
        analysis_results['threat_analysis'] = threat_analysis
        
        if threat_analysis['critical_threat']:
            analysis_results['final_decision'] = AccessDecision.DENY
            analysis_results['risk_factors'].append('Critical threat detected')
            analysis_results['recommendations'].append('Block access immediately')
            
            await self._log_security_event(
                "ACCESS_DENIED_CRITICAL_THREAT",
                request.user_id,
                ThreatLevel.CRITICAL,
                f"Access denied due to critical threat: {request.resource}",
                threat_analysis
            )
            return AccessDecision.DENY, analysis_results
        
        # Behavioral analysis if enabled
        if policy.get('behavioral_analysis', False):
            profile = self.behavioral_profiles.get(request.user_id)
            if profile:
                behavior_context = {
                    'location': request.context.location,
                    'device_id': request.context.device_fingerprint,
                    'session_duration': 0,  # Would be calculated from actual session
                    'actions_count': 1
                }
                
                anomaly_score = profile.calculate_anomaly_score(behavior_context)
                analysis_results['behavioral_analysis'] = {
                    'anomaly_score': anomaly_score,
                    'anomaly_detected': anomaly_score > 0.5
                }
                
                if anomaly_score > 0.7:
                    analysis_results['final_decision'] = AccessDecision.CHALLENGE
                    analysis_results['risk_factors'].append('High behavioral anomaly detected')
                    analysis_results['recommendations'].append('Require additional authentication')
        
        # Device trust check if required
        if policy.get('device_trust_required', False):
            device_info = self.device_registry.get(request.context.device_fingerprint)
            if device_info:
                device_trusted = device_info.get('trusted', False)
                analysis_results['device_analysis'] = {
                    'device_registered': True,
                    'device_trusted': device_trusted,
                    'first_seen': device_info.get('first_seen')
                }
                
                if not device_trusted:
                    analysis_results['final_decision'] = AccessDecision.CHALLENGE
                    analysis_results['risk_factors'].append('Untrusted device')
                    analysis_results['recommendations'].append('Device approval required')
            else:
                analysis_results['device_analysis'] = {
                    'device_registered': False,
                    'device_trusted': False
                }
                analysis_results['final_decision'] = AccessDecision.DENY
                analysis_results['risk_factors'].append('Unregistered device')
                analysis_results['recommendations'].append('Device registration required')
        
        # Log enhanced access decision
        await self._log_security_event(
            f"ENHANCED_ACCESS_{analysis_results['final_decision'].value}",
            request.user_id,
            ThreatLevel.LOW if analysis_results['final_decision'] == AccessDecision.ALLOW else ThreatLevel.MEDIUM,
            f"Enhanced access decision for {request.resource}: {analysis_results['final_decision'].value}",
            {
                'resource': request.resource,
                'risk_factors': analysis_results['risk_factors'],
                'threat_score': threat_analysis.get('threat_score', 0),
                'behavioral_anomaly': analysis_results.get('behavioral_analysis', {}).get('anomaly_score', 0)
            }
        )
        
        return analysis_results['final_decision'], analysis_results
    
    def get_security_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive security dashboard data"""
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        
        # User statistics
        total_users = len(self.users)
        active_sessions = len(self.sessions)
        locked_accounts = len([u for u in self.users.values() if u.account_locked])
        mfa_enabled = len([u for u in self.users.values() if u.mfa_enabled])
        
        # Device statistics
        total_devices = len(self.device_registry)
        trusted_devices = len([d for d in self.device_registry.values() if d.get('trusted', False)])
        
        # Threat statistics
        active_threats = len([t for t in self.threat_intelligence.values() if not t.is_expired()])
        critical_threats = len([t for t in self.threat_intelligence.values() 
                              if not t.is_expired() and t.threat_level == ThreatLevel.CRITICAL])
        
        # Recent security events
        recent_events = [e for e in self.security_events if e.timestamp >= last_24h]
        high_severity_events = [e for e in recent_events if e.severity in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]]
        
        return {
            'timestamp': now.isoformat(),
            'users': {
                'total': total_users,
                'active_sessions': active_sessions,
                'locked_accounts': locked_accounts,
                'mfa_enabled': mfa_enabled,
                'mfa_adoption_rate': mfa_enabled / max(total_users, 1)
            },
            'devices': {
                'total': total_devices,
                'trusted': trusted_devices,
                'trust_ratio': trusted_devices / max(total_devices, 1),
                'fingerprints_registered': len(self.device_fingerprints)
            },
            'threats': {
                'active_indicators': active_threats,
                'critical_threats': critical_threats,
                'threat_sources': list(set(t.source for t in self.threat_intelligence.values()))
            },
            'behavioral_analytics': {
                'profiles_created': len(self.behavioral_profiles),
                'profiles_updated_24h': len([p for p in self.behavioral_profiles.values() 
                                           if p.last_updated >= last_24h])
            },
            'security_events': {
                'total_24h': len(recent_events),
                'high_severity_24h': len(high_severity_events),
                'authentication_failures': len([e for e in recent_events 
                                               if e.event_type == 'AUTHENTICATION_FAILED']),
                'access_denials': len([e for e in recent_events 
                                     if 'ACCESS_DENIED' in e.event_type])
            }
        }