"""
Security Middleware for Zero-Trust Architecture - Phase 5 Enterprise Feature
Comprehensive security implementation including RBAC, audit trails, and feature flags

This module implements enterprise-grade security features:
- Zero-Trust architecture principles
- Role-Based Access Control (RBAC)
- Immutable audit trails
- Feature flags for emergency controls
- Request validation and sanitization
- Rate limiting and DDoS protection
"""

import json
import time
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum

from fastapi import Request, Response, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import jwt
from passlib.context import CryptContext
import redis
from sqlalchemy.orm import Session

# Kafka for audit trails
from kafka import KafkaProducer
import uuid

# Configure logging
logger = logging.getLogger(__name__)

# Security configuration
@dataclass
class SecurityConfig:
    """Security configuration settings"""
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    enable_audit_logging: bool = True
    kafka_bootstrap_servers: str = "kafka:9092"
    redis_url: str = "redis://redis:6379"


class UserRole(str, Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    TRADER = "trader"
    ANALYST = "analyst"
    VIEWER = "viewer"
    SYSTEM = "system"


class Permission(str, Enum):
    """System permissions"""
    # Trading permissions
    PLACE_ORDER = "place_order"
    CANCEL_ORDER = "cancel_order"
    VIEW_PORTFOLIO = "view_portfolio"
    MODIFY_STRATEGY = "modify_strategy"
    
    # Analytics permissions
    RUN_BACKTEST = "run_backtest"
    VIEW_ANALYTICS = "view_analytics"
    EXPORT_DATA = "export_data"
    
    # System permissions
    MANAGE_USERS = "manage_users"
    VIEW_SYSTEM_METRICS = "view_system_metrics"
    MODIFY_SYSTEM_CONFIG = "modify_system_config"
    
    # AI permissions
    USE_AI_ASSISTANT = "use_ai_assistant"
    TRAIN_MODELS = "train_models"


@dataclass
class RolePermissions:
    """Role-based permission mapping"""
    role: UserRole
    permissions: Set[Permission]


# Define role permissions
ROLE_PERMISSIONS = {
    UserRole.ADMIN: {
        Permission.PLACE_ORDER, Permission.CANCEL_ORDER, Permission.VIEW_PORTFOLIO,
        Permission.MODIFY_STRATEGY, Permission.RUN_BACKTEST, Permission.VIEW_ANALYTICS,
        Permission.EXPORT_DATA, Permission.MANAGE_USERS, Permission.VIEW_SYSTEM_METRICS,
        Permission.MODIFY_SYSTEM_CONFIG, Permission.USE_AI_ASSISTANT, Permission.TRAIN_MODELS
    },
    UserRole.TRADER: {
        Permission.PLACE_ORDER, Permission.CANCEL_ORDER, Permission.VIEW_PORTFOLIO,
        Permission.MODIFY_STRATEGY, Permission.RUN_BACKTEST, Permission.VIEW_ANALYTICS,
        Permission.USE_AI_ASSISTANT
    },
    UserRole.ANALYST: {
        Permission.VIEW_PORTFOLIO, Permission.RUN_BACKTEST, Permission.VIEW_ANALYTICS,
        Permission.EXPORT_DATA, Permission.USE_AI_ASSISTANT, Permission.TRAIN_MODELS
    },
    UserRole.VIEWER: {
        Permission.VIEW_PORTFOLIO, Permission.VIEW_ANALYTICS
    },
    UserRole.SYSTEM: {
        Permission.VIEW_SYSTEM_METRICS, Permission.MODIFY_SYSTEM_CONFIG
    }
}


@dataclass
class AuditEvent:
    """Audit event for immutable logging"""
    event_id: str
    timestamp: datetime
    user_id: str
    user_role: str
    action: str
    resource: str
    ip_address: str
    user_agent: str
    request_data: Optional[Dict[str, Any]] = None
    response_status: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary for serialization"""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "user_role": self.user_role,
            "action": self.action,
            "resource": self.resource,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_data": self.request_data,
            "response_status": self.response_status,
            "success": self.success,
            "error_message": self.error_message,
            "session_id": self.session_id
        }


class SecurityService:
    """Core security service implementing Zero-Trust principles"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.security = HTTPBearer()
        
        # Initialize Redis for rate limiting and session management
        try:
            self.redis_client = redis.from_url(config.redis_url)
            self.redis_client.ping()
            logger.info("Redis connection established for security service")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
        
        # Initialize Kafka producer for audit logging
        if config.enable_audit_logging:
            try:
                self.kafka_producer = KafkaProducer(
                    bootstrap_servers=config.kafka_bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None
                )
                logger.info("Kafka producer initialized for audit logging")
            except Exception as e:
                logger.error(f"Failed to initialize Kafka producer: {e}")
                self.kafka_producer = None
        else:
            self.kafka_producer = None
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.config.access_token_expire_minutes)
        to_encode.update({"exp": expire, "type": "access"})
        
        return jwt.encode(to_encode, self.config.jwt_secret_key, algorithm=self.config.jwt_algorithm)
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.config.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        return jwt.encode(to_encode, self.config.jwt_secret_key, algorithm=self.config.jwt_algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.config.jwt_secret_key, algorithms=[self.config.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def check_rate_limit(self, identifier: str, limit: int = None, window: int = None) -> bool:
        """Check if request is within rate limits"""
        if not self.redis_client:
            return True  # Allow if Redis is not available
        
        limit = limit or self.config.rate_limit_requests
        window = window or self.config.rate_limit_window_seconds
        
        try:
            current_time = int(time.time())
            window_start = current_time - window
            
            # Use sliding window rate limiting
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(identifier, 0, window_start)
            pipe.zcard(identifier)
            pipe.zadd(identifier, {str(current_time): current_time})
            pipe.expire(identifier, window)
            
            results = pipe.execute()
            request_count = results[1]
            
            return request_count < limit
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            return True  # Allow if rate limiting fails
    
    def log_audit_event(self, event: AuditEvent):
        """Log audit event to Kafka for immutable storage"""
        if not self.kafka_producer:
            logger.warning("Audit logging disabled - Kafka producer not available")
            return
        
        try:
            self.kafka_producer.send(
                topic="audit.events",
                key=event.event_id,
                value=event.to_dict()
            )
            self.kafka_producer.flush()
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    def has_permission(self, user_role: UserRole, permission: Permission) -> bool:
        """Check if user role has specific permission"""
        return permission in ROLE_PERMISSIONS.get(user_role, set())
    
    def validate_request_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize request data"""
        # Basic input validation and sanitization
        sanitized_data = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # Basic XSS prevention
                value = value.replace('<', '&lt;').replace('>', '&gt;')
                # SQL injection prevention (basic)
                dangerous_patterns = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'SELECT', '--', ';']
                for pattern in dangerous_patterns:
                    if pattern.upper() in value.upper():
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid input detected: {pattern}"
                        )
            
            sanitized_data[key] = value
        
        return sanitized_data


class ZeroTrustMiddleware(BaseHTTPMiddleware):
    """Zero-Trust security middleware"""
    
    def __init__(self, app, security_service: SecurityService):
        super().__init__(app)
        self.security_service = security_service
    
    async def dispatch(self, request: Request, call_next):
        """Process request through Zero-Trust security checks"""
        start_time = time.time()
        
        # Extract client information
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")
        
        # Rate limiting check
        rate_limit_key = f"rate_limit:{client_ip}"
        if not self.security_service.check_rate_limit(rate_limit_key):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"}
            )
        
        # Process request
        response = await call_next(request)
        
        # Log processing time
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class RBACMiddleware:
    """Role-Based Access Control middleware"""
    
    def __init__(self, security_service: SecurityService):
        self.security_service = security_service
    
    def require_permission(self, permission: Permission):
        """Decorator to require specific permission"""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract user from request context
                # This would be set by authentication middleware
                request = kwargs.get('request') or (args[0] if args else None)
                if not request:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Request context not available"
                    )
                
                user_role = getattr(request.state, 'user_role', None)
                if not user_role:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required"
                    )
                
                if not self.security_service.has_permission(UserRole(user_role), permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission {permission.value} required"
                    )
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator


class AuditMiddleware(BaseHTTPMiddleware):
    """Audit logging middleware for immutable trails"""
    
    def __init__(self, app, security_service: SecurityService):
        super().__init__(app)
        self.security_service = security_service
    
    async def dispatch(self, request: Request, call_next):
        """Log all requests for audit trail"""
        # Generate unique event ID
        event_id = str(uuid.uuid4())
        
        # Extract request information
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")
        method = request.method
        url = str(request.url)
        
        # Extract user information if available
        user_id = getattr(request.state, 'user_id', 'anonymous')
        user_role = getattr(request.state, 'user_role', 'unknown')
        session_id = getattr(request.state, 'session_id', None)
        
        # Read request body for audit (if not too large)
        request_data = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if len(body) < 10000:  # Only log small payloads
                    request_data = body.decode('utf-8')
            except Exception:
                request_data = "Unable to read request body"
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Create audit event
        audit_event = AuditEvent(
            event_id=event_id,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            user_role=user_role,
            action=f"{method} {url}",
            resource=url,
            ip_address=client_ip,
            user_agent=user_agent,
            request_data={"body": request_data, "process_time": process_time},
            response_status=response.status_code,
            success=response.status_code < 400,
            session_id=session_id
        )
        
        # Log audit event
        self.security_service.log_audit_event(audit_event)
        
        # Add audit ID to response headers
        response.headers["X-Audit-ID"] = event_id
        
        return response


# Feature flags service for emergency controls
class FeatureFlagService:
    """Feature flag service for dynamic system control"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.default_flags = {
            "trading_enabled": True,
            "ai_assistant_enabled": True,
            "backtesting_enabled": True,
            "new_user_registration": True,
            "high_frequency_trading": True,
            "options_trading": True,
            "emergency_stop": False
        }
    
    def is_enabled(self, flag_name: str) -> bool:
        """Check if feature flag is enabled"""
        if not self.redis_client:
            return self.default_flags.get(flag_name, False)
        
        try:
            value = self.redis_client.get(f"feature_flag:{flag_name}")
            if value is None:
                return self.default_flags.get(flag_name, False)
            return value.decode('utf-8').lower() == 'true'
        except Exception as e:
            logger.error(f"Error checking feature flag {flag_name}: {e}")
            return self.default_flags.get(flag_name, False)
    
    def set_flag(self, flag_name: str, enabled: bool):
        """Set feature flag value"""
        if not self.redis_client:
            logger.warning(f"Cannot set feature flag {flag_name} - Redis not available")
            return
        
        try:
            self.redis_client.set(f"feature_flag:{flag_name}", str(enabled).lower())
            logger.info(f"Feature flag {flag_name} set to {enabled}")
        except Exception as e:
            logger.error(f"Error setting feature flag {flag_name}: {e}")
    
    def emergency_stop(self):
        """Emergency stop - disable all trading activities"""
        critical_flags = [
            "trading_enabled",
            "high_frequency_trading",
            "options_trading"
        ]
        
        for flag in critical_flags:
            self.set_flag(flag, False)
        
        self.set_flag("emergency_stop", True)
        logger.critical("EMERGENCY STOP ACTIVATED - All trading disabled")


# Initialize security services
security_config = SecurityConfig()
security_service = SecurityService(security_config)
rbac_middleware = RBACMiddleware(security_service)

# Feature flags service
feature_flags = FeatureFlagService(security_service.redis_client) if security_service.redis_client else None


# Dependency functions for FastAPI
def get_security_service() -> SecurityService:
    """Dependency to get security service"""
    return security_service


def get_feature_flags() -> FeatureFlagService:
    """Dependency to get feature flags service"""
    if not feature_flags:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Feature flags service not available"
        )
    return feature_flags


def require_feature_flag(flag_name: str):
    """Dependency to require feature flag to be enabled"""
    def check_flag(flags: FeatureFlagService = Depends(get_feature_flags)):
        if not flags.is_enabled(flag_name):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Feature {flag_name} is currently disabled"
            )
        return True
    return check_flag


# Permission decorators
require_trading_permission = rbac_middleware.require_permission(Permission.PLACE_ORDER)
require_analytics_permission = rbac_middleware.require_permission(Permission.VIEW_ANALYTICS)
require_admin_permission = rbac_middleware.require_permission(Permission.MANAGE_USERS)