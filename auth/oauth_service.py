#!/usr/bin/env python3
"""
OAuth2/OIDC Authentication Service with Zero-Trust Architecture
Enterprise-grade authentication and authorization service
"""

import os
import jwt
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import aiohttp
import logging
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import pyotp
import qrcode
from io import BytesIO
import re
import json
from .keycloak_client import KeycloakClient, KeycloakConfig, OIDCTokens, UserInfo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserRole(Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    TRADER = "trader"
    ANALYST = "analyst"
    VIEWER = "viewer"
    RISK_MANAGER = "risk_manager"
    COMPLIANCE_OFFICER = "compliance_officer"

class Permission(Enum):
    """System permissions"""
    READ_PORTFOLIO = "read:portfolio"
    WRITE_PORTFOLIO = "write:portfolio"
    EXECUTE_TRADES = "execute:trades"
    VIEW_ANALYTICS = "view:analytics"
    MANAGE_USERS = "manage:users"
    SYSTEM_CONFIG = "system:config"
    RISK_OVERRIDE = "risk:override"
    COMPLIANCE_REVIEW = "compliance:review"

@dataclass
class User:
    """User entity"""
    id: str
    username: str
    email: str
    roles: List[UserRole]
    permissions: List[Permission]
    mfa_enabled: bool = False
    last_login: Optional[datetime] = None
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    created_at: datetime = None
    updated_at: datetime = None

@dataclass
class AuthToken:
    """Authentication token with metadata"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    user_id: str = ""
    username: str = ""
    roles: List[UserRole] = field(default_factory=list)
    permissions: List[Permission] = field(default_factory=list)
    mfa_required: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_oidc: bool = False
    id_token: str = ""
    scope: str = ""

class ZeroTrustValidator:
    """Zero-trust security validator"""
    
    def __init__(self):
        self.risk_threshold = 0.7
        self.device_fingerprints = {}
        self.behavioral_patterns = {}
    
    async def validate_request(self, user_id: str, request_context: Dict) -> Dict[str, Any]:
        """Validate request using zero-trust principles"""
        risk_score = 0.0
        factors = []
        
        # Device fingerprinting
        device_risk = await self._assess_device_risk(user_id, request_context)
        risk_score += device_risk * 0.3
        factors.append(f"Device risk: {device_risk:.2f}")
        
        # Behavioral analysis
        behavior_risk = await self._assess_behavioral_risk(user_id, request_context)
        risk_score += behavior_risk * 0.3
        factors.append(f"Behavior risk: {behavior_risk:.2f}")
        
        # Network analysis
        network_risk = await self._assess_network_risk(request_context)
        risk_score += network_risk * 0.2
        factors.append(f"Network risk: {network_risk:.2f}")
        
        # Time-based analysis
        time_risk = await self._assess_time_risk(user_id, request_context)
        risk_score += time_risk * 0.2
        factors.append(f"Time risk: {time_risk:.2f}")
        
        return {
            "risk_score": risk_score,
            "requires_mfa": risk_score > self.risk_threshold,
            "factors": factors,
            "recommendation": "allow" if risk_score < self.risk_threshold else "challenge"
        }
    
    async def _assess_device_risk(self, user_id: str, context: Dict) -> float:
        """Assess device-based risk"""
        device_id = context.get("device_id", "unknown")
        user_agent = context.get("user_agent", "")
        
        if device_id not in self.device_fingerprints.get(user_id, []):
            return 0.8  # New device
        
        return 0.1  # Known device
    
    async def _assess_behavioral_risk(self, user_id: str, context: Dict) -> float:
        """Assess behavioral risk"""
        current_time = datetime.now().hour
        typical_hours = self.behavioral_patterns.get(user_id, {}).get("typical_hours", [])
        
        if typical_hours and current_time not in typical_hours:
            return 0.6  # Unusual time
        
        return 0.2  # Normal behavior
    
    async def _assess_network_risk(self, context: Dict) -> float:
        """Assess network-based risk"""
        ip_address = context.get("ip_address", "")
        
        # Check for VPN/Proxy/Tor
        if await self._is_suspicious_ip(ip_address):
            return 0.7
        
        return 0.1
    
    async def _assess_time_risk(self, user_id: str, context: Dict) -> float:
        """Assess time-based risk"""
        current_hour = datetime.now().hour
        
        # Higher risk during off-hours (10 PM - 6 AM)
        if current_hour >= 22 or current_hour <= 6:
            return 0.5
        
        return 0.1
    
    async def _is_suspicious_ip(self, ip_address: str) -> bool:
        """Check if IP is suspicious (VPN/Proxy/Tor)"""
        # Placeholder for IP reputation check
        suspicious_ranges = ["10.0.0.0/8", "192.168.0.0/16", "172.16.0.0/12"]
        return False  # Implement actual IP checking logic

class MFAService:
    """Multi-Factor Authentication service"""
    
    def __init__(self):
        self.totp_secrets = {}
        self.backup_codes = {}
    
    def generate_totp_secret(self, user_id: str) -> str:
        """Generate TOTP secret for user"""
        secret = secrets.token_urlsafe(32)
        self.totp_secrets[user_id] = secret
        return secret
    
    def verify_totp(self, user_id: str, token: str) -> bool:
        """Verify TOTP token"""
        # Placeholder for TOTP verification
        # In production, use libraries like pyotp
        return len(token) == 6 and token.isdigit()
    
    def generate_backup_codes(self, user_id: str) -> List[str]:
        """Generate backup codes for user"""
        codes = [secrets.token_hex(4).upper() for _ in range(10)]
        self.backup_codes[user_id] = codes
        return codes
    
    def verify_backup_code(self, user_id: str, code: str) -> bool:
        """Verify backup code"""
        user_codes = self.backup_codes.get(user_id, [])
        if code in user_codes:
            user_codes.remove(code)  # Single use
            return True
        return False

class OAuthService:
    """OAuth2/OIDC Service with Keycloak integration"""
    
    def __init__(self, keycloak_config: KeycloakConfig = None):
        self.secret_key = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
        self.algorithm = "HS256"
        self.access_token_expire = 3600  # 1 hour
        self.refresh_token_expire = 86400 * 7  # 7 days
        
        # In-memory stores (use Redis/Database in production)
        self.users = {}
        self.refresh_tokens = {}
        self.blacklisted_tokens = set()
        
        # Services
        self.zero_trust = ZeroTrustValidator()
        self.mfa_service = MFAService()
        
        # Initialize Keycloak client
        self.keycloak_config = keycloak_config or KeycloakConfig()
        self.keycloak_client = None
        self._keycloak_enabled = True
        
        # Role-Permission mapping
        self.role_permissions = {
            UserRole.ADMIN: list(Permission),
            UserRole.TRADER: [
                Permission.READ_PORTFOLIO, Permission.WRITE_PORTFOLIO,
                Permission.EXECUTE_TRADES, Permission.VIEW_ANALYTICS
            ],
            UserRole.ANALYST: [
                Permission.READ_PORTFOLIO, Permission.VIEW_ANALYTICS
            ],
            UserRole.VIEWER: [Permission.READ_PORTFOLIO],
            UserRole.RISK_MANAGER: [
                Permission.READ_PORTFOLIO, Permission.VIEW_ANALYTICS,
                Permission.RISK_OVERRIDE
            ],
            UserRole.COMPLIANCE_OFFICER: [
                Permission.READ_PORTFOLIO, Permission.VIEW_ANALYTICS,
                Permission.COMPLIANCE_REVIEW
            ]
        }
    
    async def _get_keycloak_client(self) -> Optional[KeycloakClient]:
        """Get initialized Keycloak client"""
        if not self._keycloak_enabled:
            return None
            
        if not self.keycloak_client:
            self.keycloak_client = KeycloakClient(self.keycloak_config)
            await self.keycloak_client.__aenter__()
        return self.keycloak_client
    
    async def close(self):
        """Close Keycloak client connection"""
        if self.keycloak_client:
            await self.keycloak_client.__aexit__(None, None, None)
            self.keycloak_client = None
    
    def _hash_password(self, password: str) -> str:
        """Hash password using PBKDF2"""
        salt = os.urandom(32)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(password.encode())
        return base64.b64encode(salt + key).decode()
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            decoded = base64.b64decode(hashed.encode())
            salt = decoded[:32]
            key = decoded[32:]
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            kdf.verify(password.encode(), key)
            return True
        except Exception:
            return False
    
    def create_user(self, username: str, email: str, password: str, roles: List[UserRole]) -> User:
        """Create new user"""
        user_id = secrets.token_urlsafe(16)
        permissions = []
        
        for role in roles:
            permissions.extend(self.role_permissions.get(role, []))
        
        user = User(
            id=user_id,
            username=username,
            email=email,
            roles=roles,
            permissions=list(set(permissions)),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Store user with hashed password
        self.users[user_id] = {
            "user": user,
            "password_hash": self._hash_password(password)
        }
        
        logger.info(f"Created user: {username} with roles: {[r.value for r in roles]}")
        return user
    
    async def authenticate(self, username: str, password: str, request_context: Dict) -> Optional[AuthToken]:
        """Authenticate user with zero-trust validation"""
        # Find user
        user_data = None
        user_id = None
        
        for uid, data in self.users.items():
            if data["user"].username == username:
                user_data = data
                user_id = uid
                break
        
        if not user_data:
            logger.warning(f"Authentication failed: User {username} not found")
            return None
        
        user = user_data["user"]
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.now():
            logger.warning(f"Authentication failed: Account {username} is locked")
            return None
        
        # Verify password
        if not self._verify_password(password, user_data["password_hash"]):
            user.failed_attempts += 1
            if user.failed_attempts >= 5:
                user.locked_until = datetime.now() + timedelta(minutes=30)
                logger.warning(f"Account {username} locked due to failed attempts")
            return None
        
        # Reset failed attempts on successful password verification
        user.failed_attempts = 0
        user.locked_until = None
        
        # Zero-trust validation
        risk_assessment = await self.zero_trust.validate_request(user_id, request_context)
        
        if risk_assessment["requires_mfa"] and not user.mfa_enabled:
            logger.warning(f"MFA required for user {username} but not enabled")
            return None
        
        # Update last login
        user.last_login = datetime.now()
        user.updated_at = datetime.now()
        
        # Generate tokens
        return self._generate_tokens(user)
    
    async def get_oidc_authorization_url(self, state: str = None, nonce: str = None) -> Optional[str]:
        """Get OIDC authorization URL for Keycloak"""
        client = await self._get_keycloak_client()
        if not client:
            logger.error("Keycloak client not available")
            return None
        
        return client.get_authorization_url(state, nonce)
    
    async def authenticate_with_oidc_code(self, code: str, state: str = None, 
                                        request_context: Dict = None) -> Optional[AuthToken]:
        """Authenticate user using OIDC authorization code"""
        client = await self._get_keycloak_client()
        if not client:
            logger.error("Keycloak client not available")
            return None
        
        # Exchange code for tokens
        oidc_tokens = await client.exchange_code_for_tokens(code, state)
        if not oidc_tokens:
            logger.error("Failed to exchange authorization code for tokens")
            return None
        
        # Get user info
        user_info = await client.get_user_info(oidc_tokens.access_token)
        if not user_info:
            logger.error("Failed to get user info from Keycloak")
            return None
        
        # Zero-trust validation
        if request_context:
            risk_assessment = await self.zero_trust.validate_request(user_info.sub, request_context)
            if risk_assessment["requires_mfa"]:
                logger.warning(f"OIDC authentication blocked: High risk for {user_info.username}")
                return None
        
        # Create or update user in local store
        user = await self._sync_keycloak_user(user_info)
        if not user:
            logger.error(f"Failed to sync user {user_info.username}")
            return None
        
        # Create auth token with OIDC tokens
        auth_token = AuthToken(
            access_token=oidc_tokens.access_token,
            refresh_token=oidc_tokens.refresh_token,
            token_type=oidc_tokens.token_type,
            expires_in=oidc_tokens.expires_in
        )
        
        logger.info(f"User {user.username} authenticated via OIDC successfully")
        return auth_token
    
    async def _sync_keycloak_user(self, user_info: UserInfo) -> Optional[User]:
        """Sync Keycloak user with local user store"""
        # Map Keycloak roles to system roles
        system_roles = []
        for role in user_info.roles:
            if role == "admin":
                system_roles.append(UserRole.ADMIN)
            elif role == "trader":
                system_roles.append(UserRole.TRADER)
            elif role == "analyst":
                system_roles.append(UserRole.ANALYST)
            elif role == "viewer":
                system_roles.append(UserRole.VIEWER)
            elif role == "risk_manager":
                system_roles.append(UserRole.RISK_MANAGER)
            elif role == "compliance_officer":
                system_roles.append(UserRole.COMPLIANCE_OFFICER)
        
        if not system_roles:
            system_roles = [UserRole.VIEWER]  # Default role
        
        # Get permissions for roles
        permissions = []
        for role in system_roles:
            permissions.extend(self.role_permissions.get(role, []))
        
        # Create or update user
        user = User(
            id=user_info.sub,
            username=user_info.username,
            email=user_info.email,
            roles=system_roles,
            permissions=list(set(permissions)),
            mfa_enabled=False,  # Keycloak handles MFA
            last_login=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Store user
        self.users[user.id] = {
            "user": user,
            "password_hash": ""  # Not used for OIDC users
        }
        
        return user
    
    def _generate_tokens(self, user: User) -> AuthToken:
        """Generate access and refresh tokens"""
        now = datetime.utcnow()
        
        # Access token payload
        access_payload = {
            "sub": user.id,
            "username": user.username,
            "email": user.email,
            "roles": [role.value for role in user.roles],
            "permissions": [perm.value for perm in user.permissions],
            "iat": now,
            "exp": now + timedelta(seconds=self.access_token_expire),
            "type": "access"
        }
        
        # Refresh token payload
        refresh_payload = {
            "sub": user.id,
            "iat": now,
            "exp": now + timedelta(seconds=self.refresh_token_expire),
            "type": "refresh"
        }
        
        access_token = jwt.encode(access_payload, self.secret_key, algorithm=self.algorithm)
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm=self.algorithm)
        
        # Store refresh token
        self.refresh_tokens[refresh_token] = user.id
        
        return AuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire
        )
    
    async def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode JWT token (local or OIDC)"""
        if token in self.blacklisted_tokens:
            return None
        
        # Try OIDC token verification first
        client = await self._get_keycloak_client()
        if client:
            payload = await client.verify_token(token)
            if payload:
                return payload
        
        # Fallback to local token verification
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[AuthToken]:
        """Refresh access token using refresh token (local or OIDC)"""
        # Try OIDC token refresh first
        client = await self._get_keycloak_client()
        if client:
            oidc_tokens = await client.refresh_tokens(refresh_token)
            if oidc_tokens:
                # Get updated user info
                user_info = await client.get_user_info(oidc_tokens.access_token)
                if user_info:
                    # Update local user
                    user = await self._sync_keycloak_user(user_info)
                    if user:
                        # Create new auth token
                        auth_token = AuthToken(
                            access_token=oidc_tokens.access_token,
                            refresh_token=oidc_tokens.refresh_token,
                            token_type=oidc_tokens.token_type,
                            expires_in=oidc_tokens.expires_in
                        )
                        
                        # Update token stores
                        self.refresh_tokens[oidc_tokens.refresh_token] = user.id
                        
                        logger.info(f"OIDC tokens refreshed for user {user.username}")
                        return auth_token
        
        # Fallback to local token refresh
        if refresh_token not in self.refresh_tokens:
            return None
        
        payload = await self.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None
        
        user_id = payload["sub"]
        user_data = self.users.get(user_id)
        
        if not user_data:
            return None
        
        logger.info(f"Local tokens refreshed for user {user_data['user'].username}")
        return self._generate_tokens(user_data["user"])
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke token (local or OIDC)"""
        revoked = False
        
        # Add to blacklist for local tokens
        self.blacklisted_tokens.add(token)
        
        # Try OIDC logout if it's an OIDC token
        client = await self._get_keycloak_client()
        if client:
            # Verify if it's an OIDC token and get user info
            payload = await client.verify_token(token)
            if payload:
                # Find refresh token for this user
                user_id = payload.get('sub')
                refresh_token = None
                for rt, uid in self.refresh_tokens.items():
                    if uid == user_id:
                        refresh_token = rt
                        break
                
                if refresh_token:
                    await client.logout(refresh_token)
                    if refresh_token in self.refresh_tokens:
                        del self.refresh_tokens[refresh_token]
                
                logger.info(f"OIDC token revoked for user {payload.get('username', user_id)}")
                revoked = True
        
        return True
    
    def has_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if user has specific permission"""
        user_data = self.users.get(user_id)
        if not user_data:
            return False
        
        return permission in user_data["user"].permissions
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        user_data = self.users.get(user_id)
        return user_data["user"] if user_data else None

# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Initialize OAuth service
        oauth = OAuthService()
        
        # Create test users
        admin_user = oauth.create_user(
            "admin", "admin@trading.com", "admin123",
            [UserRole.ADMIN]
        )
        
        trader_user = oauth.create_user(
            "trader1", "trader@trading.com", "trader123",
            [UserRole.TRADER]
        )
        
        analyst_user = oauth.create_user(
            "analyst1", "analyst@trading.com", "analyst123",
            [UserRole.ANALYST]
        )
        
        # Test authentication
        request_context = {
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0...",
            "device_id": "device123"
        }
        
        # Authenticate trader
        token = await oauth.authenticate("trader1", "trader123", request_context)
        if token:
            print(f"Authentication successful: {token.access_token[:50]}...")
            
            # Verify token
            payload = oauth.verify_token(token.access_token)
            if payload:
                print(f"Token valid for user: {payload['username']}")
                print(f"Roles: {payload['roles']}")
                print(f"Permissions: {payload['permissions']}")
        
        # Test permission checking
        user_id = trader_user.id
        can_trade = oauth.has_permission(user_id, Permission.EXECUTE_TRADES)
        can_manage = oauth.has_permission(user_id, Permission.MANAGE_USERS)
        
        print(f"Trader can execute trades: {can_trade}")
        print(f"Trader can manage users: {can_manage}")
        
        # Test logout functionality
        if token:
            await oauth.revoke_token(token.access_token)
            print("Token revoked successfully")
        
        # Close OAuth service
        await oauth.close()
        
        logger.info("OAuth2/OIDC service initialized successfully")
    
    asyncio.run(main())