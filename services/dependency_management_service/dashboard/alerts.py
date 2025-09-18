"""
Alert configuration and management.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
import json
from pydantic import BaseModel, validator

class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    
class AlertType(str, Enum):
    """Types of alerts"""
    VULNERABILITY = "vulnerability"
    UPDATE_AVAILABLE = "update_available"
    HEALTH_CHECK = "health_check"
    ERROR_RATE = "error_rate"
    DEPENDENCY_CHANGE = "dependency_change"
    
class AlertChannel(str, Enum):
    """Alert notification channels"""
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    WEBHOOK = "webhook"
    
class AlertRule(BaseModel):
    """Alert rule configuration"""
    name: str
    description: str
    alert_type: AlertType
    severity: AlertSeverity
    conditions: Dict
    channels: List[AlertChannel]
    enabled: bool = True
    
    @validator('conditions')
    def validate_conditions(cls, v, values):
        """Validate alert conditions"""
        alert_type = values.get('alert_type')
        
        required_fields = {
            AlertType.VULNERABILITY: ['min_severity'],
            AlertType.UPDATE_AVAILABLE: ['update_type'],
            AlertType.HEALTH_CHECK: ['status'],
            AlertType.ERROR_RATE: ['threshold', 'window'],
            AlertType.DEPENDENCY_CHANGE: ['change_type']
        }
        
        if alert_type:
            for field in required_fields[alert_type]:
                if field not in v:
                    raise ValueError(
                        f"Missing required condition field: {field}"
                    )
                    
        return v
        
class Alert(BaseModel):
    """Alert instance"""
    id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    details: Dict
    timestamp: datetime
    acknowledged: bool = False
    
class AlertManager:
    """Manage alerts and alert rules"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.load_rules()
        
    def load_rules(self) -> None:
        """Load alert rules from config"""
        try:
            with open(self.config_path) as f:
                rules_data = json.load(f)
                
            self.rules = {
                name: AlertRule(**rule)
                for name, rule in rules_data.items()
            }
        except FileNotFoundError:
            # Create default rules
            self.rules = self._create_default_rules()
            self.save_rules()
            
    def save_rules(self) -> None:
        """Save alert rules to config"""
        rules_data = {
            name: rule.dict()
            for name, rule in self.rules.items()
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(rules_data, f, indent=2)
            
    def _create_default_rules(self) -> Dict[str, AlertRule]:
        """Create default alert rules"""
        return {
            "critical_vulnerability": AlertRule(
                name="Critical Vulnerability",
                description="Alert on critical vulnerabilities",
                alert_type=AlertType.VULNERABILITY,
                severity=AlertSeverity.CRITICAL,
                conditions={"min_severity": "critical"},
                channels=[AlertChannel.EMAIL, AlertChannel.SLACK]
            ),
            "major_update": AlertRule(
                name="Major Update Available",
                description="Alert on major version updates",
                alert_type=AlertType.UPDATE_AVAILABLE,
                severity=AlertSeverity.HIGH,
                conditions={"update_type": "major"},
                channels=[AlertChannel.SLACK]
            ),
            "high_error_rate": AlertRule(
                name="High Error Rate",
                description="Alert on high error rates",
                alert_type=AlertType.ERROR_RATE,
                severity=AlertSeverity.HIGH,
                conditions={
                    "threshold": 0.05,
                    "window": 300
                },
                channels=[AlertChannel.SLACK, AlertChannel.EMAIL]
            )
        }
        
    def check_conditions(
        self,
        rule: AlertRule,
        data: Dict
    ) -> Optional[Alert]:
        """Check if conditions are met for an alert"""
        if not rule.enabled:
            return None
            
        alert_data = None
        
        if rule.alert_type == AlertType.VULNERABILITY:
            if (
                data.get('severity', '').lower()
                >= rule.conditions['min_severity']
            ):
                alert_data = {
                    "vulnerability": data['vulnerability_id'],
                    "package": data['package'],
                    "severity": data['severity']
                }
                
        elif rule.alert_type == AlertType.UPDATE_AVAILABLE:
            if (
                data.get('update_type', '').lower()
                == rule.conditions['update_type']
            ):
                alert_data = {
                    "package": data['package'],
                    "current_version": data['current_version'],
                    "new_version": data['new_version']
                }
                
        elif rule.alert_type == AlertType.ERROR_RATE:
            rate = data.get('error_rate', 0)
            if rate >= rule.conditions['threshold']:
                alert_data = {
                    "error_rate": rate,
                    "window": rule.conditions['window'],
                    "errors": data.get('errors', [])
                }
                
        if alert_data:
            return Alert(
                id=f"{rule.name}_{datetime.now(timezone.utc).isoformat()}",
                rule_name=rule.name,
                severity=rule.severity,
                message=rule.description,
                details=alert_data,
                timestamp=datetime.now(timezone.utc)
            )
            
        return None
        
    def process_alerts(self, data: Dict) -> List[Alert]:
        """Process data against all rules"""
        new_alerts = []
        
        for rule in self.rules.values():
            alert = self.check_conditions(rule, data)
            if alert:
                self.active_alerts[alert.id] = alert
                new_alerts.append(alert)
                
        return new_alerts
        
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            return True
        return False
        
    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """Get active alerts"""
        alerts = list(self.active_alerts.values())
        
        if severity:
            alerts = [
                alert for alert in alerts
                if alert.severity == severity
            ]
            
        return sorted(
            alerts,
            key=lambda x: (
                AlertSeverity[x.severity].value,
                x.timestamp
            ),
            reverse=True
        )
