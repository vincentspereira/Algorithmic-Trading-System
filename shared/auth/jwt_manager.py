"""JWT Token Management

Provides secure JWT token generation, validation, and refresh capabilities
for the algorithmic trading system authentication.
"""

import jwt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from .exceptions import TokenError, AuthenticationError


class TokenData(BaseModel):
    """Token payload data structure"""
    user_id: str
    username: str
    email: str
    roles: List[str]
    permissions: List[str]
    exp: datetime
    iat: datetime
    jti: str  # JWT ID for token revocation
    token_type: str = "access"  # access or refresh


class JWTManager:
    """JWT Token Manager for authentication and authorization"""
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7
    ):
        self.secret_key = secret_key or self._generate_secret_key()
        self.algorithm = algorithm
        self.access_token_expire_delta = timedelta(minutes=access_token_expire_minutes)
        self.refresh_token_expire_delta = timedelta(days=refresh_token_expire_days)
        self._revoked_tokens = set()  # In production, use Redis or database
    
    def _generate_secret_key(self) -> str:
        """Generate a secure random secret key"""
        return secrets.token_urlsafe(32)
    
    def create_access_token(
        self,
        user_id: str,
        username: str,
        email: str,
        roles: List[str],
        permissions: List[str],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a new access token
        
        Args:
            user_id: Unique user identifier
            username: Username
            email: User email
            roles: List of user roles
            permissions: List of user permissions
            expires_delta: Custom expiration time
            
        Returns:
            Encoded JWT token string
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + self.access_token_expire_delta
        
        now = datetime.now(timezone.utc)
        jti = secrets.token_urlsafe(16)
        
        payload = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "roles": roles,
            "permissions": permissions,
            "exp": expire,
            "iat": now,
            "jti": jti,
            "token_type": "access"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(
        self,
        user_id: str,
        username: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a new refresh token
        
        Args:
            user_id: Unique user identifier
            username: Username
            expires_delta: Custom expiration time
            
        Returns:
            Encoded JWT refresh token string
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + self.refresh_token_expire_delta
        
        now = datetime.now(timezone.utc)
        jti = secrets.token_urlsafe(16)
        
        payload = {
            "user_id": user_id,
            "username": username,
            "email": "",  # Refresh tokens don't need email
            "roles": [],  # Refresh tokens don't need roles
            "permissions": [],  # Refresh tokens don't need permissions
            "exp": expire,
            "iat": now,
            "jti": jti,
            "token_type": "refresh"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, token_type: str = "access") -> TokenData:
        """Verify and decode a JWT token
        
        Args:
            token: JWT token string
            token_type: Expected token type (access or refresh)
            
        Returns:
            Decoded token data
            
        Raises:
            TokenError: If token is invalid, expired, or revoked
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            # Check if token is revoked
            jti = payload.get("jti")
            if jti in self._revoked_tokens:
                raise TokenError("Token has been revoked")
            
            # Verify token type
            if payload.get("token_type") != token_type:
                raise TokenError(f"Invalid token type. Expected {token_type}")
            
            # Convert datetime strings back to datetime objects
            payload["exp"] = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            payload["iat"] = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
            
            return TokenData(**payload)
            
        except jwt.ExpiredSignatureError:
            raise TokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise TokenError(f"Invalid token: {str(e)}")
        except Exception as e:
            raise TokenError(f"Token verification failed: {str(e)}")
    
    def validate_token(self, token: str, token_type: str = "access") -> TokenData:
        """Validate a JWT token (alias for verify_token)
        
        Args:
            token: JWT token string
            token_type: Expected token type (access or refresh)
            
        Returns:
            Decoded token data
            
        Raises:
            TokenError: If token is invalid, expired, or revoked
        """
        return self.verify_token(token, token_type)
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """Create new access token using refresh token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Dictionary with new access and refresh tokens
            
        Raises:
            TokenError: If refresh token is invalid
        """
        try:
            # Verify refresh token
            token_data = self.verify_token(refresh_token, token_type="refresh")
            
            # For security, we need to get fresh user data
            # In a real implementation, you'd fetch from database
            # Here we'll create new tokens with minimal data
            new_access_token = self.create_access_token(
                user_id=token_data.user_id,
                username=token_data.username,
                email="",  # Would fetch from database
                roles=[],  # Would fetch from database
                permissions=[]  # Would fetch from database
            )
            
            new_refresh_token = self.create_refresh_token(
                user_id=token_data.user_id,
                username=token_data.username
            )
            
            # Revoke old refresh token
            self.revoke_token(refresh_token)
            
            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer"
            }
            
        except TokenError:
            raise
        except Exception as e:
            raise TokenError(f"Token refresh failed: {str(e)}")
    
    def revoke_token(self, token: str) -> None:
        """Revoke a token (add to blacklist)
        
        Args:
            token: JWT token to revoke
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # Allow expired tokens to be revoked
            )
            jti = payload.get("jti")
            if jti:
                self._revoked_tokens.add(jti)
        except Exception:
            # If we can't decode the token, it's already invalid
            pass
    
    def is_token_revoked(self, token: str) -> bool:
        """Check if a token is revoked
        
        Args:
            token: JWT token to check
            
        Returns:
            True if token is revoked, False otherwise
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            jti = payload.get("jti")
            return jti in self._revoked_tokens
        except Exception:
            return True  # Invalid tokens are considered revoked
    
    def get_token_claims(self, token: str) -> Dict[str, Any]:
        """Get token claims without verification (for debugging)
        
        Args:
            token: JWT token
            
        Returns:
            Token claims dictionary
        """
        try:
            return jwt.decode(
                token, 
                options={"verify_signature": False, "verify_exp": False}
            )
        except Exception as e:
            raise TokenError(f"Cannot decode token: {str(e)}")