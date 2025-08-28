"""
Dashboard utilities for dependency management system.
Provides tools for managing and updating Grafana dashboards.
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

@dataclass
class DashboardConfig:
    """Configuration for a Grafana dashboard"""
    uid: str
    title: str
    folder: str
    variables: List[Dict[str, Any]]
    refresh_interval: str = "5s"
    time_range: Dict[str, str] = None

class DashboardManager:
    """Manages Grafana dashboards"""
    
    def __init__(
        self,
        grafana_url: str,
        api_key: str,
        dashboard_dir: str
    ):
        self.grafana_url = grafana_url.rstrip('/')
        self.api_key = api_key
        self.dashboard_dir = Path(dashboard_dir)
        
    def load_dashboard(self, dashboard_file: str) -> Dict[str, Any]:
        """Load dashboard configuration from file"""
        path = self.dashboard_dir / dashboard_file
        with open(path, 'r') as f:
            return json.load(f)
            
    def save_dashboard(
        self,
        dashboard_file: str,
        config: Dict[str, Any]
    ) -> None:
        """Save dashboard configuration to file"""
        path = self.dashboard_dir / dashboard_file
        with open(path, 'w') as f:
            json.dump(config, f, indent=2)
            
    def create_dashboard(
        self,
        config: DashboardConfig,
        panels: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a new dashboard configuration"""
        dashboard = {
            "uid": config.uid,
            "title": config.title,
            "tags": ["dependency", "monitoring"],
            "timezone": "",
            "editable": True,
            "style": "dark",
            "graphTooltip": 0,
            "panels": panels,
            "time": config.time_range or {
                "from": "now-6h",
                "to": "now"
            },
            "timepicker": {},
            "refresh": config.refresh_interval,
            "schemaVersion": 38,
            "version": 1,
            "templating": {
                "list": config.variables
            }
        }
        
        return dashboard
        
    def deploy_dashboard(
        self,
        dashboard: Dict[str, Any],
        folder: str
    ) -> bool:
        """Deploy dashboard to Grafana"""
        url = f"{self.grafana_url}/api/dashboards/db"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "dashboard": dashboard,
            "folderUid": folder,
            "message": f"Updated at {datetime.utcnow().isoformat()}",
            "overwrite": True
        }
        
        response = requests.post(url, headers=headers, json=payload)
        return response.status_code == 200
        
    def create_alert_rule(
        self,
        name: str,
        expr: str,
        duration: str = "5m",
        severity: str = "warning"
    ) -> Dict[str, Any]:
        """Create a Grafana alert rule"""
        return {
            "name": name,
            "type": "alerting",
            "message": f"Alert: {name}",
            "alertRuleTags": {
                "severity": severity
            },
            "conditions": [
                {
                    "type": "query",
                    "query": {
                        "params": [expr]
                    },
                    "reducer": {
                        "params": [],
                        "type": "avg"
                    },
                    "evaluator": {
                        "params": [0],
                        "type": "gt"
                    }
                }
            ],
            "executionErrorState": "alerting",
            "frequency": "1m",
            "handler": 1,
            "notifications": [],
            "for": duration
        }
        
    def create_performance_panel(
        self,
        title: str,
        metric: str,
        unit: str = "short",
        panel_type: str = "graph"
    ) -> Dict[str, Any]:
        """Create a performance metrics panel"""
        return {
            "title": title,
            "type": panel_type,
            "datasource": {
                "type": "prometheus",
                "uid": "prometheus"
            },
            "targets": [
                {
                    "expr": metric,
                    "legendFormat": "{{label}}",
                    "refId": "A"
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "color": {
                        "mode": "palette-classic"
                    }
                }
            }
        }
        
    def create_security_panel(
        self,
        title: str,
        metric: str,
        thresholds: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create a security metrics panel"""
        return {
            "title": title,
            "type": "stat",
            "datasource": {
                "type": "prometheus",
                "uid": "prometheus"
            },
            "targets": [
                {
                    "expr": metric,
                    "legendFormat": "{{severity}}",
                    "refId": "A"
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "thresholds": {
                        "mode": "absolute",
                        "steps": thresholds
                    }
                }
            }
        }
        
    def create_resource_panel(
        self,
        title: str,
        metrics: List[str],
        unit: str = "percent"
    ) -> Dict[str, Any]:
        """Create a resource usage panel"""
        return {
            "title": title,
            "type": "timeseries",
            "datasource": {
                "type": "prometheus",
                "uid": "prometheus"
            },
            "targets": [
                {
                    "expr": metric,
                    "legendFormat": "{{resource}}",
                    "refId": chr(65 + i)
                }
                for i, metric in enumerate(metrics)
            ],
            "fieldConfig": {
                "defaults": {
                    "unit": unit,
                    "color": {
                        "mode": "palette-classic"
                    },
                    "custom": {
                        "fillOpacity": 20,
                        "lineWidth": 2,
                        "drawStyle": "line"
                    }
                }
            }
        }
        
def get_default_variables() -> List[Dict[str, Any]]:
    """Get default dashboard variables"""
    return [
        {
            "name": "tier",
            "type": "query",
            "datasource": {
                "type": "prometheus",
                "uid": "prometheus"
            },
            "query": {
                "query": "label_values(dependency_performance_score, tier)"
            },
            "refresh": 1,
            "sort": 1
        },
        {
            "name": "dependency",
            "type": "query",
            "datasource": {
                "type": "prometheus",
                "uid": "prometheus"
            },
            "query": {
                "query": "label_values(dependency_performance_score{tier=\"$tier\"}, dependency)"
            },
            "refresh": 1,
            "sort": 1
        }
    ]
