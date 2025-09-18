"""Role-Based Access Control (RBAC) System

Provides comprehensive role and permission management for the algorithmic
trading system with hierarchical roles and fine-grained permissions.
"""

from enum import Enum
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .exceptions import AuthorizationError


class Permission(Enum):
    """System permissions for fine-grained access control"""
    
    # Order Management Permissions (for test compatibility)
    CREATE_ORDERS = "orders:create"
    READ_ORDERS = "orders:read"
    UPDATE_ORDERS = "orders:update"
    DELETE_ORDERS = "orders:delete"
    MANAGE_USERS = "users:manage"
    VIEW_METRICS = "metrics:view"
    
    # Trading Permissions
    TRADING_VIEW = "trading:view"
    TRADING_EXECUTE = "trading:execute"
    TRADING_PAPER = "trading:paper"
    TRADING_LIVE = "trading:live"
    TRADING_CANCEL = "trading:cancel"
    TRADING_MODIFY = "trading:modify"
    
    # Portfolio Permissions
    PORTFOLIO_VIEW = "portfolio:view"
    PORTFOLIO_MANAGE = "portfolio:manage"
    PORTFOLIO_CREATE = "portfolio:create"
    PORTFOLIO_DELETE = "portfolio:delete"
    PORTFOLIO_REBALANCE = "portfolio:rebalance"
    
    # Market Data Permissions
    MARKET_DATA_VIEW = "market_data:view"
    MARKET_DATA_REAL_TIME = "market_data:real_time"
    MARKET_DATA_HISTORICAL = "market_data:historical"
    MARKET_DATA_PREMIUM = "market_data:premium"
    
    # Strategy Permissions
    STRATEGY_VIEW = "strategy:view"
    STRATEGY_CREATE = "strategy:create"
    STRATEGY_EDIT = "strategy:edit"
    STRATEGY_DELETE = "strategy:delete"
    STRATEGY_BACKTEST = "strategy:backtest"
    STRATEGY_DEPLOY = "strategy:deploy"
    
    # Risk Management Permissions
    RISK_VIEW = "risk:view"
    RISK_MANAGE = "risk:manage"
    RISK_LIMITS_SET = "risk:limits:set"
    RISK_OVERRIDE = "risk:override"
    
    # User Management Permissions
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_EDIT = "user:edit"
    USER_DELETE = "user:delete"
    USER_ROLES_MANAGE = "user:roles:manage"
    
    # System Administration Permissions
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_LOGS = "system:logs"
    SYSTEM_BACKUP = "system:backup"
    SYSTEM_MAINTENANCE = "system:maintenance"
    
    # API Permissions
    API_READ = "api:read"
    API_WRITE = "api:write"
    API_ADMIN = "api:admin"
    
    # Reporting Permissions
    REPORTS_VIEW = "reports:view"
    REPORTS_CREATE = "reports:create"
    REPORTS_EXPORT = "reports:export"
    REPORTS_SCHEDULE = "reports:schedule"


@dataclass
class Role:
    """Role definition with permissions and metadata"""
    name: str
    description: str
    permissions: Set[Permission] = field(default_factory=set)
    parent_roles: Set[str] = field(default_factory=set)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_permission(self, permission: Permission) -> None:
        """Add a permission to this role"""
        self.permissions.add(permission)
        self.updated_at = datetime.utcnow()
    
    def remove_permission(self, permission: Permission) -> None:
        """Remove a permission from this role"""
        self.permissions.discard(permission)
        self.updated_at = datetime.utcnow()
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if role has a specific permission"""
        return permission in self.permissions


class RBACManager:
    """Role-Based Access Control Manager"""
    
    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.user_roles: Dict[str, Set[str]] = {}  # user_id -> set of role names
        self._initialize_default_roles()
    
    def _initialize_default_roles(self) -> None:
        """Initialize default system roles"""
        
        # Super Admin - Full system access
        super_admin = Role(
            name="super_admin",
            description="Super Administrator with full system access",
            permissions=set(Permission)  # All permissions
        )
        
        # System Admin - System management without user management
        system_admin = Role(
            name="system_admin",
            description="System Administrator for infrastructure management",
            permissions={
                Permission.SYSTEM_CONFIG,
                Permission.SYSTEM_MONITOR,
                Permission.SYSTEM_LOGS,
                Permission.SYSTEM_BACKUP,
                Permission.SYSTEM_MAINTENANCE,
                Permission.API_ADMIN,
                Permission.REPORTS_VIEW,
                Permission.REPORTS_CREATE,
                Permission.REPORTS_EXPORT
            }
        )
        
        # Portfolio Manager - Full trading and portfolio management
        portfolio_manager = Role(
            name="portfolio_manager",
            description="Portfolio Manager with full trading capabilities",
            permissions={
                Permission.TRADING_VIEW,
                Permission.TRADING_EXECUTE,
                Permission.TRADING_PAPER,
                Permission.TRADING_LIVE,
                Permission.TRADING_CANCEL,
                Permission.TRADING_MODIFY,
                Permission.PORTFOLIO_VIEW,
                Permission.PORTFOLIO_MANAGE,
                Permission.PORTFOLIO_CREATE,
                Permission.PORTFOLIO_DELETE,
                Permission.PORTFOLIO_REBALANCE,
                Permission.MARKET_DATA_VIEW,
                Permission.MARKET_DATA_REAL_TIME,
                Permission.MARKET_DATA_HISTORICAL,
                Permission.MARKET_DATA_PREMIUM,
                Permission.STRATEGY_VIEW,
                Permission.STRATEGY_CREATE,
                Permission.STRATEGY_EDIT,
                Permission.STRATEGY_DELETE,
                Permission.STRATEGY_BACKTEST,
                Permission.STRATEGY_DEPLOY,
                Permission.RISK_VIEW,
                Permission.RISK_MANAGE,
                Permission.API_READ,
                Permission.API_WRITE,
                Permission.REPORTS_VIEW,
                Permission.REPORTS_CREATE,
                Permission.REPORTS_EXPORT
            }
        )
        
        # Trader - Trading execution with limited portfolio access
        trader = Role(
            name="trader",
            description="Trader with execution capabilities",
            permissions={
                Permission.CREATE_ORDERS,
                Permission.READ_ORDERS,
                Permission.UPDATE_ORDERS,
                Permission.TRADING_VIEW,
                Permission.TRADING_EXECUTE,
                Permission.TRADING_PAPER,
                Permission.TRADING_CANCEL,
                Permission.TRADING_MODIFY,
                Permission.PORTFOLIO_VIEW,
                Permission.MARKET_DATA_VIEW,
                Permission.MARKET_DATA_REAL_TIME,
                Permission.MARKET_DATA_HISTORICAL,
                Permission.STRATEGY_VIEW,
                Permission.STRATEGY_BACKTEST,
                Permission.RISK_VIEW,
                Permission.API_READ,
                Permission.REPORTS_VIEW
            }
        )
        
        # Analyst - Research and analysis capabilities
        analyst = Role(
            name="analyst",
            description="Research Analyst with strategy development capabilities",
            permissions={
                Permission.TRADING_VIEW,
                Permission.TRADING_PAPER,
                Permission.PORTFOLIO_VIEW,
                Permission.MARKET_DATA_VIEW,
                Permission.MARKET_DATA_REAL_TIME,
                Permission.MARKET_DATA_HISTORICAL,
                Permission.STRATEGY_VIEW,
                Permission.STRATEGY_CREATE,
                Permission.STRATEGY_EDIT,
                Permission.STRATEGY_BACKTEST,
                Permission.RISK_VIEW,
                Permission.API_READ,
                Permission.REPORTS_VIEW,
                Permission.REPORTS_CREATE
            }
        )
        
        # Risk Manager - Risk monitoring and management
        risk_manager = Role(
            name="risk_manager",
            description="Risk Manager with risk oversight capabilities",
            permissions={
                Permission.TRADING_VIEW,
                Permission.PORTFOLIO_VIEW,
                Permission.MARKET_DATA_VIEW,
                Permission.MARKET_DATA_REAL_TIME,
                Permission.STRATEGY_VIEW,
                Permission.RISK_VIEW,
                Permission.RISK_MANAGE,
                Permission.RISK_LIMITS_SET,
                Permission.RISK_OVERRIDE,
                Permission.API_READ,
                Permission.REPORTS_VIEW,
                Permission.REPORTS_CREATE,
                Permission.REPORTS_EXPORT
            }
        )
        
        # Viewer - Read-only access
        viewer = Role(
            name="viewer",
            description="Read-only access to system data",
            permissions={
                Permission.READ_ORDERS,
                Permission.TRADING_VIEW,
                Permission.PORTFOLIO_VIEW,
                Permission.MARKET_DATA_VIEW,
                Permission.STRATEGY_VIEW,
                Permission.RISK_VIEW,
                Permission.API_READ,
                Permission.REPORTS_VIEW
            }
        )
        
        # Paper Trader - Limited to paper trading only
        paper_trader = Role(
            name="paper_trader",
            description="Paper Trading access only",
            permissions={
                Permission.TRADING_VIEW,
                Permission.TRADING_PAPER,
                Permission.TRADING_CANCEL,
                Permission.PORTFOLIO_VIEW,
                Permission.MARKET_DATA_VIEW,
                Permission.STRATEGY_VIEW,
                Permission.STRATEGY_BACKTEST,
                Permission.RISK_VIEW,
                Permission.API_READ
            }
        )
        
        # Register all default roles
        for role in [super_admin, system_admin, portfolio_manager, trader, 
                    analyst, risk_manager, viewer, paper_trader]:
            self.roles[role.name] = role
    
    def create_role(
        self, 
        name: str, 
        description: str, 
        permissions: Optional[Set[Permission]] = None,
        parent_roles: Optional[Set[str]] = None
    ) -> Role:
        """Create a new role
        
        Args:
            name: Role name (must be unique)
            description: Role description
            permissions: Set of permissions for the role
            parent_roles: Set of parent role names for inheritance
            
        Returns:
            Created role object
            
        Raises:
            AuthorizationError: If role already exists
        """
        if name in self.roles:
            raise AuthorizationError(f"Role '{name}' already exists")
        
        role = Role(
            name=name,
            description=description,
            permissions=permissions or set(),
            parent_roles=parent_roles or set()
        )
        
        self.roles[name] = role
        return role
    
    def get_role(self, name: str) -> Optional[Role]:
        """Get a role by name"""
        return self.roles.get(name)
    
    def delete_role(self, name: str) -> None:
        """Delete a role
        
        Args:
            name: Role name to delete
            
        Raises:
            AuthorizationError: If role doesn't exist or is a default role
        """
        if name not in self.roles:
            raise AuthorizationError(f"Role '{name}' does not exist")
        
        # Prevent deletion of default roles
        default_roles = {
            "super_admin", "system_admin", "portfolio_manager", 
            "trader", "analyst", "risk_manager", "viewer", "paper_trader"
        }
        if name in default_roles:
            raise AuthorizationError(f"Cannot delete default role '{name}'")
        
        # Remove role from all users
        for user_id in self.user_roles:
            self.user_roles[user_id].discard(name)
        
        del self.roles[name]
    
    def assign_role_to_user(self, user_id: str, role_name: str) -> None:
        """Assign a role to a user
        
        Args:
            user_id: User identifier
            role_name: Role name to assign
            
        Raises:
            AuthorizationError: If role doesn't exist
        """
        if role_name not in self.roles:
            raise AuthorizationError(f"Role '{role_name}' does not exist")
        
        if user_id not in self.user_roles:
            self.user_roles[user_id] = set()
        
        self.user_roles[user_id].add(role_name)
    
    def remove_role_from_user(self, user_id: str, role_name: str) -> None:
        """Remove a role from a user"""
        if user_id in self.user_roles:
            self.user_roles[user_id].discard(role_name)
    
    def get_user_roles(self, user_id: str) -> Set[str]:
        """Get all roles assigned to a user"""
        return self.user_roles.get(user_id, set())
    
    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for a user (including inherited)
        
        Args:
            user_id: User identifier
            
        Returns:
            Set of all permissions the user has
        """
        permissions = set()
        user_roles = self.get_user_roles(user_id)
        
        for role_name in user_roles:
            role = self.roles.get(role_name)
            if role and role.is_active:
                permissions.update(role.permissions)
                
                # Add permissions from parent roles (inheritance)
                for parent_role_name in role.parent_roles:
                    parent_role = self.roles.get(parent_role_name)
                    if parent_role and parent_role.is_active:
                        permissions.update(parent_role.permissions)
        
        return permissions
    
    def user_has_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if a user has a specific permission
        
        Args:
            user_id: User identifier
            permission: Permission to check
            
        Returns:
            True if user has the permission, False otherwise
        """
        user_permissions = self.get_user_permissions(user_id)
        return permission in user_permissions
    
    def assign_user_role(self, user_id: str, role_name: str) -> None:
        """Alias for assign_role_to_user for backward compatibility"""
        self.assign_role_to_user(user_id, role_name)
    
    def check_user_permission(self, user_id: str, permission: Permission) -> bool:
        """Alias for user_has_permission for backward compatibility"""
        return self.user_has_permission(user_id, permission)
    
    def get_role_permissions(self, role_name: str) -> Set[Permission]:
        """Get all permissions for a specific role
        
        Args:
            role_name: Role name to get permissions for
            
        Returns:
            Set of permissions for the role
        """
        role = self.roles.get(role_name)
        if not role or not role.is_active:
            return set()
        
        permissions = role.permissions.copy()
        
        # Add permissions from parent roles (inheritance)
        for parent_role_name in role.parent_roles:
            parent_role = self.roles.get(parent_role_name)
            if parent_role and parent_role.is_active:
                permissions.update(parent_role.permissions)
        
        return permissions
    
    def check_user_role(self, user_id: str, role_name: str) -> bool:
        """Check if a user has a specific role
        
        Args:
            user_id: User identifier
            role_name: Role name to check
            
        Returns:
            True if user has the role, False otherwise
        """
        user_roles = self.user_roles.get(user_id, set())
        return role_name in user_roles
    
    def remove_user_role(self, user_id: str, role_name: str) -> bool:
        """Remove a role from a user
        
        Args:
            user_id: User identifier
            role_name: Role name to remove
            
        Returns:
            True if role was removed, False if user didn't have the role
        """
        if user_id not in self.user_roles:
            return False
        
        if role_name in self.user_roles[user_id]:
            self.user_roles[user_id].remove(role_name)
            return True
        
        return False
    
    def user_has_any_permission(self, user_id: str, permissions: List[Permission]) -> bool:
        """Check if a user has any of the specified permissions
        
        Args:
            user_id: User identifier
            permissions: List of permissions to check
            
        Returns:
            True if user has at least one permission, False otherwise
        """
        user_permissions = self.get_user_permissions(user_id)
        return any(perm in user_permissions for perm in permissions)
    
    def user_has_all_permissions(self, user_id: str, permissions: List[Permission]) -> bool:
        """Check if a user has all specified permissions
        
        Args:
            user_id: User identifier
            permissions: List of permissions to check
            
        Returns:
            True if user has all permissions, False otherwise
        """
        user_permissions = self.get_user_permissions(user_id)
        return all(perm in user_permissions for perm in permissions)
    
    def require_permission(self, user_id: str, permission: Permission) -> None:
        """Require a user to have a specific permission
        
        Args:
            user_id: User identifier
            permission: Required permission
            
        Raises:
            AuthorizationError: If user doesn't have the permission
        """
        if not self.user_has_permission(user_id, permission):
            raise AuthorizationError(
                f"User '{user_id}' does not have permission '{permission.value}'"
            )
    
    def require_any_permission(self, user_id: str, permissions: List[Permission]) -> None:
        """Require a user to have at least one of the specified permissions
        
        Args:
            user_id: User identifier
            permissions: List of permissions (user needs at least one)
            
        Raises:
            AuthorizationError: If user doesn't have any of the permissions
        """
        if not self.user_has_any_permission(user_id, permissions):
            perm_names = [p.value for p in permissions]
            raise AuthorizationError(
                f"User '{user_id}' does not have any of the required permissions: {perm_names}"
            )
    
    def require_all_permissions(self, user_id: str, permissions: List[Permission]) -> None:
        """Require a user to have all specified permissions
        
        Args:
            user_id: User identifier
            permissions: List of permissions (user needs all)
            
        Raises:
            AuthorizationError: If user doesn't have all permissions
        """
        if not self.user_has_all_permissions(user_id, permissions):
            missing_perms = []
            user_permissions = self.get_user_permissions(user_id)
            for perm in permissions:
                if perm not in user_permissions:
                    missing_perms.append(perm.value)
            
            raise AuthorizationError(
                f"User '{user_id}' is missing required permissions: {missing_perms}"
            )
    
    def list_roles(self) -> List[Role]:
        """List all available roles"""
        return list(self.roles.values())
    
    def get_role_hierarchy(self) -> Dict[str, List[str]]:
        """Get role hierarchy mapping
        
        Returns:
            Dictionary mapping role names to their parent roles
        """
        hierarchy = {}
        for role_name, role in self.roles.items():
            hierarchy[role_name] = list(role.parent_roles)
        return hierarchy