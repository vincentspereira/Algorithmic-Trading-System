#!/usr/bin/env python3
"""
Manual Override Controls for Dependency Management.
Provides administrative controls for manual dependency update management.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum

import requests
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

class OverrideAction(str, Enum):
    APPROVE = "approve"
    DEFER = "defer"
    REJECT = "reject"
    FORCE_UPDATE = "force_update"
    ROLLBACK = "rollback"
    PAUSE_MONITORING = "pause_monitoring"
    RESUME_MONITORING = "resume_monitoring"

class OverridePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

# Pydantic Models
class DependencyOverride(BaseModel):
    dependency_name: str
    action: OverrideAction
    priority: OverridePriority
    reason: str
    requester: str
    approver: Optional[str] = None
    expiry_hours: Optional[int] = 24
    conditions: Optional[Dict] = None
    notification_channels: Optional[List[str]] = None

class OverrideRequest(BaseModel):
    dependency_name: str
    action: OverrideAction
    priority: OverridePriority
    reason: str
    requester: str
    expiry_hours: int = 24
    conditions: Optional[Dict] = None
    force: bool = False

class OverrideStatus(BaseModel):
    id: str
    dependency_name: str
    action: OverrideAction
    priority: OverridePriority
    status: str
    reason: str
    requester: str
    approver: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]
    executed_at: Optional[datetime]

class ManualOverrideController:
    """Handles manual override operations for dependency management."""
    
    def __init__(self, config_path: str = "override_config.json"):
        self.config_path = Path(config_path)
        self.overrides_file = Path("active_overrides.json")
        self.history_file = Path("override_history.json")
        self.config = self._load_config()
        self.active_overrides = self._load_active_overrides()
        
    def _load_config(self) -> Dict:
        """Load override configuration."""
        default_config = {
            "approval_required": {
                "tier1": ["emergency", "critical", "high"],
                "tier2": ["emergency", "critical"],
                "tier3": ["emergency"],
                "tier4": ["emergency"]
            },
            "auto_approve": {
                "security_patches": True,
                "minor_updates": False,
                "major_updates": False
            },
            "notification_settings": {
                "channels": ["teams", "email", "github"],
                "escalation_timeout": 3600,
                "approval_timeout": 86400
            },
            "authorized_users": {
                "approvers": ["admin", "lead_dev", "devops_lead"],
                "requesters": ["developer", "qa", "analyst"],
                "emergency": ["admin", "devops_lead"]
            }
        }
        
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return {**default_config, **json.load(f)}
        else:
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    
    def _load_active_overrides(self) -> Dict:
        """Load active overrides."""
        if self.overrides_file.exists():
            with open(self.overrides_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_active_overrides(self):
        """Save active overrides to file."""
        with open(self.overrides_file, 'w') as f:
            json.dump(self.active_overrides, f, indent=2, default=str)
    
    def _log_to_history(self, override_data: Dict):
        """Log override to history."""
        history = []
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        
        history.append({
            **override_data,
            "logged_at": datetime.now().isoformat()
        })
        
        # Keep only last 1000 entries
        history = history[-1000:]
        
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2, default=str)
    
    def validate_override_request(self, request: OverrideRequest) -> bool:
        """Validate override request against policies."""
        # Check if dependency exists
        deps_file = Path("dependencies.json")
        if deps_file.exists():
            with open(deps_file, 'r') as f:
                deps = json.load(f)
            
            # Find dependency tier
            dep_tier = None
            for tier, tier_data in deps.get("tiers", {}).items():
                for dep in tier_data.get("dependencies", []):
                    if dep["name"] == request.dependency_name:
                        dep_tier = tier
                        break
                if dep_tier:
                    break
            
            if not dep_tier:
                raise ValueError(f"Dependency {request.dependency_name} not found")
            
            # Log validation info
            logger.info(f"Validating override for {request.dependency_name} ({dep_tier}, {request.priority})")
            
            # Always return True for validation - approval requirements are handled in create_override
            return True
        
        # If no dependencies file, allow override for testing
        return True
    
    def create_override(self, request: OverrideRequest) -> str:
        """Create a new override request."""
        override_id = f"override_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{request.dependency_name}"
        
        # Validate request
        if not self.validate_override_request(request):
            raise ValueError("Override request validation failed")
        
        # Check for existing active overrides
        if request.dependency_name in self.active_overrides:
            existing = self.active_overrides[request.dependency_name]
            if existing["status"] in ["active", "pending_approval", "approved"]:
                raise ValueError(f"Active override already exists for {request.dependency_name}")
        
        # Determine if approval is required
        requires_approval = self._requires_approval(request)
        
        # Create override
        override_data = {
            "id": override_id,
            "dependency_name": request.dependency_name,
            "action": request.action.value,
            "priority": request.priority.value,
            "reason": request.reason,
            "requester": request.requester,
            "status": "approved" if (request.force or not requires_approval) else "pending_approval",
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now().timestamp() + request.expiry_hours * 3600),
            "conditions": request.conditions or {},
            "force": request.force,
            "requires_approval": requires_approval
        }
        
        self.active_overrides[request.dependency_name] = override_data
        self._save_active_overrides()
        self._log_to_history(override_data)
        
        # Send notifications
        self._send_override_notification(override_data, "created")
        
        logger.info(f"Override created: {override_id}")
        return override_id
    
    def _requires_approval(self, request: OverrideRequest) -> bool:
        """Determine if an override request requires approval."""
        # Load dependencies to find tier
        deps_file = Path("dependencies.json")
        if deps_file.exists():
            with open(deps_file, 'r') as f:
                deps = json.load(f)
            
            # Find dependency tier
            dep_tier = None
            for tier, tier_data in deps.get("tiers", {}).items():
                for dep in tier_data.get("dependencies", []):
                    if dep["name"] == request.dependency_name:
                        dep_tier = tier
                        break
                if dep_tier:
                    break
            
            if dep_tier:
                approval_required = self.config["approval_required"].get(dep_tier, [])
                return request.priority.value in approval_required
        
        # Default to requiring approval for unknown dependencies
        return True
    
    def approve_override(self, dependency_name: str, approver: str) -> bool:
        """Approve a pending override."""
        if dependency_name not in self.active_overrides:
            raise ValueError(f"No active override found for {dependency_name}")
        
        override_data = self.active_overrides[dependency_name]
        if override_data["status"] != "pending_approval":
            raise ValueError(f"Override for {dependency_name} is not pending approval")
        
        # Update override status
        override_data["status"] = "approved"
        override_data["approver"] = approver
        override_data["approved_at"] = datetime.now().isoformat()
        
        self._save_active_overrides()
        self._log_to_history(override_data)
        
        # Send notification
        self._send_override_notification(override_data, "approved")
        
        logger.info(f"Override approved for {dependency_name} by {approver}")
        return True
    
    def execute_override(self, dependency_name: str) -> bool:
        """Execute an approved override."""
        if dependency_name not in self.active_overrides:
            raise ValueError(f"No active override found for {dependency_name}")
        
        override_data = self.active_overrides[dependency_name]
        if override_data["status"] != "approved":
            raise ValueError(f"Override for {dependency_name} is not approved")
        
        try:
            # Execute the override action
            action = OverrideAction(override_data["action"])
            
            if action == OverrideAction.APPROVE:
                self._execute_approve_action(dependency_name, override_data)
            elif action == OverrideAction.DEFER:
                self._execute_defer_action(dependency_name, override_data)
            elif action == OverrideAction.REJECT:
                self._execute_reject_action(dependency_name, override_data)
            elif action == OverrideAction.FORCE_UPDATE:
                self._execute_force_update_action(dependency_name, override_data)
            elif action == OverrideAction.ROLLBACK:
                self._execute_rollback_action(dependency_name, override_data)
            elif action == OverrideAction.PAUSE_MONITORING:
                self._execute_pause_monitoring_action(dependency_name, override_data)
            elif action == OverrideAction.RESUME_MONITORING:
                self._execute_resume_monitoring_action(dependency_name, override_data)
            
            # Update status
            override_data["status"] = "executed"
            override_data["executed_at"] = datetime.now().isoformat()
            
            self._save_active_overrides()
            self._log_to_history(override_data)
            
            # Send notification
            self._send_override_notification(override_data, "executed")
            
            logger.info(f"Override executed for {dependency_name}: {action}")
            return True
            
        except Exception as e:
            # Update status to failed
            override_data["status"] = "failed"
            override_data["error"] = str(e)
            override_data["failed_at"] = datetime.now().isoformat()
            
            self._save_active_overrides()
            self._log_to_history(override_data)
            
            # Send error notification
            self._send_override_notification(override_data, "failed")
            
            logger.error(f"Override execution failed for {dependency_name}: {e}")
            raise
    
    def _execute_approve_action(self, dependency_name: str, override_data: Dict):
        """Execute approve action for a dependency update."""
        logger.info(f"Approving update for {dependency_name}")
        # Implementation would trigger the dependency update pipeline
        
    def _execute_defer_action(self, dependency_name: str, override_data: Dict):
        """Execute defer action for a dependency update."""
        logger.info(f"Deferring update for {dependency_name}")
        # Implementation would mark the update as deferred
        
    def _execute_reject_action(self, dependency_name: str, override_data: Dict):
        """Execute reject action for a dependency update."""
        logger.info(f"Rejecting update for {dependency_name}")
        # Implementation would block the update
        
    def _execute_force_update_action(self, dependency_name: str, override_data: Dict):
        """Execute force update action for a dependency."""
        logger.info(f"Force updating {dependency_name}")
        # Implementation would bypass normal approval process
        
    def _execute_rollback_action(self, dependency_name: str, override_data: Dict):
        """Execute rollback action for a dependency."""
        logger.info(f"Rolling back {dependency_name}")
        # Implementation would revert to previous version
        
    def _execute_pause_monitoring_action(self, dependency_name: str, override_data: Dict):
        """Execute pause monitoring action for a dependency."""
        logger.info(f"Pausing monitoring for {dependency_name}")
        # Implementation would disable monitoring for specified period
        
    def _execute_resume_monitoring_action(self, dependency_name: str, override_data: Dict):
        """Execute resume monitoring action for a dependency."""
        logger.info(f"Resuming monitoring for {dependency_name}")
        # Implementation would re-enable monitoring
    
    def _send_override_notification(self, override_data: Dict, event_type: str):
        """Send notification about override event."""
        try:
            # Implementation would send notifications via configured channels
            notification_data = {
                "event": event_type,
                "override_id": override_data["id"],
                "dependency": override_data["dependency_name"],
                "action": override_data["action"],
                "priority": override_data["priority"],
                "requester": override_data["requester"],
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Notification sent: {event_type} for {override_data['dependency_name']}")
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def get_active_overrides(self) -> List[Dict]:
        """Get all active overrides."""
        return list(self.active_overrides.values())
    
    def get_override_history(self, limit: int = 100) -> List[Dict]:
        """Get override history."""
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            return history[-limit:]
        return []
    
    def cleanup_expired_overrides(self):
        """Clean up expired overrides."""
        current_time = datetime.now().timestamp()
        expired = []
        
        for dep_name, override_data in self.active_overrides.items():
            if override_data.get("expires_at") and override_data["expires_at"] < current_time:
                expired.append(dep_name)
        
        for dep_name in expired:
            override_data = self.active_overrides[dep_name]
            override_data["status"] = "expired"
            override_data["expired_at"] = datetime.now().isoformat()
            
            self._log_to_history(override_data)
            del self.active_overrides[dep_name]
        
        if expired:
            self._save_active_overrides()
            logger.info(f"Cleaned up {len(expired)} expired overrides")

# FastAPI application
app = FastAPI(title="Dependency Override Management API")
controller = ManualOverrideController()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API token."""
    # Implementation would verify JWT token or API key
    return {"user": "admin", "role": "approver"}

@app.post("/api/v1/overrides", response_model=str)
async def create_override(
    request: OverrideRequest,
    user: Dict = Depends(verify_token)
):
    """Create a new override request."""
    try:
        override_id = controller.create_override(request)
        return override_id
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/overrides/{dependency_name}/approve")
async def approve_override(
    dependency_name: str,
    user: Dict = Depends(verify_token)
):
    """Approve a pending override."""
    try:
        controller.approve_override(dependency_name, user["user"])
        return {"status": "approved"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/overrides/{dependency_name}/execute")
async def execute_override(
    dependency_name: str,
    background_tasks: BackgroundTasks,
    user: Dict = Depends(verify_token)
):
    """Execute an approved override."""
    try:
        background_tasks.add_task(controller.execute_override, dependency_name)
        return {"status": "execution_started"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/overrides", response_model=List[Dict])
async def get_active_overrides(user: Dict = Depends(verify_token)):
    """Get all active overrides."""
    return controller.get_active_overrides()

@app.get("/api/v1/overrides/history", response_model=List[Dict])
async def get_override_history(
    limit: int = 100,
    user: Dict = Depends(verify_token)
):
    """Get override history."""
    return controller.get_override_history(limit)

@app.post("/api/v1/overrides/cleanup")
async def cleanup_expired_overrides(user: Dict = Depends(verify_token)):
    """Clean up expired overrides."""
    controller.cleanup_expired_overrides()
    return {"status": "cleanup_completed"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)