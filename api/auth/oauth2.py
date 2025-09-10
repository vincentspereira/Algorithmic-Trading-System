"""
OAuth2/OIDC Authentication Module for Algorithmic Trading System

This module provides comprehensive authentication and authorization using:
- OAuth2 with Keycloak as the identity provider
- OpenID Connect for user authentication
- Role-Based Access Control (RBAC)
- Multi-Factor Authentication (MFA) support
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
import jwt
import requests
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Configure logging
logger = logging.getLogger(__name__)

class OAuth2Config:
    """OAuth2 configuration settings"""
    
    def __init__(self):
        # Keycloak settings
        self.keycloak_url = os.getenv("KEYCLOAK_URL", "http://localhost:8090")
        self.realm = os.getenv("KEYCLOAK_REALM", "trading-system")
        self.client_id = os.getenv("KEYCLOAK_CLIENT_ID", "trading-api")
        self.client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET", "trading-api-secret")
        self.redirect_uri = os.getenv("KEYCLOAK_REDIRECT_URI", "http://localhost:3000/callback")
        
        # JWT settings
        self.jwt_algorithm = "RS256"
        self.jwt_expiry_hours = 24
        
        # MFA settings
        self.mfa_required_for_roles = ["admin", "risk_manager", "super_admin"]
        self.mfa_window_seconds = 30
        
        # Cache settings
        self.jwks_cache_duration = 3600  # 1 hour

class KeycloakClient:
    """Keycloak client for OAuth2/OIDC operations"""
    
    def __init__(self, config: OAuth2Config):
        self.config = config
        self.jwks_cache = None
        self.jwks_cache_time = None
        self.public_key = None
        
    async def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set from Keycloak"""
        try:
            # Check cache first
            if (self.jwks_cache and self.jwks_cache_time and 
                datetime.now().timestamp() - self.jwks_cache_time < self.config.jwks_cache_duration):
                return self.jwks_cache
                
            async with httpx.AsyncClient() as client:
                url = f"{self.config.keycloak_url}/realms/{self.config.realm}/protocol/openid-connect/certs"
                response = await client.get(url)
                response.raise_for_status()
                jwks = response.json()
                
                # Cache the result
                self.jwks_cache = jwks
                self.jwks_cache_time = datetime.now().timestamp()
                
                return jwks
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch authentication keys")
    
    def get_public_key(self, kid: str) -> str:
        """Get public key for JWT verification"""
        try:
            jwks = asyncio.run(self.get_jwks())
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    # Convert JWK to PEM format
                    public_numbers = rsa.RSAPublicNumbers(
                        e=int.from_bytes(self.base64url_decode(key["e"]), byteorder="big"),
                        n=int.from_bytes(self.base64url_decode(key["n"]), byteorder="big")
                    )
                    public_key = public_numbers.public_key()
                    pem = public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    )
                    return pem.decode("utf-8")
            raise HTTPException(status_code=401, detail="Invalid token key")
        except Exception as e:
            logger.error(f"Failed to get public key: {e}")
            raise HTTPException(status_code=500, detail="Failed to process authentication keys")
    
    def base64url_decode(self, input: str) -> bytes:
        """Base64 URL decode with padding"""
        input += '=' * (4 - len(input) % 4)
        return base64.urlsafe_b64decode(input.encode('utf-8'))
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        try:
            async with httpx.AsyncClient() as client:
                data = {
                    "grant_type": "authorization_code",
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "code": code,
                    "redirect_uri": self.config.redirect_uri
                }
                
                url = f"{self.config.keycloak_url}/realms/{self.config.realm}/protocol/openid-connect/token"
                response = await client.post(url, data=data)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Token exchange failed: {e.response.text}")
            raise HTTPException(status_code=401, detail="Invalid authorization code")
        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            raise HTTPException(status_code=500, detail="Failed to exchange authorization code")
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token"""
        try:
            async with httpx.AsyncClient() as client:
                data = {
                    "grant_type": "refresh_token",
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "refresh_token": refresh_token
                }
                
                url = f"{self.config.keycloak_url}/realms/{self.config.realm}/protocol/openid-connect/token"
                response = await client.post(url, data=data)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Token refresh failed: {e.response.text}")
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise HTTPException(status_code=500, detail="Failed to refresh token")
    
    async def logout(self, refresh_token: str) -> bool:
        """Logout user from Keycloak"""
        try:
            async with httpx.AsyncClient() as client:
                data = {
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "refresh_token": refresh_token
                }
                
                url = f"{self.config.keycloak_url}/realms/{self.config.realm}/protocol/openid-connect/logout"
                response = await client.post(url, data=data)
                return response.status_code == 204
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False

class RBACManager:
    """Role-Based Access Control Manager"""
    
    def __init__(self):
        # Define role hierarchy and permissions
        self.role_permissions = {
            "super_admin": {
                "user_manage", "system_config", "audit_view", "order_create", 
                "order_modify", "order_cancel", "order_approve", "risk_override",
                "sensitive_data_view", "api_admin"
            },
            "admin": {
                "user_manage", "system_config", "audit_view", "order_create",
                "order_modify", "order_cancel", "risk_view", "risk_modify",
                "data_export", "api_write"
            },
            "risk_manager": {
                "order_approve", "risk_override", "risk_view", "risk_modify",
                "sensitive_data_view", "audit_view"
            },
            "trader": {
                "order_create", "order_modify", "order_cancel", "order_view",
                "risk_view", "data_view", "api_read", "api_write"
            },
            "analyst": {
                "order_view", "risk_view", "data_view", "data_export", "api_read"
            },
            "viewer": {
                "order_view", "risk_view", "data_view"
            },
            "api_user": {
                "api_read", "api_write", "order_view", "data_view"
            }
        }
        
        # Define role hierarchy (higher roles inherit lower role permissions)
        self.role_hierarchy = {
            "super_admin": ["admin", "risk_manager", "trader", "analyst", "viewer", "api_user"],
            "admin": ["trader", "analyst", "viewer", "api_user"],
            "risk_manager": ["trader", "analyst", "viewer"],
            "trader": ["analyst", "viewer"],
            "analyst": ["viewer"],
            "viewer": [],
            "api_user": []
        }
    
    def get_effective_permissions(self, roles: List[str]) -> set:
        """Get all effective permissions for a user based on their roles"""
        permissions = set()
        for role in roles:
            # Add direct permissions
            permissions.update(self.role_permissions.get(role, set()))
            
            # Add inherited permissions from role hierarchy
            for inherited_role in self.role_hierarchy.get(role, []):
                permissions.update(self.role_permissions.get(inherited_role, set()))
        
        return permissions
    
    def check_permission(self, roles: List[str], required_permission: str) -> bool:
        """Check if user has required permission"""
        effective_permissions = self.get_effective_permissions(roles)
        return required_permission in effective_permissions

class MFAService:
    """Multi-Factor Authentication Service"""
    
    def __init__(self, config: OAuth2Config):
        self.config = config
        self.mfa_attempts = {}  # In production, use Redis or database
        
    def is_mfa_required(self, roles: List[str]) -> bool:
        """Check if MFA is required for user roles"""
        return any(role in self.config.mfa_required_for_roles for role in roles)
    
    async def verify_totp(self, user_id: str, totp_code: str, secret: str) -> bool:
        """Verify TOTP code"""
        try:
            import pyotp
            totp = pyotp.TOTP(secret)
            return totp.verify(totp_code, valid_window=self.config.mfa_window_seconds // 30)
        except Exception as e:
            logger.error(f"TOTP verification error: {e}")
            return False
    
    def is_mfa_verified(self, session_id: str) -> bool:
        """Check if MFA is verified for session"""
        session_data = self.mfa_attempts.get(session_id, {})
        return session_data.get("verified", False)
    
    def mark_mfa_verified(self, session_id: str) -> None:
        """Mark session as MFA verified"""
        if session_id not in self.mfa_attempts:
            self.mfa_attempts[session_id] = {}
        self.mfa_attempts[session_id]["verified"] = True
        self.mfa_attempts[session_id]["verified_at"] = datetime.now().timestamp()

class OAuth2AuthenticationService:
    """Main OAuth2 authentication service"""
    
    def __init__(self):
        self.config = OAuth2Config()
        self.keycloak_client = KeycloakClient(self.config)
        self.rbac_manager = RBACManager()
        self.mfa_service = MFAService(self.config)
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
        self.http_bearer = HTTPBearer()
    
    async def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            # Decode header to get key ID
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            
            if not kid:
                raise HTTPException(status_code=401, detail="Invalid token format")
            
            # Get public key
            public_key = self.keycloak_client.get_public_key(kid)
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[self.config.jwt_algorithm],
                audience=self.config.client_id,
                issuer=f"{self.config.keycloak_url}/realms/{self.config.realm}"
            )
            
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(status_code=500, detail="Failed to verify token")
    
    async def authenticate_user(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> Dict[str, Any]:
        """Authenticate user using JWT token"""
        token = credentials.credentials
        payload = await self.verify_jwt_token(token)
        
        # Extract user information
        user_info = {
            "user_id": payload.get("sub"),
            "username": payload.get("preferred_username"),
            "email": payload.get("email"),
            "roles": payload.get("realm_access", {}).get("roles", []),
            "permissions": list(self.rbac_manager.get_effective_permissions(
                payload.get("realm_access", {}).get("roles", [])
            )),
            "session_id": payload.get("session_state"),
            "exp": payload.get("exp"),
            "iat": payload.get("iat")
        }
        
        # Check if MFA is required and verified
        if self.mfa_service.is_mfa_required(user_info["roles"]):
            if not self.mfa_service.is_mfa_verified(user_info["session_id"]):
                raise HTTPException(
                    status_code=401, 
                    detail="MFA required for this account. Please complete MFA verification."
                )
        
        return user_info
    
    def require_permission(self, permission: str):
        """Dependency for checking specific permissions"""
        def permission_checker(user: Dict[str, Any] = Depends(self.authenticate_user)) -> Dict[str, Any]:
            if not self.rbac_manager.check_permission(user["roles"], permission):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Permission '{permission}' required for this operation"
                )
            return user
        return permission_checker
    
    async def get_authorization_url(self) -> str:
        """Get Keycloak authorization URL"""
        params = {
            "client_id": self.config.client_id,
            "response_type": "code",
            "redirect_uri": self.config.redirect_uri,
            "scope": "openid profile email roles",
            "response_mode": "query"
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.config.keycloak_url}/realms/{self.config.realm}/protocol/openid-connect/auth?{query_string}"
    
    async def handle_callback(self, code: str) -> Dict[str, Any]:
        """Handle OAuth2 callback and return tokens"""
        return await self.keycloak_client.exchange_code_for_token(code)
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token"""
        return await self.keycloak_client.refresh_token(refresh_token)
    
    async def logout_user(self, refresh_token: str) -> bool:
        """Logout user"""
        return await self.keycloak_client.logout(refresh_token)

# Global authentication service instance
auth_service = OAuth2AuthenticationService()

# Export commonly used dependencies
authenticate_user = auth_service.authenticate_user
require_permission = auth_service.require_permission
oauth2_scheme = auth_service.oauth2_scheme