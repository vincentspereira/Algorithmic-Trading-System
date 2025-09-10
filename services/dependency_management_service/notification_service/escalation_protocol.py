#!/usr/bin/env python3
"""
Escalation Protocol System
Manages alert escalation for the Algorithmic Trading System's dependency management.
"""

import json
import requests
import sys
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, asdict
from enum import Enum

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EscalationLevel(Enum):
    """Escalation levels."""
    LEVEL_1 = "level_1"  # Initial alert
    LEVEL_2 = "level_2"  # Escalated after timeout
    LEVEL_3 = "level_3"  # Critical escalation
    CCB = "ccb"          # Change Control Board

@dataclass
class EscalationRule:
    """Escalation rule definition."""
    alert_type: str
    severity: str
    timeout_seconds: int
    escalation_path: List[Dict[str, Any]]
    notification_template: str

@dataclass
class AlertInstance:
    """Instance of an alert being tracked."""
    alert_id: str
    alert_type: str
    severity: str
    title: str
    message: str
    timestamp: str
    details: Dict[str, Any]
    current_level: EscalationLevel
    escalation_history: List[Dict[str, Any]]
    acknowledged: bool
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[str]

class EscalationProtocolManager:
    def __init__(self):
        self.rules_file = 'dependency_management/notifications/escalation_rules.json'
        self.alerts_file = 'dependency_management/notifications/active_alerts.json'
        self.rules = self._load_rules()
        self.active_alerts = self._load_active_alerts()
    
    def _load_rules(self) -> List[EscalationRule]:
        """Load escalation rules from configuration file."""
        default_rules = [
            EscalationRule(
                alert_type="security_vulnerability",
                severity="critical",
                timeout_seconds=900,  # 15 minutes
                escalation_path=[
                    {
                        "level": "level_1",
                        "channels": ["teams", "discord", "email"],
                        "recipients": ["security-team@company.com"],
                        "message": "Critical security vulnerability detected: {title}"
                    },
                    {
                        "level": "level_2",
                        "channels": ["teams", "discord", "email", "slack"],
                        "recipients": ["security-team@company.com", "devops-team@company.com"],
                        "message": "CRITICAL SECURITY VULNERABILITY - ESCALATED: {title}"
                    },
                    {
                        "level": "ccb",
                        "channels": ["teams", "email"],
                        "recipients": ["ccb@company.com", "cto@company.com", "security-team@company.com"],
                        "message": "CRITICAL SECURITY VULNERABILITY - CCB NOTIFICATION REQUIRED: {title}"
                    }
                ],
                notification_template="security_vulnerability_template"
            ),
            EscalationRule(
                alert_type="breaking_change",
                severity="high",
                timeout_seconds=3600,  # 1 hour
                escalation_path=[
                    {
                        "level": "level_1",
                        "channels": ["teams", "discord", "email"],
                        "recipients": ["dev-team@company.com"],
                        "message": "Breaking change detected: {title}"
                    },
                    {
                        "level": "level_2",
                        "channels": ["teams", "email"],
                        "recipients": ["dev-team@company.com", "tech-lead@company.com"],
                        "message": "BREAKING CHANGE - ESCALATED: {title}"
                    }
                ],
                notification_template="breaking_change_template"
            ),
            EscalationRule(
                alert_type="monitoring_failure",
                severity="high",
                timeout_seconds=1800,  # 30 minutes
                escalation_path=[
                    {
                        "level": "level_1",
                        "channels": ["teams", "email"],
                        "recipients": ["devops-team@company.com"],
                        "message": "Monitoring system failure: {title}"
                    },
                    {
                        "level": "level_2",
                        "channels": ["teams", "email", "slack"],
                        "recipients": ["devops-team@company.com", "sre-team@company.com"],
                        "message": "MONITORING SYSTEM FAILURE - ESCALATED: {title}"
                    }
                ],
                notification_template="monitoring_failure_template"
            )
        ]
        
        try:
            if os.path.exists(self.rules_file):
                with open(self.rules_file, 'r') as f:
                    rules_data = json.load(f)
                    rules = []
                    for rule_data in rules_data:
                        rule = EscalationRule(
                            alert_type=rule_data['alert_type'],
                            severity=rule_data['severity'],
                            timeout_seconds=rule_data['timeout_seconds'],
                            escalation_path=rule_data['escalation_path'],
                            notification_template=rule_data['notification_template']
                        )
                        rules.append(rule)
                    return rules
        except Exception as e:
            logger.error(f"Error loading escalation rules: {e}")
        
        return default_rules
    
    def _load_active_alerts(self) -> Dict[str, AlertInstance]:
        """Load active alerts from file."""
        try:
            if os.path.exists(self.alerts_file):
                with open(self.alerts_file, 'r') as f:
                    alerts_data = json.load(f)
                    alerts = {}
                    for alert_id, alert_data in alerts_data.items():
                        alert = AlertInstance(
                            alert_id=alert_data['alert_id'],
                            alert_type=alert_data['alert_type'],
                            severity=alert_data['severity'],
                            title=alert_data['title'],
                            message=alert_data['message'],
                            timestamp=alert_data['timestamp'],
                            details=alert_data['details'],
                            current_level=EscalationLevel(alert_data['current_level']),
                            escalation_history=alert_data['escalation_history'],
                            acknowledged=alert_data['acknowledged'],
                            acknowledged_by=alert_data['acknowledged_by'],
                            acknowledged_at=alert_data['acknowledged_at']
                        )
                        alerts[alert_id] = alert
                    return alerts
        except Exception as e:
            logger.error(f"Error loading active alerts: {e}")
        
        return {}
    
    def _save_active_alerts(self):
        """Save active alerts to file."""
        try:
            # Convert AlertInstance objects to dictionaries
            alerts_data = {}
            for alert_id, alert in self.active_alerts.items():
                alerts_data[alert_id] = {
                    'alert_id': alert.alert_id,
                    'alert_type': alert.alert_type,
                    'severity': alert.severity,
                    'title': alert.title,
                    'message': alert.message,
                    'timestamp': alert.timestamp,
                    'details': alert.details,
                    'current_level': alert.current_level.value,
                    'escalation_history': alert.escalation_history,
                    'acknowledged': alert.acknowledged,
                    'acknowledged_by': alert.acknowledged_by,
                    'acknowledged_at': alert.acknowledged_at
                }
            
            with open(self.alerts_file, 'w') as f:
                json.dump(alerts_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving active alerts: {e}")
    
    def _find_rule(self, alert_type: str, severity: str) -> Optional[EscalationRule]:
        """Find matching escalation rule."""
        for rule in self.rules:
            if rule.alert_type == alert_type and rule.severity == severity:
                return rule
        return None
    
    def create_alert(self, alert_type: str, severity: str, title: str, message: str, details: Dict[str, Any] = None) -> str:
        """Create a new alert instance."""
        alert_id = f"{alert_type}_{severity}_{int(datetime.now().timestamp())}"
        
        alert = AlertInstance(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            timestamp=datetime.now().isoformat(),
            details=details or {},
            current_level=EscalationLevel.LEVEL_1,
            escalation_history=[],
            acknowledged=False,
            acknowledged_by=None,
            acknowledged_at=None
        )
        
        self.active_alerts[alert_id] = alert
        self._save_active_alerts()
        
        # Send initial notification
        self._send_notification(alert, EscalationLevel.LEVEL_1)
        
        return alert_id
    
    def _send_notification(self, alert: AlertInstance, level: EscalationLevel):
        """Send notification for specific escalation level."""
        rule = self._find_rule(alert.alert_type, alert.severity)
        if not rule:
            logger.warning(f"No escalation rule found for {alert.alert_type}/{alert.severity}")
            return
        
        # Find the escalation step for this level
        escalation_step = None
        for step in rule.escalation_path:
            if step['level'] == level.value:
                escalation_step = step
                break
        
        if not escalation_step:
            logger.warning(f"No escalation step found for level {level.value}")
            return
        
        try:
            # Import the notification system
            sys.path.append('services/dependency_management_service')
            from notification_service.multi_channel_notifier import MultiChannelNotifier, Alert, AlertSeverity, AlertType
            
            notifier = MultiChannelNotifier()
            
            # Create alert for notification system
            notification_alert = Alert(
                title=escalation_step['message'].format(title=alert.title),
                message=alert.message,
                severity=AlertSeverity(alert.severity),
                alert_type=AlertType(alert.alert_type),
                timestamp=alert.timestamp,
                details=alert.details,
                recipients=escalation_step['recipients'],
                channels=escalation_step['channels']
            )
            
            # Send notification
            results = notifier.send_notification(notification_alert)
            
            # Record in escalation history
            history_entry = {
                "level": level.value,
                "timestamp": datetime.now().isoformat(),
                "notification_results": results,
                "recipients": escalation_step['recipients']
            }
            alert.escalation_history.append(history_entry)
            
            logger.info(f"Sent {level.value} notification for alert {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Acknowledge an alert to prevent escalation."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.now().isoformat()
            self._save_active_alerts()
            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
        else:
            logger.warning(f"Alert {alert_id} not found")
    
    def check_escalation(self):
        """Check all active alerts for escalation."""
        now = datetime.now()
        escalated_alerts = []
        
        for alert_id, alert in self.active_alerts.items():
            # Skip acknowledged alerts
            if alert.acknowledged:
                continue
            
            # Find matching rule
            rule = self._find_rule(alert.alert_type, alert.severity)
            if not rule:
                continue
            
            # Check if timeout has been reached
            alert_time = datetime.fromisoformat(alert.timestamp)
            time_since_alert = (now - alert_time).total_seconds()
            
            if time_since_alert >= rule.timeout_seconds:
                # Determine next escalation level
                current_index = -1
                for i, step in enumerate(rule.escalation_path):
                    if step['level'] == alert.current_level.value:
                        current_index = i
                        break
                
                # Escalate if there's a next level
                if current_index < len(rule.escalation_path) - 1:
                    next_step = rule.escalation_path[current_index + 1]
                    next_level = EscalationLevel(next_step['level'])
                    
                    # Update alert
                    alert.current_level = next_level
                    self._save_active_alerts()
                    
                    # Send escalated notification
                    self._send_notification(alert, next_level)
                    
                    escalated_alerts.append(alert_id)
                    logger.info(f"Escalated alert {alert_id} to {next_level.value}")
        
        return escalated_alerts
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get list of active alerts."""
        return [asdict(alert) for alert in self.active_alerts.values()]
    
    def resolve_alert(self, alert_id: str):
        """Resolve an alert (remove from active alerts)."""
        if alert_id in self.active_alerts:
            del self.active_alerts[alert_id]
            self._save_active_alerts()
            logger.info(f"Resolved alert {alert_id}")
        else:
            logger.warning(f"Alert {alert_id} not found")

def main():
    """Main function to demonstrate escalation protocol."""
    print("Starting Escalation Protocol System...")
    
    manager = EscalationProtocolManager()
    
    # Create sample alerts
    print("\n=== CREATING SAMPLE ALERTS ===")
    
    # 1. Critical security vulnerability
    security_alert_id = manager.create_alert(
        alert_type="security_vulnerability",
        severity="critical",
        title="Critical Vulnerability in NautilusTrader",
        message="CVE-2023-XXXX detected in NautilusTrader dependency requiring immediate attention.",
        details={
            "package": "nautilus_trader",
            "current_version": "1.2.3",
            "vulnerable_version": "< 1.2.5",
            "cvss_score": 9.8,
            "recommendation": "Update to version 1.2.5 or later immediately",
            "affected_services": ["trading_engine", "backtesting_service"]
        }
    )
    print(f"Created security alert: {security_alert_id}")
    
    # 2. Breaking change alert
    breaking_alert_id = manager.create_alert(
        alert_type="breaking_change",
        severity="high",
        title="Breaking Changes in Kafka-Python",
        message="Kafka-Python 3.0.0 introduces breaking API changes requiring migration.",
        details={
            "dependency": "kafka-python",
            "from_version": "2.0.2",
            "to_version": "3.0.0",
            "breaking_changes": [
                "API signature changes in KafkaConsumer",
                "Removed deprecated methods"
            ],
            "affected_services": ["market_data_service", "order_processor"],
            "migration_required": True,
            "estimated_effort": "4 hours"
        }
    )
    print(f"Created breaking change alert: {breaking_alert_id}")
    
    # Show active alerts
    print("\n=== ACTIVE ALERTS ===")
    active_alerts = manager.get_active_alerts()
    for alert in active_alerts:
        print(f"ID: {alert['alert_id']}")
        print(f"  Type: {alert['alert_type']}")
        print(f"  Severity: {alert['severity']}")
        print(f"  Title: {alert['title']}")
        print(f"  Current Level: {alert['current_level']}")
        print(f"  Acknowledged: {alert['acknowledged']}")
        print(f"  Created: {alert['timestamp']}")
        print()
    
    # Simulate escalation check
    print("=== CHECKING FOR ESCALATION ===")
    escalated = manager.check_escalation()
    if escalated:
        print(f"Escalated alerts: {escalated}")
    else:
        print("No alerts escalated")
    
    # Acknowledge one alert
    print("\n=== ACKNOWLEDGING ALERT ===")
    manager.acknowledge_alert(security_alert_id, "john.doe@company.com")
    
    # Show updated active alerts
    print("\n=== UPDATED ACTIVE ALERTS ===")
    active_alerts = manager.get_active_alerts()
    for alert in active_alerts:
        print(f"ID: {alert['alert_id']}")
        print(f"  Type: {alert['alert_type']}")
        print(f"  Severity: {alert['severity']}")
        print(f"  Title: {alert['title']}")
        print(f"  Current Level: {alert['current_level']}")
        print(f"  Acknowledged: {alert['acknowledged']}")
        if alert['acknowledged']:
            print(f"  Acknowledged by: {alert['acknowledged_by']}")
        print()
    
    # Resolve an alert
    print("=== RESOLVING ALERT ===")
    manager.resolve_alert(breaking_alert_id)
    print(f"Resolved alert: {breaking_alert_id}")
    
    # Show final active alerts
    print("\n=== FINAL ACTIVE ALERTS ===")
    active_alerts = manager.get_active_alerts()
    if active_alerts:
        for alert in active_alerts:
            print(f"ID: {alert['alert_id']}")
            print(f"  Type: {alert['alert_type']}")
            print(f"  Severity: {alert['severity']}")
            print(f"  Title: {alert['title']}")
    else:
        print("No active alerts")
    
    print("\nEscalation Protocol System demonstration completed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())