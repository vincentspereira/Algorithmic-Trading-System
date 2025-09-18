#!/usr/bin/env python3
"""
Role-Based Access Control (RBAC) and Multi-Factor Authentication (MFA) Service
Enterprise-grade authorization and multi-factor authentication
"""

import os
import pyotp
import qrcode
import secrets
import smtplib
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import json
from io import BytesIO
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResourceType(Enum):
    """System resource types"""
    PORTFOLIO = "portfolio"
    STRATEGY = "strategy"
    TRADE = "trade"
    ANALYTICS = "analytics"
    USER = "user"
    SYSTEM = "system"
    RISK = "risk"
    COMPLIANCE = "compliance"
    DATA_FEED = "data_feed"
    NOTIFICATION = "notification"

class Action(Enum):
    """Available actions on resources"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    APPROVE = "approve"
    OVERRIDE = "override"
    CONFIGURE = "configure"

class MFAMethod(Enum):
    """Multi-factor authentication methods"""
    TOTP = "totp"  # Time-based One-Time Password
    SMS = "sms"    # SMS verification
    EMAIL = "email" # Email verification
    BACKUP_CODES = "backup_codes"
    HARDWARE_TOKEN = "hardware_token"

@dataclass
class Permission:
    """Permission entity"""
    resource: ResourceType
    action: Action
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self):
        return f"{self.action.value}:{self.resource.value}"

@dataclass
class Role:
    """Role entity with permissions"""
    name: str
    description: str
    permissions: Set[Permission] = field(default_factory=set)
    inherits_from: Optional['Role'] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_permission(self, permission: Permission):
        """Add permission to role"""
        self.permissions.add(permission)
        self.updated_at = datetime.now()
    
    def remove_permission(self, permission: Permission):
        """Remove permission from role"""
        self.permissions.discard(permission)
        self.updated_at = datetime.now()
    
    def get_all_permissions(self) -> Set[Permission]:
        """Get all permissions including inherited ones"""
        all_permissions = self.permissions.copy()
        if self.inherits_from:
            all_permissions.update(self.inherits_from.get_all_permissions())
        return all_permissions

@dataclass
class MFAConfig:
    """MFA configuration for user"""
    user_id: str
    enabled_methods: Set[MFAMethod] = field(default_factory=set)
    totp_secret: Optional[str] = None
    backup_codes: List[str] = field(default_factory=list)
    phone_number: Optional[str] = None
    email: Optional[str] = None
    last_used_method: Optional[MFAMethod] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class AccessRequest:
    """Access request for authorization"""
    user_id: str
    resource: ResourceType
    action: Action
    resource_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class AccessDecision:
    """Authorization decision"""
    granted: bool
    reason: str
    conditions: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None

class RBACService:
    """Role-Based Access Control Service"""
    
    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.user_roles: Dict[str, Set[str]] = {}  # user_id -> role_names
        self.resource_owners: Dict[str, str] = {}  # resource_id -> user_id
        self.access_cache: Dict[str, AccessDecision] = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Initialize default roles
        self._initialize_default_roles()
    
    def _initialize_default_roles(self):
        """Initialize default system roles"""
        # Super Admin Role
        super_admin = Role(
            name="super_admin",
            description="Full system access"
        )
        super_admin.permissions = {
            Permission(resource, action) 
            for resource in ResourceType 
            for action in Action
        }
        self.roles["super_admin"] = super_admin
        
        # Admin Role
        admin = Role(
            name="admin",
            description="Administrative access"
        )
        admin_permissions = [
            Permission(ResourceType.USER, Action.CREATE),
            Permission(ResourceType.USER, Action.READ),
            Permission(ResourceType.USER, Action.UPDATE),
            Permission(ResourceType.USER, Action.DELETE),
            Permission(ResourceType.SYSTEM, Action.CONFIGURE),
            Permission(ResourceType.PORTFOLIO, Action.READ),
            Permission(ResourceType.ANALYTICS, Action.READ),
        ]
        admin.permissions = set(admin_permissions)
        self.roles["admin"] = admin
        
        # Trader Role
        trader = Role(
            name="trader",
            description="Trading operations access"
        )
        trader_permissions = [
            Permission(ResourceType.PORTFOLIO, Action.READ),
            Permission(ResourceType.PORTFOLIO, Action.UPDATE),
            Permission(ResourceType.TRADE, Action.CREATE),
            Permission(ResourceType.TRADE, Action.READ),
            Permission(ResourceType.TRADE, Action.EXECUTE),
            Permission(ResourceType.STRATEGY, Action.READ),
            Permission(ResourceType.STRATEGY, Action.EXECUTE),
            Permission(ResourceType.ANALYTICS, Action.READ),
        ]
        trader.permissions = set(trader_permissions)
        self.roles["trader"] = trader
        
        # Analyst Role
        analyst = Role(
            name="analyst",
            description="Analysis and research access"
        )
        analyst_permissions = [
            Permission(ResourceType.PORTFOLIO, Action.READ),
            Permission(ResourceType.ANALYTICS, Action.READ),
            Permission(ResourceType.ANALYTICS, Action.CREATE),
            Permission(ResourceType.STRATEGY, Action.READ),
            Permission(ResourceType.DATA_FEED, Action.READ),
        ]
        analyst.permissions = set(analyst_permissions)
        self.roles["analyst"] = analyst
        
        # Risk Manager Role
        risk_manager = Role(
            name="risk_manager",
            description="Risk management access"
        )
        risk_manager_permissions = [
            Permission(ResourceType.PORTFOLIO, Action.READ),
            Permission(ResourceType.TRADE, Action.READ),
            Permission(ResourceType.RISK, Action.READ),
            Permission(ResourceType.RISK, Action.OVERRIDE),
            Permission(ResourceType.ANALYTICS, Action.READ),
        ]
        risk_manager.permissions = set(risk_manager_permissions)
        self.roles["risk_manager"] = risk_manager
        
        # Compliance Officer Role
        compliance = Role(
            name="compliance_officer",
            description="Compliance and audit access"
        )
        compliance_permissions = [
            Permission(ResourceType.PORTFOLIO, Action.READ),
            Permission(ResourceType.TRADE, Action.READ),
            Permission(ResourceType.COMPLIANCE, Action.READ),
            Permission(ResourceType.COMPLIANCE, Action.APPROVE),
            Permission(ResourceType.ANALYTICS, Action.READ),
        ]
        compliance.permissions = set(compliance_permissions)
        self.roles["compliance_officer"] = compliance
        
        # Viewer Role
        viewer = Role(
            name="viewer",
            description="Read-only access"
        )
        viewer_permissions = [
            Permission(ResourceType.PORTFOLIO, Action.READ),
            Permission(ResourceType.ANALYTICS, Action.READ),
        ]
        viewer.permissions = set(viewer_permissions)
        self.roles["viewer"] = viewer
        
        logger.info("Initialized default RBAC roles")
    
    def create_role(self, name: str, description: str, permissions: List[Permission] = None) -> Role:
        """Create new role"""
        if name in self.roles:
            raise ValueError(f"Role {name} already exists")
        
        role = Role(name=name, description=description)
        if permissions:
            role.permissions = set(permissions)
        
        self.roles[name] = role
        logger.info(f"Created role: {name}")
        return role
    
    def assign_role(self, user_id: str, role_name: str) -> bool:
        """Assign role to user"""
        if role_name not in self.roles:
            logger.error(f"Role {role_name} does not exist")
            return False
        
        if user_id not in self.user_roles:
            self.user_roles[user_id] = set()
        
        self.user_roles[user_id].add(role_name)
        self._clear_user_cache(user_id)
        logger.info(f"Assigned role {role_name} to user {user_id}")
        return True
    
    def revoke_role(self, user_id: str, role_name: str) -> bool:
        """Revoke role from user"""
        if user_id not in self.user_roles:
            return False
        
        self.user_roles[user_id].discard(role_name)
        self._clear_user_cache(user_id)
        logger.info(f"Revoked role {role_name} from user {user_id}")
        return True
    
    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for user"""
        all_permissions = set()
        user_role_names = self.user_roles.get(user_id, set())
        
        for role_name in user_role_names:
            role = self.roles.get(role_name)
            if role:
                all_permissions.update(role.get_all_permissions())
        
        return all_permissions
    
    def authorize(self, request: AccessRequest) -> AccessDecision:
        """Authorize access request"""
        cache_key = f"{request.user_id}:{request.resource.value}:{request.action.value}:{request.resource_id}"
        
        # Check cache
        if cache_key in self.access_cache:
            decision = self.access_cache[cache_key]
            if decision.expires_at and decision.expires_at > datetime.now():
                return decision
        
        # Get user permissions
        user_permissions = self.get_user_permissions(request.user_id)
        
        # Check if user has required permission
        required_permission = Permission(request.resource, request.action)
        
        for permission in user_permissions:
            if (permission.resource == required_permission.resource and 
                permission.action == required_permission.action):
                
                # Check conditions if any
                if self._check_conditions(permission, request):
                    decision = AccessDecision(
                        granted=True,
                        reason="Permission granted",
                        expires_at=datetime.now() + timedelta(seconds=self.cache_ttl)
                    )
                    self.access_cache[cache_key] = decision
                    return decision
        
        # Check resource ownership
        if self._check_resource_ownership(request):
            decision = AccessDecision(
                granted=True,
                reason="Resource owner",
                expires_at=datetime.now() + timedelta(seconds=self.cache_ttl)
            )
            self.access_cache[cache_key] = decision
            return decision
        
        # Access denied
        decision = AccessDecision(
            granted=False,
            reason="Insufficient permissions"
        )
        return decision
    
    def _check_conditions(self, permission: Permission, request: AccessRequest) -> bool:
        """Check permission conditions"""
        if not permission.conditions:
            return True
        
        # Implement condition checking logic
        # For example: time-based access, IP restrictions, etc.
        return True
    
    def _check_resource_ownership(self, request: AccessRequest) -> bool:
        """Check if user owns the resource"""
        if not request.resource_id:
            return False
        
        owner_id = self.resource_owners.get(request.resource_id)
        return owner_id == request.user_id
    
    def _clear_user_cache(self, user_id: str):
        """Clear cache entries for user"""
        keys_to_remove = [key for key in self.access_cache.keys() if key.startswith(f"{user_id}:")]
        for key in keys_to_remove:
            del self.access_cache[key]

class MFAService:
    """Multi-Factor Authentication Service"""
    
    def __init__(self):
        self.user_configs: Dict[str, MFAConfig] = {}
        self.pending_verifications: Dict[str, Dict] = {}
        self.verification_attempts: Dict[str, int] = {}
        self.max_attempts = 3
        self.verification_timeout = 300  # 5 minutes
        
        # Email configuration
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
    
    def setup_totp(self, user_id: str, user_email: str) -> Dict[str, str]:
        """Setup TOTP for user"""
        if user_id not in self.user_configs:
            self.user_configs[user_id] = MFAConfig(user_id=user_id, email=user_email)
        
        config = self.user_configs[user_id]
        
        # Generate TOTP secret
        secret = pyotp.random_base32()
        config.totp_secret = secret
        config.enabled_methods.add(MFAMethod.TOTP)
        config.updated_at = datetime.now()
        
        # Generate QR code
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name="Algorithmic Trading System"
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        qr_img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        logger.info(f"TOTP setup completed for user {user_id}")
        
        return {
            "secret": secret,
            "qr_code": qr_code_base64,
            "manual_entry_key": secret
        }
    
    def generate_backup_codes(self, user_id: str) -> List[str]:
        """Generate backup codes for user"""
        if user_id not in self.user_configs:
            raise ValueError("User MFA not configured")
        
        config = self.user_configs[user_id]
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
        config.backup_codes = backup_codes
        config.enabled_methods.add(MFAMethod.BACKUP_CODES)
        config.updated_at = datetime.now()
        
        logger.info(f"Generated backup codes for user {user_id}")
        return backup_codes
    
    def verify_totp(self, user_id: str, token: str) -> bool:
        """Verify TOTP token"""
        config = self.user_configs.get(user_id)
        if not config or not config.totp_secret:
            return False
        
        totp = pyotp.TOTP(config.totp_secret)
        is_valid = totp.verify(token, valid_window=1)
        
        if is_valid:
            config.last_used_method = MFAMethod.TOTP
            config.updated_at = datetime.now()
            logger.info(f"TOTP verification successful for user {user_id}")
        else:
            logger.warning(f"TOTP verification failed for user {user_id}")
        
        return is_valid
    
    def verify_backup_code(self, user_id: str, code: str) -> bool:
        """Verify backup code"""
        config = self.user_configs.get(user_id)
        if not config or code not in config.backup_codes:
            return False
        
        # Remove used backup code
        config.backup_codes.remove(code)
        config.last_used_method = MFAMethod.BACKUP_CODES
        config.updated_at = datetime.now()
        
        logger.info(f"Backup code verification successful for user {user_id}")
        return True
    
    async def send_email_verification(self, user_id: str) -> str:
        """Send email verification code"""
        config = self.user_configs.get(user_id)
        if not config or not config.email:
            raise ValueError("User email not configured")
        
        # Generate verification code
        verification_code = secrets.randbelow(900000) + 100000  # 6-digit code
        
        # Store pending verification
        self.pending_verifications[user_id] = {
            "code": str(verification_code),
            "method": MFAMethod.EMAIL,
            "expires_at": datetime.now() + timedelta(seconds=self.verification_timeout)
        }
        
        # Send email
        try:
            await self._send_email(
                config.email,
                "Trading System - Verification Code",
                f"Your verification code is: {verification_code}\n\nThis code expires in 5 minutes."
            )
            logger.info(f"Email verification sent to user {user_id}")
            return str(verification_code)
        except Exception as e:
            logger.error(f"Failed to send email verification: {e}")
            raise
    
    async def _send_email(self, to_email: str, subject: str, body: str):
        """Send email using SMTP"""
        if not self.smtp_username or not self.smtp_password:
            logger.warning("SMTP credentials not configured")
            return
        
        msg = MIMEMultipart()
        msg['From'] = self.smtp_username
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(self.smtp_server, self.smtp_port)
        server.starttls()
        server.login(self.smtp_username, self.smtp_password)
        server.send_message(msg)
        server.quit()
    
    def verify_email_code(self, user_id: str, code: str) -> bool:
        """Verify email verification code"""
        pending = self.pending_verifications.get(user_id)
        if not pending or pending["method"] != MFAMethod.EMAIL:
            return False
        
        if datetime.now() > pending["expires_at"]:
            del self.pending_verifications[user_id]
            return False
        
        if pending["code"] == code:
            del self.pending_verifications[user_id]
            config = self.user_configs[user_id]
            config.last_used_method = MFAMethod.EMAIL
            config.updated_at = datetime.now()
            logger.info(f"Email verification successful for user {user_id}")
            return True
        
        return False
    
    def is_mfa_enabled(self, user_id: str) -> bool:
        """Check if MFA is enabled for user"""
        config = self.user_configs.get(user_id)
        return config is not None and len(config.enabled_methods) > 0
    
    def get_enabled_methods(self, user_id: str) -> List[MFAMethod]:
        """Get enabled MFA methods for user"""
        config = self.user_configs.get(user_id)
        return list(config.enabled_methods) if config else []
    
    def disable_mfa(self, user_id: str) -> bool:
        """Disable MFA for user"""
        if user_id in self.user_configs:
            del self.user_configs[user_id]
            logger.info(f"MFA disabled for user {user_id}")
            return True
        return False

# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Initialize services
        rbac = RBACService()
        mfa = MFAService()
        
        # Test RBAC
        user_id = "test_user_123"
        
        # Assign roles
        rbac.assign_role(user_id, "trader")
        rbac.assign_role(user_id, "analyst")
        
        # Test authorization
        request = AccessRequest(
            user_id=user_id,
            resource=ResourceType.TRADE,
            action=Action.EXECUTE
        )
        
        decision = rbac.authorize(request)
        print(f"Trade execution authorized: {decision.granted} - {decision.reason}")
        
        # Test MFA setup
        totp_setup = mfa.setup_totp(user_id, "test@example.com")
        print(f"TOTP secret: {totp_setup['secret']}")
        
        # Generate backup codes
        backup_codes = mfa.generate_backup_codes(user_id)
        print(f"Backup codes: {backup_codes[:3]}...")  # Show first 3
        
        # Test TOTP verification (would need actual TOTP app)
        # is_valid = mfa.verify_totp(user_id, "123456")
        # print(f"TOTP verification: {is_valid}")
        
        logger.info("RBAC and MFA services initialized successfully")
    
    asyncio.run(main())