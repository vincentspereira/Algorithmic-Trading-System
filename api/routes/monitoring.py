"""
Monitoring API Routes for Algorithmic Trading System
Provides endpoints for health dashboard data
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

# Import shared utilities and models to avoid circular imports with api.main
from api.app.core.security import verify_token
from api.app.models import APIResponse
from api.app.utils import get_cached_data, set_cached_data

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitoring", tags=["monitoring"]) 

# Pydantic models for monitoring data
class DependencyHealth(BaseModel):
    """Dependency health status"""
    name: str
    tier: int
    status: str  # healthy, warning, critical
    version: str
    last_update: datetime
    uptime: float  # percentage
    latency: float  # ms
    error_count: int
    last_error: Optional[str] = None

class VulnerabilityInfo(BaseModel):
    """Vulnerability information"""
    id: str
    severity: str  # critical, high, medium, low
    component: str
    description: str
    published_date: datetime
    remediation: Optional[str] = None

class SystemMetrics(BaseModel):
    """System metrics"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_in: float  # Mbps
    network_out: float  # Mbps
    active_connections: int

class HealthDashboardData(BaseModel):
    """Complete health dashboard data"""
    timestamp: datetime
    system_status: str  # healthy, degraded, critical
    system_metrics: SystemMetrics
    dependencies: List[DependencyHealth]
    vulnerabilities: List[VulnerabilityInfo]
    alerts: List[Dict[str, Any]]
    last_scan: datetime

# Mock data for demonstration
MOCK_DEPENDENCIES = [
    {
        "name": "NautilusTrader",
        "tier": 1,
        "status": "healthy",
        "version": "2.0.1",
        "last_update": datetime.now(timezone.utc) - timedelta(hours=2),
        "uptime": 99.98,
        "latency": 12.5,
        "error_count": 0
    },
    {
        "name": "Apache Kafka",
        "tier": 1,
        "status": "healthy",
        "version": "3.5.0",
        "last_update": datetime.now(timezone.utc) - timedelta(hours=1),
        "uptime": 99.99,
        "latency": 8.2,
        "error_count": 0
    },
    {
        "name": "LangChain",
        "tier": 1,
        "status": "warning",
        "version": "0.1.5",
        "last_update": datetime.now(timezone.utc) - timedelta(days=1),
        "uptime": 98.5,
        "latency": 45.3,
        "error_count": 3,
        "last_error": "Timeout in LLM call"
    },
    {
        "name": "PostgreSQL",
        "tier": 2,
        "status": "healthy",
        "version": "15.3",
        "last_update": datetime.now(timezone.utc) - timedelta(hours=3),
        "uptime": 99.95,
        "latency": 5.1,
        "error_count": 0
    },
    {
        "name": "Redis",
        "tier": 2,
        "status": "healthy",
        "version": "7.0.11",
        "last_update": datetime.now(timezone.utc) - timedelta(minutes=30),
        "uptime": 99.99,
        "latency": 0.8,
        "error_count": 0
    }
]

MOCK_VULNERABILITIES = [
    {
        "id": "CVE-2023-12345",
        "severity": "high",
        "component": "NautilusTrader",
        "description": "Potential memory leak in order processing module",
        "published_date": datetime.now(timezone.utc) - timedelta(days=7),
        "remediation": "Upgrade to version 2.0.2 or apply patch"
    },
    {
        "id": "CVE-2023-67890",
        "severity": "medium",
        "component": "LangChain",
        "description": "Insecure temporary file creation",
        "published_date": datetime.now(timezone.utc) - timedelta(days=14),
        "remediation": "Upgrade to version 0.1.6"
    }
]

MOCK_ALERTS = [
    {
        "id": "alert_001",
        "severity": "warning",
        "title": "High latency in LangChain service",
        "description": "Average response time exceeded 40ms threshold",
        "timestamp": datetime.now(timezone.utc) - timedelta(minutes=15),
        "component": "AI Assistant"
    }
]

MOCK_METRICS = {
    "cpu_usage": 45.2,
    "memory_usage": 67.8,
    "disk_usage": 34.1,
    "network_in": 12.5,
    "network_out": 8.7,
    "active_connections": 142
}

@router.get("/health-dashboard", response_model=APIResponse)
async def get_health_dashboard(user: dict = Depends(verify_token)):
    """Get comprehensive health dashboard data"""
    try:
        # Check cache first
        cache_key = "health_dashboard_data"
        cached_data = await get_cached_data(cache_key)
        
        if cached_data and isinstance(cached_data, dict):
            # Check if cached data is recent (less than 30 seconds old)
            cached_timestamp = datetime.fromisoformat(cached_data.get("timestamp", ""))
            if datetime.now(timezone.utc) - cached_timestamp < timedelta(seconds=30):
                return APIResponse(
                    success=True, 
                    data=cached_data, 
                    message="Health dashboard data retrieved from cache"
                )
        
        # Generate fresh data (in a real implementation, this would query actual services)
        dashboard_data = HealthDashboardData(
            timestamp=datetime.now(timezone.utc),
            system_status="healthy",
            system_metrics=SystemMetrics(**MOCK_METRICS),
            dependencies=[DependencyHealth(**dep) for dep in MOCK_DEPENDENCIES],
            vulnerabilities=[VulnerabilityInfo(**vuln) for vuln in MOCK_VULNERABILITIES],
            alerts=MOCK_ALERTS,
            last_scan=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        
        # Convert to dict for caching
        data_dict = dashboard_data.dict()
        
        # Cache the data for 30 seconds
        await set_cached_data(cache_key, data_dict, 30)
        
        return APIResponse(
            success=True,
            data=data_dict,
            message="Health dashboard data retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Failed to retrieve health dashboard data", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve health dashboard data: {str(e)}")

@router.get("/dependencies", response_model=APIResponse)
async def get_dependencies_health(user: dict = Depends(verify_token)):
    """Get health status of all dependencies"""
    try:
        dependencies = [DependencyHealth(**dep) for dep in MOCK_DEPENDENCIES]
        return APIResponse(
            success=True,
            data=dependencies,
            message=f"Retrieved health status for {len(dependencies)} dependencies"
        )
    except Exception as e:
        logger.error("Failed to retrieve dependencies health", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve dependencies health: {str(e)}")

@router.get("/vulnerabilities", response_model=APIResponse)
async def get_vulnerabilities(user: dict = Depends(verify_token)):
    """Get current vulnerability information"""
    try:
        vulnerabilities = [VulnerabilityInfo(**vuln) for vuln in MOCK_VULNERABILITIES]
        return APIResponse(
            success=True,
            data=vulnerabilities,
            message=f"Retrieved {len(vulnerabilities)} vulnerabilities"
        )
    except Exception as e:
        logger.error("Failed to retrieve vulnerabilities", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve vulnerabilities: {str(e)}")

@router.get("/system-metrics", response_model=APIResponse)
async def get_system_metrics(user: dict = Depends(verify_token)):
    """Get current system metrics"""
    try:
        metrics = SystemMetrics(**MOCK_METRICS)
        return APIResponse(
            success=True,
            data=metrics.dict(),
            message="System metrics retrieved successfully"
        )
    except Exception as e:
        logger.error("Failed to retrieve system metrics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve system metrics: {str(e)}")