#!/usr/bin/env python3
"""
Secure Session Manager
Enhanced session management with secure token handling
"""

import logging
import secrets
import json
import base64
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os

from authentication_framework import AuthenticationManager, Session, SessionStatus

logger = logging.getLogger(__name__)

@dataclass
class SecureSessionToken:
    """Secure session token with encryption"""
    token_id: str
    session_id: str
    encrypted_data: str
    created_at: datetime
    expires_at: datetime
    refresh_token: Optional[str] = None
    refresh_expires_at: Optional[datetime] = None

class SecureSessionManager:
    """Enhanced session management with secure token handling"""
    
    def __init__(self, auth_manager: AuthenticationManager):
        self.auth_manager = auth_manager
        self.secure_tokens: Dict[str, SecureSessionToken] = {}
        self.refresh_tokens: Dict[str, str] = {}  # refresh_token -> token_id
        self._init_encryption()
    
    def _init_encryption(self):
        """Initialize encryption for secure token handling"""
        # Generate or load encryption key
        key = os.environ.get('SESSION_ENCRYPTION_KEY')
        if not key:
            key = Fernet.generate_key()
            logger.warning("Generated new session encryption key. Set SESSION_ENCRYPTION_KEY environment variable for production.")
        else:
            key = key.encode()
        
        self.cipher_suite = Fernet(key)
    
    def _generate_token_id(self) -> str:
        """Generate secure token ID"""
        return secrets.token_urlsafe(32)
    
    def _generate_refresh_token(self) -> str:
        """Generate refresh token"""
        return secrets.token_urlsafe(48)
    
    def _encrypt_session_data(self, session_data: Dict[str, Any]) -> str:
        """Encrypt session data"""
        data_json = json.dumps(session_data)
        encrypted_data = self.cipher_suite.encrypt(data_json.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def _decrypt_session_data(self, encrypted_data: str) -> Optional[Dict[str, Any]]:
        """Decrypt session data"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt session data: {e}")
            return None
    
    def create_secure_session(self, session: Session, 
                            refreshable: bool = True,
                            refresh_expiry_hours: int = 720) -> Tuple[str, Optional[str]]:
        """
        Create a secure session token
        
        Args:
            session: The session to secure
            refreshable: Whether to create a refresh token
            refresh_expiry_hours: How long refresh token is valid
            
        Returns:
            Tuple of (access_token, refresh_token)
        """
        # Create token ID
        token_id = self._generate_token_id()
        
        # Prepare session data
        session_data = {
            'session_id': session.session_id,
            'user_id': session.user_id,
            'username': session.username,
            'roles': [role.value for role in session.roles],
            'permissions': [perm.value for perm in session.permissions],
            'created_at': session.created_at.isoformat(),
            'ip_address': session.ip_address,
            'user_agent': session.user_agent
        }
        
        # Encrypt session data
        encrypted_data = self._encrypt_session_data(session_data)
        
        # Create refresh token if requested
        refresh_token = None
        refresh_expires_at = None
        if refreshable:
            refresh_token = self._generate_refresh_token()
            refresh_expires_at = datetime.now() + timedelta(hours=refresh_expiry_hours)
        
        # Create secure token
        secure_token = SecureSessionToken(
            token_id=token_id,
            session_id=session.session_id,
            encrypted_data=encrypted_data,
            created_at=datetime.now(),
            expires_at=session.expires_at,
            refresh_token=refresh_token,
            refresh_expires_at=refresh_expires_at
        )
        
        # Store secure token
        self.secure_tokens[token_id] = secure_token
        if refresh_token:
            self.refresh_tokens[refresh_token] = token_id
        
        # Create access token (combination of token_id and a random part for security)
        access_token = f"{token_id}.{secrets.token_urlsafe(16)}"
        
        logger.info(f"Created secure session token for user {session.username}")
        return access_token, refresh_token
    
    def validate_secure_token(self, access_token: str, 
                            ip_address: str = "unknown") -> Optional[Session]:
        """
        Validate secure session token
        
        Args:
            access_token: The access token to validate
            ip_address: IP address for validation
            
        Returns:
            Session if valid, None otherwise
        """
        # Parse access token
        if '.' not in access_token:
            return None
        
        token_id = access_token.split('.')[0]
        
        # Get secure token
        secure_token = self.secure_tokens.get(token_id)
        if not secure_token:
            return None
        
        # Check if token is expired
        if datetime.now() > secure_token.expires_at:
            del self.secure_tokens[token_id]
            if secure_token.refresh_token:
                self.refresh_tokens.pop(secure_token.refresh_token, None)
            return None
        
        # Decrypt session data
        session_data = self._decrypt_session_data(secure_token.encrypted_data)
        if not session_data:
            return None
        
        # Validate IP address if session IP validation is enabled
        if (self.auth_manager.config.session_ip_validation and 
            session_data.get('ip_address') != ip_address):
            logger.warning(f"IP address mismatch for session {session_data.get('session_id')}")
            return None
        
        # Get original session
        original_session = self.auth_manager.sessions.get(session_data.get('session_id'))
        if not original_session:
            return None
        
        # Check if original session is still valid
        if not original_session.is_active:
            del self.secure_tokens[token_id]
            if secure_token.refresh_token:
                self.refresh_tokens.pop(secure_token.refresh_token, None)
            return None
        
        # Update last activity on original session
        original_session.last_activity = datetime.now()
        
        return original_session
    
    def refresh_secure_token(self, refresh_token: str) -> Optional[Tuple[str, str]]:
        """
        Refresh secure session token using refresh token
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            Tuple of (new_access_token, new_refresh_token) if successful, None otherwise
        """
        # Get token ID from refresh token
        token_id = self.refresh_tokens.get(refresh_token)
        if not token_id:
            return None
        
        # Get secure token
        secure_token = self.secure_tokens.get(token_id)
        if not secure_token:
            return None
        
        # Check if refresh token is expired
        if (secure_token.refresh_expires_at and 
            datetime.now() > secure_token.refresh_expires_at):
            # Remove expired tokens
            del self.secure_tokens[token_id]
            self.refresh_tokens.pop(refresh_token, None)
            return None
        
        # Get original session
        original_session = self.auth_manager.sessions.get(secure_token.session_id)
        if not original_session or not original_session.is_active:
            # Remove invalid tokens
            del self.secure_tokens[token_id]
            self.refresh_tokens.pop(refresh_token, None)
            return None
        
        # Extend session
        original_session.extend_session()
        
        # Create new secure token
        new_access_token, new_refresh_token = self.create_secure_session(
            original_session, 
            refreshable=True
        )
        
        # Remove old tokens
        del self.secure_tokens[token_id]
        self.refresh_tokens.pop(refresh_token, None)
        
        return new_access_token, new_refresh_token
    
    def revoke_secure_token(self, access_token: str):
        """
        Revoke secure session token
        
        Args:
            access_token: The access token to revoke
        """
        # Parse access token
        if '.' not in access_token:
            return
        
        token_id = access_token.split('.')[0]
        
        # Get secure token
        secure_token = self.secure_tokens.get(token_id)
        if not secure_token:
            return
        
        # Remove tokens
        del self.secure_tokens[token_id]
        if secure_token.refresh_token:
            self.refresh_tokens.pop(secure_token.refresh_token, None)
        
        logger.info(f"Revoked secure session token {token_id}")
    
    def cleanup_expired_tokens(self):
        """Clean up expired secure tokens"""
        now = datetime.now()
        expired_tokens = []
        
        # Find expired tokens
        for token_id, secure_token in self.secure_tokens.items():
            if now > secure_token.expires_at:
                expired_tokens.append(token_id)
        
        # Remove expired tokens
        for token_id in expired_tokens:
            secure_token = self.secure_tokens.pop(token_id, None)
            if secure_token and secure_token.refresh_token:
                self.refresh_tokens.pop(secure_token.refresh_token, None)
        
        logger.info(f"Cleaned up {len(expired_tokens)} expired secure tokens")
    
    def get_session_metrics(self) -> Dict[str, Any]:
        """Get session management metrics"""
        active_sessions = len([s for s in self.auth_manager.sessions.values() if s.is_active])
        secure_tokens = len(self.secure_tokens)
        refresh_tokens = len(self.refresh_tokens)
        
        return {
            "active_sessions": active_sessions,
            "secure_tokens": secure_tokens,
            "refresh_tokens": refresh_tokens
        }

# Example usage
if __name__ == "__main__":
    print("Secure Session Manager module loaded")