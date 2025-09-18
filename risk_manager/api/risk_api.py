"""Risk Manager API

FastAPI-based REST API for risk management operations,
providing endpoints for risk assessment, monitoring, and configuration.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from ..models.risk_models import (
    RiskLimits, RiskAssessmentRequest, RiskAssessmentResponse,
    PortfolioRiskSummary, RiskCheckResult, RiskLevel
)
from ..engine.risk_engine import RiskEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global risk engine instance
risk_engine: Optional[RiskEngine] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    
    global risk_engine
    
    # Startup
    logger.info("Starting Risk Manager API...")
    
    try:
        # Initialize risk engine
        risk_engine = RiskEngine(
            enable_realtime_monitoring=True,
            monitoring_interval=1.0
        )
        await risk_engine.initialize()
        
        logger.info("Risk Manager API started successfully")
        
        yield
        
    finally:
        # Shutdown
        logger.info("Shutting down Risk Manager API...")
        
        if risk_engine:
            await risk_engine.shutdown()
        
        logger.info("Risk Manager API shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Risk Manager API",
    description="Comprehensive risk management system for algorithmic trading",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API

class RiskAssessmentRequestAPI(BaseModel):
    """API model for risk assessment request"""
    
    account_id: str = Field(..., description="Account identifier")
    symbol: str = Field(..., description="Trading symbol")
    quantity: int = Field(..., gt=0, description="Order quantity")
    price: float = Field(..., gt=0, description="Order price")
    order_type: str = Field(default="MARKET", description="Order type")
    side: str = Field(..., description="Order side (BUY/SELL)")
    request_id: Optional[str] = Field(None, description="Request identifier")

class MonitoringRequest(BaseModel):
    """Request to start/stop monitoring"""
    
    account_ids: List[str] = Field(..., description="List of account IDs to monitor")

class RiskLimitsUpdate(BaseModel):
    """Risk limits update request"""
    
    max_position_size: Optional[float] = Field(None, gt=0)
    max_portfolio_exposure: Optional[float] = Field(None, gt=0)
    max_concentration_percent: Optional[float] = Field(None, gt=0, le=100)
    max_leverage: Optional[float] = Field(None, gt=0)
    max_daily_loss: Optional[float] = Field(None, gt=0)
    max_var_percentage: Optional[float] = Field(None, gt=0, le=100)

class HealthResponse(BaseModel):
    """Health check response"""
    
    status: str
    timestamp: datetime
    version: str
    uptime_seconds: float
    engine_status: Dict[str, Any]

# Dependency to get risk engine
async def get_risk_engine() -> RiskEngine:
    """Get risk engine instance"""
    
    if not risk_engine or not risk_engine.is_initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Risk engine not available"
        )
    
    return risk_engine

# API Routes

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    
    try:
        engine_status = {}
        if risk_engine:
            engine_status = risk_engine.get_engine_status()
        
        return HealthResponse(
            status="healthy" if risk_engine and risk_engine.is_initialized else "unhealthy",
            timestamp=datetime.now(timezone.utc),
            version="1.0.0",
            uptime_seconds=0.0,  # Would track actual uptime
            engine_status=engine_status
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )

@app.post("/risk/assess", response_model=RiskAssessmentResponse)
async def assess_order_risk(
    request: RiskAssessmentRequestAPI,
    engine: RiskEngine = Depends(get_risk_engine)
):
    """Assess risk for a trading order"""
    
    try:
        # Convert API request to internal model
        risk_request = RiskAssessmentRequest(
            account_id=request.account_id,
            symbol=request.symbol,
            quantity=request.quantity,
            price=request.price,
            order_type=request.order_type,
            side=request.side,
            request_id=request.request_id or f"req_{datetime.now().timestamp()}"
        )
        
        # Perform risk assessment
        response = await engine.assess_order_risk(risk_request)
        
        logger.info(f"Risk assessment completed for {request.symbol}: {response.result}")
        
        return response
        
    except Exception as e:
        logger.error(f"Risk assessment failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk assessment failed: {str(e)}"
        )

@app.get("/risk/portfolio/{account_id}", response_model=PortfolioRiskSummary)
async def get_portfolio_risk(
    account_id: str,
    engine: RiskEngine = Depends(get_risk_engine)
):
    """Get portfolio risk summary"""
    
    try:
        risk_summary = await engine.get_portfolio_risk_summary(account_id)
        
        if not risk_summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio risk data not found for account {account_id}"
            )
        
        return risk_summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get portfolio risk for {account_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get portfolio risk: {str(e)}"
        )

@app.post("/risk/monitoring/start")
async def start_monitoring(
    request: MonitoringRequest,
    background_tasks: BackgroundTasks,
    engine: RiskEngine = Depends(get_risk_engine)
):
    """Start real-time risk monitoring"""
    
    try:
        await engine.start_realtime_monitoring(request.account_ids)
        
        return {
            "message": f"Started monitoring for accounts: {request.account_ids}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to start monitoring: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start monitoring: {str(e)}"
        )

@app.post("/risk/monitoring/stop")
async def stop_monitoring(
    engine: RiskEngine = Depends(get_risk_engine)
):
    """Stop real-time risk monitoring"""
    
    try:
        await engine.stop_realtime_monitoring()
        
        return {
            "message": "Risk monitoring stopped",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to stop monitoring: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop monitoring: {str(e)}"
        )

@app.get("/risk/monitoring/status")
async def get_monitoring_status(
    engine: RiskEngine = Depends(get_risk_engine)
):
    """Get monitoring status"""
    
    try:
        status_info = engine.get_engine_status()
        
        return {
            "monitoring_status": status_info,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get monitoring status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monitoring status: {str(e)}"
        )

@app.post("/risk/check/{account_id}")
async def force_risk_check(
    account_id: str,
    engine: RiskEngine = Depends(get_risk_engine)
):
    """Force immediate risk check for account"""
    
    try:
        check_result = await engine.force_risk_check(account_id)
        
        return {
            "account_id": account_id,
            "check_result": check_result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to force risk check for {account_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to force risk check: {str(e)}"
        )

@app.get("/risk/limits")
async def get_risk_limits(
    engine: RiskEngine = Depends(get_risk_engine)
):
    """Get current risk limits"""
    
    try:
        return {
            "risk_limits": engine.risk_limits.__dict__,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get risk limits: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get risk limits: {str(e)}"
        )

@app.put("/risk/limits")
async def update_risk_limits(
    limits_update: RiskLimitsUpdate,
    engine: RiskEngine = Depends(get_risk_engine)
):
    """Update risk limits"""
    
    try:
        # Update only provided fields
        current_limits = engine.risk_limits
        
        if limits_update.max_position_size is not None:
            current_limits.max_position_size = limits_update.max_position_size
        
        if limits_update.max_portfolio_exposure is not None:
            current_limits.max_portfolio_exposure = limits_update.max_portfolio_exposure
        
        if limits_update.max_concentration_percent is not None:
            current_limits.max_concentration_percent = limits_update.max_concentration_percent
        
        if limits_update.max_leverage is not None:
            current_limits.max_leverage = limits_update.max_leverage
        
        if limits_update.max_daily_loss is not None:
            current_limits.max_daily_loss = limits_update.max_daily_loss
        
        if limits_update.max_var_percentage is not None:
            current_limits.max_var_percentage = limits_update.max_var_percentage
        
        return {
            "message": "Risk limits updated successfully",
            "updated_limits": current_limits.__dict__,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to update risk limits: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update risk limits: {str(e)}"
        )

@app.get("/risk/metrics/{account_id}")
async def get_risk_metrics(
    account_id: str,
    engine: RiskEngine = Depends(get_risk_engine)
):
    """Get current risk metrics for account"""
    
    try:
        # Get risk metrics from real-time monitor
        if engine.realtime_monitor:
            metrics = engine.realtime_monitor.current_metrics.get(account_id, [])
            violations = engine.realtime_monitor.active_violations.get(account_id, [])
            
            return {
                "account_id": account_id,
                "metrics": [metric.__dict__ for metric in metrics],
                "violations": [violation.__dict__ for violation in violations],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "account_id": account_id,
                "metrics": [],
                "violations": [],
                "message": "Real-time monitoring not enabled",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
    except Exception as e:
        logger.error(f"Failed to get risk metrics for {account_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get risk metrics: {str(e)}"
        )

@app.get("/risk/violations/{account_id}")
async def get_risk_violations(
    account_id: str,
    engine: RiskEngine = Depends(get_risk_engine)
):
    """Get active risk violations for account"""
    
    try:
        if engine.realtime_monitor:
            violations = engine.realtime_monitor.active_violations.get(account_id, [])
            
            return {
                "account_id": account_id,
                "violations": [violation.__dict__ for violation in violations],
                "violation_count": len(violations),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "account_id": account_id,
                "violations": [],
                "violation_count": 0,
                "message": "Real-time monitoring not enabled",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
    except Exception as e:
        logger.error(f"Failed to get risk violations for {account_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get risk violations: {str(e)}"
        )

# Error handlers

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle ValueError exceptions"""
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    
    logger.error(f"Unhandled exception: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

# WebSocket endpoint for real-time risk updates (optional)

from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    """WebSocket connection manager"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                # Remove disconnected clients
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.websocket("/ws/risk/{account_id}")
async def websocket_risk_updates(websocket: WebSocket, account_id: str):
    """WebSocket endpoint for real-time risk updates"""
    
    await manager.connect(websocket)
    
    try:
        while True:
            # Send periodic risk updates
            if risk_engine and risk_engine.realtime_monitor:
                risk_summary = await risk_engine.get_portfolio_risk_summary(account_id)
                
                if risk_summary:
                    await websocket.send_json({
                        "type": "risk_update",
                        "account_id": account_id,
                        "data": risk_summary.__dict__,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
            
            await asyncio.sleep(5)  # Send updates every 5 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error for {account_id}: {str(e)}")
        manager.disconnect(websocket)

# Main function to run the API

def main():
    """Main function to run the Risk Manager API"""
    
    uvicorn.run(
        "risk_manager.api.risk_api:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()