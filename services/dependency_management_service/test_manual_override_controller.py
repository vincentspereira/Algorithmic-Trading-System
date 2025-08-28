#!/usr/bin/env python3
"""
Test suite for Manual Override Controller.
Comprehensive tests for all override functionality.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add the service directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from manual_override_controller import (
    ManualOverrideController,
    OverrideRequest,
    OverrideAction,
    OverridePriority
)

class TestManualOverrideController:
    """Test suite for ManualOverrideController."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        self.deps_path = os.path.join(self.temp_dir, "dependencies.json")
        
        # Create test dependencies file
        test_deps = {
            "tiers": {
                "tier1": {
                    "dependencies": [
                        {"name": "nautilus_trader", "tier": "tier1"},
                        {"name": "kafka", "tier": "tier1"}
                    ]
                },
                "tier2": {
                    "dependencies": [
                        {"name": "ta-lib", "tier": "tier2"},
                        {"name": "vectorbt", "tier": "tier2"}
                    ]
                },
                "tier3": {
                    "dependencies": [
                        {"name": "react", "tier": "tier3"}
                    ]
                },
                "tier4": {
                    "dependencies": [
                        {"name": "prometheus", "tier": "tier4"}
                    ]
                }
            }
        }
        
        with open(self.deps_path, 'w') as f:
            json.dump(test_deps, f)
        
        # Change to temp directory for testing
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        self.controller = ManualOverrideController(self.config_path)
    
    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_controller_initialization(self):
        """Test controller initialization."""
        assert self.controller is not None
        assert self.controller.config is not None
        assert self.controller.active_overrides == {}
        assert Path(self.config_path).exists()
    
    def test_create_valid_override_request(self):
        """Test creating a valid override request."""
        request = OverrideRequest(
            dependency_name="nautilus_trader",
            action=OverrideAction.FORCE_UPDATE,
            priority=OverridePriority.HIGH,
            reason="Critical security patch required",
            requester="admin",
            expiry_hours=12
        )
        
        override_id = self.controller.create_override(request)
        
        assert override_id is not None
        assert override_id.startswith("override_")
        assert "nautilus_trader" in self.controller.active_overrides
        
        override_data = self.controller.active_overrides["nautilus_trader"]
        assert override_data["dependency_name"] == "nautilus_trader"
        assert override_data["action"] == "force_update"
        assert override_data["priority"] == "high"
        assert override_data["status"] == "pending_approval"
    
    def test_create_emergency_override(self):
        """Test creating an emergency override (auto-approved)."""
        request = OverrideRequest(
            dependency_name="kafka",
            action=OverrideAction.ROLLBACK,
            priority=OverridePriority.EMERGENCY,
            reason="Production system failure due to update",
            requester="admin",
            force=True
        )
        
        override_id = self.controller.create_override(request)
        
        override_data = self.controller.active_overrides["kafka"]
        assert override_data["status"] == "approved"
        assert override_data["force"] is True
    
    def test_approve_override(self):
        """Test approving a pending override."""
        # Create a pending override for tier1 with high priority (requires approval)
        request = OverrideRequest(
            dependency_name="nautilus_trader",  # tier1
            action=OverrideAction.DEFER,
            priority=OverridePriority.HIGH,  # High priority on tier1 requires approval
            reason="Update conflicts with current implementation",
            requester="developer"
        )
        
        self.controller.create_override(request)
        
        # Verify it's pending approval
        override_data = self.controller.active_overrides["nautilus_trader"]
        assert override_data["status"] == "pending_approval"
        
        # Approve the override
        result = self.controller.approve_override("nautilus_trader", "lead_dev")
        
        assert result is True
        override_data = self.controller.active_overrides["nautilus_trader"]
        assert override_data["status"] == "approved"
        assert override_data["approver"] == "lead_dev"
        assert "approved_at" in override_data
    
    def test_execute_override(self):
        """Test executing an approved override."""
        # Create and approve an override for tier1 with high priority
        request = OverrideRequest(
            dependency_name="kafka",  # tier1
            action=OverrideAction.PAUSE_MONITORING,
            priority=OverridePriority.HIGH,  # High priority on tier1 requires approval
            reason="Maintenance window scheduled",
            requester="devops"
        )
        
        self.controller.create_override(request)
        
        # Verify it's pending approval
        override_data = self.controller.active_overrides["kafka"]
        assert override_data["status"] == "pending_approval"
        
        # Approve the override
        self.controller.approve_override("kafka", "admin")
        
        # Execute the override
        result = self.controller.execute_override("kafka")
        
        assert result is True
        override_data = self.controller.active_overrides["kafka"]
        assert override_data["status"] == "executed"
        assert "executed_at" in override_data
    
    def test_duplicate_override_rejection(self):
        """Test that duplicate overrides are rejected."""
        request = OverrideRequest(
            dependency_name="react",
            action=OverrideAction.APPROVE,
            priority=OverridePriority.LOW,
            reason="Version update approved",
            requester="developer"
        )
        
        # Create first override
        self.controller.create_override(request)
        
        # Try to create duplicate
        with pytest.raises(ValueError, match="Active override already exists"):
            self.controller.create_override(request)
    
    def test_invalid_dependency_rejection(self):
        """Test that overrides for invalid dependencies are rejected."""
        request = OverrideRequest(
            dependency_name="non_existent_dependency",
            action=OverrideAction.APPROVE,
            priority=OverridePriority.LOW,
            reason="Test invalid dependency",
            requester="developer"
        )
        
        with pytest.raises(ValueError, match="Dependency .* not found"):
            self.controller.create_override(request)
    
    def test_approval_not_required_for_low_priority(self):
        """Test that low priority overrides don't require approval."""
        request = OverrideRequest(
            dependency_name="prometheus",  # tier4
            action=OverrideAction.DEFER,
            priority=OverridePriority.LOW,
            reason="Minor update can be deferred",
            requester="developer"
        )
        
        override_id = self.controller.create_override(request)
        override_data = self.controller.active_overrides["prometheus"]
        
        # Low priority tier4 should NOT require approval (auto-approved)
        assert override_data["status"] == "approved"
    
    def test_override_expiry_cleanup(self):
        """Test cleanup of expired overrides."""
        # Create an override with short expiry
        request = OverrideRequest(
            dependency_name="react",
            action=OverrideAction.DEFER,
            priority=OverridePriority.LOW,
            reason="Short term test",
            requester="developer",
            expiry_hours=0  # Immediate expiry
        )
        
        self.controller.create_override(request)
        
        # Force expiry by setting past timestamp
        override_data = self.controller.active_overrides["react"]
        override_data["expires_at"] = datetime.now().timestamp() - 3600  # 1 hour ago
        self.controller._save_active_overrides()
        
        # Run cleanup
        self.controller.cleanup_expired_overrides()
        
        # Override should be removed from active overrides
        assert "react" not in self.controller.active_overrides
    
    def test_override_history_logging(self):
        """Test that overrides are logged to history."""
        request = OverrideRequest(
            dependency_name="kafka",
            action=OverrideAction.APPROVE,
            priority=OverridePriority.MEDIUM,
            reason="Standard update approval",
            requester="developer"
        )
        
        self.controller.create_override(request)
        history = self.controller.get_override_history()
        
        assert len(history) == 1
        assert history[0]["dependency_name"] == "kafka"
        assert history[0]["action"] == "approve"
        assert "logged_at" in history[0]
    
    def test_get_active_overrides(self):
        """Test retrieving active overrides."""
        # Create multiple overrides
        requests = [
            OverrideRequest(
                dependency_name="nautilus_trader",
                action=OverrideAction.FORCE_UPDATE,
                priority=OverridePriority.HIGH,
                reason="Security patch",
                requester="admin"
            ),
            OverrideRequest(
                dependency_name="ta-lib",
                action=OverrideAction.DEFER,
                priority=OverridePriority.LOW,
                reason="Conflicts with current work",
                requester="developer"
            )
        ]
        
        for request in requests:
            self.controller.create_override(request)
        
        active_overrides = self.controller.get_active_overrides()
        
        assert len(active_overrides) == 2
        dependency_names = [override["dependency_name"] for override in active_overrides]
        assert "nautilus_trader" in dependency_names
        assert "ta-lib" in dependency_names
    
    def test_override_action_execution(self):
        """Test specific override action execution methods."""
        # Test different action types
        actions_to_test = [
            OverrideAction.APPROVE,
            OverrideAction.DEFER,
            OverrideAction.REJECT,
            OverrideAction.FORCE_UPDATE,
            OverrideAction.ROLLBACK,
            OverrideAction.PAUSE_MONITORING,
            OverrideAction.RESUME_MONITORING
        ]
        
        for i, action in enumerate(actions_to_test):
            dependency_name = f"test_dep_{i}"
            
            # Add test dependency to config
            test_dep = {"name": dependency_name, "tier": "tier4"}
            self.controller.config.setdefault("test_dependencies", []).append(test_dep)
            
            # Mock the dependency in our test data
            with open(self.deps_path, 'r') as f:
                deps_data = json.load(f)
            deps_data["tiers"]["tier4"]["dependencies"].append(test_dep)
            with open(self.deps_path, 'w') as f:
                json.dump(deps_data, f)
            
            # Create and execute override
            request = OverrideRequest(
                dependency_name=dependency_name,
                action=action,
                priority=OverridePriority.LOW,
                reason=f"Testing {action.value} action",
                requester="admin",
                force=True  # Auto-approve for testing
            )
            
            override_id = self.controller.create_override(request)
            result = self.controller.execute_override(dependency_name)
            
            assert result is True
            override_data = self.controller.active_overrides[dependency_name]
            assert override_data["status"] == "executed"

class TestOverrideRequestValidation:
    """Test override request validation."""
    
    def test_override_request_creation(self):
        """Test creating OverrideRequest objects."""
        request = OverrideRequest(
            dependency_name="test_dep",
            action=OverrideAction.APPROVE,
            priority=OverridePriority.MEDIUM,
            reason="Test reason",
            requester="test_user"
        )
        
        assert request.dependency_name == "test_dep"
        assert request.action == OverrideAction.APPROVE
        assert request.priority == OverridePriority.MEDIUM
        assert request.reason == "Test reason"
        assert request.requester == "test_user"
        assert request.expiry_hours == 24  # Default value
        assert request.force is False  # Default value
    
    def test_override_action_enum(self):
        """Test OverrideAction enum values."""
        assert OverrideAction.APPROVE == "approve"
        assert OverrideAction.DEFER == "defer"
        assert OverrideAction.REJECT == "reject"
        assert OverrideAction.FORCE_UPDATE == "force_update"
        assert OverrideAction.ROLLBACK == "rollback"
        assert OverrideAction.PAUSE_MONITORING == "pause_monitoring"
        assert OverrideAction.RESUME_MONITORING == "resume_monitoring"
    
    def test_override_priority_enum(self):
        """Test OverridePriority enum values."""
        assert OverridePriority.LOW == "low"
        assert OverridePriority.MEDIUM == "medium"
        assert OverridePriority.HIGH == "high"
        assert OverridePriority.CRITICAL == "critical"
        assert OverridePriority.EMERGENCY == "emergency"

if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])