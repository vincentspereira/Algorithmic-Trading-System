"""Trading Mode Management API Routes

Provides REST endpoints for managing trading mode switching between paper and live trading.
Includes validation, risk controls, and audit logging for compliance.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import asyncio
import logging
from enum import Enum

from shared.config import settings
from nautilus_trader_engine.core.trading_mode_manager import TradingModeManager
from nautilus_trader_engine.validation.ibkr_integration_validator import IBKRIntegrationValidator
from database.models.audit_log import AuditLog
from database.session import get_db_session

# Configure logging
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Router setup
router = APIRouter(prefix="/api/trading", tags=["trading-mode"])

class TradingModeEnum(str, Enum):
    PAPER = "paper"
    LIVE = "live"
    SIMULATION = "simulation"

class RiskLimits(BaseModel):
    max_position_size: float = Field(..., gt=0, description="Maximum position size in USD")
    max_daily_loss: float = Field(..., gt=0, description="Maximum daily loss in USD")
    max_orders_per_minute: int = Field(..., gt=0, le=1000, description="Maximum orders per minute")
    max_leverage: float = Field(default=1.0, ge=1.0, le=10.0, description="Maximum leverage allowed")

class TradingModeStatus(BaseModel):
    mode: TradingModeEnum
    is_running: bool
    last_switched: datetime
    risk_limits: RiskLimits
    connection_status: Dict[str, Any]
    active_positions: int
    daily_pnl: float
    orders_today: int

class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    checks_performed: List[str] = []
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ModeSwitchRequest(BaseModel):
    target_mode: TradingModeEnum
    force: bool = Field(default=False, description="Force switch even with warnings")
    reason: Optional[str] = Field(None, description="Reason for mode switch")

class ModeSwitchResponse(BaseModel):
    success: bool
    message: str
    previous_mode: TradingModeEnum
    current_mode: TradingModeEnum
    switched_at: datetime
    validation_result: Optional[ValidationResult] = None

# Global trading mode manager instance
trading_mode_manager = TradingModeManager()
ibkr_validator = IBKRIntegrationValidator()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate JWT token and return user info"""
    # TODO: Implement proper JWT validation
    # For now, return a mock user for development
    return {"user_id": "dev_user", "permissions": ["trading_mode_switch"]}

async def log_audit_event(event_type: str, details: Dict[str, Any], user_id: str):
    """Log audit events for compliance"""
    try:
        async with get_db_session() as session:
            audit_log = AuditLog(
                event_type=event_type,
                user_id=user_id,
                details=details,
                timestamp=datetime.now(timezone.utc)
            )
            session.add(audit_log)
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")

@router.get("/mode/status", response_model=TradingModeStatus)
async def get_trading_mode_status(user: dict = Depends(get_current_user)):
    """Get current trading mode status and configuration"""
    try:
        status = await trading_mode_manager.get_current_status()
        
        # Get risk limits based on current mode
        if status["mode"] == TradingModeEnum.LIVE:
            risk_limits = RiskLimits(
                max_position_size=100000.0,  # $100K for live
                max_daily_loss=5000.0,       # $5K daily loss limit
                max_orders_per_minute=10,    # Conservative for live
                max_leverage=2.0
            )
        else:
            risk_limits = RiskLimits(
                max_position_size=1000000.0,  # $1M for paper
                max_daily_loss=50000.0,       # $50K for paper
                max_orders_per_minute=100,    # Higher for testing
                max_leverage=5.0
            )
        
        return TradingModeStatus(
            mode=status["mode"],
            is_running=status["is_running"],
            last_switched=status["last_switched"],
            risk_limits=risk_limits,
            connection_status=status.get("connection_status", {}),
            active_positions=status.get("active_positions", 0),
            daily_pnl=status.get("daily_pnl", 0.0),
            orders_today=status.get("orders_today", 0)
        )
        
    except Exception as e:
        logger.error(f"Failed to get trading mode status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve trading mode status")

@router.post("/mode/validate", response_model=ValidationResult)
async def validate_mode_switch(
    request: ModeSwitchRequest,
    user: dict = Depends(get_current_user)
):
    """Validate if a trading mode switch is safe and possible"""
    try:
        # Perform comprehensive validation
        validation_result = await ibkr_validator.validate_mode_switch(
            target_mode=request.target_mode.value,
            force=request.force
        )
        
        # Log validation attempt
        await log_audit_event(
            event_type="mode_switch_validation",
            details={
                "target_mode": request.target_mode.value,
                "validation_result": validation_result,
                "force": request.force
            },
            user_id=user["user_id"]
        )
        
        return ValidationResult(
            is_valid=validation_result["is_valid"],
            errors=validation_result.get("errors", []),
            warnings=validation_result.get("warnings", []),
            checks_performed=validation_result.get("checks_performed", [])
        )
        
    except Exception as e:
        logger.error(f"Mode switch validation failed: {e}")
        return ValidationResult(
            is_valid=False,
            errors=[f"Validation failed: {str(e)}"],
            warnings=[],
            checks_performed=["error_handling"]
        )

@router.post("/mode/switch", response_model=ModeSwitchResponse)
async def switch_trading_mode(
    request: ModeSwitchRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Switch between paper and live trading modes"""
    try:
        # Get current mode
        current_status = await trading_mode_manager.get_current_status()
        previous_mode = current_status["mode"]
        
        # Validate the switch first (unless forced)
        if not request.force:
            validation = await ibkr_validator.validate_mode_switch(
                target_mode=request.target_mode.value,
                force=False
            )
            
            if not validation["is_valid"]:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Mode switch validation failed",
                        "errors": validation.get("errors", []),
                        "warnings": validation.get("warnings", [])
                    }
                )
        
        # Perform the mode switch
        switch_result = await trading_mode_manager.switch_mode(
            target_mode=request.target_mode.value,
            force=request.force,
            reason=request.reason
        )
        
        if not switch_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Mode switch failed: {switch_result.get('error', 'Unknown error')}"
            )
        
        # Log the successful switch
        background_tasks.add_task(
            log_audit_event,
            event_type="mode_switch_completed",
            details={
                "previous_mode": previous_mode,
                "target_mode": request.target_mode.value,
                "reason": request.reason,
                "force": request.force,
                "switch_duration_ms": switch_result.get("duration_ms", 0)
            },
            user_id=user["user_id"]
        )
        
        return ModeSwitchResponse(
            success=True,
            message=f"Successfully switched from {previous_mode} to {request.target_mode.value} mode",
            previous_mode=previous_mode,
            current_mode=request.target_mode,
            switched_at=datetime.now(timezone.utc),
            validation_result=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mode switch failed: {e}")
        
        # Log the failed attempt
        background_tasks.add_task(
            log_audit_event,
            event_type="mode_switch_failed",
            details={
                "target_mode": request.target_mode.value,
                "error": str(e),
                "reason": request.reason
            },
            user_id=user["user_id"]
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Mode switch failed: {str(e)}"
        )

@router.post("/mode/emergency-stop")
async def emergency_stop(
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user)
):
    """Emergency stop all trading activities"""
    try:
        # Perform emergency stop
        stop_result = await trading_mode_manager.emergency_stop()
        
        # Log emergency stop
        background_tasks.add_task(
            log_audit_event,
            event_type="emergency_stop",
            details={
                "triggered_by": user["user_id"],
                "stop_result": stop_result
            },
            user_id=user["user_id"]
        )
        
        return {
            "success": True,
            "message": "Emergency stop executed successfully",
            "stopped_at": datetime.now(timezone.utc)
        }
        
    except Exception as e:
        logger.error(f"Emergency stop failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Emergency stop failed: {str(e)}"
        )

@router.get("/mode/history")
async def get_mode_switch_history(
    limit: int = 50,
    user: dict = Depends(get_current_user)
):
    """Get history of trading mode switches"""
    try:
        # TODO: Implement database query for mode switch history
        # For now, return mock data
        return {
            "switches": [
                {
                    "timestamp": datetime.now(timezone.utc),
                    "from_mode": "paper",
                    "to_mode": "live",
                    "user_id": user["user_id"],
                    "reason": "Production deployment",
                    "duration_ms": 1250
                }
            ],
            "total_count": 1
        }
        
    except Exception as e:
        logger.error(f"Failed to get mode switch history: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve mode switch history"
        )

@router.get("/health")
async def health_check():
    """Health check endpoint for trading mode service"""
    try:
        # Check if trading mode manager is responsive
        status = await trading_mode_manager.get_current_status()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc),
            "current_mode": status["mode"],
            "is_running": status["is_running"]
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc),
            "error": str(e)
        }