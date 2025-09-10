#!/usr/bin/env python3
"""
Tests for Enhanced RBAC Implementation
"""

import unittest
import sys
import os
from datetime import datetime, timedelta

# Add the security directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from authentication_framework import (
    AuthenticationManager, UserRole, Permission, GranularPermission
)


class TestEnhancedRBAC(unittest.TestCase):
    """Test cases for Enhanced RBAC Implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.auth_manager = AuthenticationManager()
        
        # Create test users with different roles
        self.admin_user = self.auth_manager.create_user(
            username="admin_user",
            email="admin@example.com",
            password="SecureAdmin123!",
            roles={UserRole.ADMIN}
        )
        
        self.trader_user = self.auth_manager.create_user(
            username="trader_user",
            email="trader@example.com",
            password="SecureTrader123!",
            roles={UserRole.TRADER}
        )
        
        self.risk_manager_user = self.auth_manager.create_user(
            username="risk_manager",
            email="risk@example.com",
            password="SecureRisk123!",
            roles={UserRole.RISK_MANAGER}
        )
    
    def test_granular_permission_assignment(self):
        """Test granular permission assignment based on roles"""
        # Admin user should have granular permissions
        self.assertTrue(
            self.admin_user.has_granular_permission(GranularPermission.ORDER_VIEW_ALL)
        )
        self.assertTrue(
            self.admin_user.has_granular_permission(GranularPermission.USER_MANAGE_TEAM)
        )
        
        # Trader user should have limited granular permissions
        self.assertTrue(
            self.trader_user.has_granular_permission(GranularPermission.ORDER_CREATE_EQUITY)
        )
        self.assertTrue(
            self.trader_user.has_granular_permission(GranularPermission.ORDER_VIEW_OWN)
        )
        self.assertFalse(
            self.trader_user.has_granular_permission(GranularPermission.USER_MANAGE_ALL)
        )
    
    def test_context_based_permission_checking(self):
        """Test context-based permission checking"""
        # Trader should be able to create equity orders
        self.assertTrue(
            self.trader_user.has_granular_permission(
                GranularPermission.ORDER_CREATE_EQUITY,
                {'asset_class': 'EQUITY'}
            )
        )
        
        # Trader should not be able to create equity orders for other asset classes
        self.assertFalse(
            self.trader_user.has_granular_permission(
                GranularPermission.ORDER_CREATE_EQUITY,
                {'asset_class': 'FUTURES'}
            )
        )
    
    def test_temporary_role_assignment(self):
        """Test temporary role assignment"""
        # Assign temporary admin role to trader
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        result = self.auth_manager.assign_temporary_role(
            self.trader_user.user_id,
            UserRole.ADMIN,
            start_time,
            end_time
        )
        
        self.assertTrue(result)
        
        # Trader should now have admin permissions
        self.assertTrue(
            self.trader_user.has_granular_permission(GranularPermission.USER_MANAGE_TEAM)
        )
    
    def test_conditional_role_assignment(self):
        """Test conditional role assignment"""
        # Assign conditional role
        conditions = {'department': 'trading', 'experience_years': 5}
        
        result = self.auth_manager.assign_conditional_role(
            self.trader_user.user_id,
            UserRole.RISK_MANAGER,
            conditions
        )
        
        self.assertTrue(result)
        
        # Trader should now have risk manager permissions
        self.assertTrue(
            self.trader_user.has_granular_permission(GranularPermission.RISK_VIEW_ALL)
        )
    
    def test_session_based_granular_permission_checking(self):
        """Test session-based granular permission checking"""
        # Authenticate trader user
        session = self.auth_manager.authenticate_user(
            username="trader_user",
            password="SecureTrader123!",
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(session)
        
        # Check granular permission through session
        can_create_equity_order = self.auth_manager.check_granular_permission(
            session.session_id,
            GranularPermission.ORDER_CREATE_EQUITY,
            "equity_order",
            {'asset_class': 'EQUITY'}
        )
        
        self.assertTrue(can_create_equity_order)
        
        # Check forbidden permission
        can_manage_all_users = self.auth_manager.check_granular_permission(
            session.session_id,
            GranularPermission.USER_MANAGE_ALL,
            "user_management"
        )
        
        self.assertFalse(can_manage_all_users)
    
    def test_permission_inheritance(self):
        """Test permission inheritance from roles"""
        # SUPER_ADMIN should have all granular permissions
        super_admin = self.auth_manager.create_user(
            username="super_admin",
            email="superadmin@example.com",
            password="SuperSecure123!",
            roles={UserRole.SUPER_ADMIN}
        )
        
        # Check that super admin has all permissions
        all_permissions = list(GranularPermission)
        for permission in all_permissions[:10]:  # Test first 10 permissions
            self.assertTrue(
                super_admin.has_granular_permission(permission),
                f"Super admin should have permission: {permission.value}"
            )
    
    def test_audit_logging_for_granular_permissions(self):
        """Test audit logging for granular permission checks"""
        # Authenticate trader user
        session = self.auth_manager.authenticate_user(
            username="trader_user",
            password="SecureTrader123!",
            ip_address="192.168.1.100"
        )
        
        # Check a permission
        self.auth_manager.check_granular_permission(
            session.session_id,
            GranularPermission.ORDER_CREATE_EQUITY,
            "test_order",
            {'asset_class': 'EQUITY'}
        )
        
        # Check audit events
        events = self.auth_manager.get_audit_events(
            user_id=self.trader_user.user_id,
            limit=5
        )
        
        # Should have permission check events
        permission_events = [
            e for e in events 
            if e.action == GranularPermission.ORDER_CREATE_EQUITY.value
        ]
        
        self.assertGreater(len(permission_events), 0)
        self.assertEqual(permission_events[0].result, "SUCCESS")


def run_tests():
    """Run all enhanced RBAC tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestEnhancedRBAC))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)