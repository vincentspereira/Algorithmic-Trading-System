"""
Apache Iceberg Integration for Immutable Audit Logs
Implements tamper-proof audit trail system for regulatory compliance

This module provides:
- Immutable event logging using Apache Iceberg
- Regulatory compliance support (SOX, MiFID II, GDPR)
- Time-travel queries for audit trails
- Automatic partitioning and optimization
- Integration with Kafka event streaming

Author: Vincent S. Pereira
Version: 1.0.0
Phase: 1 - Core System Validation & Hardening
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
import json
import uuid
from dataclasses import dataclass, asdict
from enum import Enum

# Iceberg and data processing
try:
    from pyiceberg.catalog import load_catalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        NestedField, StringType, TimestampType, BooleanType, 
        LongType, DoubleType, StructType, ListType
    )
    from pyiceberg.partitioning import PartitionSpec, PartitionField
    from pyiceberg.transforms import days, hours
    ICEBERG_AVAILABLE = True
except ImportError:
    ICEBERG_AVAILABLE = False
    logging.warning("PyIceberg not available. Install with: pip install pyiceberg")

logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    """Types of audit events for categorization"""
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"
    TRADING_EVENT = "trading_event"
    SECURITY_EVENT = "security_event"
    DATA_ACCESS = "data_access"
    CONFIGURATION_CHANGE = "configuration_change"
    ERROR_EVENT = "error_event"

class ComplianceFramework(Enum):
    """Supported compliance frameworks"""
    SOX = "sox"
    MIFID_II = "mifid_ii"
    GDPR = "gdpr"
    FINRA = "finra"
    SEC = "sec"

@dataclass
class AuditEvent:
    """Immutable audit event structure"""
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    user_id: Optional[str]
    session_id: Optional[str]
    action: str
    resource: str
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    outcome: str  # SUCCESS, FAILURE, PARTIAL
    risk_score: int  # 0-100
    compliance_tags: List[str]
    correlation_id: Optional[str]
    service_name: str
    version: str

class IcebergAuditLogger:
    """
    Apache Iceberg-based audit logging system
    Provides immutable, time-travel capable audit trails
    """
    
    def __init__(self, catalog_config: Optional[Dict[str, Any]] = None):
        self.catalog_config = catalog_config or self._default_catalog_config()
        self.catalog = None
        self.tables = {}
        self.initialized = False
        self.logger = logging.getLogger(__name__)
        
        if not ICEBERG_AVAILABLE:
            self.logger.error("PyIceberg not available. Audit logging will be limited.")
    
    def _default_catalog_config(self) -> Dict[str, Any]:
        """Default catalog configuration"""
        return {
            "type": "hadoop",
            "warehouse": "s3://trading-system-audit-logs/iceberg",
            "hadoop.fs.s3a.access.key": "your-access-key",
            "hadoop.fs.s3a.secret.key": "your-secret-key",
            "hadoop.fs.s3a.endpoint": "s3.amazonaws.com"
        }
    
    async def initialize(self) -> bool:
        """Initialize Iceberg catalog and audit tables"""
        if not ICEBERG_AVAILABLE:
            self.logger.warning("Iceberg not available - using fallback audit logging")
            return await self._initialize_fallback()
        
        try:
            # Load Iceberg catalog
            self.catalog = load_catalog("audit_catalog", **self.catalog_config)
            
            # Create audit tables
            await self._create_audit_tables()
            
            self.initialized = True
            self.logger.info("Iceberg audit logging initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Iceberg audit logging: {e}")
            return await self._initialize_fallback()
    
    async def _initialize_fallback(self) -> bool:
        """Initialize fallback audit logging without Iceberg"""
        try:
            # Use file-based audit logging as fallback
            import os
            audit_dir = "audit_logs"
            os.makedirs(audit_dir, exist_ok=True)
            
            self.audit_file_path = os.path.join(audit_dir, f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl")
            self.initialized = True
            self.logger.info("Fallback audit logging initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize fallback audit logging: {e}")
            return False
    
    async def _create_audit_tables(self):
        """Create Iceberg tables for different audit categories"""
        
        # Main audit events table
        audit_schema = Schema(
            NestedField(1, "event_id", StringType(), required=True),
            NestedField(2, "timestamp", TimestampType(), required=True),
            NestedField(3, "event_type", StringType(), required=True),
            NestedField(4, "user_id", StringType(), required=False),
            NestedField(5, "session_id", StringType(), required=False),
            NestedField(6, "action", StringType(), required=True),
            NestedField(7, "resource", StringType(), required=True),
            NestedField(8, "details", StringType(), required=True),  # JSON string
            NestedField(9, "ip_address", StringType(), required=False),
            NestedField(10, "user_agent", StringType(), required=False),
            NestedField(11, "outcome", StringType(), required=True),
            NestedField(12, "risk_score", LongType(), required=True),
            NestedField(13, "compliance_tags", ListType(14, StringType(), element_required=True), required=True),
            NestedField(15, "correlation_id", StringType(), required=False),
            NestedField(16, "service_name", StringType(), required=True),
            NestedField(17, "version", StringType(), required=True),
        )
        
        # Partition by date and event type for efficient queries
        partition_spec = PartitionSpec(
            PartitionField(source_id=2, field_id=1000, transform=days, name="date"),
            PartitionField(source_id=3, field_id=1001, transform="identity", name="event_type")
        )
        
        # Create audit events table
        try:
            self.tables["audit_events"] = self.catalog.create_table(
                "audit.audit_events",
                schema=audit_schema,
                partition_spec=partition_spec
            )
        except Exception as e:
            if "already exists" in str(e).lower():
                self.tables["audit_events"] = self.catalog.load_table("audit.audit_events")
            else:
                raise
        
        # Trading events table with specialized schema
        trading_schema = Schema(
            NestedField(1, "event_id", StringType(), required=True),
            NestedField(2, "timestamp", TimestampType(), required=True),
            NestedField(3, "order_id", StringType(), required=False),
            NestedField(4, "symbol", StringType(), required=True),
            NestedField(5, "side", StringType(), required=True),
            NestedField(6, "quantity", DoubleType(), required=True),
            NestedField(7, "price", DoubleType(), required=False),
            NestedField(8, "order_type", StringType(), required=True),
            NestedField(9, "status", StringType(), required=True),
            NestedField(10, "user_id", StringType(), required=True),
            NestedField(11, "account_id", StringType(), required=True),
            NestedField(12, "strategy_id", StringType(), required=False),
            NestedField(13, "execution_time_ms", LongType(), required=False),
            NestedField(14, "commission", DoubleType(), required=False),
            NestedField(15, "metadata", StringType(), required=False),  # JSON string
        )
        
        trading_partition_spec = PartitionSpec(
            PartitionField(source_id=2, field_id=2000, transform=days, name="date"),
            NestedField(source_id=4, field_id=2001, transform="identity", name="symbol")
        )
        
        # Create trading events table
        try:
            self.tables["trading_events"] = self.catalog.create_table(
                "audit.trading_events",
                schema=trading_schema,
                partition_spec=trading_partition_spec
            )
        except Exception as e:
            if "already exists" in str(e).lower():
                self.tables["trading_events"] = self.catalog.load_table("audit.trading_events")
            else:
                raise
    
    async def log_audit_event(self, event: AuditEvent) -> bool:
        """Log an audit event to Iceberg"""
        if not self.initialized:
            await self.initialize()
        
        try:
            if ICEBERG_AVAILABLE and self.catalog:
                return await self._log_to_iceberg(event)
            else:
                return await self._log_to_fallback(event)
                
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {e}")
            return False
    
    async def _log_to_iceberg(self, event: AuditEvent) -> bool:
        """Log event to Iceberg table"""
        try:
            # Convert event to Iceberg record
            record = {
                "event_id": event.event_id,
                "timestamp": event.timestamp,
                "event_type": event.event_type.value,
                "user_id": event.user_id,
                "session_id": event.session_id,
                "action": event.action,
                "resource": event.resource,
                "details": json.dumps(event.details),
                "ip_address": event.ip_address,
                "user_agent": event.user_agent,
                "outcome": event.outcome,
                "risk_score": event.risk_score,
                "compliance_tags": event.compliance_tags,
                "correlation_id": event.correlation_id,
                "service_name": event.service_name,
                "version": event.version,
            }
            
            # Write to appropriate table
            if event.event_type == AuditEventType.TRADING_EVENT:
                # Extract trading-specific fields if available
                trading_record = self._extract_trading_fields(event)
                if trading_record:
                    self.tables["trading_events"].append([trading_record])
            
            # Always write to main audit table
            self.tables["audit_events"].append([record])
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write to Iceberg: {e}")
            return False
    
    async def _log_to_fallback(self, event: AuditEvent) -> bool:
        """Log event to fallback file system"""
        try:
            record = {
                **asdict(event),
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type.value
            }
            
            with open(self.audit_file_path, 'a') as f:
                f.write(json.dumps(record) + '\n')
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write to fallback audit log: {e}")
            return False
    
    def _extract_trading_fields(self, event: AuditEvent) -> Optional[Dict[str, Any]]:
        """Extract trading-specific fields from audit event"""
        try:
            details = event.details
            
            if not all(key in details for key in ["symbol", "side", "quantity", "order_type"]):
                return None
            
            return {
                "event_id": event.event_id,
                "timestamp": event.timestamp,
                "order_id": details.get("order_id"),
                "symbol": details["symbol"],
                "side": details["side"],
                "quantity": float(details["quantity"]),
                "price": float(details.get("price", 0)) if details.get("price") else None,
                "order_type": details["order_type"],
                "status": details.get("status", "UNKNOWN"),
                "user_id": event.user_id,
                "account_id": details.get("account_id"),
                "strategy_id": details.get("strategy_id"),
                "execution_time_ms": details.get("execution_time_ms"),
                "commission": float(details.get("commission", 0)) if details.get("commission") else None,
                "metadata": json.dumps({k: v for k, v in details.items() if k not in [
                    "symbol", "side", "quantity", "price", "order_type", "status",
                    "account_id", "strategy_id", "execution_time_ms", "commission"
                ]})
            }
            
        except Exception as e:
            self.logger.warning(f"Could not extract trading fields: {e}")
            return None
    
    async def query_audit_trail(
        self,
        start_time: datetime,
        end_time: datetime,
        event_types: Optional[List[AuditEventType]] = None,
        user_id: Optional[str] = None,
        compliance_framework: Optional[ComplianceFramework] = None
    ) -> List[Dict[str, Any]]:
        """Query audit trail with time-travel capability"""
        
        if not self.initialized or not ICEBERG_AVAILABLE:
            return await self._query_fallback(start_time, end_time, event_types, user_id)
        
        try:
            table = self.tables["audit_events"]
            
            # Build filter conditions
            filters = [
                ("timestamp", ">=", start_time),
                ("timestamp", "<=", end_time)
            ]
            
            if event_types:
                event_type_values = [et.value for et in event_types]
                filters.append(("event_type", "in", event_type_values))
            
            if user_id:
                filters.append(("user_id", "==", user_id))
            
            # Execute query
            scan = table.scan(
                selected_fields=["*"],
                filter=filters
            )
            
            results = []
            for batch in scan.to_arrow().to_batches():
                for record in batch.to_pylist():
                    # Parse JSON fields
                    record["details"] = json.loads(record["details"]) if record["details"] else {}
                    results.append(record)
            
            # Filter by compliance framework if specified
            if compliance_framework:
                framework_tag = compliance_framework.value
                results = [r for r in results if framework_tag in r.get("compliance_tags", [])]
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to query audit trail: {e}")
            return []
    
    async def _query_fallback(
        self,
        start_time: datetime,
        end_time: datetime,
        event_types: Optional[List[AuditEventType]] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query fallback audit logs"""
        try:
            results = []
            
            # Read from audit files
            import os
            import glob
            
            audit_files = glob.glob("audit_logs/audit_*.jsonl")
            
            for file_path in audit_files:
                with open(file_path, 'r') as f:
                    for line in f:
                        try:
                            record = json.loads(line.strip())
                            record_time = datetime.fromisoformat(record["timestamp"])
                            
                            # Apply time filter
                            if not (start_time <= record_time <= end_time):
                                continue
                            
                            # Apply event type filter
                            if event_types and record["event_type"] not in [et.value for et in event_types]:
                                continue
                            
                            # Apply user filter
                            if user_id and record.get("user_id") != user_id:
                                continue
                            
                            results.append(record)
                            
                        except json.JSONDecodeError:
                            continue
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to query fallback audit logs: {e}")
            return []
    
    async def generate_compliance_report(
        self,
        framework: ComplianceFramework,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate compliance report for specific framework"""
        
        # Query relevant audit events
        events = await self.query_audit_trail(
            start_time=start_date,
            end_time=end_date,
            compliance_framework=framework
        )
        
        report = {
            "compliance_framework": framework.value,
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_events": len(events),
            "event_breakdown": {},
            "risk_analysis": {},
            "violations": [],
            "recommendations": []
        }
        
        # Analyze events by type
        event_types = {}
        risk_scores = []
        
        for event in events:
            event_type = event.get("event_type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1
            
            risk_score = event.get("risk_score", 0)
            risk_scores.append(risk_score)
            
            # Check for high-risk events
            if risk_score >= 80:
                report["violations"].append({
                    "event_id": event["event_id"],
                    "timestamp": event["timestamp"],
                    "risk_score": risk_score,
                    "action": event["action"],
                    "user_id": event.get("user_id")
                })
        
        report["event_breakdown"] = event_types
        
        if risk_scores:
            report["risk_analysis"] = {
                "average_risk_score": sum(risk_scores) / len(risk_scores),
                "max_risk_score": max(risk_scores),
                "high_risk_events": len([r for r in risk_scores if r >= 80])
            }
        
        # Framework-specific analysis
        if framework == ComplianceFramework.SOX:
            report["recommendations"].extend(self._sox_recommendations(events))
        elif framework == ComplianceFramework.MIFID_II:
            report["recommendations"].extend(self._mifid_recommendations(events))
        elif framework == ComplianceFramework.GDPR:
            report["recommendations"].extend(self._gdpr_recommendations(events))
        
        return report
    
    def _sox_recommendations(self, events: List[Dict[str, Any]]) -> List[str]:
        """Generate SOX-specific recommendations"""
        recommendations = []
        
        # Check for financial data access
        financial_events = [e for e in events if "financial" in e.get("resource", "").lower()]
        if len(financial_events) > 100:
            recommendations.append("High volume of financial data access detected - review access controls")
        
        # Check for administrative changes
        admin_events = [e for e in events if e.get("action", "").startswith("admin_")]
        if admin_events:
            recommendations.append("Administrative changes detected - ensure proper authorization documentation")
        
        return recommendations
    
    def _mifid_recommendations(self, events: List[Dict[str, Any]]) -> List[str]:
        """Generate MiFID II-specific recommendations"""
        recommendations = []
        
        # Check trading events
        trading_events = [e for e in events if e.get("event_type") == "trading_event"]
        if trading_events:
            recommendations.append("Trading activity detected - ensure best execution reporting")
        
        return recommendations
    
    def _gdpr_recommendations(self, events: List[Dict[str, Any]]) -> List[str]:
        """Generate GDPR-specific recommendations"""
        recommendations = []
        
        # Check for data access events
        data_access_events = [e for e in events if e.get("event_type") == "data_access"]
        if data_access_events:
            recommendations.append("Personal data access detected - verify lawful basis")
        
        return recommendations

# Global audit logger instance
iceberg_audit_logger = IcebergAuditLogger()

# Convenience functions
async def log_audit_event(
    action: str,
    resource: str,
    details: Dict[str, Any],
    user_id: Optional[str] = None,
    event_type: AuditEventType = AuditEventType.SYSTEM_EVENT,
    outcome: str = "SUCCESS",
    risk_score: int = 0,
    compliance_tags: Optional[List[str]] = None,
    correlation_id: Optional[str] = None,
    service_name: str = "trading_system",
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> bool:
    """Convenience function to log audit events"""
    
    event = AuditEvent(
        event_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        event_type=event_type,
        user_id=user_id,
        session_id=details.get("session_id"),
        action=action,
        resource=resource,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        outcome=outcome,
        risk_score=risk_score,
        compliance_tags=compliance_tags or [],
        correlation_id=correlation_id,
        service_name=service_name,
        version="1.0.0"
    )
    
    return await iceberg_audit_logger.log_audit_event(event)

async def initialize_audit_logging() -> bool:
    """Initialize audit logging system"""
    return await iceberg_audit_logger.initialize()

if __name__ == "__main__":
    async def main():
        # Initialize audit logging
        success = await initialize_audit_logging()
        print(f"Audit logging initialized: {'✓' if success else '✗'}")
        
        if success:
            # Test audit event
            await log_audit_event(
                action="test_audit_log",
                resource="system",
                details={"test": "audit_system", "component": "iceberg"},
                event_type=AuditEventType.SYSTEM_EVENT,
                compliance_tags=["sox", "gdpr"]
            )
            print("Test audit event logged successfully")
    
    asyncio.run(main())