"""
Dashboard service for dependency monitoring visualization.
Provides API endpoints and Grafana data source integration.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prometheus_client import CollectorRegistry, Counter, Gauge, start_http_server

from ..monitoring.dependency_monitor import DependencyMonitor
from ..notifications.notification_manager import NotificationManager

logger = logging.getLogger(__name__)

# Models for API requests/responses
class DependencyOverview(BaseModel):
    """Overview of dependency status"""
    total_dependencies: int
    critical_issues: int
    high_issues: int
    normal_issues: int
    healthy_dependencies: int
    updates_available: int
    vulnerabilities_by_severity: Dict[str, int]
    issues_by_tier: Dict[str, int]

class DependencyDetail(BaseModel):
    """Detailed dependency information"""
    name: str
    tier: str
    health_status: str
    last_check: datetime
    last_update: datetime
    current_version: Optional[str]
    latest_version: Optional[str]
    vulnerabilities: List[Dict]
    available_update: Optional[Dict]
    error_count: int

class DashboardMetrics:
    """Prometheus metrics for dashboard"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        
        # Dependency counts
        self.total_dependencies = Gauge(
            'dependency_total',
            'Total number of dependencies',
            ['tier'],
            registry=self.registry
        )
        
        # Health metrics
        self.health_status = Gauge(
            'dependency_health_status',
            'Health status of dependencies',
            ['tier', 'status'],
            registry=self.registry
        )
        
        # Vulnerability metrics
        self.vulnerability_count = Gauge(
            'dependency_vulnerabilities',
            'Number of vulnerabilities',
            ['tier', 'severity'],
            registry=self.registry
        )
        
        # Update metrics
        self.updates_available = Gauge(
            'dependency_updates_available',
            'Number of available updates',
            ['tier', 'type'],
            registry=self.registry
        )
        
        # Error metrics
        self.error_count = Counter(
            'dependency_errors_total',
            'Total number of errors',
            ['tier'],
            registry=self.registry
        )

class DashboardService:
    """Service for dependency monitoring dashboard"""
    
    def __init__(
        self,
        config_path: str,
        github_token: str,
        nvd_api_key: str
    ):
        self.monitor = DependencyMonitor(
            config_path,
            github_token,
            nvd_api_key
        )
        self.notification_manager = NotificationManager(config_path)
        self.metrics = DashboardMetrics()
        self.app = self._create_app()
        
    def _create_app(self) -> FastAPI:
        """Create FastAPI application"""
        app = FastAPI(
            title="Dependency Dashboard API",
            description="API for dependency monitoring dashboard"
        )
        
        # Enable CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )
        
        # Register routes
        self._register_routes(app)
        
        return app
        
    def _register_routes(self, app: FastAPI):
        """Register API routes"""
        
        @app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy"}
            
        @app.get("/api/v1/overview", response_model=DependencyOverview)
        async def get_overview():
            """Get dependency monitoring overview"""
            try:
                results = self.monitor.monitor_all()
                
                overview = {
                    "total_dependencies": 0,
                    "critical_issues": 0,
                    "high_issues": 0,
                    "normal_issues": 0,
                    "healthy_dependencies": 0,
                    "updates_available": 0,
                    "vulnerabilities_by_severity": {},
                    "issues_by_tier": {}
                }
                
                for tier, statuses in results.items():
                    tier_issues = 0
                    self.metrics.total_dependencies.labels(tier).set(len(statuses))
                    
                    for status in statuses:
                        overview["total_dependencies"] += 1
                        
                        # Track health status
                        if status.health_status == "critical":
                            overview["critical_issues"] += 1
                            tier_issues += 1
                        elif status.health_status == "high":
                            overview["high_issues"] += 1
                            tier_issues += 1
                        elif status.health_status == "normal":
                            overview["normal_issues"] += 1
                        else:
                            overview["healthy_dependencies"] += 1
                            
                        self.metrics.health_status.labels(
                            tier,
                            status.health_status
                        ).set(1)
                        
                        # Track vulnerabilities
                        for vuln in status.vulnerabilities:
                            severity = vuln.severity.lower()
                            overview["vulnerabilities_by_severity"][severity] = \
                                overview["vulnerabilities_by_severity"].get(severity, 0) + 1
                            self.metrics.vulnerability_count.labels(
                                tier,
                                severity
                            ).inc()
                            
                        # Track updates
                        if status.available_update:
                            overview["updates_available"] += 1
                            update_type = "breaking" if status.available_update.breaking_changes else "normal"
                            self.metrics.updates_available.labels(
                                tier,
                                update_type
                            ).inc()
                            
                        # Track errors
                        if status.error_count > 0:
                            self.metrics.error_count.labels(tier).inc(
                                status.error_count
                            )
                            
                    overview["issues_by_tier"][tier] = tier_issues
                    
                return overview
                
            except Exception as e:
                logger.error(f"Error getting overview: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to get dependency overview"
                )
                
        @app.get(
            "/api/v1/dependencies/{tier}",
            response_model=List[DependencyDetail]
        )
        async def get_dependencies(tier: str):
            """Get dependencies for a tier"""
            try:
                results = self.monitor.monitor_tier(
                    tier,
                    self.monitor.repo_manager.config["tiers"][tier]
                )
                
                return [
                    DependencyDetail(
                        name=status.name,
                        tier=status.tier,
                        health_status=status.health_status,
                        last_check=status.last_check,
                        last_update=status.last_update,
                        current_version=getattr(
                            status.available_update,
                            'current_version',
                            None
                        ),
                        latest_version=getattr(
                            status.available_update,
                            'latest_version',
                            None
                        ),
                        vulnerabilities=[
                            vars(v) for v in status.vulnerabilities
                        ],
                        available_update=vars(status.available_update)
                        if status.available_update else None,
                        error_count=status.error_count
                    )
                    for status in results
                ]
                
            except KeyError:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tier {tier} not found"
                )
            except Exception as e:
                logger.error(f"Error getting dependencies: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to get dependencies"
                )
                
        @app.get("/api/v1/critical-issues")
        async def get_critical_issues():
            """Get critical issues across all dependencies"""
            try:
                return self.monitor.get_critical_issues()
            except Exception as e:
                logger.error(f"Error getting critical issues: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to get critical issues"
                )
                
        @app.get("/api/v1/metrics")
        async def get_metrics():
            """Get Prometheus metrics"""
            try:
                return self.metrics.registry
            except Exception as e:
                logger.error(f"Error getting metrics: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to get metrics"
                )
                
    def start(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the dashboard service"""
        try:
            # Start Prometheus metrics server
            start_http_server(port + 1)
            
            # Start FastAPI server
            import uvicorn
            uvicorn.run(self.app, host=host, port=port)
            
        except Exception as e:
            logger.error(f"Error starting dashboard service: {str(e)}")
            raise
            
def main():
    """Main entry point for dashboard service"""
    logging.basicConfig(level=logging.INFO)
    
    config_path = os.getenv(
        "REPO_CONFIG",
        "config/repository_management.json"
    )
    github_token = os.getenv("GITHUB_TOKEN")
    nvd_api_key = os.getenv("NVD_API_KEY")
    
    if not github_token:
        raise ValueError("GITHUB_TOKEN environment variable not set")
        
    if not nvd_api_key:
        raise ValueError("NVD_API_KEY environment variable not set")
        
    service = DashboardService(config_path, github_token, nvd_api_key)
    service.start()
    
if __name__ == "__main__":
    main()
