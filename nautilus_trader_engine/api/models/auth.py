"""
Pydantic models for authentication

This module contains all authentication-related data models used throughout the API.
These models define the structure for login requests, token responses, user information,
and authentication status checks.
"""

from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    """
    Login request model for user authentication
    
    Used to authenticate users and obtain JWT tokens for API access.
    """
    username: str = Field(
        ...,
        description="Username for authentication",
        min_length=3,
        max_length=50,
        example="demo"
    )
    password: str = Field(
        ...,
        description="Password for authentication",
        min_length=6,
        max_length=100,
        example="demo123"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "username": "demo",
                "password": "demo123"
            }
        }


class TokenResponse(BaseModel):
    """
    JWT token response model
    
    Contains access and refresh tokens returned after successful authentication.
    The access token is used for API requests, while the refresh token is used
    to obtain new access tokens when they expire.
    """
    access_token: str = Field(
        ...,
        description="JWT access token for API authentication",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token for obtaining new access tokens",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer' for JWT)",
        example="bearer"
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds",
        example=1800
    )

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }


class RefreshTokenRequest(BaseModel):
    """
    Refresh token request model
    
    Used to exchange a valid refresh token for a new access token
    when the current access token expires.
    """
    refresh_token: str = Field(
        ...,
        description="Valid refresh token to exchange for new access token",
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class UserInfo(BaseModel):
    """
    User information model
    
    Contains detailed information about the authenticated user,
    including their ID, username, status, and account creation date.
    """
    user_id: str = Field(
        ...,
        description="Unique user identifier",
        example="demo_user_001"
    )
    username: Optional[str] = Field(
        None,
        description="Username for the account",
        example="demo"
    )
    is_active: bool = Field(
        default=True,
        description="Whether the user account is active and can authenticate",
        example=True
    )
    created_at: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp when the user account was created",
        example="2024-01-01T00:00:00Z"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "demo_user_001",
                "username": "demo",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z"
            }
        }


class AuthStatus(BaseModel):
    """
    Authentication status model
    
    Provides information about the current authentication state,
    including whether the user is authenticated and when their token expires.
    """
    authenticated: bool = Field(
        ...,
        description="Whether the user is currently authenticated with a valid token",
        example=True
    )
    user_id: Optional[str] = Field(
        None,
        description="User ID if authenticated, null otherwise",
        example="demo_user_001"
    )
    expires_at: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp when the current token expires",
        example="2024-01-01T01:00:00Z"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "authenticated": True,
                "user_id": "demo_user_001",
                "expires_at": "2024-01-01T01:00:00Z"
            }
        }