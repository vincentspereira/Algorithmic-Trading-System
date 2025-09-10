"""
Security Dashboard Generator for Dependency Management System

Creates comprehensive security dashboards with vulnerability tracking,
threat modeling visualization, and compliance monitoring.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import json
from datetime import datetime
from typing import Dict, List, Any
from .dashboard_utils import DashboardManager, DashboardConfig

class SecurityDashboardGenerator:
    """Generates security-focused dashboards for the dependency management system"""
    
    def __init__(self, dashboard_manager: DashboardManager):
        self.manager = dashboard_manager
        
    def generate_security_dashboard(self) -> Dict[str, Any]:
        """Generate the main security dashboard"""
        config = DashboardConfig(
            uid="dep-security",
            title="Dependency Security Dashboard",
            folder="Dependency Management",
            variables=self.manager.get_default_variables(),
            time_range={
                "from": "now-24h",
                "to": "now"
            }
        )
        
        panels = [
            # Overall Security Score
            self.manager.create_performance_panel(
                title="Overall Security Score",
                metric="dependency_overall_security_score{tier=\"$tier\", dependency=\"$dependency\"}",
                unit="percent",
                panel_type="gauge"
            ),
            
            # Active Vulnerabilities by Severity
            self.manager.create_security_panel(
                title="Active Vulnerabilities by Severity",
                metric="sum(dependency_vulnerabilities{tier=\"$tier\", dependency=\"$dependency\"}) by (severity)",
                thresholds=[
                    {"color": "green", "value": 0},
                    {"color": "yellow", "value": 1},
                    {"color": "red", "value": 5}
                ]
            ),
            
            # STRIDE Threat Categories
            self.manager.create_security_panel(
                title="STRIDE Threat Categories",
                metric="sum(dependency_stride_threats{tier=\"$tier\", dependency=\"$dependency\"}) by (category)",
                thresholds=[
                    {"color": "green", "value": 0},
                    {"color": "yellow", "value": 1},
                    {"color": "red", "value": 3}
                ]
            ),
            
            # Security Scan Results Over Time
            self.manager.create_performance_panel(
                title="Security Scans Over Time",
                metric='rate(dependency_security_scans_total{tier="$tier", dependency="$dependency"}[5m])',
                unit="scans/s"
            ),
            
            # License Compliance Status
            self.manager.create_security_panel(
                title="License Compliance",
                metric="dependency_license_compliance{tier=\"$tier\", dependency=\"$dependency\"}",
                thresholds=[
                    {"color": "red", "value": 0},
                    {"color": "yellow", "value": 0.5},
                    {"color": "green", "value": 1}
                ]
            ),
            
            # Recent Security Alerts
            self.manager.create_alerts_panel(
                title="Recent Security Alerts",
                metric="dependency_security_alerts{tier=\"$tier\", dependency=\"$dependency\"}"
            ),
            
            # SAST Findings by Severity
            self.manager.create_security_panel(
                title="SAST Findings by Severity",
                metric="sum(dependency_sast_findings{tier=\"$tier\", dependency=\"$dependency\"}) by (severity)",
                thresholds=[
                    {"color": "green", "value": 0},
                    {"color": "yellow", "value": 5},
                    {"color": "red", "value": 20}
                ]
            )
        ]
        
        dashboard = self.manager.create_dashboard(config, panels)
        
        # Add security-specific alert rules
        dashboard["alerts"] = [
            self.manager.create_alert_rule(
                name="Critical Vulnerability Detected",
                expr='dependency_vulnerabilities{tier="$tier", dependency="$dependency", severity="critical"} > 0',
                severity="critical",
                duration="1m"
            ),
            self.manager.create_alert_rule(
                name="Low Security Score",
                expr='dependency_overall_security_score{tier="$tier", dependency="$dependency"} < 70',
                severity="warning",
                duration="5m"
            ),
            self.manager.create_alert_rule(
                name="High STRIDE Threat Count",
                expr='sum(dependency_stride_threats{tier="$tier", dependency="$dependency"}) > 10',
                severity="warning",
                duration="5m"
            )
        ]
        
        return dashboard
        
    def generate_compliance_dashboard(self) -> Dict[str, Any]:
        """Generate compliance monitoring dashboard"""
        config = DashboardConfig(
            uid="dep-compliance",
            title="Dependency Compliance Dashboard",
            folder="Dependency Management",
            variables=self.manager.get_default_variables()
        )
        
        panels = [
            # Compliance Score
            self.manager.create_performance_panel(
                title="Overall Compliance Score",
                metric="dependency_compliance_score{tier=\"$tier\", dependency=\"$dependency\"}",
                unit="percent",
                panel_type="gauge"
            ),
            
            # License Violations
            self.manager.create_security_panel(
                title="License Violations",
                metric="dependency_license_violations{tier=\"$tier\", dependency=\"$dependency\"}",
                thresholds=[
                    {"color": "green", "value": 0},
                    {"color": "yellow", "value": 1},
                    {"color": "red", "value": 5}
                ]
            ),
            
            # Audit Trail Completeness
            self.manager.create_performance_panel(
                title="Audit Trail Completeness",
                metric="dependency_audit_trail_completeness{tier=\"$tier\", dependency=\"$dependency\"}",
                unit="percent",
                panel_type="gauge"
            ),
            
            # Recent Compliance Events
            self.manager.create_alerts_panel(
                title="Recent Compliance Events",
                metric="dependency_compliance_events{tier=\"$tier\", dependency=\"$dependency\"}"
            )
        ]
        
        dashboard = self.manager.create_dashboard(config, panels)
        
        # Add compliance alert rules
        dashboard["alerts"] = [
            self.manager.create_alert_rule(
                name="Compliance Violation",
                expr='dependency_compliance_violations{tier="$tier", dependency="$dependency"} > 0',
                severity="warning",
                duration="1m"
            ),
            self.manager.create_alert_rule(
                name="Low Compliance Score",
                expr='dependency_compliance_score{tier="$tier", dependency="$dependency"} < 80',
                severity="warning",
                duration="10m"
            )
        ]
        
        return dashboard
        
    def generate_threat_modeling_dashboard(self) -> Dict[str, Any]:
        """Generate STRIDE threat modeling dashboard"""
        config = DashboardConfig(
            uid="dep-threat-model",
            title="STRIDE Threat Modeling Dashboard",
            folder="Dependency Management",
            variables=self.manager.get_default_variables()
        )
        
        panels = [
            # Overall Threat Risk Score
            self.manager.create_performance_panel(
                title="Overall Threat Risk Score",
                metric="dependency_threat_risk_score{tier=\"$tier\", dependency=\"$dependency\"}",
                unit="score",
                panel_type="gauge"
            ),
            
            # Threats by Category
            self.manager.create_security_panel(
                title="Threats by STRIDE Category",
                metric="sum(dependency_stride_threats{tier=\"$tier\", dependency=\"$dependency\"}) by (category)",
                thresholds=[
                    {"color": "green", "value": 0},
                    {"color": "yellow", "value": 3},
                    {"color": "red", "value": 10}
                ]
            ),
            
            # Threats by Severity
            self.manager.create_security_panel(
                title="Threats by Severity",
                metric="sum(dependency_stride_threats{tier=\"$tier\", dependency=\"$dependency\"}) by (severity)",
                thresholds=[
                    {"color": "green", "value": 0},
                    {"color": "yellow", "value": 2},
                    {"color": "red", "value": 5}
                ]
            ),
            
            # Mitigation Status
            self.manager.create_performance_panel(
                title="Threat Mitigation Status",
                metric="dependency_threat_mitigation_status{tier=\"$tier\", dependency=\"$dependency\"}",
                unit="percent",
                panel_type="gauge"
            ),
            
            # Recent Threat Model Updates
            self.manager.create_alerts_panel(
                title="Recent Threat Model Updates",
                metric="dependency_threat_model_updates{tier=\"$tier\", dependency=\"$dependency\"}"
            )
        ]
        
        dashboard = self.manager.create_dashboard(config, panels)
        
        # Add threat modeling alert rules
        dashboard["alerts"] = [
            self.manager.create_alert_rule(
                name="High Threat Risk Score",
                expr='dependency_threat_risk_score{tier="$tier", dependency="$dependency"} > 8.0',
                severity="critical",
                duration="1m"
            ),
            self.manager.create_alert_rule(
                name="Unmitigated Critical Threats",
                expr='dependency_unmitigated_threats{tier="$tier", dependency="$dependency", severity="critical"} > 0',
                severity="critical",
                duration="1m"
            )
        ]
        
        return dashboard
        
    def deploy_all_security_dashboards(self) -> None:
        """Generate and deploy all security dashboards"""
        dashboards = {
            "security": self.generate_security_dashboard(),
            "compliance": self.generate_compliance_dashboard(),
            "threat-modeling": self.generate_threat_modeling_dashboard()
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
                    print(f"Successfully deployed {name} dashboard")
                else:
                    print(f"Failed to deploy {name} dashboard")
                    
            except Exception as e:
                print(f"Error deploying {name} dashboard: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Initialize dashboard manager
    manager = DashboardManager(
        grafana_url="http://localhost:3000",
        api_key="your-api-key-here",
        dashboard_dir="./dashboards"
    )
    
    # Create security dashboard generator
    generator = SecurityDashboardGenerator(manager)
    
    # Generate and deploy dashboards
    generator.deploy_all_security_dashboards()