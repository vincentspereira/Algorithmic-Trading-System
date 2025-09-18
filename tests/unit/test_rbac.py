"""Unit tests for RBAC (Role-Based Access Control) system."""

import pytest
from datetime import datetime
from unittest.mock import patch

from shared.auth.rbac import Permission, Role, RBACManager
from shared.auth.exceptions import AuthorizationError


class TestPermission:
    """Test Permission enum"""
    
    def test_permission_values(self):
        """Test permission enum values"""
        assert Permission.CREATE_ORDERS.value == "orders:create"
        assert Permission.TRADING_LIVE.value == "trading:live"
        assert Permission.SYSTEM_CONFIG.value == "system:config"
        assert Permission.API_ADMIN.value == "api:admin"
    
    def test_all_permissions_exist(self):
        """Test that all expected permissions exist"""
        expected_permissions = [
            "orders:create", "orders:read", "orders:update", "orders:delete",
            "trading:view", "trading:execute", "trading:live", "trading:paper",
            "portfolio:view", "portfolio:manage", "strategy:create",
            "risk:view", "risk:manage", "user:create", "system:config"
        ]
        
        permission_values = [p.value for p in Permission]
        for expected in expected_permissions:
            assert expected in permission_values


class TestRole:
    """Test Role class"""
    
    @pytest.fixture
    def sample_role(self):
        """Create a sample role for testing"""
        return Role(
            name="test_role",
            description="Test role for unit tests",
            permissions={Permission.CREATE_ORDERS, Permission.READ_ORDERS}
        )
    
    def test_role_initialization(self, sample_role):
        """Test role initialization"""
        assert sample_role.name == "test_role"
        assert sample_role.description == "Test role for unit tests"
        assert Permission.CREATE_ORDERS in sample_role.permissions
        assert Permission.READ_ORDERS in sample_role.permissions
        assert sample_role.is_active is True
        assert isinstance(sample_role.created_at, datetime)
        assert isinstance(sample_role.updated_at, datetime)
    
    def test_role_with_parent_roles(self):
        """Test role with parent roles"""
        role = Role(
            name="child_role",
            description="Child role",
            parent_roles={"parent_role1", "parent_role2"}
        )
        
        assert "parent_role1" in role.parent_roles
        assert "parent_role2" in role.parent_roles
    
    def test_add_permission(self, sample_role):
        """Test adding permission to role"""
        initial_updated_at = sample_role.updated_at
        
        with patch('shared.auth.rbac.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 2)
            sample_role.add_permission(Permission.UPDATE_ORDERS)
        
        assert Permission.UPDATE_ORDERS in sample_role.permissions
        assert sample_role.updated_at == datetime(2024, 1, 2)
    
    def test_remove_permission(self, sample_role):
        """Test removing permission from role"""
        with patch('shared.auth.rbac.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 3)
            sample_role.remove_permission(Permission.CREATE_ORDERS)
        
        assert Permission.CREATE_ORDERS not in sample_role.permissions
        assert Permission.READ_ORDERS in sample_role.permissions  # Should still exist
        assert sample_role.updated_at == datetime(2024, 1, 3)
    
    def test_remove_nonexistent_permission(self, sample_role):
        """Test removing permission that doesn't exist"""
        initial_permissions = sample_role.permissions.copy()
        sample_role.remove_permission(Permission.SYSTEM_CONFIG)
        
        assert sample_role.permissions == initial_permissions
    
    def test_has_permission(self, sample_role):
        """Test checking if role has permission"""
        assert sample_role.has_permission(Permission.CREATE_ORDERS) is True
        assert sample_role.has_permission(Permission.READ_ORDERS) is True
        assert sample_role.has_permission(Permission.SYSTEM_CONFIG) is False


class TestRBACManager:
    """Test RBACManager class"""
    
    @pytest.fixture
    def rbac_manager(self):
        """Create RBAC manager for testing"""
        return RBACManager()
    
    def test_initialization_creates_default_roles(self, rbac_manager):
        """Test that initialization creates default roles"""
        expected_roles = [
            "super_admin", "system_admin", "portfolio_manager",
            "trader", "analyst", "risk_manager", "viewer", "paper_trader"
        ]
        
        for role_name in expected_roles:
            assert role_name in rbac_manager.roles
            assert isinstance(rbac_manager.roles[role_name], Role)
    
    def test_super_admin_has_all_permissions(self, rbac_manager):
        """Test that super_admin role has all permissions"""
        super_admin = rbac_manager.get_role("super_admin")
        assert super_admin is not None
        assert len(super_admin.permissions) == len(Permission)
        
        for permission in Permission:
            assert permission in super_admin.permissions
    
    def test_create_role_success(self, rbac_manager):
        """Test successful role creation"""
        permissions = {Permission.CREATE_ORDERS, Permission.READ_ORDERS}
        parent_roles = {"trader"}
        
        role = rbac_manager.create_role(
            name="custom_role",
            description="Custom test role",
            permissions=permissions,
            parent_roles=parent_roles
        )
        
        assert role.name == "custom_role"
        assert role.description == "Custom test role"
        assert role.permissions == permissions
        assert role.parent_roles == parent_roles
        assert "custom_role" in rbac_manager.roles
    
    def test_create_role_duplicate_name(self, rbac_manager):
        """Test creating role with duplicate name"""
        with pytest.raises(AuthorizationError, match="Role 'trader' already exists"):
            rbac_manager.create_role("trader", "Duplicate trader role")
    
    def test_create_role_minimal_params(self, rbac_manager):
        """Test creating role with minimal parameters"""
        role = rbac_manager.create_role("minimal_role", "Minimal role")
        
        assert role.name == "minimal_role"
        assert role.description == "Minimal role"
        assert len(role.permissions) == 0
        assert len(role.parent_roles) == 0
    
    def test_get_role_existing(self, rbac_manager):
        """Test getting existing role"""
        role = rbac_manager.get_role("trader")
        assert role is not None
        assert role.name == "trader"
    
    def test_get_role_nonexistent(self, rbac_manager):
        """Test getting non-existent role"""
        role = rbac_manager.get_role("nonexistent_role")
        assert role is None
    
    def test_delete_role_success(self, rbac_manager):
        """Test successful role deletion"""
        # Create a custom role first
        rbac_manager.create_role("deletable_role", "Role to delete")
        assert "deletable_role" in rbac_manager.roles
        
        # Assign role to a user
        rbac_manager.assign_role_to_user("user1", "deletable_role")
        assert "deletable_role" in rbac_manager.get_user_roles("user1")
        
        # Delete the role
        rbac_manager.delete_role("deletable_role")
        
        assert "deletable_role" not in rbac_manager.roles
        assert "deletable_role" not in rbac_manager.get_user_roles("user1")
    
    def test_delete_role_nonexistent(self, rbac_manager):
        """Test deleting non-existent role"""
        with pytest.raises(AuthorizationError, match="Role 'nonexistent' does not exist"):
            rbac_manager.delete_role("nonexistent")
    
    def test_delete_default_role(self, rbac_manager):
        """Test deleting default role (should fail)"""
        with pytest.raises(AuthorizationError, match="Cannot delete default role 'trader'"):
            rbac_manager.delete_role("trader")
    
    def test_assign_role_to_user(self, rbac_manager):
        """Test assigning role to user"""
        rbac_manager.assign_role_to_user("user1", "trader")
        
        user_roles = rbac_manager.get_user_roles("user1")
        assert "trader" in user_roles
    
    def test_assign_nonexistent_role_to_user(self, rbac_manager):
        """Test assigning non-existent role to user"""
        with pytest.raises(AuthorizationError, match="Role 'nonexistent' does not exist"):
            rbac_manager.assign_role_to_user("user1", "nonexistent")
    
    def test_assign_multiple_roles_to_user(self, rbac_manager):
        """Test assigning multiple roles to user"""
        rbac_manager.assign_role_to_user("user1", "trader")
        rbac_manager.assign_role_to_user("user1", "analyst")
        
        user_roles = rbac_manager.get_user_roles("user1")
        assert "trader" in user_roles
        assert "analyst" in user_roles
        assert len(user_roles) == 2
    
    def test_remove_role_from_user(self, rbac_manager):
        """Test removing role from user"""
        rbac_manager.assign_role_to_user("user1", "trader")
        rbac_manager.assign_role_to_user("user1", "analyst")
        
        rbac_manager.remove_role_from_user("user1", "trader")
        
        user_roles = rbac_manager.get_user_roles("user1")
        assert "trader" not in user_roles
        assert "analyst" in user_roles
    
    def test_remove_role_from_nonexistent_user(self, rbac_manager):
        """Test removing role from user that doesn't exist"""
        # Should not raise an error
        rbac_manager.remove_role_from_user("nonexistent_user", "trader")
    
    def test_get_user_roles_existing_user(self, rbac_manager):
        """Test getting roles for existing user"""
        rbac_manager.assign_role_to_user("user1", "trader")
        rbac_manager.assign_role_to_user("user1", "analyst")
        
        roles = rbac_manager.get_user_roles("user1")
        assert isinstance(roles, set)
        assert "trader" in roles
        assert "analyst" in roles
    
    def test_get_user_roles_nonexistent_user(self, rbac_manager):
        """Test getting roles for non-existent user"""
        roles = rbac_manager.get_user_roles("nonexistent_user")
        assert isinstance(roles, set)
        assert len(roles) == 0
    
    def test_get_user_permissions(self, rbac_manager):
        """Test getting user permissions"""
        rbac_manager.assign_role_to_user("user1", "trader")
        
        permissions = rbac_manager.get_user_permissions("user1")
        trader_role = rbac_manager.get_role("trader")
        
        assert isinstance(permissions, set)
        assert len(permissions) > 0
        # Check that trader permissions are included
        for perm in trader_role.permissions:
            assert perm in permissions
    
    def test_get_user_permissions_with_inheritance(self, rbac_manager):
        """Test getting user permissions with role inheritance"""
        # Create a role with parent
        rbac_manager.create_role(
            "child_role",
            "Child role",
            permissions={Permission.CREATE_ORDERS},
            parent_roles={"trader"}
        )
        
        rbac_manager.assign_role_to_user("user1", "child_role")
        
        permissions = rbac_manager.get_user_permissions("user1")
        trader_role = rbac_manager.get_role("trader")
        
        # Should have both child and parent permissions
        assert Permission.CREATE_ORDERS in permissions
        for perm in trader_role.permissions:
            assert perm in permissions
    
    def test_get_user_permissions_inactive_role(self, rbac_manager):
        """Test getting permissions when role is inactive"""
        rbac_manager.assign_role_to_user("user1", "trader")
        
        # Deactivate the role
        trader_role = rbac_manager.get_role("trader")
        trader_role.is_active = False
        
        permissions = rbac_manager.get_user_permissions("user1")
        assert len(permissions) == 0
    
    def test_user_has_permission(self, rbac_manager):
        """Test checking if user has permission"""
        rbac_manager.assign_role_to_user("user1", "trader")
        
        assert rbac_manager.user_has_permission("user1", Permission.CREATE_ORDERS) is True
        assert rbac_manager.user_has_permission("user1", Permission.SYSTEM_CONFIG) is False
    
    def test_user_has_permission_no_roles(self, rbac_manager):
        """Test checking permission for user with no roles"""
        assert rbac_manager.user_has_permission("user1", Permission.CREATE_ORDERS) is False
    
    def test_assign_user_role_alias(self, rbac_manager):
        """Test assign_user_role alias method"""
        rbac_manager.assign_user_role("user1", "trader")
        
        user_roles = rbac_manager.get_user_roles("user1")
        assert "trader" in user_roles
    
    def test_check_user_permission_alias(self, rbac_manager):
        """Test check_user_permission alias method"""
        rbac_manager.assign_role_to_user("user1", "trader")
        
        assert rbac_manager.check_user_permission("user1", Permission.CREATE_ORDERS) is True
        assert rbac_manager.check_user_permission("user1", Permission.SYSTEM_CONFIG) is False
    
    def test_get_role_permissions(self, rbac_manager):
        """Test getting permissions for a specific role"""
        permissions = rbac_manager.get_role_permissions("trader")
        trader_role = rbac_manager.get_role("trader")
        
        assert isinstance(permissions, set)
        assert permissions == trader_role.permissions
    
    def test_get_role_permissions_with_inheritance(self, rbac_manager):
        """Test getting role permissions with inheritance"""
        # Create role with parent
        rbac_manager.create_role(
            "child_role",
            "Child role",
            permissions={Permission.CREATE_ORDERS},
            parent_roles={"trader"}
        )
        
        permissions = rbac_manager.get_role_permissions("child_role")
        trader_permissions = rbac_manager.get_role("trader").permissions
        
        # Should include both child and parent permissions
        assert Permission.CREATE_ORDERS in permissions
        for perm in trader_permissions:
            assert perm in permissions
    
    def test_get_role_permissions_nonexistent(self, rbac_manager):
        """Test getting permissions for non-existent role"""
        permissions = rbac_manager.get_role_permissions("nonexistent")
        assert isinstance(permissions, set)
        assert len(permissions) == 0
    
    def test_get_role_permissions_inactive(self, rbac_manager):
        """Test getting permissions for inactive role"""
        trader_role = rbac_manager.get_role("trader")
        trader_role.is_active = False
        
        permissions = rbac_manager.get_role_permissions("trader")
        assert len(permissions) == 0
    
    def test_check_user_role(self, rbac_manager):
        """Test checking if user has specific role"""
        rbac_manager.assign_role_to_user("user1", "trader")
        
        assert rbac_manager.check_user_role("user1", "trader") is True
        assert rbac_manager.check_user_role("user1", "analyst") is False
    
    def test_check_user_role_nonexistent_user(self, rbac_manager):
        """Test checking role for non-existent user"""
        assert rbac_manager.check_user_role("nonexistent", "trader") is False
    
    def test_remove_user_role(self, rbac_manager):
        """Test removing user role"""
        rbac_manager.assign_role_to_user("user1", "trader")
        rbac_manager.assign_role_to_user("user1", "analyst")
        
        result = rbac_manager.remove_user_role("user1", "trader")
        assert result is True
        
        user_roles = rbac_manager.get_user_roles("user1")
        assert "trader" not in user_roles
        assert "analyst" in user_roles
    
    def test_remove_user_role_not_assigned(self, rbac_manager):
        """Test removing role that user doesn't have"""
        rbac_manager.assign_role_to_user("user1", "analyst")
        
        result = rbac_manager.remove_user_role("user1", "trader")
        assert result is False
    
    def test_remove_user_role_nonexistent_user(self, rbac_manager):
        """Test removing role from non-existent user"""
        result = rbac_manager.remove_user_role("nonexistent", "trader")
        assert result is False
    
    def test_user_has_any_permission(self, rbac_manager):
        """Test checking if user has any of specified permissions"""
        rbac_manager.assign_role_to_user("user1", "trader")
        
        permissions = [Permission.CREATE_ORDERS, Permission.SYSTEM_CONFIG]
        assert rbac_manager.user_has_any_permission("user1", permissions) is True
        
        permissions = [Permission.SYSTEM_CONFIG, Permission.API_ADMIN]
        assert rbac_manager.user_has_any_permission("user1", permissions) is False
    
    def test_user_has_all_permissions(self, rbac_manager):
        """Test checking if user has all specified permissions"""
        rbac_manager.assign_role_to_user("user1", "trader")
        
        trader_permissions = list(rbac_manager.get_role("trader").permissions)[:2]
        assert rbac_manager.user_has_all_permissions("user1", trader_permissions) is True
        
        mixed_permissions = [Permission.CREATE_ORDERS, Permission.SYSTEM_CONFIG]
        assert rbac_manager.user_has_all_permissions("user1", mixed_permissions) is False
    
    def test_require_permission_success(self, rbac_manager):
        """Test requiring permission when user has it"""
        rbac_manager.assign_role_to_user("user1", "trader")
        
        # Should not raise an exception
        rbac_manager.require_permission("user1", Permission.CREATE_ORDERS)
    
    def test_require_permission_failure(self, rbac_manager):
        """Test requiring permission when user doesn't have it"""
        rbac_manager.assign_role_to_user("user1", "trader")
        
        with pytest.raises(AuthorizationError, match="does not have permission 'system:config'"):
            rbac_manager.require_permission("user1", Permission.SYSTEM_CONFIG)
    
    def test_require_any_permission_success(self, rbac_manager):
        """Test requiring any permission when user has one"""
        rbac_manager.assign_role_to_user("user1", "trader")
        
        permissions = [Permission.CREATE_ORDERS, Permission.SYSTEM_CONFIG]
        # Should not raise an exception
        rbac_manager.require_any_permission("user1", permissions)
    
    def test_require_any_permission_failure(self, rbac_manager):
        """Test requiring any permission when user has none"""
        rbac_manager.assign_role_to_user("user1", "trader")
        
        permissions = [Permission.SYSTEM_CONFIG, Permission.API_ADMIN]
        with pytest.raises(AuthorizationError, match="does not have any of the required permissions"):
            rbac_manager.require_any_permission("user1", permissions)
    
    def test_require_all_permissions_success(self, rbac_manager):
        """Test requiring all permissions when user has them"""
        rbac_manager.assign_role_to_user("user1", "trader")
        
        trader_permissions = list(rbac_manager.get_role("trader").permissions)[:2]
        # Should not raise an exception
        rbac_manager.require_all_permissions("user1", trader_permissions)
    
    def test_require_all_permissions_failure(self, rbac_manager):
        """Test requiring all permissions when user is missing some"""
        rbac_manager.assign_role_to_user("user1", "trader")
        
        permissions = [Permission.CREATE_ORDERS, Permission.SYSTEM_CONFIG]
        with pytest.raises(AuthorizationError, match="is missing required permissions"):
            rbac_manager.require_all_permissions("user1", permissions)
    
    def test_list_roles(self, rbac_manager):
        """Test listing all roles"""
        roles = rbac_manager.list_roles()
        
        assert isinstance(roles, list)
        assert len(roles) >= 8  # At least the default roles
        
        role_names = [role.name for role in roles]
        assert "trader" in role_names
        assert "analyst" in role_names
        assert "super_admin" in role_names
    
    def test_get_role_hierarchy(self, rbac_manager):
        """Test getting role hierarchy"""
        # Create role with parents
        rbac_manager.create_role(
            "child_role",
            "Child role",
            parent_roles={"trader", "analyst"}
        )
        
        hierarchy = rbac_manager.get_role_hierarchy()
        
        assert isinstance(hierarchy, dict)
        assert "child_role" in hierarchy
        assert "trader" in hierarchy["child_role"]
        assert "analyst" in hierarchy["child_role"]
        
        # Default roles should have empty parent lists
        assert hierarchy["trader"] == []
        assert hierarchy["analyst"] == []