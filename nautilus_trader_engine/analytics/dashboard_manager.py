"""Dashboard Manager for Analytics Module
Manages real-time dashboards for monitoring trading performance and risk.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
import pandas as pd
import json


@dataclass
class DashboardConfig:
    """Configuration for dashboard management."""
    update_frequency: int = 5  # seconds
    enable_real_time: bool = True
    max_data_points: int = 1000
    enable_alerts: bool = True
    alert_thresholds: Dict[str, float] = field(default_factory=dict)


@dataclass
class DashboardWidget:
    """Represents a widget in the dashboard."""
    widget_id: str
    widget_type: str  # chart, metric, table, alert
    title: str
    data_source: str
    update_callback: Optional[Callable] = None
    config: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class AlertRule:
    """Represents an alert rule for monitoring."""
    rule_id: str
    metric_name: str
    threshold: float
    operator: str  # gt, lt, eq, ne
    severity: str  # info, warning, critical
    enabled: bool = True
    notification_channels: List[str] = field(default_factory=list)


class DashboardManager:
    """Manages real-time dashboards for trading analytics."""
    
    def __init__(self, config: DashboardConfig):
        """Initialize the dashboard manager with configuration.
        
        Args:
            config: DashboardConfig object with management parameters
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Dashboard components
        self.widgets: Dict[str, DashboardWidget] = {}
        self.alert_rules: Dict[str, AlertRule] = {}
        self.data_cache: Dict[str, Any] = {}
        self.active_alerts: List[Dict[str, Any]] = []
        
        # Runtime state
        self.is_running = False
        self.update_task: Optional[asyncio.Task] = None
        
    def add_widget(self, widget_id: str, widget_type: str, title: str, 
                   data_source: str, update_callback: Optional[Callable] = None,
                   config: Dict[str, Any] = None) -> DashboardWidget:
        """Add a widget to the dashboard.
        
        Args:
            widget_id: Unique identifier for the widget
            widget_type: Type of widget (chart, metric, table, alert)
            title: Widget title
            data_source: Data source for the widget
            update_callback: Optional callback function for updating widget data
            config: Optional widget configuration
            
        Returns:
            DashboardWidget object
        """
        widget = DashboardWidget(
            widget_id=widget_id,
            widget_type=widget_type,
            title=title,
            data_source=data_source,
            update_callback=update_callback,
            config=config or {}
        )
        
        self.widgets[widget_id] = widget
        self.logger.info(f"Added widget: {widget_id}")
        return widget
    
    def remove_widget(self, widget_id: str):
        """Remove a widget from the dashboard.
        
        Args:
            widget_id: ID of widget to remove
        """
        if widget_id in self.widgets:
            del self.widgets[widget_id]
            self.logger.info(f"Removed widget: {widget_id}")
    
    def add_alert_rule(self, rule_id: str, metric_name: str, threshold: float,
                      operator: str, severity: str, 
                      notification_channels: List[str] = None) -> AlertRule:
        """Add an alert rule for monitoring.
        
        Args:
            rule_id: Unique identifier for the rule
            metric_name: Name of metric to monitor
            threshold: Threshold value for triggering alert
            operator: Comparison operator (gt, lt, eq, ne)
            severity: Alert severity (info, warning, critical)
            notification_channels: List of notification channels
            
        Returns:
            AlertRule object
        """
        rule = AlertRule(
            rule_id=rule_id,
            metric_name=metric_name,
            threshold=threshold,
            operator=operator,
            severity=severity,
            notification_channels=notification_channels or []
        )
        
        self.alert_rules[rule_id] = rule
        self.logger.info(f"Added alert rule: {rule_id}")
        return rule
    
    def remove_alert_rule(self, rule_id: str):
        """Remove an alert rule.
        
        Args:
            rule_id: ID of rule to remove
        """
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            self.logger.info(f"Removed alert rule: {rule_id}")
    
    async def start_dashboard(self):
        """Start the dashboard update process."""
        if self.is_running:
            self.logger.warning("Dashboard is already running")
            return
        
        self.is_running = True
        self.logger.info("Starting dashboard updates")
        
        if self.config.enable_real_time:
            self.update_task = asyncio.create_task(self._update_loop())
    
    async def stop_dashboard(self):
        """Stop the dashboard update process."""
        self.is_running = False
        
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Dashboard updates stopped")
    
    async def update_real_time_dashboard(self, widget_data: Dict[str, Any]):
        """Update real-time dashboard with new data.
        
        Args:
            widget_data: Dictionary mapping widget IDs to data
        """
        try:
            for widget_id, data in widget_data.items():
                if widget_id in self.widgets:
                    # Update data cache
                    self.data_cache[widget_id] = data
                    self.widgets[widget_id].last_updated = datetime.now()
                    
                    # Call update callback if provided
                    widget = self.widgets[widget_id]
                    if widget.update_callback:
                        try:
                            await widget.update_callback(data)
                        except Exception as e:
                            self.logger.error(f"Error in widget update callback for {widget_id}: {e}")
            
            # Check for alerts if enabled
            if self.config.enable_alerts:
                await self._check_alerts()
                
        except Exception as e:
            self.logger.error(f"Error updating real-time dashboard: {e}")
    
    async def _update_loop(self):
        """Main update loop for real-time dashboard updates."""
        while self.is_running:
            try:
                # Update all widgets that have callbacks
                for widget_id, widget in self.widgets.items():
                    if widget.update_callback and widget.data_source in self.data_cache:
                        try:
                            data = self.data_cache[widget.data_source]
                            await widget.update_callback(data)
                            widget.last_updated = datetime.now()
                        except Exception as e:
                            self.logger.error(f"Error updating widget {widget_id}: {e}")
                
                # Wait for next update
                await asyncio.sleep(self.config.update_frequency)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in dashboard update loop: {e}")
                await asyncio.sleep(self.config.update_frequency)
    
    async def _check_alerts(self):
        """Check alert rules and trigger alerts if conditions are met."""
        try:
            for rule_id, rule in self.alert_rules.items():
                if not rule.enabled:
                    continue
                
                # Get current metric value from data cache
                if rule.metric_name in self.data_cache:
                    current_value = self.data_cache[rule.metric_name]
                    
                    # Check if alert condition is met
                    alert_triggered = False
                    if rule.operator == "gt" and current_value > rule.threshold:
                        alert_triggered = True
                    elif rule.operator == "lt" and current_value < rule.threshold:
                        alert_triggered = True
                    elif rule.operator == "eq" and current_value == rule.threshold:
                        alert_triggered = True
                    elif rule.operator == "ne" and current_value != rule.threshold:
                        alert_triggered = True
                    
                    if alert_triggered:
                        # Create alert
                        alert = {
                            "rule_id": rule_id,
                            "metric_name": rule.metric_name,
                            "current_value": current_value,
                            "threshold": rule.threshold,
                            "operator": rule.operator,
                            "severity": rule.severity,
                            "timestamp": datetime.now().isoformat(),
                            "message": f"{rule.metric_name} {rule.operator} {rule.threshold} (current: {current_value})"
                        }
                        
                        self.active_alerts.append(alert)
                        self.logger.warning(f"Alert triggered: {alert['message']}")
                        
                        # Limit active alerts to prevent memory issues
                        if len(self.active_alerts) > 100:
                            self.active_alerts = self.active_alerts[-50:]
        
        except Exception as e:
            self.logger.error(f"Error checking alerts: {e}")
    
    def get_dashboard_state(self) -> Dict[str, Any]:
        """Get current dashboard state.
        
        Returns:
            Dictionary with dashboard state information
        """
        return {
            "is_running": self.is_running,
            "widget_count": len(self.widgets),
            "alert_rule_count": len(self.alert_rules),
            "active_alerts": len(self.active_alerts),
            "data_cache_size": len(self.data_cache),
            "last_updated": datetime.now().isoformat()
        }