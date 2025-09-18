"""Authentication API Endpoints

Provides REST API endpoints for user authentication, registration, and
token management for the order management service.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr

from shared.auth import (
    JWTManager,
    RBACManager,
    UserManager,
    UserCreateRequest,
    UserUpdateRequest,
    PasswordChangeRequest,
    TokenData,
    UserProfile,
    LoginAttemptResult,
    JWTBearer,
    get_current_user,
    get_current_user_id,
    AuthenticationError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
    get_http_status_code,
    create_error_response
)

logger = logging.getLogger(__name__)

# Initialize authentication components
jwt_manager = JWTManager(
    secret_key="your-super-secret-jwt-key-change-in-production",  # TODO: Use environment variable
    algorithm="HS256",
    access_token_expire_minutes=30,
    refresh_token_expire_days=7
)

rbac_manager = RBACManager()
user_manager = UserManager(rbac_manager, jwt_manager)
jwt_bearer = JWTBearer(jwt_manager, rbac_manager)

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])


# Request/Response Models
class LoginRequest(BaseModel):
    """Login request model"""
    username_or_email: str
    password: str


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""
    refresh_token: str


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """User response model"""
    user_id: str
    username: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    status: str
    roles: list
    permissions: list
    created_at: str
    last_login: Optional[str]


class ChangePasswordResponse(BaseModel):
    """Change password response model"""
    message: str
    success: bool


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: UserCreateRequest,
    http_request: Request
) -> UserResponse:
    """Register a new user account
    
    Creates a new user account with the provided information.
    Default role 'viewer' is assigned unless specific roles are provided.
    """
    try:
        # Create user
        user = user_manager.create_user(request)
        
        # Get user roles and permissions
        user_roles = rbac_manager.get_user_roles(user.user_id)
        user_permissions = rbac_manager.get_user_permissions(user.user_id)
        
        logger.info(
            f"User registered: {user.username} ({user.user_id}) "
            f"from {http_request.client.host}"
        )
        
        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            status=user.status.value,
            roles=list(user_roles),
            permissions=[p.value for p in user_permissions],
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
        
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    http_request: Request
) -> LoginResponse:
    """Authenticate user and return JWT tokens
    
    Validates user credentials and returns access and refresh tokens
    if authentication is successful.
    """
    try:
        # Get client information
        client_ip = http_request.client.host
        user_agent = http_request.headers.get("user-agent", "unknown")
        
        # Authenticate user
        user, login_result = user_manager.authenticate_user(
            request.username_or_email,
            request.password,
            client_ip,
            user_agent
        )
        
        # Handle authentication result
        if login_result != LoginAttemptResult.SUCCESS or not user:
            error_messages = {
                LoginAttemptResult.INVALID_CREDENTIALS: "Invalid username or password",
                LoginAttemptResult.ACCOUNT_LOCKED: "Account is locked due to too many failed attempts",
                LoginAttemptResult.ACCOUNT_SUSPENDED: "Account is suspended",
                LoginAttemptResult.ACCOUNT_INACTIVE: "Account is inactive",
                LoginAttemptResult.TOO_MANY_ATTEMPTS: "Too many login attempts"
            }
            
            error_message = error_messages.get(login_result, "Authentication failed")
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_message
            )
        
        # Get user roles
        user_roles = rbac_manager.get_user_roles(user.user_id)
        user_permissions = rbac_manager.get_user_permissions(user.user_id)
        
        # Generate tokens
        access_token = jwt_manager.create_access_token(
            user_id=user.user_id,
            username=user.username,
            roles=list(user_roles)
        )
        
        refresh_token = jwt_manager.create_refresh_token(
            user_id=user.user_id,
            username=user.username
        )
        
        logger.info(
            f"Successful login: {user.username} ({user.user_id}) "
            f"from {client_ip}"
        )
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=jwt_manager.access_token_expire_minutes * 60,
            user={
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "status": user.status.value,
                "roles": list(user_roles),
                "permissions": [p.value for p in user_permissions],
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest
) -> TokenResponse:
    """Refresh access token using refresh token
    
    Validates the refresh token and returns a new access token
    if the refresh token is valid and not expired.
    """
    try:
        # Validate refresh token and get new access token
        new_access_token = jwt_manager.refresh_access_token(request.refresh_token)
        
        if not new_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        return TokenResponse(
            access_token=new_access_token,
            expires_in=jwt_manager.access_token_expire_minutes * 60
        )
        
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


@router.post("/logout")
async def logout(
    token_data: TokenData = Depends(jwt_bearer)
) -> Dict[str, str]:
    """Logout user and revoke token
    
    Revokes the current access token to prevent further use.
    """
    try:
        # Revoke the token
        jwt_manager.revoke_token(token_data.jti)
        
        logger.info(f"User logged out: {token_data.username} ({token_data.user_id})")
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    token_data: TokenData = Depends(jwt_bearer)
) -> UserResponse:
    """Get current user profile
    
    Returns the profile information for the currently authenticated user.
    """
    try:
        user = user_manager.get_user_by_id(token_data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get user roles and permissions
        user_roles = rbac_manager.get_user_roles(user.user_id)
        user_permissions = rbac_manager.get_user_permissions(user.user_id)
        
        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            status=user.status.value,
            roles=list(user_roles),
            permissions=[p.value for p in user_permissions],
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    request: UserUpdateRequest,
    token_data: TokenData = Depends(jwt_bearer)
) -> UserResponse:
    """Update current user profile
    
    Updates the profile information for the currently authenticated user.
    """
    try:
        user = user_manager.update_user(token_data.user_id, request)
        
        # Get user roles and permissions
        user_roles = rbac_manager.get_user_roles(user.user_id)
        user_permissions = rbac_manager.get_user_permissions(user.user_id)
        
        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            status=user.status.value,
            roles=list(user_roles),
            permissions=[p.value for p in user_permissions],
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
        
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    except Exception as e:
        logger.error(f"Update profile error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: PasswordChangeRequest,
    token_data: TokenData = Depends(jwt_bearer)
) -> ChangePasswordResponse:
    """Change user password
    
    Changes the password for the currently authenticated user.
    Requires the current password for verification.
    """
    try:
        success = user_manager.change_password(token_data.user_id, request)
        
        if success:
            logger.info(f"Password changed for user: {token_data.username} ({token_data.user_id})")
            return ChangePasswordResponse(
                message="Password changed successfully",
                success=True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to change password"
            )
            
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@router.get("/validate")
async def validate_token(
    token_data: TokenData = Depends(jwt_bearer)
) -> Dict[str, Any]:
    """Validate current token
    
    Validates the current JWT token and returns token information.
    """
    return {
        "valid": True,
        "user_id": token_data.user_id,
        "username": token_data.username,
        "roles": token_data.roles,
        "expires_at": token_data.exp,
        "issued_at": token_data.iat
    }


# Health check endpoint
@router.get("/health")
async def auth_health_check() -> Dict[str, str]:
    """Authentication service health check"""
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": datetime.utcnow().isoformat()
    }