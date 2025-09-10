#!/usr/bin/env python3
"""
OAuth2/OpenID Connect Authentication Provider
Enterprise-grade implementation with comprehensive security features
"""

import asyncio
import json
import logging
import secrets
import time
import uuid
import hashlib
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict
import jwt
import requests
from authlib.integrations.requests_client import OAuth2Session
from authlib.oauth2.rfc6749 import grants
from authlib.oauth2.rfc6750 import BearerToken
from authlib.oauth2.rfc7636 import CodeChallenge
from authlib.oidc.core import UserInfo
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OAuth2GrantType(Enum):
    """OAuth2 Grant Types"""
    AUTHORIZATION_CODE = "authorization_code"
    IMPLICIT = "implicit"
    PASSWORD = "password"
    CLIENT_CREDENTIALS = "client_credentials"
    REFRESH_TOKEN = "refresh_token"

class OIDCScope(Enum):
    """OpenID Connect Scopes"""
    OPENID = "openid"
    PROFILE = "profile"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"

@dataclass
class OAuth2Client:
    """OAuth2 Client Application"""
    client_id: str
    client_secret: str  # Store the plain text secret
    client_secret_hash: str  # Store the hashed secret for verification
    redirect_uris: List[str]
    grant_types: List[OAuth2GrantType]
    scopes: List[str]
    client_name: str
    client_uri: Optional[str] = None
    logo_uri: Optional[str] = None
    contacts: List[str] = field(default_factory=list)
    tos_uri: Optional[str] = None
    policy_uri: Optional[str] = None
    jwks_uri: Optional[str] = None
    jwks: Optional[Dict[str, Any]] = None
    software_id: Optional[str] = None
    software_version: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True

@dataclass
class OAuth2AuthorizationCode:
    """OAuth2 Authorization Code"""
    code: str
    client_id: str
    redirect_uri: str
    user_id: str
    scopes: List[str]
    expires_at: datetime
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class OAuth2Token:
    """OAuth2 Token"""
    token_id: str
    client_id: str
    user_id: Optional[str]
    access_token: str
    refresh_token: Optional[str]
    token_type: str
    scopes: List[str]
    expires_in: int
    created_at: datetime
    expires_at: datetime
    refresh_expires_at: Optional[datetime] = None
    is_revoked: bool = False

@dataclass
class OIDCUserInfo:
    """OpenID Connect User Information"""
    sub: str  # Subject - Unique identifier for the user
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    middle_name: Optional[str] = None
    nickname: Optional[str] = None
    preferred_username: Optional[str] = None
    profile: Optional[str] = None
    picture: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    email_verified: Optional[bool] = None
    gender: Optional[str] = None
    birthdate: Optional[str] = None
    zoneinfo: Optional[str] = None
    locale: Optional[str] = None
    phone_number: Optional[str] = None
    phone_number_verified: Optional[bool] = None
    address: Optional[Dict[str, str]] = None
    updated_at: Optional[int] = None

class OAuth2OIDCProvider:
    """OAuth2/OpenID Connect Provider Implementation"""
    
    def __init__(self, issuer: str, secret_key: str = None):
        self.issuer = issuer
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        
        # Initialize encryption for sensitive data
        self._init_encryption()
        
        # Storage for clients, codes, and tokens
        self.clients: Dict[str, OAuth2Client] = {}
        self.authorization_codes: Dict[str, OAuth2AuthorizationCode] = {}
        self.tokens: Dict[str, OAuth2Token] = {}
        self.user_info: Dict[str, OIDCUserInfo] = {}
        
        # Token configuration
        self.access_token_lifetime = 3600  # 1 hour
        self.refresh_token_lifetime = 2592000  # 30 days
        self.authorization_code_lifetime = 600  # 10 minutes
        
        # PKCE support
        self.code_challenge = CodeChallenge()
        
        logger.info(f"OAuth2/OIDC Provider initialized with issuer: {issuer}")
    
    def _init_encryption(self):
        """Initialize encryption for sensitive data"""
        # Generate or load encryption key
        key = os.environ.get('OAUTH2_ENCRYPTION_KEY')
        if not key:
            key = Fernet.generate_key()
            logger.warning("Generated new encryption key. Set OAUTH2_ENCRYPTION_KEY environment variable for production.")
        else:
            key = key.encode()
        
        self.cipher_suite = Fernet(key)
    
    def register_client(self, client_data: Dict[str, Any]) -> OAuth2Client:
        """Register a new OAuth2 client"""
        client_id = client_data.get('client_id') or str(uuid.uuid4())
        client_secret = client_data.get('client_secret') or secrets.token_urlsafe(48)
        
        # Hash client secret for storage
        client_secret_hash = self._hash_client_secret(client_secret)
        
        client = OAuth2Client(
            client_id=client_id,
            client_secret=client_secret,  # Store plain text for returning to client
            client_secret_hash=client_secret_hash,  # Store hash for verification
            redirect_uris=client_data.get('redirect_uris', []),
            grant_types=[OAuth2GrantType(g) for g in client_data.get('grant_types', [])],
            scopes=client_data.get('scopes', []),
            client_name=client_data.get('client_name', ''),
            client_uri=client_data.get('client_uri'),
            logo_uri=client_data.get('logo_uri'),
            contacts=client_data.get('contacts', []),
            tos_uri=client_data.get('tos_uri'),
            policy_uri=client_data.get('policy_uri'),
            jwks_uri=client_data.get('jwks_uri'),
            software_id=client_data.get('software_id'),
            software_version=client_data.get('software_version')
        )
        
        self.clients[client_id] = client
        
        logger.info(f"Registered OAuth2 client: {client.client_name} ({client_id})")
        return client
    
    def _hash_client_secret(self, client_secret: str) -> str:
        """Hash client secret for secure storage"""
        return base64.b64encode(
            hashlib.sha256(client_secret.encode()).digest()
        ).decode()
    
    def _verify_client_secret(self, client_secret: str, hashed_secret: str) -> bool:
        """Verify client secret against stored hash"""
        return self._hash_client_secret(client_secret) == hashed_secret
    
    def get_client(self, client_id: str) -> Optional[OAuth2Client]:
        """Get client by ID"""
        return self.clients.get(client_id)
    
    def authenticate_client(self, client_id: str, client_secret: str) -> bool:
        """Authenticate OAuth2 client"""
        client = self.get_client(client_id)
        if not client or not client.is_active:
            return False
        
        return self._verify_client_secret(client_secret, client.client_secret_hash)
    
    def create_authorization_code(self, client_id: str, user_id: str, 
                                redirect_uri: str, scopes: List[str],
                                code_challenge: Optional[str] = None,
                                code_challenge_method: Optional[str] = None) -> str:
        """Create authorization code for OAuth2 flow"""
        client = self.get_client(client_id)
        if not client:
            raise ValueError("Invalid client")
        
        # Validate redirect URI
        if redirect_uri not in client.redirect_uris:
            raise ValueError("Invalid redirect URI")
        
        # Validate scopes
        invalid_scopes = set(scopes) - set(client.scopes)
        if invalid_scopes:
            raise ValueError(f"Invalid scopes: {invalid_scopes}")
        
        # Generate authorization code
        code = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(seconds=self.authorization_code_lifetime)
        
        auth_code = OAuth2AuthorizationCode(
            code=code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            user_id=user_id,
            scopes=scopes,
            expires_at=expires_at,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method
        )
        
        self.authorization_codes[code] = auth_code
        
        logger.info(f"Created authorization code for client {client_id} and user {user_id}")
        return code
    
    def exchange_authorization_code(self, code: str, client_id: str, 
                                  client_secret: str, redirect_uri: str,
                                  code_verifier: Optional[str] = None) -> OAuth2Token:
        """Exchange authorization code for access token"""
        # Authenticate client
        if not self.authenticate_client(client_id, client_secret):
            raise ValueError("Invalid client credentials")
        
        # Get authorization code
        auth_code = self.authorization_codes.get(code)
        if not auth_code:
            raise ValueError("Invalid authorization code")
        
        # Check if code is expired
        if datetime.now() > auth_code.expires_at:
            del self.authorization_codes[code]
            raise ValueError("Authorization code expired")
        
        # Validate client ID
        if auth_code.client_id != client_id:
            raise ValueError("Client ID mismatch")
        
        # Validate redirect URI
        if auth_code.redirect_uri != redirect_uri:
            raise ValueError("Redirect URI mismatch")
        
        # Validate PKCE if used
        if auth_code.code_challenge and code_verifier:
            if not self.code_challenge.validate_code_verifier(
                code_verifier, auth_code.code_challenge, auth_code.code_challenge_method
            ):
                raise ValueError("Invalid code verifier")
        elif auth_code.code_challenge and not code_verifier:
            raise ValueError("Code verifier required")
        
        # Create tokens
        access_token = self._generate_access_token()
        refresh_token = self._generate_refresh_token()
        
        expires_at = datetime.now() + timedelta(seconds=self.access_token_lifetime)
        refresh_expires_at = datetime.now() + timedelta(seconds=self.refresh_token_lifetime)
        
        token = OAuth2Token(
            token_id=str(uuid.uuid4()),
            client_id=client_id,
            user_id=auth_code.user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            scopes=auth_code.scopes,
            expires_in=self.access_token_lifetime,
            created_at=datetime.now(),
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at
        )
        
        self.tokens[access_token] = token
        if refresh_token:
            self.tokens[refresh_token] = token
        
        # Remove used authorization code
        del self.authorization_codes[code]
        
        logger.info(f"Exchanged authorization code for tokens for client {client_id}")
        return token
    
    def refresh_access_token(self, refresh_token: str, client_id: str, 
                           client_secret: str) -> OAuth2Token:
        """Refresh access token using refresh token"""
        # Authenticate client
        if not self.authenticate_client(client_id, client_secret):
            raise ValueError("Invalid client credentials")
        
        # Get existing token
        existing_token = self.tokens.get(refresh_token)
        if not existing_token:
            raise ValueError("Invalid refresh token")
        
        # Check if refresh token is for the correct client
        if existing_token.client_id != client_id:
            raise ValueError("Client ID mismatch")
        
        # Check if refresh token is expired
        if (existing_token.refresh_expires_at and 
            datetime.now() > existing_token.refresh_expires_at):
            # Revoke all tokens for this refresh token
            self._revoke_token(refresh_token)
            raise ValueError("Refresh token expired")
        
        # Check if token is revoked
        if existing_token.is_revoked:
            raise ValueError("Token revoked")
        
        # Create new tokens
        new_access_token = self._generate_access_token()
        new_refresh_token = self._generate_refresh_token()
        
        expires_at = datetime.now() + timedelta(seconds=self.access_token_lifetime)
        refresh_expires_at = datetime.now() + timedelta(seconds=self.refresh_token_lifetime)
        
        new_token = OAuth2Token(
            token_id=str(uuid.uuid4()),
            client_id=client_id,
            user_id=existing_token.user_id,
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="Bearer",
            scopes=existing_token.scopes,
            expires_in=self.access_token_lifetime,
            created_at=datetime.now(),
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at
        )
        
        self.tokens[new_access_token] = new_token
        if new_refresh_token:
            self.tokens[new_refresh_token] = new_token
        
        # Revoke old tokens
        self._revoke_token(refresh_token)
        
        logger.info(f"Refreshed access token for client {client_id}")
        return new_token
    
    def _generate_access_token(self) -> str:
        """Generate access token"""
        return secrets.token_urlsafe(48)
    
    def _generate_refresh_token(self) -> str:
        """Generate refresh token"""
        return secrets.token_urlsafe(48)
    
    def validate_access_token(self, access_token: str) -> Optional[OAuth2Token]:
        """Validate access token"""
        token = self.tokens.get(access_token)
        if not token:
            return None
        
        # Check if token is expired
        if datetime.now() > token.expires_at:
            self._revoke_token(access_token)
            return None
        
        # Check if token is revoked
        if token.is_revoked:
            return None
        
        return token
    
    def _revoke_token(self, token_value: str):
        """Revoke token and related tokens"""
        token = self.tokens.get(token_value)
        if not token:
            return
        
        # Mark token as revoked
        token.is_revoked = True
        
        # Revoke related tokens
        if token.access_token in self.tokens:
            self.tokens[token.access_token].is_revoked = True
        
        if token.refresh_token and token.refresh_token in self.tokens:
            self.tokens[token.refresh_token].is_revoked = True
    
    def revoke_token(self, token_value: str, client_id: str, client_secret: str):
        """Revoke token (public endpoint)"""
        # Authenticate client
        if not self.authenticate_client(client_id, client_secret):
            raise ValueError("Invalid client credentials")
        
        token = self.tokens.get(token_value)
        if not token:
            return  # Token not found, nothing to revoke
        
        # Check if token belongs to client
        if token.client_id != client_id:
            raise ValueError("Token does not belong to client")
        
        self._revoke_token(token_value)
        logger.info(f"Revoked token for client {client_id}")
    
    def get_user_info(self, access_token: str) -> Optional[OIDCUserInfo]:
        """Get user information for OpenID Connect"""
        token = self.validate_access_token(access_token)
        if not token:
            return None
        
        # Check if openid scope is present
        if OIDCScope.OPENID.value not in token.scopes:
            raise ValueError("OpenID scope not present in token")
        
        return self.user_info.get(token.user_id)
    
    def set_user_info(self, user_id: str, user_info: OIDCUserInfo):
        """Set user information for OpenID Connect"""
        self.user_info[user_id] = user_info
        logger.info(f"Set user info for user {user_id}")
    
    def introspect_token(self, token_value: str, client_id: str, 
                        client_secret: str) -> Dict[str, Any]:
        """Introspect token according to RFC 7662"""
        # Authenticate client
        if not self.authenticate_client(client_id, client_secret):
            raise ValueError("Invalid client credentials")
        
        token = self.tokens.get(token_value)
        if not token:
            return {"active": False}
        
        # Check if token belongs to client
        if token.client_id != client_id:
            return {"active": False}
        
        # Check if token is active
        active = (
            not token.is_revoked and 
            datetime.now() <= token.expires_at
        )
        
        if not active:
            return {"active": False}
        
        # Return token information
        return {
            "active": True,
            "scope": " ".join(token.scopes),
            "client_id": token.client_id,
            "username": token.user_id,  # In a real implementation, this would be the username
            "token_type": token.token_type,
            "exp": int(token.expires_at.timestamp()),
            "iat": int(token.created_at.timestamp()),
            "nbf": int(token.created_at.timestamp()),
            "sub": token.user_id,
            "aud": token.client_id,
            "iss": self.issuer
        }
    
    def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set for token verification"""
        # In a production implementation, this would return actual JWKs
        # For this implementation, we'll return a minimal structure
        return {
            "keys": []
        }
    
    def get_openid_configuration(self) -> Dict[str, Any]:
        """Get OpenID Connect configuration"""
        return {
            "issuer": self.issuer,
            "authorization_endpoint": f"{self.issuer}/oauth2/authorize",
            "token_endpoint": f"{self.issuer}/oauth2/token",
            "userinfo_endpoint": f"{self.issuer}/oauth2/userinfo",
            "jwks_uri": f"{self.issuer}/oauth2/jwks",
            "scopes_supported": [scope.value for scope in OIDCScope],
            "response_types_supported": ["code", "token", "id_token"],
            "grant_types_supported": [grant.value for grant in OAuth2GrantType],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
            "claims_supported": [
                "sub", "name", "given_name", "family_name", "middle_name",
                "nickname", "preferred_username", "profile", "picture",
                "website", "email", "email_verified", "gender", "birthdate",
                "zoneinfo", "locale", "phone_number", "phone_number_verified",
                "address", "updated_at"
            ]
        }

# Example usage and testing
if __name__ == "__main__":
    # Initialize OAuth2/OIDC provider
    provider = OAuth2OIDCProvider("https://trading-system.example.com")
    
    # Register a test client
    client_data = {
        "client_name": "Trading Dashboard",
        "redirect_uris": ["https://dashboard.trading-system.example.com/callback"],
        "grant_types": ["authorization_code", "refresh_token"],
        "scopes": ["openid", "profile", "email"]
    }
    
    client = provider.register_client(client_data)
    print(f"Registered client: {client.client_name} with ID: {client.client_id}")
    
    # Set user info for testing
    user_info = OIDCUserInfo(
        sub="user123",
        name="John Doe",
        email="john.doe@example.com",
        email_verified=True
    )
    provider.set_user_info("user123", user_info)
    
    # Create authorization code
    auth_code = provider.create_authorization_code(
        client_id=client.client_id,
        user_id="user123",
        redirect_uri="https://dashboard.trading-system.example.com/callback",
        scopes=["openid", "profile"]
    )
    print(f"Created authorization code: {auth_code}")
    
    # Exchange for tokens
    try:
        token = provider.exchange_authorization_code(
            code=auth_code,
            client_id=client.client_id,
            client_secret=client.client_secret,  # In practice, this would be the actual secret
            redirect_uri="https://dashboard.trading-system.example.com/callback"
        )
        print(f"Exchanged for access token: {token.access_token[:10]}...")
        
        # Get user info
        user_info = provider.get_user_info(token.access_token)
        print(f"User info: {user_info}")
        
        # Introspect token
        introspection = provider.introspect_token(
            token_value=token.access_token,
            client_id=client.client_id,
            client_secret=client.client_secret
        )
        print(f"Token introspection: {introspection}")
        
    except Exception as e:
        print(f"Error: {e}")