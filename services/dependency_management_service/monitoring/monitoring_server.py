"""
Monitoring Server for exposing metrics and providing monitoring API endpoints.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import uvicorn
from typing import Dict, Any
from datetime import datetime, timezone
from monitoring_infrastructure import monitoring

app = FastAPI(title="Dependency Monitoring Server")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/metrics")
async def metrics():
    """Expose Prometheus metrics"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/dependencies/{dependency}/metrics")
async def get_dependency_metrics(dependency: str):
    """Get metrics for a specific dependency"""
    metrics = monitoring.get_dependency_metrics(dependency)
    if not metrics:
        raise HTTPException(status_code=404, detail=f"No metrics found for {dependency}")
    return {
        "dependency": dependency,
        "metrics": {
            "cpu_usage": metrics.cpu_usage,
            "memory_usage": metrics.memory_usage,
            "disk_io": metrics.disk_io,
            "network_io": metrics.network_io,
            "scan_times": metrics.scan_times,
            "error_count": metrics.error_count,
            "last_update": metrics.last_update.isoformat(),
            "health_score": metrics.health_score
        }
    }

@app.get("/dependencies/all/metrics")
async def get_all_metrics():
    """Get metrics for all dependencies"""
    return monitoring.export_metrics()

@app.get("/dependencies/{dependency}/health")
async def get_dependency_health(dependency: str):
    """Get health status for a specific dependency"""
    metrics = monitoring.get_dependency_metrics(dependency)
    if not metrics:
        raise HTTPException(status_code=404, detail=f"No metrics found for {dependency}")
    return {
        "dependency": dependency,
        "health_score": metrics.health_score,
        "status": "healthy" if metrics.health_score >= 70 else "degraded" if metrics.health_score >= 40 else "unhealthy",
        "last_update": metrics.last_update.isoformat(),
        "error_count": metrics.error_count
    }

@app.get("/dependencies/summary")
async def get_dependencies_summary():
    """Get summary of all dependencies"""
    all_metrics = monitoring.export_metrics()
    return {
        "total_dependencies": len(all_metrics),
        "healthy_count": sum(1 for m in all_metrics.values() if m["health_score"] >= 70),
        "degraded_count": sum(1 for m in all_metrics.values() if 40 <= m["health_score"] < 70),
        "unhealthy_count": sum(1 for m in all_metrics.values() if m["health_score"] < 40),
        "total_errors": sum(m["error_count"] for m in all_metrics.values()),
        "dependencies": [
            {
                "name": name,
                "health_score": metrics["health_score"],
                "status": "healthy" if metrics["health_score"] >= 70 else "degraded" if metrics["health_score"] >= 40 else "unhealthy",
                "error_count": metrics["error_count"]
            }
            for name, metrics in all_metrics.items()
        ]
    }

def start_server():
    """Start the monitoring server"""
    uvicorn.run(app, host="0.0.0.0", port=8000)
