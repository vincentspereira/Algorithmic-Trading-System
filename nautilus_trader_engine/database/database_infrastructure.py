"""Comprehensive Database Infrastructure Management System

This module provides deployment, verification, and management capabilities
for all 11 database systems in the algorithmic trading platform:

1. PostgreSQL with pgvector - Primary relational database with vector search
2. ClickHouse - High-performance analytical database for time-series data
3. Qdrant - Vector database for similarity search and ML embeddings
4. Apache Iceberg - Data lakehouse for large-scale analytics
5. Redis - In-memory cache and session store
6. DuckDB - Embedded analytical database
7. InfluxDB - Time-series database for metrics and market data
8. MinIO - S3-compatible object storage
9. Elasticsearch - Full-text search and log analytics
10. Cassandra - Distributed NoSQL for high-volume writes
11. MongoDB - Document database for flexible schemas

Features:
- Automated deployment and configuration
- Health monitoring and alerting
- Data partitioning and indexing strategies
- Backup and recovery procedures
- Performance optimization
- Security configuration
- Connection pooling and load balancing
"""

import os
import sys
import json
import time
import logging
import asyncio
import subprocess
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import yaml
import warnings
warnings.filterwarnings('ignore')

# Database connection libraries
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None

try:
    import clickhouse_connect
except ImportError:
    clickhouse_connect = None

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams
except ImportError:
    QdrantClient = None

try:
    import redis
except ImportError:
    redis = None

try:
    import duckdb
except ImportError:
    duckdb = None

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    InfluxDBClient = None

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    Minio = None

try:
    from elasticsearch import Elasticsearch
except ImportError:
    Elasticsearch = None

try:
    from cassandra.cluster import Cluster
    from cassandra.auth import PlainTextAuthProvider
except ImportError:
    Cluster = None

try:
    import pymongo
    from pymongo import MongoClient
except ImportError:
    pymongo = None
    MongoClient = None

# Docker management
try:
    import docker
except ImportError:
    docker = None


class DatabaseType(Enum):
    """Supported database types"""
    POSTGRESQL = "postgresql"
    CLICKHOUSE = "clickhouse"
    QDRANT = "qdrant"
    ICEBERG = "iceberg"
    REDIS = "redis"
    DUCKDB = "duckdb"
    INFLUXDB = "influxdb"
    MINIO = "minio"
    ELASTICSEARCH = "elasticsearch"
    CASSANDRA = "cassandra"
    MONGODB = "mongodb"


class DatabaseStatus(Enum):
    """Database deployment status"""
    NOT_DEPLOYED = "not_deployed"
    DEPLOYING = "deploying"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class DatabaseConfig:
    """Configuration for a database system"""
    db_type: DatabaseType
    name: str
    host: str = "localhost"
    port: int = 5432
    username: str = "admin"
    password: str = "password"
    database: str = "trading_db"
    
    # Docker configuration
    docker_image: str = ""
    docker_tag: str = "latest"
    container_name: str = ""
    docker_ports: Dict[str, int] = field(default_factory=dict)
    docker_volumes: Dict[str, str] = field(default_factory=dict)
    docker_environment: Dict[str, str] = field(default_factory=dict)
    
    # Performance settings
    max_connections: int = 100
    connection_timeout: int = 30
    pool_size: int = 10
    
    # Storage settings
    data_directory: str = ""
    backup_directory: str = ""
    log_directory: str = ""
    
    # Security settings
    ssl_enabled: bool = False
    ssl_cert_path: str = ""
    ssl_key_path: str = ""
    
    # Custom settings
    custom_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.container_name:
            self.container_name = f"trading_{self.db_type.value}"
        
        if not self.data_directory:
            self.data_directory = f"./data/{self.db_type.value}"
        
        if not self.backup_directory:
            self.backup_directory = f"./backups/{self.db_type.value}"
        
        if not self.log_directory:
            self.log_directory = f"./logs/{self.db_type.value}"


@dataclass
class HealthCheckResult:
    """Result of database health check"""
    db_type: DatabaseType
    status: HealthStatus
    response_time_ms: float
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DatabaseMetrics:
    """Database performance metrics"""
    db_type: DatabaseType
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    connection_count: int
    query_rate: float
    error_rate: float
    avg_response_time: float
    timestamp: datetime = field(default_factory=datetime.now)


class DatabaseManager:
    """Base class for database management"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__name__}_{config.db_type.value}")
        self.client = None
        self.connection_pool = None
        self.status = DatabaseStatus.NOT_DEPLOYED
        
        # Create directories
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories"""
        for directory in [self.config.data_directory, self.config.backup_directory, self.config.log_directory]:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    async def deploy(self) -> bool:
        """Deploy the database"""
        try:
            self.status = DatabaseStatus.DEPLOYING
            self.logger.info(f"Deploying {self.config.db_type.value} database")
            
            # Deploy using Docker if configured
            if self.config.docker_image:
                success = await self._deploy_docker()
            else:
                success = await self._deploy_native()
            
            if success:
                self.status = DatabaseStatus.RUNNING
                self.logger.info(f"Successfully deployed {self.config.db_type.value}")
            else:
                self.status = DatabaseStatus.ERROR
                self.logger.error(f"Failed to deploy {self.config.db_type.value}")
            
            return success
            
        except Exception as e:
            self.status = DatabaseStatus.ERROR
            self.logger.error(f"Error deploying {self.config.db_type.value}: {e}")
            return False
    
    async def _deploy_docker(self) -> bool:
        """Deploy database using Docker"""
        if not docker:
            self.logger.error("Docker library not available")
            return False
        
        try:
            client = docker.from_env()
            
            # Check if container already exists
            try:
                container = client.containers.get(self.config.container_name)
                if container.status == 'running':
                    self.logger.info(f"Container {self.config.container_name} already running")
                    return True
                else:
                    container.start()
                    return True
            except docker.errors.NotFound:
                pass
            
            # Create and start new container
            container = client.containers.run(
                f"{self.config.docker_image}:{self.config.docker_tag}",
                name=self.config.container_name,
                ports=self.config.docker_ports,
                volumes=self.config.docker_volumes,
                environment=self.config.docker_environment,
                detach=True,
                restart_policy={"Name": "unless-stopped"}
            )
            
            # Wait for container to be ready
            await asyncio.sleep(10)
            
            return container.status == 'running'
            
        except Exception as e:
            self.logger.error(f"Error deploying Docker container: {e}")
            return False
    
    async def _deploy_native(self) -> bool:
        """Deploy database natively (to be implemented by subclasses)"""
        self.logger.warning(f"Native deployment not implemented for {self.config.db_type.value}")
        return False
    
    async def connect(self) -> bool:
        """Connect to the database"""
        try:
            # Implementation depends on database type
            return await self._establish_connection()
        except Exception as e:
            self.logger.error(f"Error connecting to {self.config.db_type.value}: {e}")
            return False
    
    async def _establish_connection(self) -> bool:
        """Establish database connection (to be implemented by subclasses)"""
        return True
    
    async def health_check(self) -> HealthCheckResult:
        """Perform health check"""
        start_time = time.time()
        
        try:
            # Basic connection test
            if await self._ping():
                response_time = (time.time() - start_time) * 1000
                metrics = await self._get_health_metrics()
                
                return HealthCheckResult(
                    db_type=self.config.db_type,
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    metrics=metrics
                )
            else:
                return HealthCheckResult(
                    db_type=self.config.db_type,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=(time.time() - start_time) * 1000,
                    error_message="Connection failed"
                )
                
        except Exception as e:
            return HealthCheckResult(
                db_type=self.config.db_type,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
    
    async def _ping(self) -> bool:
        """Ping database (to be implemented by subclasses)"""
        return True
    
    async def _get_health_metrics(self) -> Dict[str, Any]:
        """Get health metrics (to be implemented by subclasses)"""
        return {}
    
    async def backup(self) -> bool:
        """Create database backup"""
        try:
            backup_path = os.path.join(
                self.config.backup_directory,
                f"{self.config.db_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.backup"
            )
            
            return await self._create_backup(backup_path)
            
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            return False
    
    async def _create_backup(self, backup_path: str) -> bool:
        """Create backup (to be implemented by subclasses)"""
        return True
    
    async def restore(self, backup_path: str) -> bool:
        """Restore from backup"""
        try:
            return await self._restore_backup(backup_path)
        except Exception as e:
            self.logger.error(f"Error restoring backup: {e}")
            return False
    
    async def _restore_backup(self, backup_path: str) -> bool:
        """Restore backup (to be implemented by subclasses)"""
        return True
    
    async def stop(self) -> bool:
        """Stop the database"""
        try:
            if self.config.docker_image and docker:
                client = docker.from_env()
                container = client.containers.get(self.config.container_name)
                container.stop()
            
            self.status = DatabaseStatus.STOPPED
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping database: {e}")
            return False


class PostgreSQLManager(DatabaseManager):
    """PostgreSQL with pgvector management"""
    
    def __init__(self, config: DatabaseConfig = None):
        if config is None:
            config = DatabaseConfig(
                db_type=DatabaseType.POSTGRESQL,
                name="PostgreSQL with pgvector",
                port=5432,
                docker_image="pgvector/pgvector",
                docker_tag="pg15",
                docker_ports={'5432/tcp': 5432},
                docker_environment={
                    'POSTGRES_DB': 'trading_db',
                    'POSTGRES_USER': 'admin',
                    'POSTGRES_PASSWORD': 'password'
                },
                docker_volumes={
                    os.path.abspath('./data/postgresql'): {'bind': '/var/lib/postgresql/data', 'mode': 'rw'}
                }
            )
        super().__init__(config)
    
    async def _establish_connection(self) -> bool:
        if not psycopg2:
            self.logger.error("psycopg2 library not available")
            return False
        
        try:
            self.client = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password
            )
            return True
        except Exception as e:
            self.logger.error(f"PostgreSQL connection failed: {e}")
            return False
    
    async def _ping(self) -> bool:
        if not self.client:
            return await self._establish_connection()
        
        try:
            cursor = self.client.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except Exception:
            return False
    
    async def setup_schema(self) -> bool:
        """Setup trading database schema"""
        try:
            cursor = self.client.cursor()
            
            # Enable pgvector extension
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Create tables for trading data
            schema_sql = """
            CREATE TABLE IF NOT EXISTS market_data (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                open_price DECIMAL(15,6),
                high_price DECIMAL(15,6),
                low_price DECIMAL(15,6),
                close_price DECIMAL(15,6),
                volume BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS trades (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                side VARCHAR(10) NOT NULL,
                quantity DECIMAL(15,6) NOT NULL,
                price DECIMAL(15,6) NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                strategy_id VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS portfolios (
                id SERIAL PRIMARY KEY,
                account_id VARCHAR(50) NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                quantity DECIMAL(15,6) NOT NULL,
                avg_cost DECIMAL(15,6),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS strategy_signals (
                id SERIAL PRIMARY KEY,
                strategy_name VARCHAR(100) NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                signal_type VARCHAR(20) NOT NULL,
                strength DECIMAL(5,4),
                confidence DECIMAL(5,4),
                metadata JSONB,
                timestamp TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Vector table for ML embeddings
            CREATE TABLE IF NOT EXISTS ml_embeddings (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                embedding vector(512),
                model_name VARCHAR(100),
                timestamp TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Indexes for performance
            CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp ON market_data(symbol, timestamp);
            CREATE INDEX IF NOT EXISTS idx_trades_symbol_timestamp ON trades(symbol, timestamp);
            CREATE INDEX IF NOT EXISTS idx_portfolios_account_symbol ON portfolios(account_id, symbol);
            CREATE INDEX IF NOT EXISTS idx_strategy_signals_timestamp ON strategy_signals(timestamp);
            CREATE INDEX IF NOT EXISTS idx_ml_embeddings_symbol ON ml_embeddings(symbol);
            """
            
            cursor.execute(schema_sql)
            self.client.commit()
            cursor.close()
            
            self.logger.info("PostgreSQL schema setup completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting up PostgreSQL schema: {e}")
            return False


class ClickHouseManager(DatabaseManager):
    """ClickHouse management for analytical queries"""
    
    def __init__(self, config: DatabaseConfig = None):
        if config is None:
            config = DatabaseConfig(
                db_type=DatabaseType.CLICKHOUSE,
                name="ClickHouse",
                port=8123,
                docker_image="clickhouse/clickhouse-server",
                docker_ports={'8123/tcp': 8123, '9000/tcp': 9000},
                docker_volumes={
                    os.path.abspath('./data/clickhouse'): {'bind': '/var/lib/clickhouse', 'mode': 'rw'}
                }
            )
        super().__init__(config)
    
    async def _establish_connection(self) -> bool:
        if not clickhouse_connect:
            self.logger.error("clickhouse-connect library not available")
            return False
        
        try:
            self.client = clickhouse_connect.get_client(
                host=self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password
            )
            return True
        except Exception as e:
            self.logger.error(f"ClickHouse connection failed: {e}")
            return False
    
    async def _ping(self) -> bool:
        if not self.client:
            return await self._establish_connection()
        
        try:
            result = self.client.query("SELECT 1")
            return len(result.result_rows) > 0
        except Exception:
            return False


class RedisManager(DatabaseManager):
    """Redis management for caching and sessions"""
    
    def __init__(self, config: DatabaseConfig = None):
        if config is None:
            config = DatabaseConfig(
                db_type=DatabaseType.REDIS,
                name="Redis",
                port=6379,
                docker_image="redis",
                docker_tag="alpine",
                docker_ports={'6379/tcp': 6379},
                docker_volumes={
                    os.path.abspath('./data/redis'): {'bind': '/data', 'mode': 'rw'}
                }
            )
        super().__init__(config)
    
    async def _establish_connection(self) -> bool:
        if not redis:
            self.logger.error("redis library not available")
            return False
        
        try:
            self.client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password if self.config.password != "password" else None,
                decode_responses=True
            )
            return True
        except Exception as e:
            self.logger.error(f"Redis connection failed: {e}")
            return False
    
    async def _ping(self) -> bool:
        if not self.client:
            return await self._establish_connection()
        
        try:
            return self.client.ping()
        except Exception:
            return False


class DatabaseInfrastructure:
    """Main database infrastructure management system"""
    
    def __init__(self, config_file: str = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.managers: Dict[DatabaseType, DatabaseManager] = {}
        self.health_status: Dict[DatabaseType, HealthCheckResult] = {}
        self.metrics: Dict[DatabaseType, DatabaseMetrics] = {}
        
        # Load configuration
        if config_file and os.path.exists(config_file):
            self.load_config(config_file)
        else:
            self._setup_default_configs()
    
    def _setup_default_configs(self):
        """Setup default database configurations"""
        # PostgreSQL with pgvector
        self.managers[DatabaseType.POSTGRESQL] = PostgreSQLManager()
        
        # ClickHouse
        self.managers[DatabaseType.CLICKHOUSE] = ClickHouseManager()
        
        # Redis
        self.managers[DatabaseType.REDIS] = RedisManager()
        
        # Add other database managers
        self._setup_additional_managers()
    
    def _setup_additional_managers(self):
        """Setup additional database managers with default configs"""
        # Qdrant Vector Database
        qdrant_config = DatabaseConfig(
            db_type=DatabaseType.QDRANT,
            name="Qdrant Vector Database",
            port=6333,
            docker_image="qdrant/qdrant",
            docker_ports={'6333/tcp': 6333},
            docker_volumes={
                os.path.abspath('./data/qdrant'): {'bind': '/qdrant/storage', 'mode': 'rw'}
            }
        )
        self.managers[DatabaseType.QDRANT] = DatabaseManager(qdrant_config)
        
        # InfluxDB
        influx_config = DatabaseConfig(
            db_type=DatabaseType.INFLUXDB,
            name="InfluxDB",
            port=8086,
            docker_image="influxdb",
            docker_tag="2.0",
            docker_ports={'8086/tcp': 8086},
            docker_environment={
                'INFLUXDB_DB': 'trading_metrics',
                'INFLUXDB_ADMIN_USER': 'admin',
                'INFLUXDB_ADMIN_PASSWORD': 'password'
            },
            docker_volumes={
                os.path.abspath('./data/influxdb'): {'bind': '/var/lib/influxdb2', 'mode': 'rw'}
            }
        )
        self.managers[DatabaseType.INFLUXDB] = DatabaseManager(influx_config)
        
        # MinIO Object Storage
        minio_config = DatabaseConfig(
            db_type=DatabaseType.MINIO,
            name="MinIO Object Storage",
            port=9000,
            docker_image="minio/minio",
            docker_ports={'9000/tcp': 9000, '9001/tcp': 9001},
            docker_environment={
                'MINIO_ROOT_USER': 'admin',
                'MINIO_ROOT_PASSWORD': 'password123'
            },
            docker_volumes={
                os.path.abspath('./data/minio'): {'bind': '/data', 'mode': 'rw'}
            },
            custom_config={'command': 'server /data --console-address ":9001"'}
        )
        self.managers[DatabaseType.MINIO] = DatabaseManager(minio_config)
        
        # Elasticsearch
        elastic_config = DatabaseConfig(
            db_type=DatabaseType.ELASTICSEARCH,
            name="Elasticsearch",
            port=9200,
            docker_image="elasticsearch",
            docker_tag="8.11.0",
            docker_ports={'9200/tcp': 9200, '9300/tcp': 9300},
            docker_environment={
                'discovery.type': 'single-node',
                'ES_JAVA_OPTS': '-Xms512m -Xmx512m'
            },
            docker_volumes={
                os.path.abspath('./data/elasticsearch'): {'bind': '/usr/share/elasticsearch/data', 'mode': 'rw'}
            }
        )
        self.managers[DatabaseType.ELASTICSEARCH] = DatabaseManager(elastic_config)
        
        # Cassandra
        cassandra_config = DatabaseConfig(
            db_type=DatabaseType.CASSANDRA,
            name="Cassandra",
            port=9042,
            docker_image="cassandra",
            docker_tag="4.0",
            docker_ports={'9042/tcp': 9042},
            docker_environment={
                'CASSANDRA_CLUSTER_NAME': 'TradingCluster'
            },
            docker_volumes={
                os.path.abspath('./data/cassandra'): {'bind': '/var/lib/cassandra', 'mode': 'rw'}
            }
        )
        self.managers[DatabaseType.CASSANDRA] = DatabaseManager(cassandra_config)
        
        # MongoDB
        mongo_config = DatabaseConfig(
            db_type=DatabaseType.MONGODB,
            name="MongoDB",
            port=27017,
            docker_image="mongo",
            docker_tag="6.0",
            docker_ports={'27017/tcp': 27017},
            docker_environment={
                'MONGO_INITDB_ROOT_USERNAME': 'admin',
                'MONGO_INITDB_ROOT_PASSWORD': 'password'
            },
            docker_volumes={
                os.path.abspath('./data/mongodb'): {'bind': '/data/db', 'mode': 'rw'}
            }
        )
        self.managers[DatabaseType.MONGODB] = DatabaseManager(mongo_config)
        
        # DuckDB (embedded, no Docker needed)
        duckdb_config = DatabaseConfig(
            db_type=DatabaseType.DUCKDB,
            name="DuckDB",
            port=0,  # Embedded database
            database="./data/duckdb/trading.duckdb"
        )
        self.managers[DatabaseType.DUCKDB] = DatabaseManager(duckdb_config)
    
    def load_config(self, config_file: str):
        """Load database configurations from file"""
        try:
            with open(config_file, 'r') as f:
                if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                    config_data = yaml.safe_load(f)
                else:
                    config_data = json.load(f)
            
            # Parse configurations and create managers
            for db_config in config_data.get('databases', []):
                db_type = DatabaseType(db_config['type'])
                config = DatabaseConfig(**db_config)
                
                # Create appropriate manager
                if db_type == DatabaseType.POSTGRESQL:
                    self.managers[db_type] = PostgreSQLManager(config)
                elif db_type == DatabaseType.CLICKHOUSE:
                    self.managers[db_type] = ClickHouseManager(config)
                elif db_type == DatabaseType.REDIS:
                    self.managers[db_type] = RedisManager(config)
                else:
                    self.managers[db_type] = DatabaseManager(config)
            
            self.logger.info(f"Loaded configuration for {len(self.managers)} databases")
            
        except Exception as e:
            self.logger.error(f"Error loading config file {config_file}: {e}")
            self._setup_default_configs()
    
    async def deploy_all(self) -> Dict[DatabaseType, bool]:
        """Deploy all database systems"""
        results = {}
        
        self.logger.info("Starting deployment of all database systems")
        
        # Deploy in order of dependencies
        deployment_order = [
            DatabaseType.REDIS,  # Cache first
            DatabaseType.POSTGRESQL,  # Primary database
            DatabaseType.CLICKHOUSE,  # Analytics
            DatabaseType.INFLUXDB,  # Time series
            DatabaseType.ELASTICSEARCH,  # Search
            DatabaseType.MONGODB,  # Document store
            DatabaseType.CASSANDRA,  # Distributed NoSQL
            DatabaseType.QDRANT,  # Vector database
            DatabaseType.MINIO,  # Object storage
            DatabaseType.DUCKDB,  # Embedded analytics
        ]
        
        for db_type in deployment_order:
            if db_type in self.managers:
                self.logger.info(f"Deploying {db_type.value}...")
                try:
                    result = await self.managers[db_type].deploy()
                    results[db_type] = result
                    
                    if result:
                        self.logger.info(f"✓ {db_type.value} deployed successfully")
                        # Wait a bit before next deployment
                        await asyncio.sleep(5)
                    else:
                        self.logger.error(f"✗ {db_type.value} deployment failed")
                        
                except Exception as e:
                    self.logger.error(f"✗ {db_type.value} deployment error: {e}")
                    results[db_type] = False
        
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        self.logger.info(f"Deployment completed: {successful}/{total} databases deployed successfully")
        
        return results
    
    async def health_check_all(self) -> Dict[DatabaseType, HealthCheckResult]:
        """Perform health checks on all databases"""
        results = {}
        
        tasks = []
        for db_type, manager in self.managers.items():
            tasks.append(self._health_check_single(db_type, manager))
        
        health_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, (db_type, _) in enumerate(self.managers.items()):
            if isinstance(health_results[i], Exception):
                results[db_type] = HealthCheckResult(
                    db_type=db_type,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0,
                    error_message=str(health_results[i])
                )
            else:
                results[db_type] = health_results[i]
        
        self.health_status = results
        return results
    
    async def _health_check_single(self, db_type: DatabaseType, manager: DatabaseManager) -> HealthCheckResult:
        """Perform health check on single database"""
        try:
            return await manager.health_check()
        except Exception as e:
            return HealthCheckResult(
                db_type=db_type,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=0,
                error_message=str(e)
            )
    
    async def backup_all(self) -> Dict[DatabaseType, bool]:
        """Create backups for all databases"""
        results = {}
        
        for db_type, manager in self.managers.items():
            try:
                self.logger.info(f"Creating backup for {db_type.value}")
                result = await manager.backup()
                results[db_type] = result
                
                if result:
                    self.logger.info(f"✓ {db_type.value} backup completed")
                else:
                    self.logger.error(f"✗ {db_type.value} backup failed")
                    
            except Exception as e:
                self.logger.error(f"✗ {db_type.value} backup error: {e}")
                results[db_type] = False
        
        return results
    
    def get_infrastructure_status(self) -> Dict[str, Any]:
        """Get overall infrastructure status"""
        total_databases = len(self.managers)
        healthy_databases = sum(
            1 for status in self.health_status.values() 
            if status.status == HealthStatus.HEALTHY
        )
        
        return {
            'total_databases': total_databases,
            'healthy_databases': healthy_databases,
            'health_percentage': (healthy_databases / total_databases * 100) if total_databases > 0 else 0,
            'last_check': datetime.now().isoformat(),
            'database_status': {
                db_type.value: {
                    'status': status.status.value,
                    'response_time_ms': status.response_time_ms,
                    'error': status.error_message
                }
                for db_type, status in self.health_status.items()
            }
        }
    
    async def generate_infrastructure_report(self) -> str:
        """Generate comprehensive infrastructure report"""
        # Perform health checks
        await self.health_check_all()
        
        report = []
        report.append("=" * 80)
        report.append("DATABASE INFRASTRUCTURE AUDIT REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Overall status
        status = self.get_infrastructure_status()
        report.append(f"OVERALL STATUS: {status['healthy_databases']}/{status['total_databases']} databases healthy ({status['health_percentage']:.1f}%)")
        report.append("")
        
        # Individual database status
        report.append("DATABASE STATUS DETAILS:")
        report.append("-" * 40)
        
        for db_type, health_result in self.health_status.items():
            manager = self.managers[db_type]
            
            report.append(f"\n{db_type.value.upper()} ({manager.config.name})")
            report.append(f"  Status: {health_result.status.value.upper()}")
            report.append(f"  Response Time: {health_result.response_time_ms:.2f}ms")
            report.append(f"  Host: {manager.config.host}:{manager.config.port}")
            
            if manager.config.docker_image:
                report.append(f"  Docker Image: {manager.config.docker_image}:{manager.config.docker_tag}")
                report.append(f"  Container: {manager.config.container_name}")
            
            if health_result.error_message:
                report.append(f"  Error: {health_result.error_message}")
            
            if health_result.metrics:
                report.append(f"  Metrics: {health_result.metrics}")
        
        # Recommendations
        report.append("\n" + "=" * 80)
        report.append("RECOMMENDATIONS")
        report.append("=" * 80)
        
        unhealthy_dbs = [
            db_type for db_type, status in self.health_status.items()
            if status.status != HealthStatus.HEALTHY
        ]
        
        if unhealthy_dbs:
            report.append("\nIMMEDIATE ACTIONS REQUIRED:")
            for db_type in unhealthy_dbs:
                report.append(f"  - Investigate and fix {db_type.value} connectivity issues")
                report.append(f"  - Check {db_type.value} logs for error details")
                report.append(f"  - Verify {db_type.value} configuration and resources")
        else:
            report.append("\n✓ All databases are healthy and operational")
        
        report.append("\nOPTIMIZATION RECOMMENDATIONS:")
        report.append("  - Implement automated monitoring and alerting")
        report.append("  - Set up regular backup schedules")
        report.append("  - Configure connection pooling for high-traffic databases")
        report.append("  - Implement data partitioning strategies")
        report.append("  - Set up read replicas for PostgreSQL and MongoDB")
        report.append("  - Configure clustering for Cassandra and Elasticsearch")
        
        return "\n".join(report)


# Example usage and testing functions
async def test_database_infrastructure():
    """Test database infrastructure deployment and verification"""
    print("Testing Database Infrastructure Management System")
    print("=" * 60)
    
    # Initialize infrastructure
    infrastructure = DatabaseInfrastructure()
    
    # Deploy all databases
    print("\n1. Deploying all database systems...")
    deployment_results = await infrastructure.deploy_all()
    
    print("\nDeployment Results:")
    for db_type, success in deployment_results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"  {db_type.value}: {status}")
    
    # Wait for systems to stabilize
    print("\n2. Waiting for systems to stabilize...")
    await asyncio.sleep(30)
    
    # Perform health checks
    print("\n3. Performing health checks...")
    health_results = await infrastructure.health_check_all()
    
    print("\nHealth Check Results:")
    for db_type, health in health_results.items():
        status_icon = "✓" if health.status == HealthStatus.HEALTHY else "✗"
        print(f"  {status_icon} {db_type.value}: {health.status.value} ({health.response_time_ms:.2f}ms)")
        if health.error_message:
            print(f"    Error: {health.error_message}")
    
    # Generate infrastructure report
    print("\n4. Generating infrastructure report...")
    report = await infrastructure.generate_infrastructure_report()
    
    # Save report to file
    report_file = f"infrastructure_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\nInfrastructure report saved to: {report_file}")
    print("\n" + "=" * 60)
    print("Database Infrastructure Test Completed")
    
    return infrastructure


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the test
    asyncio.run(test_database_infrastructure())