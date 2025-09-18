"""
Security API Routes for Algorithmic Trading System
Provides endpoints for security dashboard data
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import json

from ..main import APIResponse, get_cached_data, set_cached_data
from auth.middleware import AuthMiddleware, AuthContext
from auth.oauth_service import UserRole, Permission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/security", tags=["security"])

# Pydantic models for security data
class VulnerabilityInfo(BaseModel):
    """Vulnerability information"""
    id: str
    severity: str  # critical, high, medium, low
    component: str
    description: str
    published_date: datetime
    remediation: Optional[str] = None

class SastFindingInfo(BaseModel):
    """SAST finding information"""
    severity: str  # critical, high, medium, low
    confidence: str  # low, medium, high
    description: str
    file: str
    line: int
    test_id: str

class ThreatModelInfo(BaseModel):
    """Threat model information"""
    id: str
    component: str
    category: str
    description: str
    severity: str  # critical, high, medium, low
    mitigation: str
    cvss_score: float
    status: str  # Open, Mitigated, Accepted, False Positive

class SecurityDashboardData(BaseModel):
    """Complete security dashboard data"""
    timestamp: datetime
    overall_risk_score: float
    vulnerabilities: List[VulnerabilityInfo]
    sast_findings: List[SastFindingInfo]
    threat_models: List[ThreatModelInfo]

# Mock data for demonstration
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
    },
    {
        "id": "CVE-2023-11111",
        "severity": "critical",
        "component": "FastAPI",
        "description": "Remote code execution vulnerability in request parsing",
        "published_date": datetime.now(timezone.utc) - timedelta(days=3),
        "remediation": "Upgrade to version 0.104.1 or later"
    }
]

MOCK_SAST_FINDINGS = [
    {
        "severity": "high",
        "confidence": "high",
        "description": "Use of insecure cryptographic hash function",
        "file": "security/auth.py",
        "line": 45,
        "test_id": "B324"
    },
    {
        "severity": "medium",
        "confidence": "medium",
        "description": "Hardcoded password detected",
        "file": "config/database.py",
        "line": 12,
        "test_id": "B105"
    },
    {
        "severity": "low",
        "confidence": "high",
        "description": "Insecure use of temporary file",
        "file": "utils/file_handler.py",
        "line": 78,
        "test_id": "B322"
    }
]

MOCK_THREAT_MODELS = [
    {
        "id": "THREAT-TRADING-ENGINE-TAMPERING-001",
        "component": "Trading Engine",
        "category": "Tampering",
        "description": "Unauthorized modification of trade orders or execution parameters",
        "severity": "critical",
        "mitigation": "Implement immutable event sourcing, digital signatures for all trade events, audit trails",
        "cvss_score": 9.0,
        "status": "Open"
    },
    {
        "id": "THREAT-DATABASE-DISCLOSURE-001",
        "component": "PostgreSQL Database",
        "category": "Information Disclosure",
        "description": "Unauthorized access to sensitive financial data, trade history, or user information",
        "severity": "critical",
        "mitigation": "Implement AES-256 encryption at rest, TLS 1.3 for data in transit, RBAC with least privilege",
        "cvss_score": 9.0,
        "status": "Mitigated"
    },
    {
        "id": "THREAT-API-GATEWAY-SPOOFING-001",
        "component": "API Gateway",
        "category": "Spoofing",
        "description": "Unauthorized entities attempting to impersonate legitimate users",
        "severity": "high",
        "mitigation": "Implement OAuth 2.0/OIDC with JWT tokens, enforce MFA, use mutual TLS",
        "cvss_score": 7.5,
        "status": "Open"
    }
]

def calculate_overall_risk_score(vulnerabilities: List[Dict], sast_findings: List[Dict], threat_models: List[Dict]) -> float:
    """Calculate overall risk score based on security findings"""
    # Simple risk calculation based on severity weights
    severity_weights = {
        "critical": 10,
        "high": 7,
        "medium": 4,
        "low": 1
    }
    
    total_score = 0
    count = 0
    
    # Add vulnerability scores
    for vuln in vulnerabilities:
        total_score += severity_weights.get(vuln["severity"], 1)
        count += 1
    
    # Add SAST finding scores
    for finding in sast_findings:
        total_score += severity_weights.get(finding["severity"], 1)
        count += 1
        
    # Add threat model scores
    for threat in threat_models:
        total_score += threat["cvss_score"]
        count += 1
    
    # Normalize to 0-10 scale
    if count > 0:
        return min(10.0, total_score / count)
    return 0.0

@router.get("/dashboard", response_model=APIResponse)
async def get_security_dashboard(auth_context: AuthContext = Depends(AuthMiddleware.require_permission(Permission.SECURITY_READ))):
    """Get comprehensive security dashboard data"""
    try:
        # Check cache first
        cache_key = "security_dashboard_data"
        cached_data = await get_cached_data(cache_key)
        
        if cached_data and isinstance(cached_data, dict):
            # Check if cached data is recent (less than 5 minutes old)
            cached_timestamp = datetime.fromisoformat(cached_data.get("timestamp", ""))
            if datetime.now(timezone.utc) - cached_timestamp < timedelta(minutes=5):
                return APIResponse(
                    success=True, 
                    data=cached_data, 
                    message="Security dashboard data retrieved from cache"
                )
        
        # Generate fresh data (in a real implementation, this would query actual security services)
        overall_risk_score = calculate_overall_risk_score(
            MOCK_VULNERABILITIES, 
            MOCK_SAST_FINDINGS, 
            MOCK_THREAT_MODELS
        )
        
        dashboard_data = {
            "timestamp": datetime.now(timezone.utc),
            "overall_risk_score": overall_risk_score,
            "vulnerabilities": MOCK_VULNERABILITIES,
            "sast_findings": MOCK_SAST_FINDINGS,
            "threat_models": MOCK_THREAT_MODELS
        }
        
        # Convert datetime objects to strings for JSON serialization
        dashboard_data["timestamp"] = dashboard_data["timestamp"].isoformat()
        
        for vuln in dashboard_data["vulnerabilities"]:
            if isinstance(vuln.get("published_date"), datetime):
                vuln["published_date"] = vuln["published_date"].isoformat()
                
        # Cache the data for 5 minutes
        await set_cached_data(cache_key, dashboard_data, 300)
        
        return APIResponse(
            success=True,
            data=dashboard_data,
            message="Security dashboard data retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Failed to retrieve security dashboard data", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve security dashboard data: {str(e)}")

@router.get("/vulnerabilities", response_model=APIResponse)
async def get_vulnerabilities(auth_context: AuthContext = Depends(AuthMiddleware.require_permission(Permission.SECURITY_READ))):
    """Get current vulnerability information"""
    try:
        vulnerabilities = []
        for vuln in MOCK_VULNERABILITIES:
            vuln_copy = vuln.copy()
            if isinstance(vuln_copy.get("published_date"), datetime):
                vuln_copy["published_date"] = vuln_copy["published_date"].isoformat()
            vulnerabilities.append(vuln_copy)
            
        return APIResponse(
            success=True,
            data=vulnerabilities,
            message=f"Retrieved {len(vulnerabilities)} vulnerabilities"
        )
    except Exception as e:
        logger.error("Failed to retrieve vulnerabilities", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve vulnerabilities: {str(e)}")

@router.get("/sast-findings", response_model=APIResponse)
async def get_sast_findings(auth_context: AuthContext = Depends(AuthMiddleware.require_permission(Permission.SECURITY_READ))):
    """Get current SAST findings"""
    try:
        return APIResponse(
            success=True,
            data=MOCK_SAST_FINDINGS,
            message=f"Retrieved {len(MOCK_SAST_FINDINGS)} SAST findings"
        )
    except Exception as e:
        logger.error("Failed to retrieve SAST findings", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve SAST findings: {str(e)}")

@router.get("/threat-models", response_model=APIResponse)
async def get_threat_models(auth_context: AuthContext = Depends(AuthMiddleware.require_permission(Permission.SECURITY_READ))):
    """Get current threat models"""
    try:
        return APIResponse(
            success=True,
            data=MOCK_THREAT_MODELS,
            message=f"Retrieved {len(MOCK_THREAT_MODELS)} threat models"
        )
    except Exception as e:
        logger.error("Failed to retrieve threat models", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve threat models: {str(e)}")