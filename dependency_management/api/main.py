"""
FastAPI backend for the Dependency Health Dashboard.

This module provides API endpoints for retrieving dependency health metrics,
update status, and security information.

Author: Vincent S. Pereira
Version: 1.0.0
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import json
import os
from datetime import datetime

app = FastAPI(title="Dependency Health Dashboard API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DependencyHealth(BaseModel):
    """Model for dependency health data"""
    name: str
    version: str
    tier: int
    last_updated: str
    status: str  # "healthy", "warning", "critical"
    vulnerabilities: List[Dict]
    updates_available: bool
    performance_metrics: Dict[str, float]

def load_dependency_config() -> Dict:
    """Load dependency configuration from file"""
    config_path = os.path.join(
        os.path.dirname(__file__), 
        "..", 
        "dependencies.json"
    )
    with open(config_path, 'r') as f:
        return json.load(f)

@app.get("/api/dependencies/health")
async def get_dependencies_health() -> List[DependencyHealth]:
    """Get health status for all dependencies"""
    try:
        config = load_dependency_config()
        health_data = []

        for tier_key, tier_data in config["tiers"].items():
            for dep in tier_data["dependencies"]:
                # In a real implementation, these would come from actual monitoring
                # systems (Prometheus, CVE databases, etc.)
                health_data.append(DependencyHealth(
                    name=dep["name"],
                    version=dep["version"],
                    tier=int(tier_key.replace("tier", "")),
                    last_updated=datetime.utcnow().isoformat(),
                    status="healthy",  # Mock status
                    vulnerabilities=[],  # Would come from security scans
                    updates_available=False,  # Would come from version checks
                    performance_metrics={
                        "uptime": 99.99,
                        "response_time": 150,  # ms
                        "error_rate": 0.01
                    }
                ))

        return health_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dependencies/{name}/details")
async def get_dependency_details(name: str):
    """Get detailed information about a specific dependency"""
    try:
        config = load_dependency_config()
        
        # Find the dependency in the configuration
        for tier_data in config["tiers"].values():
            for dep in tier_data["dependencies"]:
                if dep["name"] == name:
                    return {
                        **dep,
                        "health_metrics": {
                            "uptime": 99.99,
                            "response_time": 150,
                            "error_rate": 0.01
                        },
                        "recent_updates": [
                            {
                                "version": dep["version"],
                                "date": datetime.utcnow().isoformat(),
                                "type": "security",
                                "status": "success"
                            }
                        ]
                    }
        
        raise HTTPException(status_code=404, detail=f"Dependency {name} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/dependencies/{name}/approve-update")
async def approve_dependency_update(name: str):
    """Approve a pending update for a dependency"""
    try:
        # In a real implementation, this would:
        # 1. Update the dependency version
        # 2. Trigger CI/CD pipeline
        # 3. Update the configuration
        return {"status": "success", "message": f"Update approved for {name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
