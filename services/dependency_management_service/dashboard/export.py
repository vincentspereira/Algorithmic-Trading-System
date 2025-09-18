"""
Data export functionality for dependency monitoring.
"""

from datetime import datetime
from enum import Enum
import io
import logging
import csv
import json
from typing import Dict, List, Optional
from fastapi import HTTPException
from pydantic import BaseModel
import pandas as pd

class ExportFormat(str, Enum):
    """Supported export formats"""
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"
    
class ExportRequest(BaseModel):
    """Export request configuration"""
    format: ExportFormat
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    tiers: Optional[List[str]] = None
    metrics: Optional[List[str]] = None
    include_alerts: bool = False
    
class ExportManager:
    """Manage data exports"""
    
    def __init__(
        self,
        cache,
        alert_manager,
        monitor
    ):
        self.cache = cache
        self.alert_manager = alert_manager
        self.monitor = monitor
        
    async def export_data(
        self,
        request: ExportRequest
    ) -> bytes:
        """Export data in requested format"""
        # Collect data
        data = await self._collect_export_data(request)
        
        # Format data
        if request.format == ExportFormat.CSV:
            return self._to_csv(data)
        elif request.format == ExportFormat.JSON:
            return self._to_json(data)
        elif request.format == ExportFormat.EXCEL:
            return self._to_excel(data)
            
    async def _collect_export_data(
        self,
        request: ExportRequest
    ) -> Dict:
        """Collect data for export"""
        data = {
            "metadata": {
                "export_date": datetime.now(timezone.utc),
                "parameters": request.dict()
            },
            "dependencies": {},
            "metrics": {},
            "alerts": []
        }
        
        # Get dependency data
        results = await self.monitor.monitor_all()
        
        for tier, deps in results.items():
            if not request.tiers or tier in request.tiers:
                data["dependencies"][tier] = []
                
                for dep in deps:
                    # Get historical data
                    history = self.cache.get_historical_data(
                        tier,
                        dep.name,
                        request.start_date,
                        request.end_date
                    )
                    
                    dep_data = {
                        "name": dep.name,
                        "current_status": dep.dict(),
                        "history": history
                    }
                    
                    data["dependencies"][tier].append(dep_data)
                    
        # Get metrics if requested
        if request.metrics:
            for metric in request.metrics:
                metric_data = self.cache.get(
                    "metrics",
                    metric
                )
                if metric_data:
                    data["metrics"][metric] = metric_data
                    
        # Get alerts if requested
        if request.include_alerts:
            alerts = self.alert_manager.get_active_alerts()
            data["alerts"] = [
                alert.dict() for alert in alerts
                if (
                    not request.start_date
                    or alert.timestamp >= request.start_date
                )
                and (
                    not request.end_date
                    or alert.timestamp <= request.end_date
                )
            ]
            
        return data
        
    def _to_csv(self, data: Dict) -> bytes:
        """Convert data to CSV format"""
        # Convert to pandas DataFrame for easy CSV export
        records = []
        
        # Process dependencies
        for tier, deps in data["dependencies"].items():
            for dep in deps:
                base_record = {
                    "tier": tier,
                    "name": dep["name"],
                    "status": dep["current_status"]["health_status"],
                    "last_check": dep["current_status"]["last_check"]
                }
                
                # Add current vulnerabilities
                vulns = dep["current_status"].get("vulnerabilities", [])
                base_record["vulnerability_count"] = len(vulns)
                
                # Add historical data points
                for point in dep["history"]:
                    record = base_record.copy()
                    record.update({
                        "timestamp": point["timestamp"],
                        "historical_status": point["data"]["status"]
                    })
                    records.append(record)
                    
        df = pd.DataFrame(records)
        return df.to_csv(index=False).encode('utf-8')
        
    def _to_json(self, data: Dict) -> bytes:
        """Convert data to JSON format"""
        return json.dumps(
            data,
            default=str,
            indent=2
        ).encode('utf-8')
        
    def _to_excel(self, data: Dict) -> bytes:
        """Convert data to Excel format"""
        # Create Excel writer
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Dependencies sheet
            deps_records = []
            for tier, deps in data["dependencies"].items():
                for dep in deps:
                    record = {
                        "tier": tier,
                        "name": dep["name"],
                        "status": dep["current_status"]["health_status"],
                        "last_check": dep["current_status"]["last_check"]
                    }
                    deps_records.append(record)
                    
            if deps_records:
                pd.DataFrame(deps_records).to_excel(
                    writer,
                    sheet_name='Dependencies',
                    index=False
                )
                
            # Metrics sheet
            if data["metrics"]:
                metrics_df = pd.DataFrame(data["metrics"]).T
                metrics_df.to_excel(
                    writer,
                    sheet_name='Metrics',
                    index=True
                )
                
            # Alerts sheet
            if data["alerts"]:
                pd.DataFrame(data["alerts"]).to_excel(
                    writer,
                    sheet_name='Alerts',
                    index=False
                )
                
        return output.getvalue()
        
class ReportScheduler:
    """Schedule regular reports"""
    
    def __init__(
        self,
        export_manager: ExportManager,
        notification_manager
    ):
        self.export_manager = export_manager
        self.notification_manager = notification_manager
        self.scheduled_reports = {}
        
    async def schedule_report(
        self,
        name: str,
        export_request: ExportRequest,
        schedule: str,
        recipients: List[str]
    ) -> None:
        """Schedule a regular report"""
        self.scheduled_reports[name] = {
            "request": export_request,
            "schedule": schedule,
            "recipients": recipients
        }
        
    async def generate_scheduled_reports(self) -> None:
        """Generate and send scheduled reports"""
        for name, config in self.scheduled_reports.items():
            try:
                # Generate report
                data = await self.export_manager.export_data(
                    config["request"]
                )
                
                # Send to recipients
                await self.notification_manager.send_report(
                    name,
                    data,
                    config["recipients"]
                )
                
            except Exception as e:
                logging.error(
                    f"Error generating report {name}: {str(e)}"
                )
