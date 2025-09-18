"""User Management System

Provides comprehensive user management functionality including user creation,
authentication, profile management, and integration with RBAC system.
"""

import hashlib
import secrets
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum

from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, validator

from .rbac import RBACManager, Permission
from .jwt_manager import JWTManager
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    UserNotFoundError,
    UserAlreadyExistsError,
    InvalidCredentialsError
)

logger = logging.getLogger(__name__)


class UserStatus(Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    LOCKED = "locked"


class LoginAttemptResult(Enum):
    """Login attempt results"""
    SUCCESS = "success"
    INVALID_CREDENTIALS = "invalid_credentials"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_SUSPENDED = "account_suspended"
    ACCOUNT_INACTIVE = "account_inactive"
    TOO_MANY_ATTEMPTS = "too_many_attempts"


@dataclass
class UserProfile:
    """User profile information"""
    user_id: str
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    timezone: str = "UTC"
    language: str = "en"
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    status: UserStatus = UserStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    email_verified: bool = False
    phone_verified: bool = False
    two_factor_enabled: bool = False
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    password_changed_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, UserStatus):
                data[key] = value.value
        return data
    
    def is_locked(self) -> bool:
        """Check if account is locked"""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
    
    def is_active(self) -> bool:
        """Check if account is active and not locked"""
        return (
            self.status == UserStatus.ACTIVE and 
            not self.is_locked()
        )


@dataclass
class LoginAttempt:
    """Login attempt record"""
    user_id: str
    ip_address: str
    user_agent: str
    timestamp: datetime
    result: LoginAttemptResult
    details: Optional[str] = None


class UserCreateRequest(BaseModel):
    """User creation request model"""
    username: str
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    roles: Optional[List[str]] = None
    
    @validator('username')
    def validate_username(cls, v):
        if len(v) < 3 or len(v) > 50:
            raise ValueError('Username must be between 3 and 50 characters')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdateRequest(BaseModel):
    """User update request model"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    bio: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    """Password change request model"""
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserManager:
    """User management system"""
    
    def __init__(
        self,
        rbac_manager: RBACManager,
        jwt_manager: JWTManager,
        max_login_attempts: int = 5,
        lockout_duration_minutes: int = 30
    ):
        self.rbac_manager = rbac_manager
        self.jwt_manager = jwt_manager
        self.max_login_attempts = max_login_attempts
        self.lockout_duration = timedelta(minutes=lockout_duration_minutes)
        
        # Password hashing
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12
        )
        
        # In-memory storage (replace with database in production)
        self.users: Dict[str, UserProfile] = {}
        self.user_passwords: Dict[str, str] = {}  # user_id -> hashed_password
        self.username_to_id: Dict[str, str] = {}  # username -> user_id
        self.email_to_id: Dict[str, str] = {}  # email -> user_id
        self.login_attempts: List[LoginAttempt] = []
        
        # Create default admin user
        self._create_default_admin()
    
    def _create_default_admin(self) -> None:
        """Create default admin user if it doesn't exist"""
        admin_username = "admin"
        admin_email = "admin@trading-system.com"
        
        if admin_username not in self.username_to_id:
            try:
                admin_user = self.create_user(
                    UserCreateRequest(
                        username=admin_username,
                        email=admin_email,
                        password="Admin123!",
                        first_name="System",
                        last_name="Administrator",
                        roles=["super_admin"]
                    )
                )
                admin_user.email_verified = True
                admin_user.status = UserStatus.ACTIVE
                logger.info("Created default admin user")
            except UserAlreadyExistsError:
                # Admin user already exists, this is fine
                logger.info("Default admin user already exists")
            except Exception as e:
                logger.error(f"Failed to create default admin user: {e}")
    
    def _generate_user_id(self) -> str:
        """Generate unique user ID"""
        return f"user_{secrets.token_hex(16)}"
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return self.pwd_context.hash(password)
    
    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(password, hashed_password)
    
    def create_user(self, request: UserCreateRequest) -> UserProfile:
        """Create a new user
        
        Args:
            request: User creation request
            
        Returns:
            Created user profile
            
        Raises:
            UserAlreadyExistsError: If username or email already exists
        """
        # Check if username already exists
        if request.username in self.username_to_id:
            raise UserAlreadyExistsError(f"Username '{request.username}' already exists")
        
        # Check if email already exists
        if request.email in self.email_to_id:
            raise UserAlreadyExistsError(f"Email '{request.email}' already exists")
        
        # Generate user ID
        user_id = self._generate_user_id()
        
        # Create user profile
        # Set status to ACTIVE if roles are provided (for testing/admin creation)
        initial_status = UserStatus.ACTIVE if request.roles else UserStatus.PENDING_VERIFICATION
        
        user = UserProfile(
            user_id=user_id,
            username=request.username,
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            phone=request.phone,
            status=initial_status
        )
        
        # Hash and store password
        hashed_password = self._hash_password(request.password)
        
        # Store user data
        self.users[user_id] = user
        self.user_passwords[user_id] = hashed_password
        self.username_to_id[request.username] = user_id
        self.email_to_id[request.email] = user_id
        
        # Assign roles
        if request.roles:
            for role_name in request.roles:
                try:
                    self.rbac_manager.assign_role_to_user(user_id, role_name)
                except AuthorizationError as e:
                    logger.warning(f"Failed to assign role '{role_name}' to user '{user_id}': {e}")
        else:
            # Assign default viewer role
            self.rbac_manager.assign_role_to_user(user_id, "viewer")
        
        logger.info(f"Created user: {request.username} ({user_id})")
        return user
    
    def authenticate_user(
        self, 
        username_or_email: str, 
        password: str,
        ip_address: str = "unknown",
        user_agent: str = "unknown"
    ) -> tuple[Optional[UserProfile], LoginAttemptResult]:
        """Authenticate user with username/email and password
        
        Args:
            username_or_email: Username or email address
            password: User password
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Tuple of (user_profile, login_result)
        """
        # Find user by username or email
        user_id = None
        if "@" in username_or_email:
            user_id = self.email_to_id.get(username_or_email)
        else:
            user_id = self.username_to_id.get(username_or_email.lower())
        
        if not user_id:
            result = LoginAttemptResult.INVALID_CREDENTIALS
            self._record_login_attempt("unknown", ip_address, user_agent, result)
            return None, result
        
        user = self.users.get(user_id)
        if not user:
            result = LoginAttemptResult.INVALID_CREDENTIALS
            self._record_login_attempt(user_id, ip_address, user_agent, result)
            return None, result
        
        # Check account status
        if user.status == UserStatus.SUSPENDED:
            result = LoginAttemptResult.ACCOUNT_SUSPENDED
            self._record_login_attempt(user_id, ip_address, user_agent, result)
            return None, result
        
        if user.status == UserStatus.INACTIVE:
            result = LoginAttemptResult.ACCOUNT_INACTIVE
            self._record_login_attempt(user_id, ip_address, user_agent, result)
            return None, result
        
        # Check if account is locked
        if user.is_locked():
            result = LoginAttemptResult.ACCOUNT_LOCKED
            self._record_login_attempt(user_id, ip_address, user_agent, result)
            return None, result
        
        # Check password
        hashed_password = self.user_passwords.get(user_id)
        if not hashed_password or not self._verify_password(password, hashed_password):
            # Increment failed attempts
            user.failed_login_attempts += 1
            
            # Lock account if too many failed attempts
            if user.failed_login_attempts >= self.max_login_attempts:
                user.locked_until = datetime.utcnow() + self.lockout_duration
                user.status = UserStatus.LOCKED
                result = LoginAttemptResult.ACCOUNT_LOCKED
                logger.warning(f"Account locked due to too many failed attempts: {user.username}")
            else:
                result = LoginAttemptResult.INVALID_CREDENTIALS
            
            self._record_login_attempt(user_id, ip_address, user_agent, result)
            return None, result
        
        # Successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        
        # Activate account if it was pending verification
        if user.status == UserStatus.PENDING_VERIFICATION:
            user.status = UserStatus.ACTIVE
        
        result = LoginAttemptResult.SUCCESS
        self._record_login_attempt(user_id, ip_address, user_agent, result)
        
        logger.info(f"Successful login: {user.username} ({user_id}) from {ip_address}")
        return user, result
    
    def _record_login_attempt(
        self, 
        user_id: str, 
        ip_address: str, 
        user_agent: str, 
        result: LoginAttemptResult
    ) -> None:
        """Record login attempt"""
        attempt = LoginAttempt(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow(),
            result=result
        )
        self.login_attempts.append(attempt)
        
        # Keep only last 1000 attempts (in production, use proper storage)
        if len(self.login_attempts) > 1000:
            self.login_attempts = self.login_attempts[-1000:]
    
    def get_user_by_id(self, user_id: str) -> Optional[UserProfile]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[UserProfile]:
        """Get user by username"""
        user_id = self.username_to_id.get(username.lower())
        return self.users.get(user_id) if user_id else None
    
    def get_user_by_email(self, email: str) -> Optional[UserProfile]:
        """Get user by email"""
        user_id = self.email_to_id.get(email)
        return self.users.get(user_id) if user_id else None
    
    def update_user(self, user_id: str, request: UserUpdateRequest) -> UserProfile:
        """Update user profile
        
        Args:
            user_id: User ID to update
            request: Update request
            
        Returns:
            Updated user profile
            
        Raises:
            UserNotFoundError: If user doesn't exist
            UserAlreadyExistsError: If email already exists
        """
        user = self.users.get(user_id)
        if not user:
            raise UserNotFoundError(f"User '{user_id}' not found")
        
        # Check email conflicts if email is being updated
        if request.email is not None and request.email != user.email:
            if request.email in self.email_to_id:
                raise UserAlreadyExistsError(f"Email '{request.email}' already exists")
        
        # Update fields
        if request.first_name is not None:
            user.first_name = request.first_name
        if request.last_name is not None:
            user.last_name = request.last_name
        if request.email is not None:
            # Remove old email mapping and add new one
            if user.email in self.email_to_id:
                del self.email_to_id[user.email]
            user.email = request.email
            self.email_to_id[request.email] = user_id
        if request.phone is not None:
            user.phone = request.phone
        if request.timezone is not None:
            user.timezone = request.timezone
        if request.language is not None:
            user.language = request.language
        if request.bio is not None:
            user.bio = request.bio
        
        user.updated_at = datetime.utcnow()
        
        logger.info(f"Updated user profile: {user.username} ({user_id})")
        return user
    
    def change_password(
        self, 
        user_id: str, 
        request: PasswordChangeRequest
    ) -> bool:
        """Change user password
        
        Args:
            user_id: User ID
            request: Password change request
            
        Returns:
            True if password changed successfully
            
        Raises:
            UserNotFoundError: If user doesn't exist
            InvalidCredentialsError: If current password is incorrect
        """
        user = self.users.get(user_id)
        if not user:
            raise UserNotFoundError(f"User '{user_id}' not found")
        
        # Verify current password
        current_hash = self.user_passwords.get(user_id)
        if not current_hash or not self._verify_password(request.current_password, current_hash):
            raise InvalidCredentialsError("Current password is incorrect")
        
        # Hash and store new password
        new_hash = self._hash_password(request.new_password)
        self.user_passwords[user_id] = new_hash
        
        # Update password change timestamp
        user.password_changed_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        
        logger.info(f"Password changed for user: {user.username} ({user_id})")
        return True
    
    def delete_user(self, user_id: str) -> bool:
        """Delete user account
        
        Args:
            user_id: User ID to delete
            
        Returns:
            True if user deleted successfully
            
        Raises:
            UserNotFoundError: If user doesn't exist
        """
        user = self.users.get(user_id)
        if not user:
            raise UserNotFoundError(f"User '{user_id}' not found")
        
        # Remove from all mappings
        del self.users[user_id]
        del self.user_passwords[user_id]
        del self.username_to_id[user.username]
        del self.email_to_id[user.email]
        
        # Remove all roles
        user_roles = self.rbac_manager.get_user_roles(user_id)
        for role_name in user_roles:
            self.rbac_manager.remove_role_from_user(user_id, role_name)
        
        logger.info(f"Deleted user: {user.username} ({user_id})")
        return True
    
    def list_users(
        self, 
        status: Optional[UserStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserProfile]:
        """List users with optional filtering
        
        Args:
            status: Filter by user status
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of user profiles
        """
        users = list(self.users.values())
        
        # Filter by status
        if status:
            users = [u for u in users if u.status == status]
        
        # Sort by creation date (newest first)
        users.sort(key=lambda u: u.created_at, reverse=True)
        
        # Apply pagination
        return users[offset:offset + limit]
    
    def get_user_login_history(
        self, 
        user_id: str, 
        limit: int = 50
    ) -> List[LoginAttempt]:
        """Get user login history
        
        Args:
            user_id: User ID
            limit: Maximum number of attempts to return
            
        Returns:
            List of login attempts
        """
        user_attempts = [
            attempt for attempt in self.login_attempts 
            if attempt.user_id == user_id
        ]
        
        # Sort by timestamp (newest first)
        user_attempts.sort(key=lambda a: a.timestamp, reverse=True)
        
        return user_attempts[:limit]