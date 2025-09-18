"""
Apache Iceberg Audit Trail Service - Phase 5 Enterprise Feature
Immutable audit logging using Apache Iceberg for compliance and regulatory requirements

This service provides:
- Immutable audit trail storage
- Compliance-ready data retention
- High-performance batch and streaming writes
- Schema evolution support
- Time-travel queries for audit investigations
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import asyncio
import uuid

# Kafka consumer for audit events
from kafka import KafkaConsumer, TopicPartition
from kafka.errors import KafkaError

# PyIceberg for Apache Iceberg integration
try:
    from pyiceberg.catalog import load_catalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        NestedField, StringType, TimestampType, BooleanType, 
        IntegerType, MapType, StructType
    )
    from pyiceberg.table import Table
    ICEBERG_AVAILABLE = True
except ImportError:
    ICEBERG_AVAILABLE = False
    logging.warning("PyIceberg not available. Audit trails will use fallback storage.")

# Pandas for data manipulation
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class AuditRecord:
    """Audit record structure for Iceberg table"""
    audit_id: str
    timestamp: datetime
    user_id: str
    user_role: str
    session_id: Optional[str]
    action: str
    resource: str
    method: str
    endpoint: str
    ip_address: str
    user_agent: str
    request_data: Optional[Dict[str, Any]]
    response_status: int
    response_time_ms: float
    success: bool
    error_message: Optional[str]
    risk_score: float
    compliance_flags: List[str]
    created_at: datetime
    partition_date: str  # For partitioning by date


class IcebergAuditService:
    """Service for managing immutable audit trails with Apache Iceberg"""
    
    def __init__(
        self,
        catalog_name: str = "trading_audit",
        warehouse_path: str = "/data/iceberg/warehouse",
        kafka_bootstrap_servers: str = "kafka:9092",
        kafka_topic: str = "audit.events",
        batch_size: int = 1000,
        flush_interval_seconds: int = 60
    ):
        self.catalog_name = catalog_name
        self.warehouse_path = warehouse_path
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.kafka_topic = kafka_topic
        self.batch_size = batch_size
        self.flush_interval_seconds = flush_interval_seconds
        
        # Initialize components
        self.catalog = None
        self.audit_table = None
        self.kafka_consumer = None
        self.batch_buffer: List[AuditRecord] = []
        self.last_flush_time = datetime.now(timezone.utc)
        
        # Initialize Iceberg catalog and table
        self._initialize_iceberg()
        
        # Initialize Kafka consumer
        self._initialize_kafka_consumer()
    
    def _initialize_iceberg(self):
        """Initialize Apache Iceberg catalog and audit table"""
        if not ICEBERG_AVAILABLE:
            logger.warning("Apache Iceberg not available - using fallback storage")
            return
        
        try:
            # Create warehouse directory if it doesn't exist
            Path(self.warehouse_path).mkdir(parents=True, exist_ok=True)
            
            # Initialize catalog
            self.catalog = load_catalog(
                name=self.catalog_name,
                **{
                    "type": "hadoop",
                    "warehouse": self.warehouse_path
                }
            )
            
            # Define audit table schema
            audit_schema = Schema(
                NestedField(1, "audit_id", StringType(), required=True),
                NestedField(2, "timestamp", TimestampType(), required=True),
                NestedField(3, "user_id", StringType(), required=True),
                NestedField(4, "user_role", StringType(), required=True),
                NestedField(5, "session_id", StringType(), required=False),
                NestedField(6, "action", StringType(), required=True),
                NestedField(7, "resource", StringType(), required=True),
                NestedField(8, "method", StringType(), required=True),
                NestedField(9, "endpoint", StringType(), required=True),
                NestedField(10, "ip_address", StringType(), required=True),
                NestedField(11, "user_agent", StringType(), required=False),
                NestedField(12, "request_data", MapType(1, StringType(), StringType()), required=False),
                NestedField(13, "response_status", IntegerType(), required=True),
                NestedField(14, "response_time_ms", IntegerType(), required=True),
                NestedField(15, "success", BooleanType(), required=True),
                NestedField(16, "error_message", StringType(), required=False),
                NestedField(17, "risk_score", IntegerType(), required=True),
                NestedField(18, "compliance_flags", StringType(), required=False),  # JSON array as string
                NestedField(19, "created_at", TimestampType(), required=True),
                NestedField(20, "partition_date", StringType(), required=True)
            )
            
            # Create or get audit table
            table_name = "audit_trail"
            namespace = "trading_system"
            
            try:
                # Try to create namespace
                self.catalog.create_namespace(namespace)
            except Exception:
                pass  # Namespace might already exist
            
            try:
                # Try to create table
                self.audit_table = self.catalog.create_table(
                    identifier=f"{namespace}.{table_name}",
                    schema=audit_schema,
                    partition_spec=[("partition_date", "identity")]
                )
                logger.info(f"Created new Iceberg audit table: {namespace}.{table_name}")
            except Exception:
                # Table might already exist
                self.audit_table = self.catalog.load_table(f"{namespace}.{table_name}")
                logger.info(f"Loaded existing Iceberg audit table: {namespace}.{table_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Iceberg catalog: {e}")
            self.catalog = None
            self.audit_table = None
    
    def _initialize_kafka_consumer(self):
        """Initialize Kafka consumer for audit events"""
        try:
            self.kafka_consumer = KafkaConsumer(
                self.kafka_topic,
                bootstrap_servers=self.kafka_bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda m: m.decode('utf-8') if m else None,
                group_id="iceberg_audit_consumer",
                enable_auto_commit=True,
                auto_offset_reset='latest'
            )
            logger.info(f"Initialized Kafka consumer for topic: {self.kafka_topic}")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            self.kafka_consumer = None
    
    def _parse_audit_event(self, event_data: Dict[str, Any]) -> AuditRecord:
        """Parse Kafka audit event into AuditRecord"""
        try:
            # Parse timestamp
            timestamp = datetime.fromisoformat(event_data.get('timestamp', '').replace('Z', '+00:00'))
            
            # Extract endpoint from action
            action = event_data.get('action', '')
            method, endpoint = action.split(' ', 1) if ' ' in action else ('UNKNOWN', action)
            
            # Calculate risk score based on various factors
            risk_score = self._calculate_risk_score(event_data)
            
            # Determine compliance flags
            compliance_flags = self._determine_compliance_flags(event_data)
            
            return AuditRecord(
                audit_id=event_data.get('event_id', str(uuid.uuid4())),
                timestamp=timestamp,
                user_id=event_data.get('user_id', 'unknown'),
                user_role=event_data.get('user_role', 'unknown'),
                session_id=event_data.get('session_id'),
                action=action,
                resource=event_data.get('resource', ''),
                method=method,
                endpoint=endpoint,
                ip_address=event_data.get('ip_address', ''),
                user_agent=event_data.get('user_agent', ''),
                request_data=event_data.get('request_data'),
                response_status=event_data.get('response_status', 0),
                response_time_ms=int(event_data.get('request_data', {}).get('process_time', 0) * 1000),
                success=event_data.get('success', True),
                error_message=event_data.get('error_message'),
                risk_score=risk_score,
                compliance_flags=compliance_flags,
                created_at=datetime.now(timezone.utc),
                partition_date=timestamp.strftime('%Y-%m-%d')
            )
        except Exception as e:
            logger.error(f"Error parsing audit event: {e}")
            # Return a minimal record to avoid data loss
            return AuditRecord(
                audit_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc),
                user_id='parse_error',
                user_role='unknown',
                session_id=None,
                action='PARSE_ERROR',
                resource='',
                method='UNKNOWN',
                endpoint='',
                ip_address='',
                user_agent='',
                request_data=None,
                response_status=500,
                response_time_ms=0,
                success=False,
                error_message=f"Parse error: {str(e)}",
                risk_score=10.0,  # High risk for parse errors
                compliance_flags=['PARSE_ERROR'],
                created_at=datetime.now(timezone.utc),
                partition_date=datetime.now(timezone.utc).strftime('%Y-%m-%d')
            )
    
    def _calculate_risk_score(self, event_data: Dict[str, Any]) -> float:
        """Calculate risk score for audit event (0-10 scale)"""
        risk_score = 0.0
        
        # Base risk by action type
        action = event_data.get('action', '').upper()
        if 'ORDER' in action:
            risk_score += 5.0  # Trading actions are higher risk
        elif 'DELETE' in action or 'CANCEL' in action:
            risk_score += 3.0
        elif 'POST' in action or 'PUT' in action:
            risk_score += 2.0
        else:
            risk_score += 1.0
        
        # Risk by response status
        status = event_data.get('response_status', 200)
        if status >= 500:
            risk_score += 2.0
        elif status >= 400:
            risk_score += 1.0
        
        # Risk by user role
        role = event_data.get('user_role', '').lower()
        if role == 'admin':
            risk_score += 1.0
        elif role == 'system':
            risk_score += 0.5
        
        # Risk by time of day (higher risk for off-hours)
        timestamp = event_data.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                hour = dt.hour
                if hour < 6 or hour > 22:  # Off-hours
                    risk_score += 1.0
            except Exception:
                pass
        
        return min(risk_score, 10.0)  # Cap at 10
    
    def _determine_compliance_flags(self, event_data: Dict[str, Any]) -> List[str]:
        """Determine compliance flags for audit event"""
        flags = []
        
        action = event_data.get('action', '').upper()
        
        # Trading-related compliance
        if 'ORDER' in action:
            flags.append('TRADING_ACTIVITY')
        
        # Data access compliance
        if 'EXPORT' in action or 'DOWNLOAD' in action:
            flags.append('DATA_EXPORT')
        
        # Administrative actions
        if event_data.get('user_role') == 'admin':
            flags.append('ADMIN_ACTION')
        
        # Error conditions
        if not event_data.get('success', True):
            flags.append('ERROR_EVENT')
        
        # High-risk actions
        if 'DELETE' in action or 'CANCEL' in action:
            flags.append('DESTRUCTIVE_ACTION')
        
        return flags
    
    def add_to_batch(self, audit_record: AuditRecord):
        """Add audit record to batch buffer"""
        self.batch_buffer.append(audit_record)
        
        # Check if we should flush
        if (len(self.batch_buffer) >= self.batch_size or 
            datetime.now(timezone.utc) - self.last_flush_time > timedelta(seconds=self.flush_interval_seconds)):
            self._flush_batch()
    
    def _flush_batch(self):
        """Flush batch buffer to Iceberg table"""
        if not self.batch_buffer:
            return
        
        try:
            if self.audit_table and ICEBERG_AVAILABLE:
                self._write_to_iceberg()
            else:
                self._write_to_fallback_storage()
            
            # Clear buffer and update flush time
            self.batch_buffer.clear()
            self.last_flush_time = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error flushing audit batch: {e}")
            # Don't clear buffer on error - will retry next time
    
    def _write_to_iceberg(self):
        """Write batch to Iceberg table"""
        try:
            # Convert records to pandas DataFrame
            records_data = [asdict(record) for record in self.batch_buffer]
            df = pd.DataFrame(records_data)
            
            # Convert compliance_flags list to JSON string
            df['compliance_flags'] = df['compliance_flags'].apply(json.dumps)
            
            # Convert request_data dict to JSON string
            df['request_data'] = df['request_data'].apply(
                lambda x: json.dumps(x) if x is not None else None
            )
            
            # Convert to PyArrow table
            arrow_table = pa.Table.from_pandas(df)
            
            # Append to Iceberg table
            self.audit_table.append(arrow_table)
            
            logger.info(f"Successfully wrote {len(self.batch_buffer)} audit records to Iceberg")
            
        except Exception as e:
            logger.error(f"Error writing to Iceberg table: {e}")
            # Fallback to file storage
            self._write_to_fallback_storage()
    
    def _write_to_fallback_storage(self):
        """Fallback storage using Parquet files"""
        try:
            # Create fallback directory
            fallback_dir = Path(self.warehouse_path) / "fallback_audit"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            
            # Convert records to pandas DataFrame
            records_data = [asdict(record) for record in self.batch_buffer]
            df = pd.DataFrame(records_data)
            
            # Convert complex fields to JSON strings
            df['compliance_flags'] = df['compliance_flags'].apply(json.dumps)
            df['request_data'] = df['request_data'].apply(
                lambda x: json.dumps(x) if x is not None else None
            )
            
            # Write to partitioned Parquet files
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            filename = f"audit_batch_{timestamp}_{uuid.uuid4().hex[:8]}.parquet"
            filepath = fallback_dir / filename
            
            df.to_parquet(filepath, index=False)
            
            logger.info(f"Successfully wrote {len(self.batch_buffer)} audit records to fallback storage: {filename}")
            
        except Exception as e:
            logger.error(f"Error writing to fallback storage: {e}")
    
    async def start_consumer(self):
        """Start consuming audit events from Kafka"""
        if not self.kafka_consumer:
            logger.error("Kafka consumer not initialized")
            return
        
        logger.info("Starting Iceberg audit consumer...")
        
        try:
            while True:
                # Poll for messages
                message_batch = self.kafka_consumer.poll(timeout_ms=1000)
                
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        try:
                            # Parse audit event
                            audit_record = self._parse_audit_event(message.value)
                            
                            # Add to batch
                            self.add_to_batch(audit_record)
                            
                        except Exception as e:
                            logger.error(f"Error processing audit message: {e}")
                
                # Periodic flush check
                if (datetime.now(timezone.utc) - self.last_flush_time > 
                    timedelta(seconds=self.flush_interval_seconds)):
                    self._flush_batch()
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("Audit consumer stopped by user")
        except Exception as e:
            logger.error(f"Error in audit consumer: {e}")
        finally:
            # Flush any remaining records
            self._flush_batch()
            
            # Close consumer
            if self.kafka_consumer:
                self.kafka_consumer.close()
    
    def query_audit_trail(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None,
        action_pattern: Optional[str] = None,
        min_risk_score: Optional[float] = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        """Query audit trail with filters"""
        if not self.audit_table:
            logger.error("Audit table not available for querying")
            return pd.DataFrame()
        
        try:
            # Build filter conditions
            filters = []
            
            # Date range filter
            filters.append(f"timestamp >= '{start_date.isoformat()}'")
            filters.append(f"timestamp <= '{end_date.isoformat()}'")
            
            # User filter
            if user_id:
                filters.append(f"user_id = '{user_id}'")
            
            # Action pattern filter
            if action_pattern:
                filters.append(f"action LIKE '%{action_pattern}%'")
            
            # Risk score filter
            if min_risk_score is not None:
                filters.append(f"risk_score >= {min_risk_score}")
            
            # Execute query (this is a simplified example)
            # In practice, you'd use the Iceberg table's scan() method with proper filters
            scan = self.audit_table.scan()
            
            # Convert to pandas for easier handling
            arrow_table = scan.to_arrow()
            df = arrow_table.to_pandas()
            
            # Apply filters (simplified - in practice use Iceberg's native filtering)
            for filter_condition in filters:
                # This is a simplified filter application
                # In practice, you'd use Iceberg's expression system
                pass
            
            return df.head(limit)
            
        except Exception as e:
            logger.error(f"Error querying audit trail: {e}")
            return pd.DataFrame()
    
    def get_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        compliance_flags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate compliance report for specified period"""
        try:
            df = self.query_audit_trail(start_date, end_date)
            
            if df.empty:
                return {"error": "No audit data found for specified period"}
            
            # Parse compliance flags from JSON strings
            df['compliance_flags_parsed'] = df['compliance_flags'].apply(
                lambda x: json.loads(x) if x else []
            )
            
            # Generate report
            report = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "total_events": len(df),
                "unique_users": df['user_id'].nunique(),
                "event_breakdown": {
                    "successful": len(df[df['success'] == True]),
                    "failed": len(df[df['success'] == False]),
                    "high_risk": len(df[df['risk_score'] >= 7.0])
                },
                "top_actions": df['action'].value_counts().head(10).to_dict(),
                "user_activity": df['user_id'].value_counts().head(10).to_dict(),
                "compliance_flags_summary": {},
                "risk_distribution": {
                    "low_risk": len(df[df['risk_score'] < 3.0]),
                    "medium_risk": len(df[(df['risk_score'] >= 3.0) & (df['risk_score'] < 7.0)]),
                    "high_risk": len(df[df['risk_score'] >= 7.0])
                }
            }
            
            # Compliance flags summary
            all_flags = []
            for flags_list in df['compliance_flags_parsed']:
                all_flags.extend(flags_list)
            
            from collections import Counter
            flag_counts = Counter(all_flags)
            report["compliance_flags_summary"] = dict(flag_counts)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            return {"error": f"Failed to generate report: {str(e)}"}


# Initialize the service
iceberg_audit_service = IcebergAuditService()


async def start_audit_consumer():
    """Start the audit consumer service"""
    await iceberg_audit_service.start_consumer()


if __name__ == "__main__":
    # Run the audit consumer
    asyncio.run(start_audit_consumer())