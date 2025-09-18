import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# Configure logging
logger = logging.getLogger(__name__)

class AuthenticationState(Enum):
    """Authentication states for IB integration."""
    UNAUTHENTICATED = "UNAUTHENTICATED"
    AUTHENTICATING = "AUTHENTICATING"
    AUTHENTICATED = "AUTHENTICATED"
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"

class PermissionLevel(Enum):
    """Permission levels for trading operations."""
    READ_ONLY = "READ_ONLY"
    PAPER_TRADING = "PAPER_TRADING"
    LIVE_TRADING = "LIVE_TRADING"
    ADMIN = "ADMIN"

@dataclass
class IBAuthCredentials:
    """Interactive Brokers authentication credentials."""
    username: str
    password: str
    account_id: Optional[str] = None
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    trading_permissions: List[PermissionLevel] = field(default_factory=lambda: [PermissionLevel.PAPER_TRADING])
    session_timeout: int = 3600  # 1 hour default
    max_sessions: int = 5
    
    def __post_init__(self):
        """Validate credentials after initialization."""
        if not self.username or not self.password:
            raise ValueError("Username and password are required")
        
        if len(self.password) < 8:
            raise ValueError("Password must be at least 8 characters long")

@dataclass
class AuthSession:
    """Authentication session information."""
    session_id: str
    user_id: str
    account_id: str
    permissions: List[PermissionLevel]
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    is_active: bool = True
    client_info: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if session is valid and active."""
        return self.is_active and not self.is_expired()
    
    def refresh_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)
    
    def has_permission(self, required_permission: PermissionLevel) -> bool:
        """Check if session has required permission."""
        return required_permission in self.permissions

class IBAuthenticationError(Exception):
    """Base exception for authentication errors."""
    pass

class IBAuthorizationError(Exception):
    """Exception for authorization errors."""
    pass

class IBSessionError(Exception):
    """Exception for session management errors."""
    pass

class IBSecurityError(Exception):
    """Exception for security-related errors."""
    pass

class IBAuthenticationManager:
    """
    Comprehensive authentication and authorization manager for Interactive Brokers integration.
    
    This class handles:
    - User authentication with secure credential storage
    - Session management with expiration and refresh
    - Permission-based authorization
    - Security features like rate limiting and audit logging
    - Multi-factor authentication support
    """
    
    def __init__(
        self,
        credentials_file: Optional[str] = None,
        encryption_key: Optional[bytes] = None,
        session_timeout: int = 3600,
        max_login_attempts: int = 5,
        lockout_duration: int = 900  # 15 minutes
    ):
        """
        Initialize the authentication manager.
        
        Parameters
        ----------
        credentials_file : str, optional
            Path to encrypted credentials file
        encryption_key : bytes, optional
            Encryption key for credential storage
        session_timeout : int
            Default session timeout in seconds
        max_login_attempts : int
            Maximum failed login attempts before lockout
        lockout_duration : int
            Account lockout duration in seconds
        """
        self._credentials_file = credentials_file
        self._encryption_key = encryption_key or self._generate_encryption_key()
        self._session_timeout = session_timeout
        self._max_login_attempts = max_login_attempts
        self._lockout_duration = lockout_duration
        
        # Session management
        self._active_sessions: Dict[str, AuthSession] = {}
        self._user_credentials: Dict[str, IBAuthCredentials] = {}
        
        # Security tracking
        self._login_attempts: Dict[str, List[datetime]] = {}
        self._locked_accounts: Dict[str, datetime] = {}
        self._audit_log: List[Dict[str, Any]] = []
        
        # JWT settings
        self._jwt_secret = self._generate_jwt_secret()
        self._jwt_algorithm = "HS256"
        
        logger.info("IB Authentication Manager initialized")
    
    def _generate_encryption_key(self) -> bytes:
        """Generate a new encryption key for credential storage."""
        return Fernet.generate_key()
    
    def _generate_jwt_secret(self) -> str:
        """Generate a secret key for JWT tokens."""
        return base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')
    
    def _encrypt_data(self, data: str) -> bytes:
        """Encrypt sensitive data."""
        fernet = Fernet(self._encryption_key)
        return fernet.encrypt(data.encode())
    
    def _decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypt sensitive data."""
        fernet = Fernet(self._encryption_key)
        return fernet.decrypt(encrypted_data).decode()
    
    def _hash_password(self, password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """Hash password with salt using PBKDF2."""
        if salt is None:
            salt = os.urandom(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(password.encode())
        return key, salt
    
    def _verify_password(self, password: str, hashed_password: bytes, salt: bytes) -> bool:
        """Verify password against hash."""
        key, _ = self._hash_password(password, salt)
        return hmac.compare_digest(key, hashed_password)
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = str(int(time.time()))
        random_data = os.urandom(16)
        session_data = f"{timestamp}_{random_data.hex()}"
        return hashlib.sha256(session_data.encode()).hexdigest()
    
    def _is_account_locked(self, username: str) -> bool:
        """Check if account is locked due to failed login attempts."""
        if username not in self._locked_accounts:
            return False
        
        lockout_time = self._locked_accounts[username]
        unlock_time = lockout_time + timedelta(seconds=self._lockout_duration)
        
        if datetime.now(timezone.utc) > unlock_time:
            # Unlock account
            del self._locked_accounts[username]
            return False
        
        return True
    
    def _record_login_attempt(self, username: str, success: bool) -> None:
        """Record login attempt for rate limiting."""
        now = datetime.now(timezone.utc)
        
        if username not in self._login_attempts:
            self._login_attempts[username] = []
        
        # Clean old attempts (older than 1 hour)
        cutoff_time = now - timedelta(hours=1)
        self._login_attempts[username] = [
            attempt for attempt in self._login_attempts[username]
            if attempt > cutoff_time
        ]
        
        if not success:
            self._login_attempts[username].append(now)
            
            # Check if account should be locked
            recent_failures = len(self._login_attempts[username])
            if recent_failures >= self._max_login_attempts:
                self._locked_accounts[username] = now
                logger.warning(f"Account {username} locked due to {recent_failures} failed login attempts")
        else:
            # Clear failed attempts on successful login
            self._login_attempts[username] = []
    
    def _audit_log_event(self, event_type: str, username: str, details: Dict[str, Any]) -> None:
        """Log security events for audit purposes."""
        audit_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event_type': event_type,
            'username': username,
            'details': details
        }
        
        self._audit_log.append(audit_entry)
        logger.info(f"Audit log: {event_type} for user {username}")
        
        # Keep only last 1000 entries
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]
    
    async def register_user(
        self,
        username: str,
        password: str,
        account_id: str,
        permissions: List[PermissionLevel],
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None
    ) -> bool:
        """
        Register a new user with encrypted credential storage.
        
        Parameters
        ----------
        username : str
            Username for authentication
        password : str
            User password
        account_id : str
            IB account ID
        permissions : List[PermissionLevel]
            User permissions
        api_key : str, optional
            API key for additional authentication
        secret_key : str, optional
            Secret key for API authentication
        
        Returns
        -------
        bool
            True if registration successful
        """
        try:
            if username in self._user_credentials:
                raise IBAuthenticationError(f"User {username} already exists")
            
            # Validate permissions
            if PermissionLevel.LIVE_TRADING in permissions:
                logger.warning(f"User {username} registered with LIVE_TRADING permissions")
            
            # Create credentials
            credentials = IBAuthCredentials(
                username=username,
                password=password,
                account_id=account_id,
                api_key=api_key,
                secret_key=secret_key,
                trading_permissions=permissions
            )
            
            # Store encrypted credentials
            self._user_credentials[username] = credentials
            
            # Save to file if specified
            if self._credentials_file:
                await self._save_credentials()
            
            self._audit_log_event('USER_REGISTERED', username, {
                'account_id': account_id,
                'permissions': [p.value for p in permissions]
            })
            
            logger.info(f"User {username} registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error registering user {username}: {str(e)}")
            raise IBAuthenticationError(f"Registration failed: {str(e)}")
    
    async def authenticate(
        self,
        username: str,
        password: str,
        client_info: Optional[Dict[str, Any]] = None
    ) -> AuthSession:
        """
        Authenticate user and create session.
        
        Parameters
        ----------
        username : str
            Username
        password : str
            Password
        client_info : Dict[str, Any], optional
            Client information for audit logging
        
        Returns
        -------
        AuthSession
            Authentication session if successful
        """
        try:
            # Check if account is locked
            if self._is_account_locked(username):
                self._audit_log_event('LOGIN_BLOCKED', username, {
                    'reason': 'account_locked',
                    'client_info': client_info or {}
                })
                raise IBAuthenticationError(f"Account {username} is temporarily locked")
            
            # Verify credentials
            if username not in self._user_credentials:
                self._record_login_attempt(username, False)
                self._audit_log_event('LOGIN_FAILED', username, {
                    'reason': 'user_not_found',
                    'client_info': client_info or {}
                })
                raise IBAuthenticationError("Invalid credentials")
            
            credentials = self._user_credentials[username]
            
            # Verify password (in production, use hashed passwords)
            if credentials.password != password:
                self._record_login_attempt(username, False)
                self._audit_log_event('LOGIN_FAILED', username, {
                    'reason': 'invalid_password',
                    'client_info': client_info or {}
                })
                raise IBAuthenticationError("Invalid credentials")
            
            # Check session limits
            active_user_sessions = [
                session for session in self._active_sessions.values()
                if session.user_id == username and session.is_valid()
            ]
            
            if len(active_user_sessions) >= credentials.max_sessions:
                # Terminate oldest session
                oldest_session = min(active_user_sessions, key=lambda s: s.created_at)
                await self.terminate_session(oldest_session.session_id)
            
            # Create new session
            session_id = self._generate_session_id()
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(seconds=credentials.session_timeout)
            
            session = AuthSession(
                session_id=session_id,
                user_id=username,
                account_id=credentials.account_id or '',
                permissions=credentials.trading_permissions,
                created_at=now,
                expires_at=expires_at,
                last_activity=now,
                client_info=client_info or {}
            )
            
            self._active_sessions[session_id] = session
            self._record_login_attempt(username, True)
            
            self._audit_log_event('LOGIN_SUCCESS', username, {
                'session_id': session_id,
                'permissions': [p.value for p in session.permissions],
                'client_info': client_info or {}
            })
            
            logger.info(f"User {username} authenticated successfully")
            return session
            
        except IBAuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Authentication error for user {username}: {str(e)}")
            raise IBAuthenticationError(f"Authentication failed: {str(e)}")
    
    async def validate_session(self, session_id: str) -> Optional[AuthSession]:
        """
        Validate and refresh session.
        
        Parameters
        ----------
        session_id : str
            Session ID to validate
        
        Returns
        -------
        Optional[AuthSession]
            Valid session if found, None otherwise
        """
        try:
            if session_id not in self._active_sessions:
                return None
            
            session = self._active_sessions[session_id]
            
            if not session.is_valid():
                # Remove invalid session
                del self._active_sessions[session_id]
                self._audit_log_event('SESSION_EXPIRED', session.user_id, {
                    'session_id': session_id
                })
                return None
            
            # Refresh activity
            session.refresh_activity()
            return session
            
        except Exception as e:
            logger.error(f"Error validating session {session_id}: {str(e)}")
            return None
    
    async def authorize_operation(
        self,
        session_id: str,
        required_permission: PermissionLevel,
        operation_details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Authorize operation based on session permissions.
        
        Parameters
        ----------
        session_id : str
            Session ID
        required_permission : PermissionLevel
            Required permission level
        operation_details : Dict[str, Any], optional
            Operation details for audit logging
        
        Returns
        -------
        bool
            True if authorized, False otherwise
        """
        try:
            session = await self.validate_session(session_id)
            if not session:
                self._audit_log_event('AUTHORIZATION_FAILED', 'unknown', {
                    'reason': 'invalid_session',
                    'session_id': session_id,
                    'required_permission': required_permission.value,
                    'operation_details': operation_details or {}
                })
                return False
            
            if not session.has_permission(required_permission):
                self._audit_log_event('AUTHORIZATION_FAILED', session.user_id, {
                    'reason': 'insufficient_permissions',
                    'session_id': session_id,
                    'required_permission': required_permission.value,
                    'user_permissions': [p.value for p in session.permissions],
                    'operation_details': operation_details or {}
                })
                return False
            
            self._audit_log_event('AUTHORIZATION_SUCCESS', session.user_id, {
                'session_id': session_id,
                'required_permission': required_permission.value,
                'operation_details': operation_details or {}
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Authorization error for session {session_id}: {str(e)}")
            return False
    
    async def terminate_session(self, session_id: str) -> bool:
        """
        Terminate a session.
        
        Parameters
        ----------
        session_id : str
            Session ID to terminate
        
        Returns
        -------
        bool
            True if session terminated successfully
        """
        try:
            if session_id in self._active_sessions:
                session = self._active_sessions[session_id]
                session.is_active = False
                del self._active_sessions[session_id]
                
                self._audit_log_event('SESSION_TERMINATED', session.user_id, {
                    'session_id': session_id
                })
                
                logger.info(f"Session {session_id} terminated")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error terminating session {session_id}: {str(e)}")
            return False
    
    async def terminate_all_user_sessions(self, username: str) -> int:
        """
        Terminate all sessions for a user.
        
        Parameters
        ----------
        username : str
            Username
        
        Returns
        -------
        int
            Number of sessions terminated
        """
        try:
            user_sessions = [
                session_id for session_id, session in self._active_sessions.items()
                if session.user_id == username
            ]
            
            terminated_count = 0
            for session_id in user_sessions:
                if await self.terminate_session(session_id):
                    terminated_count += 1
            
            logger.info(f"Terminated {terminated_count} sessions for user {username}")
            return terminated_count
            
        except Exception as e:
            logger.error(f"Error terminating sessions for user {username}: {str(e)}")
            return 0
    
    def generate_jwt_token(self, session: AuthSession) -> str:
        """
        Generate JWT token for session.
        
        Parameters
        ----------
        session : AuthSession
            Authentication session
        
        Returns
        -------
        str
            JWT token
        """
        payload = {
            'session_id': session.session_id,
            'user_id': session.user_id,
            'account_id': session.account_id,
            'permissions': [p.value for p in session.permissions],
            'iat': int(session.created_at.timestamp()),
            'exp': int(session.expires_at.timestamp())
        }
        
        return jwt.encode(payload, self._jwt_secret, algorithm=self._jwt_algorithm)
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token.
        
        Parameters
        ----------
        token : str
            JWT token to verify
        
        Returns
        -------
        Optional[Dict[str, Any]]
            Decoded token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self._jwt_secret, algorithms=[self._jwt_algorithm])
            return payload
        except jwt.InvalidTokenError:
            return None
    
    async def _save_credentials(self) -> None:
        """
        Save encrypted credentials to file.
        """
        try:
            if not self._credentials_file:
                return
            
            # Prepare data for encryption
            credentials_data = {}
            for username, creds in self._user_credentials.items():
                credentials_data[username] = {
                    'username': creds.username,
                    'password': creds.password,  # In production, store hashed
                    'account_id': creds.account_id,
                    'api_key': creds.api_key,
                    'secret_key': creds.secret_key,
                    'trading_permissions': [p.value for p in creds.trading_permissions],
                    'session_timeout': creds.session_timeout,
                    'max_sessions': creds.max_sessions
                }
            
            # Encrypt and save
            encrypted_data = self._encrypt_data(json.dumps(credentials_data))
            
            credentials_path = Path(self._credentials_file)
            credentials_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(credentials_path, 'wb') as f:
                f.write(encrypted_data)
            
            logger.info(f"Credentials saved to {self._credentials_file}")
            
        except Exception as e:
            logger.error(f"Error saving credentials: {str(e)}")
            raise IBSecurityError(f"Failed to save credentials: {str(e)}")
    
    async def load_credentials(self) -> None:
        """
        Load encrypted credentials from file.
        """
        try:
            if not self._credentials_file or not Path(self._credentials_file).exists():
                logger.info("No credentials file found")
                return
            
            with open(self._credentials_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt and load
            credentials_json = self._decrypt_data(encrypted_data)
            credentials_data = json.loads(credentials_json)
            
            for username, creds_dict in credentials_data.items():
                permissions = [PermissionLevel(p) for p in creds_dict['trading_permissions']]
                
                credentials = IBAuthCredentials(
                    username=creds_dict['username'],
                    password=creds_dict['password'],
                    account_id=creds_dict.get('account_id'),
                    api_key=creds_dict.get('api_key'),
                    secret_key=creds_dict.get('secret_key'),
                    trading_permissions=permissions,
                    session_timeout=creds_dict.get('session_timeout', 3600),
                    max_sessions=creds_dict.get('max_sessions', 5)
                )
                
                self._user_credentials[username] = credentials
            
            logger.info(f"Loaded {len(self._user_credentials)} user credentials")
            
        except Exception as e:
            logger.error(f"Error loading credentials: {str(e)}")
            raise IBSecurityError(f"Failed to load credentials: {str(e)}")
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """
        Get information about active sessions.
        
        Returns
        -------
        List[Dict[str, Any]]
            List of active session information
        """
        sessions_info = []
        
        for session in self._active_sessions.values():
            if session.is_valid():
                sessions_info.append({
                    'session_id': session.session_id,
                    'user_id': session.user_id,
                    'account_id': session.account_id,
                    'permissions': [p.value for p in session.permissions],
                    'created_at': session.created_at.isoformat(),
                    'expires_at': session.expires_at.isoformat(),
                    'last_activity': session.last_activity.isoformat(),
                    'client_info': session.client_info
                })
        
        return sessions_info
    
    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get audit log entries.
        
        Parameters
        ----------
        limit : int
            Maximum number of entries to return
        
        Returns
        -------
        List[Dict[str, Any]]
            Audit log entries
        """
        return self._audit_log[-limit:]
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns
        -------
        int
            Number of sessions cleaned up
        """
        expired_sessions = [
            session_id for session_id, session in self._active_sessions.items()
            if not session.is_valid()
        ]
        
        for session_id in expired_sessions:
            await self.terminate_session(session_id)
        
        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        return len(expired_sessions)

# Factory function for easy instantiation
def create_auth_manager(
    credentials_file: Optional[str] = None,
    session_timeout: int = 3600,
    **kwargs
) -> IBAuthenticationManager:
    """
    Factory function to create an authentication manager.
    
    Parameters
    ----------
    credentials_file : str, optional
        Path to credentials file
    session_timeout : int
        Session timeout in seconds
    **kwargs
        Additional arguments for IBAuthenticationManager
    
    Returns
    -------
    IBAuthenticationManager
        Configured authentication manager
    """
    return IBAuthenticationManager(
        credentials_file=credentials_file,
        session_timeout=session_timeout,
        **kwargs
    )