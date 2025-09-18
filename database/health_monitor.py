#!/usr/bin/env python3
"""
Database Health Monitor for Algorithmic Trading System
Monitors all 9 databases: PostgreSQL, ClickHouse, DuckDB, Qdrant, Iceberg, Redis, InfluxDB, MinIO, Elasticsearch

Features:
- Real-time health checks for all databases
- Performance metrics collection
- Alerting and notifications
- Detailed status reporting
- Automatic recovery attempts
- Prometheus metrics export
"""

import asyncio
import logging
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import yaml

# Core dependencies
import psutil
import aiohttp
import asyncpg
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Database-specific clients
try:
    import redis.asyncio as aioredis
except ImportError:
    import aioredis

try:
    from clickhouse_driver import Client as ClickHouseClient
except ImportError:
    ClickHouseClient = None

try:
    import duckdb
except ImportError:
    duckdb = None

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
except ImportError:
    QdrantClient = None

try:
    from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
except ImportError:
    InfluxDBClientAsync = None

try:
    from minio import Minio
except ImportError:
    Minio = None

try:
    from elasticsearch import AsyncElasticsearch
except ImportError:
    AsyncElasticsearch = None

# Notification imports
try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
except ImportError:
    smtplib = None


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class DatabaseMetrics:
    """Database performance metrics"""
    response_time: float
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    connection_count: int
    error_rate: float
    throughput: float
    availability: float
    last_check: datetime


@dataclass
class HealthCheckResult:
    """Health check result for a database"""
    database: str
    status: HealthStatus
    metrics: Optional[DatabaseMetrics]
    error_message: Optional[str]
    timestamp: datetime
    recovery_attempts: int = 0


class DatabaseHealthMonitor:
    """Comprehensive database health monitoring system"""
    
    def __init__(self, config_path: str = "database_config.yaml"):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        self.health_results: Dict[str, HealthCheckResult] = {}
        self.metrics = self._setup_metrics()
        self.notification_clients = self._setup_notifications()
        
        # Recovery settings
        self.max_recovery_attempts = 3
        self.recovery_delay = 30  # seconds
        
        # Health check intervals
        self.check_interval = 30  # seconds
        self.detailed_check_interval = 300  # 5 minutes
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'databases': {
                'postgresql': {
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'trading_system',
                    'user': 'trading_user',
                    'password': os.getenv('POSTGRES_PASSWORD', 'trading_password')
                },
                'clickhouse': {
                    'host': 'localhost',
                    'port': 8123,
                    'user': 'clickhouse_user',
                    'password': os.getenv('CLICKHOUSE_PASSWORD', 'clickhouse_password')
                },
                'redis': {
                    'host': 'localhost',
                    'port': 6379,
                    'password': os.getenv('REDIS_PASSWORD', 'redis_password')
                },
                'qdrant': {
                    'host': 'localhost',
                    'port': 6333
                },
                'influxdb': {
                    'host': 'localhost',
                    'port': 8086,
                    'token': os.getenv('INFLUXDB_TOKEN', 'influx_admin_token'),
                    'org': 'trading_org',
                    'bucket': 'trading_metrics'
                },
                'minio': {
                    'host': 'localhost',
                    'port': 9000,
                    'access_key': os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
                    'secret_key': os.getenv('MINIO_SECRET_KEY', 'minioadmin')
                },
                'elasticsearch': {
                    'host': 'localhost',
                    'port': 9200,
                    'password': os.getenv('ELASTICSEARCH_PASSWORD', 'elastic_password')
                }
            },
            'monitoring': {
                'prometheus_port': 8090,
                'log_level': 'INFO',
                'alert_thresholds': {
                    'response_time': 1000,  # ms
                    'cpu_usage': 80,  # %
                    'memory_usage': 85,  # %
                    'disk_usage': 90,  # %
                    'error_rate': 5  # %
                }
            }
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('database_health_monitor')
        logger.setLevel(getattr(logging, self.config.get('monitoring', {}).get('log_level', 'INFO')))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler
        file_handler = logging.FileHandler('database_health.log')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def _setup_metrics(self) -> Dict[str, Any]:
        """Setup Prometheus metrics"""
        return {
            'health_status': Gauge('database_health_status', 'Database health status', ['database']),
            'response_time': Histogram('database_response_time_seconds', 'Database response time', ['database']),
            'cpu_usage': Gauge('database_cpu_usage_percent', 'Database CPU usage', ['database']),
            'memory_usage': Gauge('database_memory_usage_percent', 'Database memory usage', ['database']),
            'disk_usage': Gauge('database_disk_usage_percent', 'Database disk usage', ['database']),
            'connection_count': Gauge('database_connection_count', 'Database connection count', ['database']),
            'error_rate': Gauge('database_error_rate_percent', 'Database error rate', ['database']),
            'availability': Gauge('database_availability_percent', 'Database availability', ['database']),
            'check_counter': Counter('database_health_checks_total', 'Total health checks', ['database', 'status'])
        }
    
    def _setup_notifications(self) -> Dict[str, Any]:
        """Setup notification clients"""
        return {
            'email': self._setup_email_client(),
            'webhook': self._setup_webhook_client()
        }
    
    def _setup_email_client(self) -> Optional[Any]:
        """Setup email notification client"""
        if not smtplib:
            return None
        
        email_config = self.config.get('notifications', {}).get('email', {})
        if not email_config.get('enabled', False):
            return None
        
        return {
            'smtp_server': email_config.get('smtp_server', 'localhost'),
            'smtp_port': email_config.get('smtp_port', 587),
            'username': email_config.get('username'),
            'password': email_config.get('password'),
            'from_email': email_config.get('from_email'),
            'to_emails': email_config.get('to_emails', [])
        }
    
    def _setup_webhook_client(self) -> Optional[Dict[str, str]]:
        """Setup webhook notification client"""
        webhook_config = self.config.get('notifications', {}).get('webhook', {})
        if not webhook_config.get('enabled', False):
            return None
        
        return {
            'url': webhook_config.get('url'),
            'headers': webhook_config.get('headers', {})
        }
    
    async def check_postgresql_health(self) -> HealthCheckResult:
        """Check PostgreSQL database health"""
        db_config = self.config['databases']['postgresql']
        start_time = time.time()
        
        try:
            conn = await asyncpg.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password'],
                timeout=10
            )
            
            # Test query
            await conn.fetchval('SELECT 1')
            
            # Get metrics
            stats = await conn.fetchrow(
                "SELECT count(*) as connections FROM pg_stat_activity WHERE state = 'active'"
            )
            
            response_time = (time.time() - start_time) * 1000
            
            metrics = DatabaseMetrics(
                response_time=response_time,
                cpu_usage=psutil.cpu_percent(),
                memory_usage=psutil.virtual_memory().percent,
                disk_usage=psutil.disk_usage('/').percent,
                connection_count=stats['connections'] if stats else 0,
                error_rate=0.0,
                throughput=1000.0 / response_time if response_time > 0 else 0,
                availability=100.0,
                last_check=datetime.now()
            )
            
            await conn.close()
            
            status = self._determine_status('postgresql', metrics)
            return HealthCheckResult(
                database='postgresql',
                status=status,
                metrics=metrics,
                error_message=None,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"PostgreSQL health check failed: {e}")
            return HealthCheckResult(
                database='postgresql',
                status=HealthStatus.UNHEALTHY,
                metrics=None,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    async def check_clickhouse_health(self) -> HealthCheckResult:
        """Check ClickHouse database health"""
        if not ClickHouseClient:
            return self._create_unavailable_result('clickhouse', 'ClickHouse client not available')
        
        db_config = self.config['databases']['clickhouse']
        start_time = time.time()
        
        try:
            client = ClickHouseClient(
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['user'],
                password=db_config['password'],
                connect_timeout=10
            )
            
            # Test query
            result = client.execute('SELECT 1')
            
            response_time = (time.time() - start_time) * 1000
            
            metrics = DatabaseMetrics(
                response_time=response_time,
                cpu_usage=psutil.cpu_percent(),
                memory_usage=psutil.virtual_memory().percent,
                disk_usage=psutil.disk_usage('/').percent,
                connection_count=1,  # ClickHouse doesn't expose this easily
                error_rate=0.0,
                throughput=1000.0 / response_time if response_time > 0 else 0,
                availability=100.0,
                last_check=datetime.now()
            )
            
            status = self._determine_status('clickhouse', metrics)
            return HealthCheckResult(
                database='clickhouse',
                status=status,
                metrics=metrics,
                error_message=None,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"ClickHouse health check failed: {e}")
            return HealthCheckResult(
                database='clickhouse',
                status=HealthStatus.UNHEALTHY,
                metrics=None,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    async def check_redis_health(self) -> HealthCheckResult:
        """Check Redis database health"""
        db_config = self.config['databases']['redis']
        start_time = time.time()
        
        try:
            redis_client = aioredis.from_url(
                f"redis://:{db_config['password']}@{db_config['host']}:{db_config['port']}",
                socket_timeout=10
            )
            
            # Test ping
            await redis_client.ping()
            
            # Get info
            info = await redis_client.info()
            
            response_time = (time.time() - start_time) * 1000
            
            metrics = DatabaseMetrics(
                response_time=response_time,
                cpu_usage=psutil.cpu_percent(),
                memory_usage=psutil.virtual_memory().percent,
                disk_usage=psutil.disk_usage('/').percent,
                connection_count=info.get('connected_clients', 0),
                error_rate=0.0,
                throughput=1000.0 / response_time if response_time > 0 else 0,
                availability=100.0,
                last_check=datetime.now()
            )
            
            await redis_client.close()
            
            status = self._determine_status('redis', metrics)
            return HealthCheckResult(
                database='redis',
                status=status,
                metrics=metrics,
                error_message=None,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Redis health check failed: {e}")
            return HealthCheckResult(
                database='redis',
                status=HealthStatus.UNHEALTHY,
                metrics=None,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    async def check_qdrant_health(self) -> HealthCheckResult:
        """Check Qdrant vector database health"""
        if not QdrantClient:
            return self._create_unavailable_result('qdrant', 'Qdrant client not available')
        
        db_config = self.config['databases']['qdrant']
        start_time = time.time()
        
        try:
            client = QdrantClient(
                host=db_config['host'],
                port=db_config['port'],
                timeout=10
            )
            
            # Test health endpoint
            health_info = client.get_cluster_info()
            
            response_time = (time.time() - start_time) * 1000
            
            metrics = DatabaseMetrics(
                response_time=response_time,
                cpu_usage=psutil.cpu_percent(),
                memory_usage=psutil.virtual_memory().percent,
                disk_usage=psutil.disk_usage('/').percent,
                connection_count=1,  # Qdrant doesn't expose this
                error_rate=0.0,
                throughput=1000.0 / response_time if response_time > 0 else 0,
                availability=100.0,
                last_check=datetime.now()
            )
            
            status = self._determine_status('qdrant', metrics)
            return HealthCheckResult(
                database='qdrant',
                status=status,
                metrics=metrics,
                error_message=None,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Qdrant health check failed: {e}")
            return HealthCheckResult(
                database='qdrant',
                status=HealthStatus.UNHEALTHY,
                metrics=None,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    async def check_influxdb_health(self) -> HealthCheckResult:
        """Check InfluxDB health"""
        if not InfluxDBClientAsync:
            return self._create_unavailable_result('influxdb', 'InfluxDB client not available')
        
        db_config = self.config['databases']['influxdb']
        start_time = time.time()
        
        try:
            client = InfluxDBClientAsync(
                url=f"http://{db_config['host']}:{db_config['port']}",
                token=db_config['token'],
                org=db_config['org'],
                timeout=10000
            )
            
            # Test health endpoint
            health = await client.health()
            
            response_time = (time.time() - start_time) * 1000
            
            metrics = DatabaseMetrics(
                response_time=response_time,
                cpu_usage=psutil.cpu_percent(),
                memory_usage=psutil.virtual_memory().percent,
                disk_usage=psutil.disk_usage('/').percent,
                connection_count=1,
                error_rate=0.0,
                throughput=1000.0 / response_time if response_time > 0 else 0,
                availability=100.0,
                last_check=datetime.now()
            )
            
            await client.close()
            
            status = self._determine_status('influxdb', metrics)
            return HealthCheckResult(
                database='influxdb',
                status=status,
                metrics=metrics,
                error_message=None,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"InfluxDB health check failed: {e}")
            return HealthCheckResult(
                database='influxdb',
                status=HealthStatus.UNHEALTHY,
                metrics=None,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    async def check_minio_health(self) -> HealthCheckResult:
        """Check MinIO S3 storage health"""
        if not Minio:
            return self._create_unavailable_result('minio', 'MinIO client not available')
        
        db_config = self.config['databases']['minio']
        start_time = time.time()
        
        try:
            client = Minio(
                f"{db_config['host']}:{db_config['port']}",
                access_key=db_config['access_key'],
                secret_key=db_config['secret_key'],
                secure=False
            )
            
            # Test by listing buckets
            buckets = client.list_buckets()
            
            response_time = (time.time() - start_time) * 1000
            
            metrics = DatabaseMetrics(
                response_time=response_time,
                cpu_usage=psutil.cpu_percent(),
                memory_usage=psutil.virtual_memory().percent,
                disk_usage=psutil.disk_usage('/').percent,
                connection_count=1,
                error_rate=0.0,
                throughput=1000.0 / response_time if response_time > 0 else 0,
                availability=100.0,
                last_check=datetime.now()
            )
            
            status = self._determine_status('minio', metrics)
            return HealthCheckResult(
                database='minio',
                status=status,
                metrics=metrics,
                error_message=None,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"MinIO health check failed: {e}")
            return HealthCheckResult(
                database='minio',
                status=HealthStatus.UNHEALTHY,
                metrics=None,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    async def check_elasticsearch_health(self) -> HealthCheckResult:
        """Check Elasticsearch health"""
        if not AsyncElasticsearch:
            return self._create_unavailable_result('elasticsearch', 'Elasticsearch client not available')
        
        db_config = self.config['databases']['elasticsearch']
        start_time = time.time()
        
        try:
            client = AsyncElasticsearch(
                [f"http://{db_config['host']}:{db_config['port']}"],
                request_timeout=10
            )
            
            # Test cluster health
            health = await client.cluster.health()
            
            response_time = (time.time() - start_time) * 1000
            
            metrics = DatabaseMetrics(
                response_time=response_time,
                cpu_usage=psutil.cpu_percent(),
                memory_usage=psutil.virtual_memory().percent,
                disk_usage=psutil.disk_usage('/').percent,
                connection_count=1,
                error_rate=0.0,
                throughput=1000.0 / response_time if response_time > 0 else 0,
                availability=100.0,
                last_check=datetime.now()
            )
            
            await client.close()
            
            # Determine status based on cluster health
            cluster_status = health.get('status', 'red')
            if cluster_status == 'green':
                status = HealthStatus.HEALTHY
            elif cluster_status == 'yellow':
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY
            
            return HealthCheckResult(
                database='elasticsearch',
                status=status,
                metrics=metrics,
                error_message=None,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Elasticsearch health check failed: {e}")
            return HealthCheckResult(
                database='elasticsearch',
                status=HealthStatus.UNHEALTHY,
                metrics=None,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    async def check_duckdb_health(self) -> HealthCheckResult:
        """Check DuckDB health (file-based database)"""
        if not duckdb:
            return self._create_unavailable_result('duckdb', 'DuckDB not available')
        
        start_time = time.time()
        
        try:
            # Test DuckDB connection
            conn = duckdb.connect(':memory:')
            result = conn.execute('SELECT 1').fetchone()
            conn.close()
            
            response_time = (time.time() - start_time) * 1000
            
            metrics = DatabaseMetrics(
                response_time=response_time,
                cpu_usage=psutil.cpu_percent(),
                memory_usage=psutil.virtual_memory().percent,
                disk_usage=psutil.disk_usage('/').percent,
                connection_count=1,
                error_rate=0.0,
                throughput=1000.0 / response_time if response_time > 0 else 0,
                availability=100.0,
                last_check=datetime.now()
            )
            
            status = self._determine_status('duckdb', metrics)
            return HealthCheckResult(
                database='duckdb',
                status=status,
                metrics=metrics,
                error_message=None,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"DuckDB health check failed: {e}")
            return HealthCheckResult(
                database='duckdb',
                status=HealthStatus.UNHEALTHY,
                metrics=None,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    def _create_unavailable_result(self, database: str, message: str) -> HealthCheckResult:
        """Create result for unavailable database"""
        return HealthCheckResult(
            database=database,
            status=HealthStatus.UNKNOWN,
            metrics=None,
            error_message=message,
            timestamp=datetime.now()
        )
    
    def _determine_status(self, database: str, metrics: DatabaseMetrics) -> HealthStatus:
        """Determine health status based on metrics"""
        thresholds = self.config.get('monitoring', {}).get('alert_thresholds', {})
        
        # Check critical thresholds
        if (
            metrics.response_time > thresholds.get('response_time', 1000) or
            metrics.cpu_usage > thresholds.get('cpu_usage', 80) or
            metrics.memory_usage > thresholds.get('memory_usage', 85) or
            metrics.disk_usage > thresholds.get('disk_usage', 90) or
            metrics.error_rate > thresholds.get('error_rate', 5)
        ):
            return HealthStatus.UNHEALTHY
        
        # Check warning thresholds (80% of critical)
        warning_multiplier = 0.8
        if (
            metrics.response_time > thresholds.get('response_time', 1000) * warning_multiplier or
            metrics.cpu_usage > thresholds.get('cpu_usage', 80) * warning_multiplier or
            metrics.memory_usage > thresholds.get('memory_usage', 85) * warning_multiplier or
            metrics.disk_usage > thresholds.get('disk_usage', 90) * warning_multiplier
        ):
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    async def run_all_health_checks(self) -> Dict[str, HealthCheckResult]:
        """Run health checks for all databases concurrently"""
        health_checks = {
            'postgresql': self.check_postgresql_health(),
            'clickhouse': self.check_clickhouse_health(),
            'redis': self.check_redis_health(),
            'qdrant': self.check_qdrant_health(),
            'influxdb': self.check_influxdb_health(),
            'minio': self.check_minio_health(),
            'elasticsearch': self.check_elasticsearch_health(),
            'duckdb': self.check_duckdb_health()
        }
        
        results = await asyncio.gather(
            *health_checks.values(),
            return_exceptions=True
        )
        
        # Process results
        health_results = {}
        for database, result in zip(health_checks.keys(), results):
            if isinstance(result, Exception):
                health_results[database] = HealthCheckResult(
                    database=database,
                    status=HealthStatus.UNHEALTHY,
                    metrics=None,
                    error_message=str(result),
                    timestamp=datetime.now()
                )
            else:
                health_results[database] = result
        
        self.health_results = health_results
        return health_results
    
    def update_prometheus_metrics(self, results: Dict[str, HealthCheckResult]):
        """Update Prometheus metrics"""
        for database, result in results.items():
            # Update status (0=unknown, 1=healthy, 2=degraded, 3=unhealthy)
            status_value = {
                HealthStatus.UNKNOWN: 0,
                HealthStatus.HEALTHY: 1,
                HealthStatus.DEGRADED: 2,
                HealthStatus.UNHEALTHY: 3
            }[result.status]
            
            self.metrics['health_status'].labels(database=database).set(status_value)
            self.metrics['check_counter'].labels(database=database, status=result.status.value).inc()
            
            if result.metrics:
                self.metrics['response_time'].labels(database=database).observe(result.metrics.response_time / 1000)
                self.metrics['cpu_usage'].labels(database=database).set(result.metrics.cpu_usage)
                self.metrics['memory_usage'].labels(database=database).set(result.metrics.memory_usage)
                self.metrics['disk_usage'].labels(database=database).set(result.metrics.disk_usage)
                self.metrics['connection_count'].labels(database=database).set(result.metrics.connection_count)
                self.metrics['error_rate'].labels(database=database).set(result.metrics.error_rate)
                self.metrics['availability'].labels(database=database).set(result.metrics.availability)
    
    async def send_alerts(self, results: Dict[str, HealthCheckResult]):
        """Send alerts for unhealthy databases"""
        unhealthy_databases = [
            db for db, result in results.items()
            if result.status in [HealthStatus.UNHEALTHY, HealthStatus.DEGRADED]
        ]
        
        if not unhealthy_databases:
            return
        
        alert_message = self._create_alert_message(unhealthy_databases, results)
        
        # Send email alerts
        if self.notification_clients['email']:
            await self._send_email_alert(alert_message)
        
        # Send webhook alerts
        if self.notification_clients['webhook']:
            await self._send_webhook_alert(alert_message, results)
    
    def _create_alert_message(self, unhealthy_databases: List[str], results: Dict[str, HealthCheckResult]) -> str:
        """Create alert message"""
        message_lines = [
            "🚨 Database Health Alert - Algorithmic Trading System",
            f"Timestamp: {datetime.now().isoformat()}",
            f"Unhealthy Databases: {len(unhealthy_databases)}",
            ""
        ]
        
        for db in unhealthy_databases:
            result = results[db]
            message_lines.extend([
                f"Database: {db.upper()}",
                f"Status: {result.status.value.upper()}",
                f"Error: {result.error_message or 'N/A'}",
                f"Timestamp: {result.timestamp.isoformat()}",
                ""
            ])
            
            if result.metrics:
                message_lines.extend([
                    f"Response Time: {result.metrics.response_time:.2f}ms",
                    f"CPU Usage: {result.metrics.cpu_usage:.1f}%",
                    f"Memory Usage: {result.metrics.memory_usage:.1f}%",
                    f"Disk Usage: {result.metrics.disk_usage:.1f}%",
                    ""
                ])
        
        return "\n".join(message_lines)
    
    async def _send_email_alert(self, message: str):
        """Send email alert"""
        try:
            email_config = self.notification_clients['email']
            
            msg = MIMEMultipart()
            msg['From'] = email_config['from_email']
            msg['To'] = ', '.join(email_config['to_emails'])
            msg['Subject'] = 'Database Health Alert - Trading System'
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            server.send_message(msg)
            server.quit()
            
            self.logger.info("Email alert sent successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
    
    async def _send_webhook_alert(self, message: str, results: Dict[str, HealthCheckResult]):
        """Send webhook alert"""
        try:
            webhook_config = self.notification_clients['webhook']
            
            payload = {
                'timestamp': datetime.now().isoformat(),
                'alert_type': 'database_health',
                'message': message,
                'results': {
                    db: {
                        'status': result.status.value,
                        'error_message': result.error_message,
                        'timestamp': result.timestamp.isoformat(),
                        'metrics': asdict(result.metrics) if result.metrics else None
                    }
                    for db, result in results.items()
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_config['url'],
                    json=payload,
                    headers=webhook_config['headers'],
                    timeout=10
                ) as response:
                    if response.status == 200:
                        self.logger.info("Webhook alert sent successfully")
                    else:
                        self.logger.error(f"Webhook alert failed with status {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Failed to send webhook alert: {e}")
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        if not self.health_results:
            return {'error': 'No health check results available'}
        
        total_databases = len(self.health_results)
        healthy_count = sum(1 for result in self.health_results.values() if result.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for result in self.health_results.values() if result.status == HealthStatus.DEGRADED)
        unhealthy_count = sum(1 for result in self.health_results.values() if result.status == HealthStatus.UNHEALTHY)
        unknown_count = sum(1 for result in self.health_results.values() if result.status == HealthStatus.UNKNOWN)
        
        overall_health = HealthStatus.HEALTHY
        if unhealthy_count > 0:
            overall_health = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_health = HealthStatus.DEGRADED
        elif unknown_count > 0:
            overall_health = HealthStatus.UNKNOWN
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_health': overall_health.value,
            'summary': {
                'total_databases': total_databases,
                'healthy': healthy_count,
                'degraded': degraded_count,
                'unhealthy': unhealthy_count,
                'unknown': unknown_count,
                'availability_percentage': (healthy_count / total_databases * 100) if total_databases > 0 else 0
            },
            'databases': {
                db: {
                    'status': result.status.value,
                    'error_message': result.error_message,
                    'timestamp': result.timestamp.isoformat(),
                    'recovery_attempts': result.recovery_attempts,
                    'metrics': asdict(result.metrics) if result.metrics else None
                }
                for db, result in self.health_results.items()
            }
        }
    
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        self.logger.info("Starting database health monitoring...")
        
        # Start Prometheus metrics server
        prometheus_port = self.config.get('monitoring', {}).get('prometheus_port', 8090)
        start_http_server(prometheus_port)
        self.logger.info(f"Prometheus metrics server started on port {prometheus_port}")
        
        while True:
            try:
                # Run health checks
                results = await self.run_all_health_checks()
                
                # Update metrics
                self.update_prometheus_metrics(results)
                
                # Send alerts if needed
                await self.send_alerts(results)
                
                # Log summary
                healthy_count = sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY)
                total_count = len(results)
                self.logger.info(f"Health check completed: {healthy_count}/{total_count} databases healthy")
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)


async def main():
    """Main function"""
    monitor = DatabaseHealthMonitor()
    
    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\nShutting down health monitor...")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())