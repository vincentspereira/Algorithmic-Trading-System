#!/usr/bin/env python3
"""
Database Initialization Script for Algorithmic Trading System
Sets up all 9 databases with proper schemas, tables, and configurations
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from dataclasses import dataclass
from datetime import datetime, timedelta

# Database-specific imports
try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    import asyncpg
except ImportError:
    print("PostgreSQL dependencies not installed. Run: pip install psycopg2-binary asyncpg")

try:
    from clickhouse_driver import Client as ClickHouseClient
except ImportError:
    print("ClickHouse dependencies not installed. Run: pip install clickhouse-driver")

try:
    import duckdb
except ImportError:
    print("DuckDB dependencies not installed. Run: pip install duckdb")

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, CreateCollection
except ImportError:
    print("Qdrant dependencies not installed. Run: pip install qdrant-client")

try:
    import redis
except ImportError:
    print("Redis dependencies not installed. Run: pip install redis")

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    print("InfluxDB dependencies not installed. Run: pip install influxdb-client")

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    print("MinIO dependencies not installed. Run: pip install minio")

try:
    from elasticsearch import Elasticsearch
except ImportError:
    print("Elasticsearch dependencies not installed. Run: pip install elasticsearch")

try:
    from pyiceberg.catalog import load_catalog
except ImportError:
    print("Apache Iceberg dependencies not installed. Run: pip install pyiceberg")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_init.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class DatabaseStatus:
    """Track database initialization status"""
    name: str
    enabled: bool
    initialized: bool = False
    error: Optional[str] = None
    connection_tested: bool = False
    schema_created: bool = False
    data_loaded: bool = False

class DatabaseInitializer:
    """Main class for initializing all databases"""
    
    def __init__(self, config_path: str = "database_config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.status: Dict[str, DatabaseStatus] = {}
        self._init_status_tracking()
    
    def _load_config(self) -> dict:
        """Load database configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
            logger.info(f"Configuration loaded from {self.config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file {self.config_path} not found")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise
    
    def _init_status_tracking(self):
        """Initialize status tracking for all databases"""
        databases = [
            'postgresql', 'clickhouse', 'duckdb', 'qdrant', 
            'iceberg', 'redis', 'influxdb', 'minio', 'elasticsearch'
        ]
        
        for db in databases:
            enabled = self.config.get(db, {}).get('enabled', False)
            self.status[db] = DatabaseStatus(name=db, enabled=enabled)
    
    async def initialize_all(self) -> Dict[str, DatabaseStatus]:
        """Initialize all enabled databases"""
        logger.info("Starting database initialization process")
        
        # Create initialization tasks for enabled databases
        tasks = []
        
        if self.status['postgresql'].enabled:
            tasks.append(self._init_postgresql())
        
        if self.status['clickhouse'].enabled:
            tasks.append(self._init_clickhouse())
        
        if self.status['duckdb'].enabled:
            tasks.append(self._init_duckdb())
        
        if self.status['qdrant'].enabled:
            tasks.append(self._init_qdrant())
        
        if self.status['redis'].enabled:
            tasks.append(self._init_redis())
        
        if self.status['influxdb'].enabled:
            tasks.append(self._init_influxdb())
        
        if self.status['minio'].enabled:
            tasks.append(self._init_minio())
        
        if self.status['elasticsearch'].enabled:
            tasks.append(self._init_elasticsearch())
        
        if self.status['iceberg'].enabled:
            tasks.append(self._init_iceberg())
        
        # Run all initialization tasks concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Generate summary report
        self._generate_report()
        
        return self.status
    
    async def _init_postgresql(self):
        """Initialize PostgreSQL with pgvector extension"""
        db_name = 'postgresql'
        logger.info(f"Initializing {db_name}...")
        
        try:
            config = self.config[db_name]
            
            # Create database connection
            conn_params = {
                'host': config['host'],
                'port': config['port'],
                'user': config['username'],
                'password': os.getenv('POSTGRES_PASSWORD', 'trading_password'),
                'database': 'postgres'  # Connect to default database first
            }
            
            # Create main database if it doesn't exist
            conn = psycopg2.connect(**conn_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{config['database']}'")
            if not cursor.fetchone():
                cursor.execute(f"CREATE DATABASE {config['database']}")
                logger.info(f"Created database {config['database']}")
            
            cursor.close()
            conn.close()
            
            # Connect to the trading database
            conn_params['database'] = config['database']
            conn = psycopg2.connect(**conn_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Install extensions
            for extension in config.get('extensions', []):
                try:
                    cursor.execute(f"CREATE EXTENSION IF NOT EXISTS {extension}")
                    logger.info(f"Installed extension: {extension}")
                except Exception as e:
                    logger.warning(f"Could not install extension {extension}: {e}")
            
            # Create schemas
            for schema in config.get('schemas', []):
                schema_name = schema['name']
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
                logger.info(f"Created schema: {schema_name}")
                
                # Create tables in schema
                for table in schema.get('tables', []):
                    self._create_postgresql_table(cursor, schema_name, table)
            
            cursor.close()
            conn.close()
            
            self.status[db_name].initialized = True
            self.status[db_name].connection_tested = True
            self.status[db_name].schema_created = True
            logger.info(f"{db_name} initialization completed successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize {db_name}: {str(e)}"
            logger.error(error_msg)
            self.status[db_name].error = error_msg
    
    def _create_postgresql_table(self, cursor, schema_name: str, table_name: str):
        """Create PostgreSQL tables with appropriate schemas"""
        table_definitions = {
            'orders': """
                CREATE TABLE IF NOT EXISTS {schema}.orders (
                    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    portfolio_id UUID NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
                    order_type VARCHAR(20) NOT NULL,
                    quantity DECIMAL(18,8) NOT NULL,
                    price DECIMAL(18,8),
                    stop_price DECIMAL(18,8),
                    time_in_force VARCHAR(10) DEFAULT 'DAY',
                    status VARCHAR(20) DEFAULT 'PENDING',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    filled_quantity DECIMAL(18,8) DEFAULT 0,
                    avg_fill_price DECIMAL(18,8),
                    commission DECIMAL(18,8) DEFAULT 0,
                    tags JSONB
                )
            """,
            'positions': """
                CREATE TABLE IF NOT EXISTS {schema}.positions (
                    position_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    portfolio_id UUID NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    quantity DECIMAL(18,8) NOT NULL,
                    avg_cost DECIMAL(18,8) NOT NULL,
                    market_value DECIMAL(18,8),
                    unrealized_pnl DECIMAL(18,8),
                    realized_pnl DECIMAL(18,8) DEFAULT 0,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(portfolio_id, symbol)
                )
            """,
            'portfolios': """
                CREATE TABLE IF NOT EXISTS {schema}.portfolios (
                    portfolio_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    base_currency VARCHAR(3) DEFAULT 'USD',
                    initial_capital DECIMAL(18,2) NOT NULL,
                    current_value DECIMAL(18,2),
                    cash_balance DECIMAL(18,2),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    status VARCHAR(20) DEFAULT 'ACTIVE',
                    risk_parameters JSONB
                )
            """,
            'strategies': """
                CREATE TABLE IF NOT EXISTS {schema}.strategies (
                    strategy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    strategy_type VARCHAR(50),
                    parameters JSONB,
                    code TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    status VARCHAR(20) DEFAULT 'INACTIVE',
                    performance_metrics JSONB
                )
            """,
            'symbols': """
                CREATE TABLE IF NOT EXISTS {schema}.symbols (
                    symbol_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    symbol VARCHAR(20) UNIQUE NOT NULL,
                    name VARCHAR(200),
                    asset_class VARCHAR(50),
                    exchange VARCHAR(50),
                    currency VARCHAR(3),
                    sector VARCHAR(100),
                    industry VARCHAR(100),
                    market_cap BIGINT,
                    is_active BOOLEAN DEFAULT TRUE,
                    metadata JSONB
                )
            """,
            'document_embeddings': """
                CREATE TABLE IF NOT EXISTS {schema}.document_embeddings (
                    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    document_id VARCHAR(100) NOT NULL,
                    document_type VARCHAR(50),
                    content_hash VARCHAR(64),
                    embedding vector(1536),
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """
        }
        
        if table_name in table_definitions:
            sql = table_definitions[table_name].format(schema=schema_name)
            cursor.execute(sql)
            logger.info(f"Created table: {schema_name}.{table_name}")
            
            # Create indexes
            self._create_postgresql_indexes(cursor, schema_name, table_name)
    
    def _create_postgresql_indexes(self, cursor, schema_name: str, table_name: str):
        """Create appropriate indexes for PostgreSQL tables"""
        index_definitions = {
            'orders': [
                f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_orders_portfolio ON {schema_name}.orders(portfolio_id)",
                f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_orders_symbol ON {schema_name}.orders(symbol)",
                f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_orders_status ON {schema_name}.orders(status)",
                f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_orders_created ON {schema_name}.orders(created_at)"
            ],
            'positions': [
                f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_positions_portfolio ON {schema_name}.positions(portfolio_id)",
                f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_positions_symbol ON {schema_name}.positions(symbol)"
            ],
            'symbols': [
                f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_symbols_asset_class ON {schema_name}.symbols(asset_class)",
                f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_symbols_exchange ON {schema_name}.symbols(exchange)"
            ],
            'document_embeddings': [
                f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_embeddings_type ON {schema_name}.document_embeddings(document_type)",
                f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_embeddings_vector ON {schema_name}.document_embeddings USING ivfflat (embedding vector_cosine_ops)"
            ]
        }
        
        for index_sql in index_definitions.get(table_name, []):
            try:
                cursor.execute(index_sql)
            except Exception as e:
                logger.warning(f"Could not create index: {e}")
    
    async def _init_clickhouse(self):
        """Initialize ClickHouse OLAP database"""
        db_name = 'clickhouse'
        logger.info(f"Initializing {db_name}...")
        
        try:
            config = self.config[db_name]
            
            client = ClickHouseClient(
                host=config['host'],
                port=config['port'],
                user=config['username'],
                password=os.getenv('CLICKHOUSE_PASSWORD', 'clickhouse_password'),
                database=config['database']
            )
            
            # Create database if it doesn't exist
            client.execute(f"CREATE DATABASE IF NOT EXISTS {config['database']}")
            
            # Create tables
            for table_config in config.get('tables', []):
                self._create_clickhouse_table(client, table_config)
            
            # Create materialized views
            for view_config in config.get('materialized_views', []):
                self._create_clickhouse_materialized_view(client, view_config)
            
            client.disconnect()
            
            self.status[db_name].initialized = True
            self.status[db_name].connection_tested = True
            self.status[db_name].schema_created = True
            logger.info(f"{db_name} initialization completed successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize {db_name}: {str(e)}"
            logger.error(error_msg)
            self.status[db_name].error = error_msg
    
    def _create_clickhouse_table(self, client, table_config: dict):
        """Create ClickHouse tables"""
        table_name = table_config['name']
        engine = table_config['engine']
        partition_by = table_config.get('partition_by', '')
        order_by = table_config.get('order_by', '')
        ttl = table_config.get('ttl', '')
        
        table_schemas = {
            'market_data_ticks': """
                CREATE TABLE IF NOT EXISTS market_data_ticks (
                    symbol String,
                    timestamp DateTime64(3),
                    price Float64,
                    volume UInt64,
                    bid Float64,
                    ask Float64,
                    bid_size UInt32,
                    ask_size UInt32,
                    exchange String
                ) ENGINE = {engine}
                PARTITION BY {partition_by}
                ORDER BY {order_by}
                {ttl_clause}
            """,
            'trade_executions': """
                CREATE TABLE IF NOT EXISTS trade_executions (
                    execution_id String,
                    portfolio_id String,
                    symbol String,
                    side Enum8('BUY' = 1, 'SELL' = 2),
                    quantity Float64,
                    price Float64,
                    execution_time DateTime64(3),
                    commission Float64,
                    pnl Float64,
                    strategy String
                ) ENGINE = {engine}
                PARTITION BY {partition_by}
                ORDER BY {order_by}
            """
        }
        
        if table_name in table_schemas:
            ttl_clause = f"TTL {ttl}" if ttl else ""
            sql = table_schemas[table_name].format(
                engine=engine,
                partition_by=partition_by,
                order_by=order_by,
                ttl_clause=ttl_clause
            )
            client.execute(sql)
            logger.info(f"Created ClickHouse table: {table_name}")
    
    def _create_clickhouse_materialized_view(self, client, view_config: dict):
        """Create ClickHouse materialized views"""
        view_name = view_config['name']
        source_table = view_config['source_table']
        aggregation = view_config['aggregation']
        
        sql = f"""
            CREATE MATERIALIZED VIEW IF NOT EXISTS {view_name}
            ENGINE = SummingMergeTree()
            ORDER BY (portfolio_id, date)
            AS SELECT
                portfolio_id,
                toDate(execution_time) as date,
                {aggregation}
            FROM {source_table}
        """
        
        client.execute(sql)
        logger.info(f"Created ClickHouse materialized view: {view_name}")
    
    async def _init_duckdb(self):
        """Initialize DuckDB for analytics"""
        db_name = 'duckdb'
        logger.info(f"Initializing {db_name}...")
        
        try:
            config = self.config[db_name]
            
            # Ensure directory exists
            db_path = Path(config['database_path'])
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Connect to DuckDB
            conn = duckdb.connect(str(db_path))
            
            # Install extensions
            for extension in config.get('extensions', []):
                try:
                    conn.execute(f"INSTALL {extension}")
                    conn.execute(f"LOAD {extension}")
                    logger.info(f"Installed DuckDB extension: {extension}")
                except Exception as e:
                    logger.warning(f"Could not install DuckDB extension {extension}: {e}")
            
            # Set memory limit
            if 'memory_limit' in config:
                conn.execute(f"SET memory_limit = '{config['memory_limit']}'")
            
            # Create schemas and tables
            for schema in config.get('schemas', []):
                schema_name = schema['name']
                conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
                logger.info(f"Created DuckDB schema: {schema_name}")
                
                for table in schema.get('tables', []):
                    self._create_duckdb_table(conn, schema_name, table)
            
            conn.close()
            
            self.status[db_name].initialized = True
            self.status[db_name].connection_tested = True
            self.status[db_name].schema_created = True
            logger.info(f"{db_name} initialization completed successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize {db_name}: {str(e)}"
            logger.error(error_msg)
            self.status[db_name].error = error_msg
    
    def _create_duckdb_table(self, conn, schema_name: str, table_name: str):
        """Create DuckDB tables"""
        table_definitions = {
            'backtest_results': f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.backtest_results (
                    backtest_id VARCHAR PRIMARY KEY,
                    strategy_name VARCHAR NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    initial_capital DECIMAL(18,2),
                    final_value DECIMAL(18,2),
                    total_return DECIMAL(10,4),
                    sharpe_ratio DECIMAL(10,4),
                    max_drawdown DECIMAL(10,4),
                    win_rate DECIMAL(10,4),
                    profit_factor DECIMAL(10,4),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """,
            'strategy_performance': f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.strategy_performance (
                    performance_id VARCHAR PRIMARY KEY,
                    strategy_id VARCHAR NOT NULL,
                    date DATE NOT NULL,
                    portfolio_value DECIMAL(18,2),
                    daily_return DECIMAL(10,6),
                    cumulative_return DECIMAL(10,6),
                    drawdown DECIMAL(10,6),
                    volatility DECIMAL(10,6)
                )
            """
        }
        
        if table_name in table_definitions:
            conn.execute(table_definitions[table_name])
            logger.info(f"Created DuckDB table: {schema_name}.{table_name}")
    
    async def _init_qdrant(self):
        """Initialize Qdrant vector database"""
        db_name = 'qdrant'
        logger.info(f"Initializing {db_name}...")
        
        try:
            config = self.config[db_name]
            
            client = QdrantClient(
                host=config['host'],
                port=config['port'],
                api_key=os.getenv('QDRANT_API_KEY')
            )
            
            # Create collections
            for collection_config in config.get('collections', []):
                collection_name = collection_config['name']
                vector_size = collection_config['vector_size']
                distance = getattr(Distance, collection_config['distance'].upper())
                
                try:
                    client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=vector_size,
                            distance=distance
                        )
                    )
                    logger.info(f"Created Qdrant collection: {collection_name}")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        logger.info(f"Qdrant collection {collection_name} already exists")
                    else:
                        raise e
            
            self.status[db_name].initialized = True
            self.status[db_name].connection_tested = True
            self.status[db_name].schema_created = True
            logger.info(f"{db_name} initialization completed successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize {db_name}: {str(e)}"
            logger.error(error_msg)
            self.status[db_name].error = error_msg
    
    async def _init_redis(self):
        """Initialize Redis cache"""
        db_name = 'redis'
        logger.info(f"Initializing {db_name}...")
        
        try:
            config = self.config[db_name]
            
            client = redis.Redis(
                host=config['host'],
                port=config['port'],
                password=os.getenv('REDIS_PASSWORD'),
                db=config['database'],
                decode_responses=True
            )
            
            # Test connection
            client.ping()
            
            # Set up key expiration policies
            for key_pattern, ttl in config.get('expiration_policies', {}).items():
                # This is just for documentation - Redis TTL is set per key
                logger.info(f"Redis expiration policy: {key_pattern} -> {ttl}s")
            
            # Configure memory policy if specified
            if 'memory_policy' in config:
                try:
                    client.config_set('maxmemory-policy', config['memory_policy'])
                    logger.info(f"Set Redis memory policy: {config['memory_policy']}")
                except Exception as e:
                    logger.warning(f"Could not set Redis memory policy: {e}")
            
            self.status[db_name].initialized = True
            self.status[db_name].connection_tested = True
            logger.info(f"{db_name} initialization completed successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize {db_name}: {str(e)}"
            logger.error(error_msg)
            self.status[db_name].error = error_msg
    
    async def _init_influxdb(self):
        """Initialize InfluxDB time-series database"""
        db_name = 'influxdb'
        logger.info(f"Initializing {db_name}...")
        
        try:
            config = self.config[db_name]
            
            client = InfluxDBClient(
                url=f"http://{config['host']}:{config['port']}",
                token=os.getenv('INFLUXDB_TOKEN'),
                org=config['organization']
            )
            
            # Test connection
            health = client.health()
            if health.status != "pass":
                raise Exception(f"InfluxDB health check failed: {health.message}")
            
            # Create bucket if it doesn't exist
            buckets_api = client.buckets_api()
            try:
                bucket = buckets_api.find_bucket_by_name(config['bucket'])
                if not bucket:
                    buckets_api.create_bucket(
                        bucket_name=config['bucket'],
                        org=config['organization']
                    )
                    logger.info(f"Created InfluxDB bucket: {config['bucket']}")
            except Exception as e:
                logger.warning(f"Could not create InfluxDB bucket: {e}")
            
            client.close()
            
            self.status[db_name].initialized = True
            self.status[db_name].connection_tested = True
            logger.info(f"{db_name} initialization completed successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize {db_name}: {str(e)}"
            logger.error(error_msg)
            self.status[db_name].error = error_msg
    
    async def _init_minio(self):
        """Initialize MinIO object storage"""
        db_name = 'minio'
        logger.info(f"Initializing {db_name}...")
        
        try:
            config = self.config[db_name]
            
            client = Minio(
                config['endpoint'],
                access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
                secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
                secure=config.get('secure', False)
            )
            
            # Create buckets
            for bucket_config in config.get('buckets', []):
                bucket_name = bucket_config['name']
                
                if not client.bucket_exists(bucket_name):
                    client.make_bucket(bucket_name)
                    logger.info(f"Created MinIO bucket: {bucket_name}")
                
                # Set bucket versioning if specified
                if bucket_config.get('versioning', False):
                    try:
                        from minio.versioningconfig import VersioningConfig, ENABLED
                        client.set_bucket_versioning(bucket_name, VersioningConfig(ENABLED))
                        logger.info(f"Enabled versioning for bucket: {bucket_name}")
                    except Exception as e:
                        logger.warning(f"Could not enable versioning for {bucket_name}: {e}")
            
            self.status[db_name].initialized = True
            self.status[db_name].connection_tested = True
            logger.info(f"{db_name} initialization completed successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize {db_name}: {str(e)}"
            logger.error(error_msg)
            self.status[db_name].error = error_msg
    
    async def _init_elasticsearch(self):
        """Initialize Elasticsearch for search and analytics"""
        db_name = 'elasticsearch'
        logger.info(f"Initializing {db_name}...")
        
        try:
            config = self.config[db_name]
            
            client = Elasticsearch(
                config['hosts'],
                basic_auth=(config['username'], os.getenv('ELASTICSEARCH_PASSWORD', 'elastic')),
                verify_certs=config.get('verify_certs', False)
            )
            
            # Test connection
            if not client.ping():
                raise Exception("Could not connect to Elasticsearch")
            
            # Create indices
            for index_config in config.get('indices', []):
                index_name = index_config['name']
                
                if not client.indices.exists(index=index_name):
                    client.indices.create(
                        index=index_name,
                        settings=index_config.get('settings', {}),
                        mappings=index_config.get('mappings', {})
                    )
                    logger.info(f"Created Elasticsearch index: {index_name}")
            
            # Create index templates
            for template_config in config.get('index_templates', []):
                template_name = template_config['name']
                client.indices.put_index_template(
                    name=template_name,
                    index_patterns=template_config['index_patterns'],
                    template={
                        'settings': template_config.get('settings', {})
                    }
                )
                logger.info(f"Created Elasticsearch index template: {template_name}")
            
            self.status[db_name].initialized = True
            self.status[db_name].connection_tested = True
            self.status[db_name].schema_created = True
            logger.info(f"{db_name} initialization completed successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize {db_name}: {str(e)}"
            logger.error(error_msg)
            self.status[db_name].error = error_msg
    
    async def _init_iceberg(self):
        """Initialize Apache Iceberg data lakehouse"""
        db_name = 'iceberg'
        logger.info(f"Initializing {db_name}...")
        
        try:
            config = self.config[db_name]
            
            # Create warehouse directory
            warehouse_path = Path(config['warehouse_path'])
            warehouse_path.mkdir(parents=True, exist_ok=True)
            
            # For now, just create the directory structure
            # Full Iceberg integration would require Hadoop/Hive setup
            logger.info(f"Created Iceberg warehouse directory: {warehouse_path}")
            
            self.status[db_name].initialized = True
            self.status[db_name].connection_tested = True
            logger.info(f"{db_name} initialization completed successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize {db_name}: {str(e)}"
            logger.error(error_msg)
            self.status[db_name].error = error_msg
    
    def _generate_report(self):
        """Generate initialization report"""
        logger.info("\n" + "="*80)
        logger.info("DATABASE INITIALIZATION REPORT")
        logger.info("="*80)
        
        total_databases = len(self.status)
        enabled_databases = sum(1 for status in self.status.values() if status.enabled)
        successful_databases = sum(1 for status in self.status.values() if status.initialized)
        failed_databases = sum(1 for status in self.status.values() if status.enabled and not status.initialized)
        
        logger.info(f"Total databases configured: {total_databases}")
        logger.info(f"Enabled databases: {enabled_databases}")
        logger.info(f"Successfully initialized: {successful_databases}")
        logger.info(f"Failed to initialize: {failed_databases}")
        logger.info("-"*80)
        
        for db_name, status in self.status.items():
            if status.enabled:
                status_symbol = "✓" if status.initialized else "✗"
                logger.info(f"{status_symbol} {db_name.upper()}: {'SUCCESS' if status.initialized else 'FAILED'}")
                if status.error:
                    logger.info(f"  Error: {status.error}")
        
        logger.info("="*80)

async def main():
    """Main function to run database initialization"""
    try:
        # Initialize databases
        initializer = DatabaseInitializer()
        status = await initializer.initialize_all()
        
        # Check if all enabled databases were initialized successfully
        failed_databases = [name for name, stat in status.items() 
                          if stat.enabled and not stat.initialized]
        
        if failed_databases:
            logger.error(f"Failed to initialize databases: {', '.join(failed_databases)}")
            sys.exit(1)
        else:
            logger.info("All enabled databases initialized successfully!")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())