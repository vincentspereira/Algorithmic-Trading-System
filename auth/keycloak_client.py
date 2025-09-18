#!/usr/bin/env python3
"""
Keycloak OIDC Client Integration
Provides Keycloak integration for OAuth2/OIDC authentication flows
"""

import os
import jwt
import json
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from urllib.parse import urlencode, parse_qs, urlparse
import secrets
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwcrypto import jwk, jwt as jwcrypto_jwt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class KeycloakConfig:
    """Keycloak configuration"""
    server_url: str = "http://keycloak.trading.local:8080"
    realm: str = "trading"
    client_id: str = "trading-frontend"
    client_secret: str = "trading-frontend-secret-2024"
    admin_client_id: str = "trading-api"
    admin_client_secret: str = "trading-api-secret-2024"
    redirect_uri: str = "http://localhost:3000/auth/callback"
    scope: str = "openid profile email roles"

@dataclass
class OIDCTokens:
    """OIDC token response"""
    access_token: str
    refresh_token: str
    id_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_expires_in: int = 1800
    scope: str = ""

@dataclass
class UserInfo:
    """User information from OIDC"""
    sub: str
    username: str
    email: str
    email_verified: bool
    name: str
    given_name: str
    family_name: str
    roles: List[str]
    permissions: List[str]
    groups: List[str]

class KeycloakClient:
    """Keycloak OIDC Client"""
    
    def __init__(self, config: KeycloakConfig = None):
        self.config = config or KeycloakConfig()
        self.session = None
        self._jwks_cache = {}
        self._jwks_cache_time = None
        self._admin_token = None
        self._admin_token_expires = None
        
        # Build URLs
        self.base_url = f"{self.config.server_url}/realms/{self.config.realm}"
        self.auth_url = f"{self.base_url}/protocol/openid-connect/auth"
        self.token_url = f"{self.base_url}/protocol/openid-connect/token"
        self.userinfo_url = f"{self.base_url}/protocol/openid-connect/userinfo"
        self.jwks_url = f"{self.base_url}/protocol/openid-connect/certs"
        self.logout_url = f"{self.base_url}/protocol/openid-connect/logout"
        
        # Admin URLs
        self.admin_base_url = f"{self.config.server_url}/admin/realms/{self.config.realm}"
        self.admin_token_url = f"{self.config.server_url}/realms/{self.config.realm}/protocol/openid-connect/token"
        self.admin_users_url = f"{self.admin_base_url}/users"
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def get_authorization_url(self, state: str = None, nonce: str = None) -> str:
        """Generate authorization URL for OAuth2 flow"""
        if not state:
            state = secrets.token_urlsafe(32)
        if not nonce:
            nonce = secrets.token_urlsafe(32)
            
        params = {
            "client_id": self.config.client_id,
            "response_type": "code",
            "scope": self.config.scope,
            "redirect_uri": self.config.redirect_uri,
            "state": state,
            "nonce": nonce
        }
        
        return f"{self.auth_url}?{urlencode(params)}"
    
    async def exchange_code_for_tokens(self, code: str, state: str = None) -> Optional[OIDCTokens]:
        """Exchange authorization code for tokens"""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
            
        data = {
            "grant_type": "authorization_code",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "redirect_uri": self.config.redirect_uri
        }
        
        try:
            async with self.session.post(self.token_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    return OIDCTokens(
                        access_token=token_data["access_token"],
                        refresh_token=token_data.get("refresh_token", ""),
                        id_token=token_data.get("id_token", ""),
                        token_type=token_data.get("token_type", "Bearer"),
                        expires_in=token_data.get("expires_in", 3600),
                        refresh_expires_in=token_data.get("refresh_expires_in", 1800),
                        scope=token_data.get("scope", "")
                    )
                else:
                    error_data = await response.json()
                    logger.error(f"Token exchange failed: {error_data}")
                    return None
        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            return None
    
    async def refresh_tokens(self, refresh_token: str) -> Optional[OIDCTokens]:
        """Refresh access token using refresh token"""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
            
        data = {
            "grant_type": "refresh_token",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": refresh_token
        }
        
        try:
            async with self.session.post(self.token_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    return OIDCTokens(
                        access_token=token_data["access_token"],
                        refresh_token=token_data.get("refresh_token", refresh_token),
                        id_token=token_data.get("id_token", ""),
                        token_type=token_data.get("token_type", "Bearer"),
                        expires_in=token_data.get("expires_in", 3600),
                        refresh_expires_in=token_data.get("refresh_expires_in", 1800),
                        scope=token_data.get("scope", "")
                    )
                else:
                    logger.error(f"Token refresh failed: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None
    
    async def get_jwks(self) -> Dict:
        """Get JSON Web Key Set from Keycloak"""
        # Cache JWKS for 1 hour
        if (self._jwks_cache_time and 
            datetime.now() - self._jwks_cache_time < timedelta(hours=1)):
            return self._jwks_cache
            
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
            
        try:
            async with self.session.get(self.jwks_url) as response:
                if response.status == 200:
                    jwks = await response.json()
                    self._jwks_cache = jwks
                    self._jwks_cache_time = datetime.now()
                    return jwks
                else:
                    logger.error(f"JWKS fetch failed: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"JWKS fetch error: {e}")
            return {}
    
    async def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token using Keycloak's public keys"""
        try:
            # Get JWKS
            jwks = await self.get_jwks()
            if not jwks or "keys" not in jwks:
                logger.error("No JWKS available for token verification")
                return None
            
            # Decode header to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if not kid:
                logger.error("No key ID in token header")
                return None
            
            # Find matching key
            public_key = None
            for key in jwks["keys"]:
                if key.get("kid") == kid:
                    # Convert JWK to PEM format
                    jwk_obj = jwk.JWK(**key)
                    public_key = jwk_obj.export_to_pem()
                    break
            
            if not public_key:
                logger.error(f"No matching key found for kid: {kid}")
                return None
            
            # Verify token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.config.client_id,
                issuer=self.base_url
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    async def get_user_info(self, access_token: str) -> Optional[UserInfo]:
        """Get user information from Keycloak"""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
            
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            async with self.session.get(self.userinfo_url, headers=headers) as response:
                if response.status == 200:
                    user_data = await response.json()
                    
                    # Extract roles from token claims
                    token_payload = await self.verify_token(access_token)
                    roles = []
                    permissions = []
                    groups = []
                    
                    if token_payload:
                        # Extract realm roles
                        realm_access = token_payload.get("realm_access", {})
                        roles.extend(realm_access.get("roles", []))
                        
                        # Extract client roles
                        resource_access = token_payload.get("resource_access", {})
                        client_access = resource_access.get(self.config.client_id, {})
                        roles.extend(client_access.get("roles", []))
                        
                        # Extract groups
                        groups = token_payload.get("groups", [])
                        
                        # Map roles to permissions (implement your mapping logic)
                        permissions = self._map_roles_to_permissions(roles)
                    
                    return UserInfo(
                        sub=user_data.get("sub", ""),
                        username=user_data.get("preferred_username", ""),
                        email=user_data.get("email", ""),
                        email_verified=user_data.get("email_verified", False),
                        name=user_data.get("name", ""),
                        given_name=user_data.get("given_name", ""),
                        family_name=user_data.get("family_name", ""),
                        roles=roles,
                        permissions=permissions,
                        groups=groups
                    )
                else:
                    logger.error(f"User info fetch failed: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"User info fetch error: {e}")
            return None
    
    def _map_roles_to_permissions(self, roles: List[str]) -> List[str]:
        """Map Keycloak roles to system permissions"""
        role_permission_map = {
            "admin": [
                "read:portfolio", "write:portfolio", "execute:trades",
                "view:analytics", "manage:users", "system:config",
                "risk:override", "compliance:review"
            ],
            "trader": [
                "read:portfolio", "write:portfolio", "execute:trades", "view:analytics"
            ],
            "analyst": ["read:portfolio", "view:analytics"],
            "viewer": ["read:portfolio"],
            "risk_manager": ["read:portfolio", "view:analytics", "risk:override"],
            "compliance_officer": ["read:portfolio", "view:analytics", "compliance:review"]
        }
        
        permissions = set()
        for role in roles:
            if role in role_permission_map:
                permissions.update(role_permission_map[role])
        
        return list(permissions)
    
    async def logout(self, refresh_token: str) -> bool:
        """Logout user and invalidate tokens"""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
            
        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": refresh_token
        }
        
        try:
            async with self.session.post(self.logout_url, data=data) as response:
                return response.status == 204
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False
    
    async def get_admin_token(self) -> Optional[str]:
        """Get admin token for Keycloak admin API"""
        # Check if we have a valid cached token
        if (self._admin_token and self._admin_token_expires and 
            datetime.now() < self._admin_token_expires):
            return self._admin_token
            
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
            
        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.admin_client_id,
            "client_secret": self.config.admin_client_secret
        }
        
        try:
            async with self.session.post(self.admin_token_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self._admin_token = token_data["access_token"]
                    expires_in = token_data.get("expires_in", 3600)
                    self._admin_token_expires = datetime.now() + timedelta(seconds=expires_in - 60)
                    return self._admin_token
                else:
                    logger.error(f"Admin token fetch failed: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Admin token fetch error: {e}")
            return None
    
    async def create_user(self, user_data: Dict) -> Optional[str]:
        """Create user in Keycloak"""
        admin_token = await self.get_admin_token()
        if not admin_token:
            return None
            
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with self.session.post(self.admin_users_url, 
                                       json=user_data, headers=headers) as response:
                if response.status == 201:
                    # Extract user ID from Location header
                    location = response.headers.get("Location", "")
                    if location:
                        return location.split("/")[-1]
                    return "created"
                else:
                    error_data = await response.text()
                    logger.error(f"User creation failed: {response.status} - {error_data}")
                    return None
        except Exception as e:
            logger.error(f"User creation error: {e}")
            return None

# Example usage
if __name__ == "__main__":
    async def main():
        config = KeycloakConfig()
        
        async with KeycloakClient(config) as client:
            # Generate authorization URL
            auth_url = client.get_authorization_url()
            print(f"Authorization URL: {auth_url}")
            
            # In a real application, user would be redirected to this URL
            # and then redirected back with an authorization code
            
            # Example: Exchange code for tokens (you'd get this from callback)
            # tokens = await client.exchange_code_for_tokens("auth_code_here")
            
            # Example: Verify a token
            # payload = await client.verify_token("jwt_token_here")
            
            # Example: Get user info
            # user_info = await client.get_user_info("access_token_here")
            
            logger.info("Keycloak client initialized successfully")
    
    asyncio.run(main())