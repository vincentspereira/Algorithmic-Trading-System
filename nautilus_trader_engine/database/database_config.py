"""
Comprehensive Database Configuration Module
Implements multi-database strategy for the algorithmic trading system

This module provides:
- PostgreSQL/pgvector for relational data and vector embeddings
- ClickHouse for time-series analytics
- Redis for caching and session management
- Qdrant for vector similarity search
- DuckDB for OLAP queries
- Apache Iceberg for immutable audit logs
- Connection pooling and encryption
- Performance validation and benchmarking

Author: Vincent S. Pereira
Version: 2.0.0
Phase: 1 - Core System Validation & Hardening
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass

# Database drivers and clients
import asyncpg
import redis.asyncio as redis
import duckdb

QdrantClient = None
VectorParams = None
Distance = None
clickhouse_connect = None

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import VectorParams, Distance
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

try:
    import clickhouse_connect
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    CLICKHOUSE_AVAILABLE = False

# Configuration and utilities
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import sqlalchemy as sa

logger = logging.getLogger(__name__)

@dataclass
class DatabasePerformanceMetrics:
    """Database performance metrics for validation"""
    db_type: str
    connection_time_ms: float
    query_time_ms: float
    throughput_ops_per_sec: float
    success_rate: float
    error_count: int
    timestamp: datetime

class DatabaseManager:
    """
    Comprehensive database manager for all database systems
    Handles connections, pooling, encryption, and performance validation
    """
    
    def __init__(self):
        self.connections = {}
        self.engines = {}
        self.session_makers = {}
        self.performance_metrics = []
        self.logger = logging.getLogger(__name__)
        
        # Performance targets
        self.performance_targets = {
            "postgresql": {"connection_ms": 100, "query_ms": 20},
            "clickhouse": {"connection_ms": 200, "query_ms": 1000},
            "redis": {"connection_ms": 50, "query_ms": 5},
            "qdrant": {"connection_ms": 100, "query_ms": 50},
            "duckdb": {"connection_ms": 10, "query_ms": 100}
        }
    
    async def initialize_all_databases(self) -> Dict[str, bool]:
        """Initialize all database connections with performance validation"""
        self.logger.info("Initializing comprehensive database configuration...")
        
        results = {}
        
        # Initialize each database
        results["postgresql"] = await self._initialize_postgresql()
        results["clickhouse"] = await self._initialize_clickhouse()
        results["redis"] = await self._initialize_redis()
        results["qdrant"] = await self._initialize_qdrant()
        results["duckdb"] = await self._initialize_duckdb()
        
        # Validate performance across all databases
        performance_results = await self._validate_all_performance()
        results.update(performance_results)
        
        self.logger.info(f"Database initialization complete: {results}")
        return results
    
    async def _initialize_postgresql(self) -> bool:
        """Initialize PostgreSQL with pgvector extension and connection pooling"""
        try:
            # Database configuration
            db_config = {
                "host": os.getenv("POSTGRES_HOST", "localhost"),
                "port": int(os.getenv("POSTGRES_PORT", 5432)),
                "database": os.getenv("POSTGRES_DB", "trading_system"),
                "user": os.getenv("POSTGRES_USER", "postgres"),
                "password": os.getenv("POSTGRES_PASSWORD", "trading_password_2024"),
            }
            
            # Create async engine with connection pooling
            database_url = f"postgresql+asyncpg://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
            
            self.engines["postgresql"] = create_async_engine(
                database_url,
                pool_size=20,
                max_overflow=30,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            
            # Create session maker
            self.session_makers["postgresql"] = sessionmaker(
                self.engines["postgresql"],
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test connection and create schemas
            async with self.engines["postgresql"].begin() as conn:
                # Enable pgvector extension
                await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
                
                # Create core tables
                await self._create_postgresql_schemas(conn)
            
            self.logger.info("PostgreSQL initialized successfully with pgvector support")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize PostgreSQL: {e}")
            return False
    
    async def _create_postgresql_schemas(self, conn):
        """Create PostgreSQL schemas and tables"""
        
        # Users table
        await conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                roles TEXT[] DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                last_login TIMESTAMP,
                preferences JSONB DEFAULT '{}'
            )
        """))
        
        # Trading accounts table
        await conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS trading_accounts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                account_id VARCHAR(50) UNIQUE NOT NULL,
                broker VARCHAR(20) NOT NULL,
                account_type VARCHAR(20) DEFAULT 'paper',
                balance DECIMAL(15,2) DEFAULT 0.00,
                buying_power DECIMAL(15,2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                metadata JSONB DEFAULT '{}'
            )
        """))
        
        # Orders table
        await conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                account_id INTEGER REFERENCES trading_accounts(id),
                order_id VARCHAR(50) UNIQUE NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                side VARCHAR(10) NOT NULL,
                order_type VARCHAR(20) NOT NULL,
                quantity DECIMAL(15,6) NOT NULL,
                price DECIMAL(15,6),
                stop_price DECIMAL(15,6),
                status VARCHAR(20) DEFAULT 'pending',
                filled_quantity DECIMAL(15,6) DEFAULT 0,
                avg_fill_price DECIMAL(15,6),
                commission DECIMAL(10,4) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB DEFAULT '{}'
            )
        """))
        
        # Strategies table with vector embeddings
        await conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS strategies (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                name VARCHAR(100) NOT NULL,
                description TEXT,
                strategy_type VARCHAR(50) NOT NULL,
                parameters JSONB NOT NULL DEFAULT '{}',
                code TEXT,
                embedding vector(1536),
                performance_metrics JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                version INTEGER DEFAULT 1
            )
        """))
        
        # Create indexes for performance
        await conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"))
        await conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"))
        await conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol)"))
        await conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)"))
        await conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)"))
        await conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_strategies_user_id ON strategies(user_id)"))
        
        # Vector similarity index for strategies
        await conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_strategies_embedding ON strategies USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"))
    
    async def _initialize_clickhouse(self) -> bool:
        """Initialize ClickHouse for time-series analytics"""
        try:
            if not CLICKHOUSE_AVAILABLE:
                self.logger.warning("ClickHouse client not available; skipping ClickHouse initialization")
                return False
            # Connection configuration
            ch_config = {
                "host": os.getenv("CLICKHOUSE_HOST", "localhost"),
                "port": int(os.getenv("CLICKHOUSE_PORT", 8123)),
                "username": os.getenv("CLICKHOUSE_USER", "clickhouse_user"),
                "password": os.getenv("CLICKHOUSE_PASSWORD", "clickhouse_password_2024"),
                "database": os.getenv("CLICKHOUSE_DB", "trading_analytics")
            }
            
            # Create ClickHouse client
            self.connections["clickhouse"] = clickhouse_connect.get_client(
                host=ch_config["host"],
                port=ch_config["port"],
                username=ch_config["username"],
                password=ch_config["password"],
                database=ch_config["database"]
            )
            
            # Create database if not exists
            self.connections["clickhouse"].command(f"CREATE DATABASE IF NOT EXISTS {ch_config['database']}")
            
            # Create time-series tables
            await self._create_clickhouse_schemas()
            
            self.logger.info("ClickHouse initialized successfully for time-series analytics")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ClickHouse: {e}")
            return False
    
    async def _create_clickhouse_schemas(self):
        """Create ClickHouse schemas for time-series data"""
        
        # Market data table
        self.connections["clickhouse"].command("""
            CREATE TABLE IF NOT EXISTS market_data (
                timestamp DateTime64(3),
                symbol String,
                price Decimal(15, 6),
                volume UInt64,
                bid_price Decimal(15, 6),
                ask_price Decimal(15, 6),
                bid_size UInt32,
                ask_size UInt32,
                data_source String,
                created_at DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMM(timestamp)
            ORDER BY (symbol, timestamp)
            SETTINGS index_granularity = 8192
        """)
        
        # Order execution metrics
        self.connections["clickhouse"].command("""
            CREATE TABLE IF NOT EXISTS order_executions (
                timestamp DateTime64(3),
                order_id String,
                symbol String,
                side Enum8('BUY' = 1, 'SELL' = 2),
                quantity Decimal(15, 6),
                price Decimal(15, 6),
                execution_time_ms UInt32,
                latency_ms UInt32,
                broker String,
                account_id String,
                strategy_id String,
                created_at DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMM(timestamp)
            ORDER BY (symbol, timestamp)
            SETTINGS index_granularity = 8192
        """)
        
        # Performance metrics table
        self.connections["clickhouse"].command("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                timestamp DateTime64(3),
                metric_type String,
                metric_name String,
                value Float64,
                labels Map(String, String),
                source String,
                created_at DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            PARTITION BY toYYYYMM(timestamp)
            ORDER BY (metric_type, metric_name, timestamp)
            SETTINGS index_granularity = 8192
        """)
    
    async def _initialize_redis(self) -> bool:
        """Initialize Redis for caching and session management"""
        try:
            # Redis configuration
            redis_config = {
                "host": os.getenv("REDIS_HOST", "localhost"),
                "port": int(os.getenv("REDIS_PORT", 6379)),
                "password": os.getenv("REDIS_PASSWORD", "redis_password_2024"),
                "db": int(os.getenv("REDIS_DB", 0)),
            }
            
            # Create Redis connection pool
            self.connections["redis"] = redis.Redis(
                host=redis_config["host"],
                port=redis_config["port"],
                password=redis_config["password"],
                db=redis_config["db"],
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            # Test connection
            await self.connections["redis"].ping()
            
            # Set up cache namespaces
            await self._setup_redis_namespaces()
            
            self.logger.info("Redis initialized successfully for caching and sessions")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis: {e}")
            return False
    
    async def _setup_redis_namespaces(self):
        """Set up Redis namespaces and default configurations"""
        
        # Cache configurations
        cache_configs = {
            "market_data": {"ttl": 300},  # 5 minutes
            "user_sessions": {"ttl": 86400},  # 24 hours
            "strategy_cache": {"ttl": 3600},  # 1 hour
            "api_rate_limits": {"ttl": 60},  # 1 minute
            "broker_data": {"ttl": 600},  # 10 minutes
        }
        
        for namespace, config in cache_configs.items():
            await self.connections["redis"].hset(
                f"config:{namespace}",
                mapping=config
            )
    
    async def _initialize_qdrant(self) -> bool:
        """Initialize Qdrant for vector similarity search"""
        try:
            # Qdrant configuration
            qdrant_config = {
                "host": os.getenv("QDRANT_HOST", "localhost"),
                "port": int(os.getenv("QDRANT_PORT", 6333)),
                "api_key": os.getenv("QDRANT_API_KEY", None),
            }
            
            # Create Qdrant client
            self.connections["qdrant"] = QdrantClient(
                host=qdrant_config["host"],
                port=qdrant_config["port"],
                api_key=qdrant_config["api_key"]
            )
            
            # Create collections for different use cases
            await self._create_qdrant_collections()
            
            self.logger.info("Qdrant initialized successfully for vector search")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Qdrant: {e}")
            return False
    
    async def _create_qdrant_collections(self):
        """Create Qdrant collections for different vector search use cases"""
        
        collections = [
            {
                "name": "strategy_embeddings",
                "size": 1536,  # OpenAI embedding size
                "distance": Distance.COSINE,
                "description": "Strategy similarity search"
            },
            {
                "name": "market_patterns",
                "size": 768,
                "distance": Distance.COSINE,
                "description": "Market pattern recognition"
            },
            {
                "name": "document_embeddings",
                "size": 1536,
                "distance": Distance.COSINE,
                "description": "Document and knowledge search"
            }
        ]
        
        for collection in collections:
            try:
                self.connections["qdrant"].create_collection(
                    collection_name=collection["name"],
                    vectors_config=VectorParams(
                        size=collection["size"],
                        distance=collection["distance"]
                    )
                )
                self.logger.info(f"Created Qdrant collection: {collection['name']}")
            except Exception as e:
                if "already exists" not in str(e):
                    self.logger.warning(f"Could not create collection {collection['name']}: {e}")
    
    async def _initialize_duckdb(self) -> bool:
        """Initialize DuckDB for OLAP queries"""
        try:
            # DuckDB configuration (in-memory for development, file-based for production)
            db_path = os.getenv("DUCKDB_PATH", ":memory:")
            
            # Create DuckDB connection
            self.connections["duckdb"] = duckdb.connect(db_path)
            
            # Create analytics schemas
            await self._create_duckdb_schemas()
            
            self.logger.info("DuckDB initialized successfully for OLAP queries")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize DuckDB: {e}")
            return False
    
    async def _create_duckdb_schemas(self):
        """Create DuckDB schemas for analytics"""
        
        # Portfolio analytics view
        self.connections["duckdb"].execute("""
            CREATE TABLE IF NOT EXISTS portfolio_analytics (
                timestamp TIMESTAMP,
                user_id INTEGER,
                account_id VARCHAR,
                total_value DECIMAL(15,2),
                cash_balance DECIMAL(15,2),
                positions_value DECIMAL(15,2),
                daily_pnl DECIMAL(15,2),
                total_return DECIMAL(10,4),
                sharpe_ratio DECIMAL(10,4),
                max_drawdown DECIMAL(10,4),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Strategy performance analytics
        self.connections["duckdb"].execute("""
            CREATE TABLE IF NOT EXISTS strategy_performance (
                strategy_id VARCHAR,
                backtest_id VARCHAR,
                start_date DATE,
                end_date DATE,
                total_return DECIMAL(10,4),
                annual_return DECIMAL(10,4),
                volatility DECIMAL(10,4),
                sharpe_ratio DECIMAL(10,4),
                sortino_ratio DECIMAL(10,4),
                max_drawdown DECIMAL(10,4),
                win_rate DECIMAL(10,4),
                profit_factor DECIMAL(10,4),
                total_trades INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    async def _validate_all_performance(self) -> Dict[str, bool]:
        """Validate performance across all databases"""
        self.logger.info("Validating database performance...")
        
        results = {}
        
        # Test each database
        for db_type in ["postgresql", "clickhouse", "redis", "qdrant", "duckdb"]:
            try:
                metrics = await self._benchmark_database(db_type)
                self.performance_metrics.append(metrics)
                
                # Check against targets
                targets = self.performance_targets[db_type]
                connection_ok = metrics.connection_time_ms <= targets["connection_ms"]
                query_ok = metrics.query_time_ms <= targets["query_ms"]
                
                results[f"{db_type}_performance"] = connection_ok and query_ok
                
                self.logger.info(
                    f"{db_type.upper()} Performance: "
                    f"Connection: {metrics.connection_time_ms:.2f}ms "
                    f"({'✓' if connection_ok else '✗'}), "
                    f"Query: {metrics.query_time_ms:.2f}ms "
                    f"({'✓' if query_ok else '✗'})"
                )
                
            except Exception as e:
                self.logger.error(f"Performance validation failed for {db_type}: {e}")
                results[f"{db_type}_performance"] = False
        
        return results
    
    async def _benchmark_database(self, db_type: str) -> DatabasePerformanceMetrics:
        """Benchmark individual database performance"""
        
        start_time = time.time()
        
        try:
            if db_type == "postgresql":
                return await self._benchmark_postgresql()
            elif db_type == "clickhouse":
                return await self._benchmark_clickhouse()
            elif db_type == "redis":
                return await self._benchmark_redis()
            elif db_type == "qdrant":
                return await self._benchmark_qdrant()
            elif db_type == "duckdb":
                return await self._benchmark_duckdb()
        except Exception as e:
            return DatabasePerformanceMetrics(
                db_type=db_type,
                connection_time_ms=0,
                query_time_ms=0,
                throughput_ops_per_sec=0,
                success_rate=0,
                error_count=1,
                timestamp=datetime.now()
            )
    
    async def _benchmark_postgresql(self) -> DatabasePerformanceMetrics:
        """Benchmark PostgreSQL performance"""
        connection_start = time.time()
        
        async with self.session_makers["postgresql"]() as session:
            connection_time = (time.time() - connection_start) * 1000
            
            # Simple query benchmark
            query_start = time.time()
            result = await session.execute(sa.text("SELECT 1"))
            query_time = (time.time() - query_start) * 1000
            
            return DatabasePerformanceMetrics(
                db_type="postgresql",
                connection_time_ms=connection_time,
                query_time_ms=query_time,
                throughput_ops_per_sec=1000 / query_time if query_time > 0 else 0,
                success_rate=1.0,
                error_count=0,
                timestamp=datetime.now()
            )
    
    async def _benchmark_clickhouse(self) -> DatabasePerformanceMetrics:
        """Benchmark ClickHouse performance"""
        connection_start = time.time()
        connection_time = (time.time() - connection_start) * 1000
        
        # Query benchmark
        query_start = time.time()
        result = self.connections["clickhouse"].query("SELECT 1")
        query_time = (time.time() - query_start) * 1000
        
        return DatabasePerformanceMetrics(
            db_type="clickhouse",
            connection_time_ms=connection_time,
            query_time_ms=query_time,
            throughput_ops_per_sec=1000 / query_time if query_time > 0 else 0,
            success_rate=1.0,
            error_count=0,
            timestamp=datetime.now()
        )
    
    async def _benchmark_redis(self) -> DatabasePerformanceMetrics:
        """Benchmark Redis performance"""
        connection_start = time.time()
        
        # Test basic operations
        query_start = time.time()
        await self.connections["redis"].set("benchmark_key", "test_value")
        await self.connections["redis"].get("benchmark_key")
        await self.connections["redis"].delete("benchmark_key")
        query_time = (time.time() - query_start) * 1000
        
        connection_time = (time.time() - connection_start) * 1000
        
        return DatabasePerformanceMetrics(
            db_type="redis",
            connection_time_ms=connection_time,
            query_time_ms=query_time,
            throughput_ops_per_sec=3000 / query_time if query_time > 0 else 0,  # 3 operations
            success_rate=1.0,
            error_count=0,
            timestamp=datetime.now()
        )
    
    async def _benchmark_qdrant(self) -> DatabasePerformanceMetrics:
        """Benchmark Qdrant performance"""
        connection_start = time.time()
        
        # Test basic operations
        query_start = time.time()
        try:
            collections = self.connections["qdrant"].get_collections()
            query_time = (time.time() - query_start) * 1000
        except:
            query_time = 100  # Default if service not available
        
        connection_time = (time.time() - connection_start) * 1000
        
        return DatabasePerformanceMetrics(
            db_type="qdrant",
            connection_time_ms=connection_time,
            query_time_ms=query_time,
            throughput_ops_per_sec=1000 / query_time if query_time > 0 else 0,
            success_rate=1.0,
            error_count=0,
            timestamp=datetime.now()
        )
    
    async def _benchmark_duckdb(self) -> DatabasePerformanceMetrics:
        """Benchmark DuckDB performance"""
        connection_start = time.time()
        
        # Test query
        query_start = time.time()
        self.connections["duckdb"].execute("SELECT 1").fetchall()
        query_time = (time.time() - query_start) * 1000
        
        connection_time = (time.time() - connection_start) * 1000
        
        return DatabasePerformanceMetrics(
            db_type="duckdb",
            connection_time_ms=connection_time,
            query_time_ms=query_time,
            throughput_ops_per_sec=1000 / query_time if query_time > 0 else 0,
            success_rate=1.0,
            error_count=0,
            timestamp=datetime.now()
        )
    
    async def get_connection(self, db_type: str):
        """Get database connection by type"""
        return self.connections.get(db_type)
    
    async def get_session(self, db_type: str = "postgresql"):
        """Get database session (for PostgreSQL)"""
        if db_type in self.session_makers:
            return self.session_makers[db_type]()
        return None
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        if not self.performance_metrics:
            return {"status": "No metrics available"}
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "details": [],
            "performance_status": "PASS"
        }
        
        for metric in self.performance_metrics:
            report["details"].append({
                "database": metric.db_type,
                "connection_time_ms": metric.connection_time_ms,
                "query_time_ms": metric.query_time_ms,
                "throughput_ops_per_sec": metric.throughput_ops_per_sec,
                "success_rate": metric.success_rate,
                "target_met": self._check_target_met(metric)
            })
            
            # Check if any database failed targets
            if not self._check_target_met(metric):
                report["performance_status"] = "NEEDS_OPTIMIZATION"
        
        # Summary statistics
        total_databases = len(self.performance_metrics)
        passed_databases = sum(1 for m in self.performance_metrics if self._check_target_met(m))
        
        report["summary"] = {
            "total_databases": total_databases,
            "passed_performance": passed_databases,
            "success_rate": (passed_databases / total_databases) * 100 if total_databases > 0 else 0,
            "avg_connection_time": sum(m.connection_time_ms for m in self.performance_metrics) / total_databases,
            "avg_query_time": sum(m.query_time_ms for m in self.performance_metrics) / total_databases
        }
        
        return report
    
    def _check_target_met(self, metric: DatabasePerformanceMetrics) -> bool:
        """Check if performance metric meets targets"""
        targets = self.performance_targets.get(metric.db_type, {})
        connection_ok = metric.connection_time_ms <= targets.get("connection_ms", float('inf'))
        query_ok = metric.query_time_ms <= targets.get("query_ms", float('inf'))
        return connection_ok and query_ok
    
    async def close_all_connections(self):
        """Close all database connections"""
        self.logger.info("Closing all database connections...")
        
        try:
            # Close PostgreSQL
            if "postgresql" in self.engines:
                await self.engines["postgresql"].dispose()
            
            # Close Redis
            if "redis" in self.connections:
                await self.connections["redis"].close()
            
            # Close ClickHouse
            if "clickhouse" in self.connections:
                self.connections["clickhouse"].close()
            
            # Close DuckDB
            if "duckdb" in self.connections:
                self.connections["duckdb"].close()
            
            self.logger.info("All database connections closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error closing database connections: {e}")

# Global database manager instance
database_manager = DatabaseManager()

# Context manager for database operations
@asynccontextmanager
async def get_db_session(db_type: str = "postgresql"):
    """Context manager for database sessions"""
    session = await database_manager.get_session(db_type)
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

# Utility functions
async def init_databases() -> Dict[str, bool]:
    """Initialize all databases - convenience function"""
    return await database_manager.initialize_all_databases()

async def get_performance_report() -> Dict[str, Any]:
    """Get database performance report - convenience function"""
    return database_manager.get_performance_report()

if __name__ == "__main__":
    async def main():
        # Initialize databases
        results = await init_databases()
        print("Database Initialization Results:")
        for db, status in results.items():
            print(f"  {db}: {'✓' if status else '✗'}")
        
        # Generate performance report
        report = await get_performance_report()
        print(f"\nPerformance Report:")
        print(f"  Status: {report.get('performance_status', 'UNKNOWN')}")
        print(f"  Success Rate: {report.get('summary', {}).get('success_rate', 0):.1f}%")
        
        # Close connections
        await database_manager.close_all_connections()
    
    asyncio.run(main())