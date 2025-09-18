"""
InfluxDB Integration for Metrics Collection and Real-time Analytics
Implements time-series database for metrics collection and real-time analytics processing

This module provides:
- InfluxDB client for time-series metrics
- Real-time analytics processing
- Performance monitoring and alerting
- Connection management and fallback mechanisms

Author: Vincent S. Pereira
Version: 1.0.0
Phase: 1 - Core System Validation & Hardening
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
import json
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

# InfluxDB client
try:
    from influxdb_client import InfluxDBClient, Point, WriteOptions
    from influxdb_client.client.write_api import ASYNCHRONOUS
    from influxdb_client.client.query_api import QueryApi
    INFLUXDB_AVAILABLE = True
except ImportError:
    INFLUXDB_AVAILABLE = False
    logging.warning("InfluxDB client not available. Install with: pip install influxdb-client")

logger = logging.getLogger(__name__)

@dataclass
class InfluxDBConfig:
    """InfluxDB configuration"""
    url: str = "http://localhost:8086"
    token: str = "influxdb_token_2024"
    org: str = "trading_org"
    bucket: str = "trading_metrics"
    timeout: int = 30
    verify_ssl: bool = True

@dataclass
class MetricPoint:
    """Structured metric point for InfluxDB storage"""
    measurement: str
    tags: Dict[str, str]
    fields: Dict[str, Any]
    timestamp: Optional[datetime] = None

@dataclass
class AnalyticsQuery:
    """Analytics query for real-time processing"""
    query: str
    params: Dict[str, Any] = None
    dashboard_name: str = "default"

class InfluxDBManager:
    """
    InfluxDB manager for metrics collection and real-time analytics
    """
    
    def __init__(self, config: Optional[InfluxDBConfig] = None):
        self.config = config or self._default_config()
        self.client = None
        self.write_api = None
        self.query_api = None
        self.initialized = False
        self.logger = logging.getLogger(__name__)
        
        if not INFLUXDB_AVAILABLE:
            self.logger.error("InfluxDB client not available. Metrics collection will be limited.")
    
    def _default_config(self) -> InfluxDBConfig:
        """Default InfluxDB configuration"""
        return InfluxDBConfig(
            url=os.getenv("INFLUXDB_URL", "http://localhost:8086"),
            token=os.getenv("INFLUXDB_TOKEN", "influxdb_token_2024"),
            org=os.getenv("INFLUXDB_ORG", "trading_org"),
            bucket=os.getenv("INFLUXDB_BUCKET", "trading_metrics"),
            timeout=int(os.getenv("INFLUXDB_TIMEOUT", "30")),
            verify_ssl=os.getenv("INFLUXDB_VERIFY_SSL", "true").lower() == "true"
        )
    
    async def initialize(self) -> bool:
        """Initialize InfluxDB client"""
        if not INFLUXDB_AVAILABLE:
            self.logger.warning("InfluxDB not available - using fallback storage")
            return await self._initialize_fallback()
        
        try:
            # Create InfluxDB client
            self.client = InfluxDBClient(
                url=self.config.url,
                token=self.config.token,
                org=self.config.org,
                timeout=self.config.timeout * 1000,  # Convert to milliseconds
                verify_ssl=self.config.verify_ssl
            )
            
            # Test connection
            health = self.client.health()
            if not health.status == "pass":
                raise Exception(f"InfluxDB health check failed: {health.message}")
            
            # Create APIs
            self.write_api = self.client.write_api(write_options=ASYNCHRONOUS)
            self.query_api = self.client.query_api()
            
            # Create bucket if not exists
            await self._create_bucket()
            
            self.initialized = True
            self.logger.info("InfluxDB initialized successfully for metrics collection")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize InfluxDB: {e}")
            return await self._initialize_fallback()
    
    async def _initialize_fallback(self) -> bool:
        """Initialize fallback storage without InfluxDB"""
        try:
            # Use file-based storage as fallback
            import os
            import json
            storage_dir = "influxdb_storage"
            os.makedirs(storage_dir, exist_ok=True)
            
            self.storage_path = os.path.join(storage_dir, f"{self.config.bucket}.json")
            
            # Load existing data if available
            if os.path.exists(self.storage_path):
                try:
                    with open(self.storage_path, "r") as f:
                        content = f.read().strip()
                        if content:
                            self.fallback_data = json.loads(content)
                        else:
                            self.fallback_data = {}
                except (json.JSONDecodeError, FileNotFoundError):
                    # If file is corrupted or doesn't exist, start with empty data
                    self.fallback_data = {}
            else:
                self.fallback_data = {}
            
            self.initialized = True
            self.logger.info("Fallback InfluxDB storage initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize fallback InfluxDB storage: {e}")
            return False
    
    async def _create_bucket(self):
        """Create bucket if not exists"""
        try:
            buckets_api = self.client.buckets_api()
            org_api = self.client.organizations_api()
            
            # Get organization
            org = org_api.find_organizations(org=self.config.org)
            if not org:
                # Create organization if not exists
                org = org_api.create_organization(org=self.config.org)
            else:
                org = org[0]
            
            # Check if bucket exists
            bucket = buckets_api.find_bucket_by_name(bucket_name=self.config.bucket)
            if not bucket:
                # Create bucket
                from influxdb_client.domain.bucket import Bucket
                bucket = Bucket(
                    name=self.config.bucket,
                    org_id=org.id,
                    retention_rules=[]
                )
                buckets_api.create_bucket(bucket)
                self.logger.info(f"Created InfluxDB bucket: {self.config.bucket}")
            else:
                self.logger.info(f"InfluxDB bucket already exists: {self.config.bucket}")
        except Exception as e:
            self.logger.warning(f"Could not create InfluxDB bucket: {e}")
    
    async def write_metric(self, metric_point: MetricPoint) -> bool:
        """Write a metric point to InfluxDB"""
        try:
            if not self.initialized:
                return False
            
            if self.client and self.write_api:
                # Write to InfluxDB
                point = Point(metric_point.measurement)
                
                # Add tags
                for tag_key, tag_value in metric_point.tags.items():
                    point.tag(tag_key, tag_value)
                
                # Add fields
                for field_key, field_value in metric_point.fields.items():
                    point.field(field_key, field_value)
                
                # Add timestamp
                if metric_point.timestamp:
                    point.time(metric_point.timestamp)
                
                # Write point
                self.write_api.write(bucket=self.config.bucket, org=self.config.org, record=point)
            else:
                # Fallback to file storage
                measurement_data = {
                    "measurement": metric_point.measurement,
                    "tags": metric_point.tags,
                    "fields": metric_point.fields,
                    "timestamp": metric_point.timestamp.isoformat() if metric_point.timestamp else datetime.now(timezone.utc).isoformat()
                }
                
                if self.config.bucket not in self.fallback_data:
                    self.fallback_data[self.config.bucket] = []
                
                self.fallback_data[self.config.bucket].append(measurement_data)
                
                # Save to file
                with open(self.storage_path, "w") as f:
                    json.dump(self.fallback_data, f, default=str)
                
                self.logger.info(f"Fallback wrote metric point to {metric_point.measurement}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to write metric point: {e}")
            return False
    
    async def write_metrics_batch(self, metric_points: List[MetricPoint]) -> bool:
        """Write a batch of metric points to InfluxDB"""
        try:
            if not self.initialized:
                return False
            
            if self.client and self.write_api:
                # Write batch to InfluxDB
                points = []
                for metric_point in metric_points:
                    point = Point(metric_point.measurement)
                    
                    # Add tags
                    for tag_key, tag_value in metric_point.tags.items():
                        point.tag(tag_key, tag_value)
                    
                    # Add fields
                    for field_key, field_value in metric_point.fields.items():
                        point.field(field_key, field_value)
                    
                    # Add timestamp
                    if metric_point.timestamp:
                        point.time(metric_point.timestamp)
                    
                    points.append(point)
                
                # Write points
                self.write_api.write(bucket=self.config.bucket, org=self.config.org, record=points)
            else:
                # Fallback to file storage
                if self.config.bucket not in self.fallback_data:
                    self.fallback_data[self.config.bucket] = []
                
                for metric_point in metric_points:
                    measurement_data = {
                        "measurement": metric_point.measurement,
                        "tags": metric_point.tags,
                        "fields": metric_point.fields,
                        "timestamp": metric_point.timestamp.isoformat() if metric_point.timestamp else datetime.now(timezone.utc).isoformat()
                    }
                    self.fallback_data[self.config.bucket].append(measurement_data)
                
                # Save to file
                with open(self.storage_path, "w") as f:
                    json.dump(self.fallback_data, f, default=str)
                
                self.logger.info(f"Fallback wrote batch of {len(metric_points)} metric points")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to write metric points batch: {e}")
            return False
    
    async def query_metrics(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """Query metrics from InfluxDB"""
        try:
            if not self.initialized:
                return []
            
            results = []
            if self.client and self.query_api:
                # Query from InfluxDB
                query_api = self.client.query_api()
                tables = query_api.query(query=query, params=params or {})
                
                for table in tables:
                    for record in table.records:
                        results.append({
                            "measurement": record.get_measurement(),
                            "time": record.get_time(),
                            "fields": record.values,
                            "tags": {k: v for k, v in record.values.items() if k not in ['result', 'table', '_time', '_value', '_field', '_measurement']}
                        })
            else:
                # Fallback to file storage
                if self.config.bucket in self.fallback_data:
                    # Simple filter based on measurement name in query
                    # This is a simplified implementation for fallback
                    for record in self.fallback_data[self.config.bucket]:
                        if record["measurement"] in query:
                            results.append(record)
            
            return results
        except Exception as e:
            self.logger.error(f"Failed to query metrics: {e}")
            return []
    
    async def get_real_time_analytics(self, analytics_query: AnalyticsQuery) -> List[Dict]:
        """Get real-time analytics from InfluxDB"""
        try:
            if not self.initialized:
                return []
            
            results = []
            if self.client and self.query_api:
                # Execute analytics query
                tables = self.query_api.query(
                    query=analytics_query.query, 
                    params=analytics_query.params or {}
                )
                
                for table in tables:
                    for record in table.records:
                        result_data = {
                            "time": record.get_time(),
                            "values": record.values
                        }
                        results.append(result_data)
            else:
                # Fallback returns empty results for analytics queries
                self.logger.warning("Analytics queries not supported in fallback mode")
            
            return results
        except Exception as e:
            self.logger.error(f"Failed to get real-time analytics: {e}")
            return []
    
    async def close(self):
        """Close InfluxDB connection"""
        if self.write_api:
            self.write_api.close()
        if self.client:
            self.client.close()
        self.logger.info("InfluxDB connection closed")


# Global InfluxDB manager instance
influxdb_manager = InfluxDBManager()

# Convenience functions
async def init_influxdb(config: Optional[InfluxDBConfig] = None) -> bool:
    """Initialize InfluxDB - convenience function"""
    if config:
        influxdb_manager.config = config
    return await influxdb_manager.initialize()

async def write_metric(metric_point: MetricPoint) -> bool:
    """Write a metric point - convenience function"""
    return await influxdb_manager.write_metric(metric_point)

async def write_metrics_batch(metric_points: List[MetricPoint]) -> bool:
    """Write a batch of metric points - convenience function"""
    return await influxdb_manager.write_metrics_batch(metric_points)

async def query_metrics(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict]:
    """Query metrics - convenience function"""
    return await influxdb_manager.query_metrics(query, params)

async def get_real_time_analytics(analytics_query: AnalyticsQuery) -> List[Dict]:
    """Get real-time analytics - convenience function"""
    return await influxdb_manager.get_real_time_analytics(analytics_query)

if __name__ == "__main__":
    async def main():
        # Initialize InfluxDB
        success = await init_influxdb()
        print(f"InfluxDB initialization: {'✓' if success else '✗'}")
        
        if success:
            # Test metric writing
            metric = MetricPoint(
                measurement="cpu_usage",
                tags={"host": "trading-server-1", "service": "nautilus-engine"},
                fields={"value": 75.5, "core_count": 8},
                timestamp=datetime.now()
            )
            write_success = await write_metric(metric)
            print(f"Metric writing: {'✓' if write_success else '✗'}")
            
            # Test batch writing
            batch_metrics = [
                MetricPoint(
                    measurement="memory_usage",
                    tags={"host": "trading-server-1", "service": "nautilus-engine"},
                    fields={"value": 65.2, "total_gb": 32},
                    timestamp=datetime.now()
                ),
                MetricPoint(
                    measurement="disk_io",
                    tags={"host": "trading-server-1", "service": "nautilus-engine"},
                    fields={"read_mb": 120.5, "write_mb": 85.3},
                    timestamp=datetime.now()
                )
            ]
            batch_success = await write_metrics_batch(batch_metrics)
            print(f"Batch metric writing: {'✓' if batch_success else '✗'}")
            
            # Close connection
            await influxdb_manager.close()
    
    asyncio.run(main())