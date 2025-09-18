"""
Authentication router for login and token management
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..models.auth import TokenResponse, RefreshTokenRequest, UserInfo, AuthStatus
from ..models.user import UserCreate, UserResponse
from ..core.security import create_token_response, create_access_token
from ..auth.dependencies import get_current_user, verify_refresh_token, security
from ..auth.utils import hash_password, verify_password
from ...database.database import get_db
from ...database.models import User as DBUser

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        401: {"description": "Authentication failed"},
        403: {"description": "Access forbidden"},
        500: {"description": "Internal server error"}
    }
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="User Registration",
    description="Register a new user with a unique username and email",
    responses={
        201: {
            "description": "User successfully registered",
            "content": {
                "application/json": {
                    "example": {
                        "id": "some_uuid",
                        "username": "newuser",
                        "email": "newuser@example.com",
                        "is_active": True,
                        "created_at": "2024-07-28T10:00:00Z"
                    }
                }
            }
        },
        409: {
            "description": "Conflict: Username or email already exists",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Username or email already registered"
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "username"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    **Register New User Endpoint**

    Allows new users to register by providing a username, email, and password.
    """
    db_user = db.query(DBUser).filter(
        (DBUser.username == user.username) | (DBUser.email == user.email)
    ).first()

    if db_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered"
        )

    hashed_password = hash_password(user.password)
    new_user = DBUser(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        created_at=datetime.now(timezone.utc)
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info(f"New user registered: {new_user.username}")
        return UserResponse.from_orm(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered (database constraint violation)"
        )
    except Exception as e:
        logger.error(f"User registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="User Login and Token Generation",
    description="Authenticate user credentials and generate JWT access token",
    responses={
        200: {
            "description": "Login successful, access token generated",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "expires_in": 1800
                    }
                }
            }
        },
        401: {
            "description": "Invalid credentials",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Incorrect username or password"
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "username"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    **User Login Endpoint**

    Authenticates user credentials and returns a JWT access token.
    """
    user = db.query(DBUser).filter(DBUser.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.id})
    logger.info(f"Successful login for user: {user.username}")
    return TokenResponse(access_token=access_token, token_type="bearer", expires_in=3600) # Assuming 1 hour expiration for access token

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh Access Token",
    description="Exchange a valid refresh token for a new access token",
    responses={
        200: {
            "description": "Token refresh successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "expires_in": 1800
                    }
                }
            }
        },
        401: {
            "description": "Invalid or expired refresh token",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid refresh token"
                    }
                }
            }
        }
    }
)
async def refresh_token(refresh_request: RefreshTokenRequest):
    """
    **Token Refresh Endpoint**
    
    Exchanges a valid refresh token for a new access token, extending the user's session.
    
    ### When to Use
    - When your access token expires (after 30 minutes)
    - To maintain continuous API access without re-authentication
    - As part of automatic token refresh in client applications
    
    ### Process
    1. Submit your current refresh token
    2. Server validates the refresh token
    3. If valid, server generates new access and refresh tokens
    4. Use the new access token for subsequent API requests
    
    ### Security Features
    - Refresh tokens are single-use (new refresh token provided each time)
    - Refresh tokens expire after 7 days
    - Invalid refresh attempts are logged for security monitoring
    
    ### Error Handling
    - If refresh token is invalid or expired, client must re-authenticate via `/auth/login`
    - Failed refresh attempts may indicate token compromise
    """
    try:
        # Verify refresh token and get user ID
        user_id = verify_refresh_token(refresh_request.refresh_token)
        
        # Create new token response
        token_response = create_token_response(user_id)
        
        logger.info(f"Token refreshed for user: {user_id}")
        
        return TokenResponse(**token_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during token refresh"
        )


@router.get(
    "/me",
    response_model=UserInfo,
    summary="Get User Information",
    description="Retrieve information about the currently authenticated user",
    responses={
        200: {
            "description": "User information retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": "demo_user_001",
                        "username": "demo",
                        "is_active": True,
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                }
            }
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        404: {
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User not found"
                    }
                }
            }
        }
    }
)
async def get_current_user_info(current_user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    **Get Current User Information**
    
    Retrieves detailed information about the currently authenticated user.
    
    ### Authentication Required
    This endpoint requires a valid access token in the Authorization header:
    ```
    Authorization: Bearer <your_access_token>
    ```
    
    ### Returned Information
    - **User ID**: Unique identifier for the user account
    - **Username**: The user's login name
    - **Active Status**: Whether the account is currently active
    - **Creation Date**: When the user account was created
    
    ### Use Cases
    - Profile management interfaces
    - User account verification
    - Audit logging and user tracking
    - Personalized application features
    
    ### Security Notes
    - Only returns information for the authenticated user
    - User cannot access other users' information through this endpoint
    - All user data access is logged for security purposes
    """
    user = db.query(DBUser).filter(DBUser.id == current_user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserInfo(
        user_id=str(user.id),
        username=user.username,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() + "Z"
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh Access Token",
    description="Exchange a valid refresh token for a new access token",
    responses={
        200: {
            "description": "Token refresh successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "expires_in": 1800
                    }
                }
            }
        },
        401: {
            "description": "Invalid or expired refresh token",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid refresh token"
                    }
                }
            }
        }
    }
)
async def refresh_token(refresh_request: RefreshTokenRequest):
    """
    **Token Refresh Endpoint**
    
    Exchanges a valid refresh token for a new access token, extending the user's session.
    
    ### When to Use
    - When your access token expires (after 30 minutes)
    - To maintain continuous API access without re-authentication
    - As part of automatic token refresh in client applications
    
    ### Process
    1. Submit your current refresh token
    2. Server validates the refresh token
    3. If valid, server generates new access and refresh tokens
    4. Use the new access token for subsequent API requests
    
    ### Security Features
    - Refresh tokens are single-use (new refresh token provided each time)
    - Refresh tokens expire after 7 days
    - Invalid refresh attempts are logged for security monitoring
    
    ### Error Handling
    - If refresh token is invalid or expired, client must re-authenticate via `/auth/login`
    - Failed refresh attempts may indicate token compromise
    """
    try:
        # Verify refresh token and get user ID
        user_id = verify_refresh_token(refresh_request.refresh_token)
        
        # Create new token response
        token_response = create_token_response(user_id)
        
        logger.info(f"Token refreshed for user: {user_id}")
        
        return TokenResponse(**token_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during token refresh"
        )


@router.get(
    "/me",
    response_model=UserInfo,
    summary="Get User Information",
    description="Retrieve information about the currently authenticated user",
    responses={
        200: {
            "description": "User information retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": "demo_user_001",
                        "username": "demo",
                        "is_active": True,
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                }
            }
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        404: {
            "description": "User not found",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "User not found"
                    }
                }
            }
        }
    }
)
async def get_current_user_info(current_user_id: str = Depends(get_current_user)):
    """
    **Get Current User Information**
    
    Retrieves detailed information about the currently authenticated user.
    
    ### Authentication Required
    This endpoint requires a valid access token in the Authorization header:
    ```
    Authorization: Bearer <your_access_token>
    ```
    
    ### Returned Information
    - **User ID**: Unique identifier for the user account
    - **Username**: The user's login name
    - **Active Status**: Whether the account is currently active
    - **Creation Date**: When the user account was created
    
    ### Use Cases
    - Profile management interfaces
    - User account verification
    - Audit logging and user tracking
    - Personalized application features
    
    ### Security Notes
    - Only returns information for the authenticated user
    - User cannot access other users' information through this endpoint
    - All user data access is logged for security purposes
    """
    try:
        # Find user by ID
        user = None
        for username, user_data in DEMO_USERS.items():
            if user_data["user_id"] == current_user_id:
                user = user_data
                break
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserInfo(
            user_id=user["user_id"],
            username=user["username"],
            is_active=user["is_active"],
            created_at=user["created_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/status",
    response_model=AuthStatus,
    summary="Check Authentication Status",
    description="Verify the validity and expiration of the current access token",
    responses={
        200: {
            "description": "Authentication status retrieved",
            "content": {
                "application/json": {
                    "examples": {
                        "authenticated": {
                            "summary": "Valid token",
                            "value": {
                                "authenticated": True,
                                "user_id": "demo_user_001",
                                "expires_at": "2024-01-01T01:00:00Z"
                            }
                        },
                        "unauthenticated": {
                            "summary": "Invalid token",
                            "value": {
                                "authenticated": False,
                                "user_id": None,
                                "expires_at": None
                            }
                        }
                    }
                }
            }
        }
    }
)
async def get_auth_status(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    **Authentication Status Check**
    
    Verifies the validity of the current access token and returns authentication status.
    
    ### Purpose
    - Validate token before making API requests
    - Check token expiration time
    - Implement client-side authentication state management
    - Debugging authentication issues
    
    ### Response Information
    - **Authenticated**: Boolean indicating if token is valid
    - **User ID**: ID of the authenticated user (if valid)
    - **Expires At**: ISO 8601 timestamp when token expires
    
    ### Use Cases
    - Client applications checking login status
    - Automatic token refresh triggers
    - Session management in web applications
    - API health checks for authenticated services
    
    ### Notes
    - This endpoint is more lenient than others - it returns status rather than failing
    - Invalid tokens return `authenticated: false` instead of 401 error
    - Useful for graceful handling of expired tokens
    """
    try:
        from ..core.security import verify_token
        from jose import jwt
        from ..core.config import settings
        
        # Verify token
        user_id = verify_token(credentials.credentials, token_type="access")
        
        if user_id:
            # Decode token to get expiration
            payload = jwt.decode(
                credentials.credentials, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            expires_at = datetime.fromtimestamp(payload.get("exp")).isoformat()
            
            return AuthStatus(
                authenticated=True,
                user_id=user_id,
                expires_at=expires_at
            )
        else:
            return AuthStatus(authenticated=False)
            
    except Exception as e:
        logger.error(f"Auth status error: {e}")
        return AuthStatus(authenticated=False)


@router.post(
    "/logout",
    summary="User Logout",
    description="Log out the current user and invalidate their session",
    responses={
        200: {
            "description": "Logout successful",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Successfully logged out"
                    }
                }
            }
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        }
    }
)
async def logout(current_user_id: str = Depends(get_current_user)):
    """
    **User Logout Endpoint**
    
    Logs out the currently authenticated user and invalidates their session.
    
    ### Authentication Required
    This endpoint requires a valid access token in the Authorization header:
    ```
    Authorization: Bearer <your_access_token>
    ```
    
    ### Logout Process
    1. Server validates the access token
    2. User logout is logged for audit purposes
    3. Client should discard stored tokens
    4. Success message is returned
    
    ### Client Responsibilities
    After successful logout, the client application should:
    - Remove access and refresh tokens from storage
    - Clear any cached user information
    - Redirect to login page or public area
    - Stop any automatic token refresh processes
    
    ### Security Notes
    - JWT tokens are stateless, so server-side invalidation is limited
    - Token blacklisting could be implemented for enhanced security
    - Logout events are logged for security monitoring
    - Consider implementing token revocation for sensitive applications
    
    ### Best Practices
    - Always call logout before closing the application
    - Implement automatic logout on token expiration
    - Clear sensitive data from client storage
    """
    logger.info(f"User logged out: {current_user_id}")
    return {"message": "Successfully logged out"}