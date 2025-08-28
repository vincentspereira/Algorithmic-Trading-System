"""
Dashboard generator for dependency monitoring system.
Creates and updates Grafana dashboard configurations.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from .dashboard_utils import DashboardConfig, DashboardManager

logger = logging.getLogger(__name__)

class DashboardGenerator:
    """Generates Grafana dashboard configurations"""
    
    def __init__(
        self,
        grafana_url: str,
        api_key: str,
        dashboard_dir: str,
        prometheus_uid: str = "prometheus"
    ):
        self.manager = DashboardManager(grafana_url, api_key, dashboard_dir)
        self.prometheus_uid = prometheus_uid
        
    def generate_overview_dashboard(self) -> Dict:
        """Generate the main dependency overview dashboard"""
        config = DashboardConfig(
            uid="dep-overview",
            title="Dependency Overview",
            folder="Dependency Management",
            variables=self.manager.get_default_variables(),
            refresh_interval="5s"
        )
        
        panels = [
            # Performance score gauge
            self.manager.create_performance_panel(
                title="Dependency Performance Score",
                metric="dependency_performance_score{tier=\"$tier\", dependency=\"$dependency\"}",
                unit="percent",
                panel_type="gauge"
            ),
            
            # Resource usage timeseries
            self.manager.create_resource_panel(
                title="Resource Usage",
                metrics=[
                    "dependency_resource_usage_cpu{tier=\"$tier\", dependency=\"$dependency\"}",
                    "dependency_resource_usage_memory{tier=\"$tier\", dependency=\"$dependency\"}"
                ]
            ),
            
            # Security alerts panel
            self.manager.create_security_panel(
                title="Security Alerts",
                metric="dependency_security_alerts{tier=\"$tier\", dependency=\"$dependency\"}",
                thresholds=[
                    {"color": "green", "value": 0},
                    {"color": "yellow", "value": 1},
                    {"color": "red", "value": 5}
                ]
            ),
            
            # Error rate graph
            self.manager.create_performance_panel(
                title="Error Rate",
                metric='rate(dependency_errors_total{tier="$tier", dependency="$dependency"}[5m])',
                unit="errors/s"
            )
        ]
        
        dashboard = self.manager.create_dashboard(config, panels)
        
        # Add alert rules
        dashboard["alerts"] = [
            self.manager.create_alert_rule(
                name="High Error Rate",
                expr='rate(dependency_errors_total{tier="$tier", dependency="$dependency"}[5m]) > 0.1',
                severity="warning"
            ),
            self.manager.create_alert_rule(
                name="Critical Performance",
                expr='dependency_performance_score{tier="$tier", dependency="$dependency"} < 60',
                severity="critical"
            ),
            self.manager.create_alert_rule(
                name="High Resource Usage",
                expr='dependency_resource_usage_cpu{tier="$tier", dependency="$dependency"} > 80 or dependency_resource_usage_memory{tier="$tier", dependency="$dependency"} > 80',
                severity="warning"
            )
        ]
        
        return dashboard
        
    def generate_security_dashboard(self) -> Dict:
        """Generate the security-focused dashboard"""
        config = DashboardConfig(
            uid="dep-security",
            title="Dependency Security",
            folder="Dependency Management",
            variables=self.manager.get_default_variables()
        )
        
        panels = [
            # Vulnerability count panel
            self.manager.create_security_panel(
                title="Active Vulnerabilities",
                metric="sum(dependency_vulnerabilities{tier=\"$tier\", dependency=\"$dependency\"}) by (severity)",
                thresholds=[
                    {"color": "green", "value": 0},
                    {"color": "yellow", "value": 1},
                    {"color": "red", "value": 3}
                ]
            ),
            
            # Security score panel
            self.manager.create_performance_panel(
                title="Security Score",
                metric="dependency_security_score{tier=\"$tier\", dependency=\"$dependency\"}",
                unit="percent",
                panel_type="gauge"
            ),
            
            # License compliance panel
            self.manager.create_security_panel(
                title="License Compliance",
                metric="dependency_license_compliance{tier=\"$tier\", dependency=\"$dependency\"}",
                thresholds=[
                    {"color": "red", "value": 0},
                    {"color": "green", "value": 1}
                ]
            )
        ]
        
        dashboard = self.manager.create_dashboard(config, panels)
        
        # Add security-specific alert rules
        dashboard["alerts"] = [
            self.manager.create_alert_rule(
                name="Critical Vulnerability",
                expr='dependency_vulnerabilities{tier="$tier", dependency="$dependency", severity="critical"} > 0',
                severity="critical"
            ),
            self.manager.create_alert_rule(
                name="Low Security Score",
                expr='dependency_security_score{tier="$tier", dependency="$dependency"} < 70',
                severity="warning"
            )
        ]
        
        return dashboard
        
    def generate_performance_dashboard(self) -> Dict:
        """Generate the performance-focused dashboard"""
        config = DashboardConfig(
            uid="dep-performance",
            title="Dependency Performance",
            folder="Dependency Management",
            variables=self.manager.get_default_variables()
        )
        
        panels = [
            # Response time panel
            self.manager.create_performance_panel(
                title="Response Time",
                metric='rate(dependency_response_time_seconds_sum{tier="$tier", dependency="$dependency"}[5m]) / rate(dependency_response_time_seconds_count{tier="$tier", dependency="$dependency"}[5m])',
                unit="s"
            ),
            
            # Throughput panel
            self.manager.create_performance_panel(
                title="Request Throughput",
                metric='rate(dependency_requests_total{tier="$tier", dependency="$dependency"}[5m])',
                unit="requests/s"
            ),
            
            # Error percentage panel
            self.manager.create_performance_panel(
                title="Error Percentage",
                metric='100 * rate(dependency_errors_total{tier="$tier", dependency="$dependency"}[5m]) / rate(dependency_requests_total{tier="$tier", dependency="$dependency"}[5m])',
                unit="percent"
            )
        ]
        
        dashboard = self.manager.create_dashboard(config, panels)
        
        # Add performance-specific alert rules
        dashboard["alerts"] = [
            self.manager.create_alert_rule(
                name="High Response Time",
                expr='rate(dependency_response_time_seconds_sum{tier="$tier", dependency="$dependency"}[5m]) / rate(dependency_response_time_seconds_count{tier="$tier", dependency="$dependency"}[5m]) > 1',
                severity="warning"
            ),
            self.manager.create_alert_rule(
                name="High Error Percentage",
                expr='100 * rate(dependency_errors_total{tier="$tier", dependency="$dependency"}[5m]) / rate(dependency_requests_total{tier="$tier", dependency="$dependency"}[5m]) > 5',
                severity="warning"
            )
        ]
        
        return dashboard
        
    def deploy_all_dashboards(self) -> None:
        """Generate and deploy all dashboards"""
        dashboards = {
            "overview": self.generate_overview_dashboard(),
            "security": self.generate_security_dashboard(),
            "performance": self.generate_performance_dashboard()
        }
        
        for name, dashboard in dashboards.items():
            try:
                # Save dashboard configuration
                self.manager.save_dashboard(
                    f"{name}_dashboard.json",
                    dashboard
                )
                
                # Deploy to Grafana
                if self.manager.deploy_dashboard(
                    dashboard,
                    "dependency-management"
                ):
                    logger.info(f"Successfully deployed {name} dashboard")
                else:
                    logger.error(f"Failed to deploy {name} dashboard")
                    
            except Exception as e:
                logger.error(f"Error deploying {name} dashboard: {str(e)}")
                
def main():
    """Main entry point for dashboard generation"""
    grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3000")
    api_key = os.getenv("GRAFANA_API_KEY")
    dashboard_dir = os.getenv(
        "DASHBOARD_DIR",
        Path(__file__).parent.parent / "dashboards"
    )
    
    if not api_key:
        raise ValueError("GRAFANA_API_KEY environment variable not set")
        
    generator = DashboardGenerator(grafana_url, api_key, dashboard_dir)
    generator.deploy_all_dashboards()
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
