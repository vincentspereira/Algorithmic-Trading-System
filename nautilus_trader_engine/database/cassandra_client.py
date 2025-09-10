"""
Cassandra Integration for Storage with Vector Search
Implements Cassandra client for scalable storage and vector search capabilities

This module provides:
- Cassandra client for scalable storage
- Vector search capabilities for market data patterns
- Time-series data storage
- Performance optimization and connection management

Author: Vincent S. Pereira
Version: 1.0.0
Phase: 1 - Core System Validation & Hardening
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json
import os
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

# Cassandra client
try:
    from cassandra.cluster import Cluster, Session
    from cassandra.auth import PlainTextAuthProvider
    from cassandra.policies import DCAwareRoundRobinPolicy, TokenAwarePolicy
    from cassandra.query import SimpleStatement, BatchStatement
    from cassandra import ConsistencyLevel
    from cassandra.cqlengine import connection
    from cassandra.cqlengine.models import Model
    from cassandra.cqlengine import columns
    CASSANDRA_AVAILABLE = True
except ImportError:
    CASSANDRA_AVAILABLE = False
    logging.warning("Cassandra client not available. Install with: pip install cassandra-driver")

logger = logging.getLogger(__name__)

@dataclass
class CassandraConfig:
    """Cassandra configuration"""
    contact_points: List[str]
    port: int = 9042
    username: Optional[str] = None
    password: Optional[str] = None
    keyspace: str = "trading_system"
    local_dc: Optional[str] = None
    protocol_version: int = 4
    connect_timeout: int = 30
    request_timeout: int = 30

@dataclass
class TimeSeriesData:
    """Time series data for Cassandra storage"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    metadata: Dict[str, Any] = None

@dataclass
class VectorData:
    """Vector data for similarity search"""
    id: str
    vector: List[float]
    metadata: Dict[str, Any] = None
    created_at: datetime = None

class CassandraManager:
    """
    Cassandra manager for scalable storage and vector search
    """
    
    def __init__(self, config: Optional[CassandraConfig] = None):
        self.config = config or self._default_config()
        self.cluster = None
        self.session = None
        self.initialized = False
        self.logger = logging.getLogger(__name__)
        
        if not CASSANDRA_AVAILABLE:
            self.logger.error("Cassandra client not available. Storage will be limited.")
    
    def _default_config(self) -> CassandraConfig:
        """Default Cassandra configuration"""
        contact_points = os.getenv("CASSANDRA_CONTACT_POINTS", "localhost")
        return CassandraConfig(
            contact_points=[cp.strip() for cp in contact_points.split(",") if cp.strip()],
            port=int(os.getenv("CASSANDRA_PORT", "9042")),
            username=os.getenv("CASSANDRA_USERNAME"),
            password=os.getenv("CASSANDRA_PASSWORD"),
            keyspace=os.getenv("CASSANDRA_KEYSPACE", "trading_system"),
            local_dc=os.getenv("CASSANDRA_LOCAL_DC"),
            connect_timeout=int(os.getenv("CASSANDRA_CONNECT_TIMEOUT", "30")),
            request_timeout=int(os.getenv("CASSANDRA_REQUEST_TIMEOUT", "30"))
        )
    
    async def initialize(self) -> bool:
        """Initialize Cassandra client and keyspace"""
        if not CASSANDRA_AVAILABLE:
            self.logger.warning("Cassandra not available - using fallback storage")
            return await self._initialize_fallback()
        
        try:
            # Create authentication provider if credentials provided
            auth_provider = None
            if self.config.username and self.config.password:
                auth_provider = PlainTextAuthProvider(
                    username=self.config.username,
                    password=self.config.password
                )
            
            # Create load balancing policy
            load_balancing_policy = TokenAwarePolicy(
                DCAwareRoundRobinPolicy(local_dc=self.config.local_dc)
                if self.config.local_dc else DCAwareRoundRobinPolicy()
            )
            
            # Create cluster
            self.cluster = Cluster(
                contact_points=self.config.contact_points,
                port=self.config.port,
                auth_provider=auth_provider,
                load_balancing_policy=load_balancing_policy,
                protocol_version=self.config.protocol_version,
                connect_timeout=self.config.connect_timeout
            )
            
            # Create session
            self.session = self.cluster.connect()
            
            # Create keyspace if not exists
            self._create_keyspace()
            
            # Set keyspace
            self.session.set_keyspace(self.config.keyspace)
            
            # Create tables
            await self._create_tables()
            
            self.initialized = True
            self.logger.info("Cassandra initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Cassandra: {e}")
            return await self._initialize_fallback()
    
    async def _initialize_fallback(self) -> bool:
        """Initialize fallback storage without Cassandra"""
        try:
            # Use file-based storage as fallback
            import os
            import json
            storage_dir = "cassandra_storage"
            os.makedirs(storage_dir, exist_ok=True)
            
            self.storage_path = os.path.join(storage_dir, f"{self.config.keyspace}.json")
            
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
            self.logger.info("Fallback Cassandra storage initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize fallback Cassandra storage: {e}")
            return False
    
    def _create_keyspace(self):
        """Create keyspace if not exists"""
        replication_strategy = "{'class': 'SimpleStrategy', 'replication_factor': 1}"
        if self.config.local_dc:
            replication_strategy = "{'class': 'NetworkTopologyStrategy', 'replication_factor': 1}"
        
        self.session.execute(f"""
            CREATE KEYSPACE IF NOT EXISTS {self.config.keyspace}
            WITH replication = {replication_strategy}
        """)
    
    async def _create_tables(self):
        """Create Cassandra tables for different use cases"""
        try:
            # Time series data table (partitioned by symbol, clustered by timestamp)
            self.session.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    symbol text,
                    timestamp timestamp,
                    open double,
                    high double,
                    low double,
                    close double,
                    volume bigint,
                    metadata text,
                    PRIMARY KEY (symbol, timestamp)
                ) WITH CLUSTERING ORDER BY (timestamp DESC)
            """)
            
            # Vector data table for similarity search
            self.session.execute("""
                CREATE TABLE IF NOT EXISTS vector_data (
                    id text PRIMARY KEY,
                    vector list<double>,
                    metadata text,
                    created_at timestamp
                )
            """)
            
            # Strategy patterns table
            self.session.execute("""
                CREATE TABLE IF NOT EXISTS strategy_patterns (
                    pattern_id text,
                    symbol text,
                    timestamp timestamp,
                    pattern_type text,
                    confidence double,
                    parameters text,
                    PRIMARY KEY (pattern_id, symbol, timestamp)
                ) WITH CLUSTERING ORDER BY (symbol ASC, timestamp DESC)
            """)
            
            # Create indexes for vector search if Cassandra version supports it
            try:
                # For newer Cassandra versions with vector search support
                self.session.execute("""
                    CREATE CUSTOM INDEX IF NOT EXISTS vector_data_index 
                    ON vector_data (vector) 
                    USING 'StorageAttachedIndex'
                """)
            except Exception:
                # Fallback for older versions
                self.logger.info("Vector search index not supported, using regular queries")
            
            self.logger.info("Cassandra tables created successfully")
        except Exception as e:
            self.logger.warning(f"Could not create Cassandra tables: {e}")
    
    async def insert_time_series_data(self, data: TimeSeriesData) -> bool:
        """Insert time series data into Cassandra"""
        try:
            if not self.initialized:
                return False
            
            if self.session:
                # Insert into Cassandra
                query = """
                    INSERT INTO market_data 
                    (symbol, timestamp, open, high, low, close, volume, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                statement = self.session.prepare(query)
                statement.consistency_level = ConsistencyLevel.LOCAL_QUORUM
                
                metadata_str = json.dumps(data.metadata) if data.metadata else None
                
                self.session.execute(statement, (
                    data.symbol,
                    data.timestamp,
                    data.open,
                    data.high,
                    data.low,
                    data.close,
                    data.volume,
                    metadata_str
                ))
            else:
                # Fallback to file storage
                table_name = "market_data"
                if table_name not in self.fallback_data:
                    self.fallback_data[table_name] = []
                
                # Add to fallback data
                data_dict = asdict(data)
                # Convert datetime to string for JSON serialization
                if "timestamp" in data_dict and data_dict["timestamp"] is not None:
                    data_dict["timestamp"] = data_dict["timestamp"].isoformat()
                self.fallback_data[table_name].append(data_dict)
                
                # Save to file
                with open(self.storage_path, "w") as f:
                    json.dump(self.fallback_data, f, default=str)
                
                self.logger.info(f"Fallback inserted time series data for {data.symbol}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to insert time series data: {e}")
            return False
    
    async def query_time_series_data(self, symbol: str, start_time: datetime, 
                                   end_time: datetime) -> List[TimeSeriesData]:
        """Query time series data from Cassandra"""
        try:
            if not self.initialized:
                return []
            
            data_points = []
            if self.session:
                # Query from Cassandra
                query = """
                    SELECT symbol, timestamp, open, high, low, close, volume, metadata
                    FROM market_data
                    WHERE symbol = ? AND timestamp >= ? AND timestamp <= ?
                    ORDER BY timestamp DESC
                """
                statement = self.session.prepare(query)
                statement.consistency_level = ConsistencyLevel.LOCAL_QUORUM
                
                rows = self.session.execute(statement, (symbol, start_time, end_time))
                
                for row in rows:
                    metadata = json.loads(row.metadata) if row.metadata else None
                    data_points.append(TimeSeriesData(
                        symbol=row.symbol,
                        timestamp=row.timestamp,
                        open=row.open,
                        high=row.high,
                        low=row.low,
                        close=row.close,
                        volume=row.volume,
                        metadata=metadata
                    ))
            else:
                # Fallback to file storage
                table_name = "market_data"
                if table_name in self.fallback_data:
                    for data_dict in self.fallback_data[table_name]:
                        data_timestamp = datetime.fromisoformat(data_dict["timestamp"])
                        if (data_dict["symbol"] == symbol and 
                            start_time <= data_timestamp <= end_time):
                            data_points.append(TimeSeriesData(**data_dict))
            
            return data_points
        except Exception as e:
            self.logger.error(f"Failed to query time series data: {e}")
            return []
    
    async def insert_vector_data(self, data: VectorData) -> bool:
        """Insert vector data for similarity search"""
        try:
            if not self.initialized:
                return False
            
            if self.session:
                # Insert into Cassandra
                query = """
                    INSERT INTO vector_data 
                    (id, vector, metadata, created_at)
                    VALUES (?, ?, ?, ?)
                """
                statement = self.session.prepare(query)
                statement.consistency_level = ConsistencyLevel.LOCAL_QUORUM
                
                metadata_str = json.dumps(data.metadata) if data.metadata else None
                created_at = data.created_at or datetime.now()
                
                self.session.execute(statement, (
                    data.id,
                    data.vector,
                    metadata_str,
                    created_at
                ))
            else:
                # Fallback to file storage
                table_name = "vector_data"
                if table_name not in self.fallback_data:
                    self.fallback_data[table_name] = []
                
                # Add to fallback data
                data_dict = asdict(data)
                data_dict["created_at"] = data.created_at.isoformat() if data.created_at else datetime.now().isoformat()
                self.fallback_data[table_name].append(data_dict)
                
                # Save to file
                with open(self.storage_path, "w") as f:
                    json.dump(self.fallback_data, f, default=str)
                
                self.logger.info(f"Fallback inserted vector data with ID: {data.id}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to insert vector data: {e}")
            return False
    
    async def search_similar_vectors(self, query_vector: List[float], limit: int = 10) -> List[Dict]:
        """Search for similar vectors (simplified implementation)"""
        try:
            if not self.initialized:
                return []
            
            results = []
            if self.session:
                # Simple implementation - in a real system, this would use vector search capabilities
                query = """
                    SELECT id, vector, metadata, created_at
                    FROM vector_data
                    LIMIT ?
                """
                statement = self.session.prepare(query)
                statement.consistency_level = ConsistencyLevel.LOCAL_QUORUM
                
                rows = self.session.execute(statement, (limit,))
                
                for row in rows:
                    metadata = json.loads(row.metadata) if row.metadata else None
                    results.append({
                        "id": row.id,
                        "vector": row.vector,
                        "metadata": metadata,
                        "created_at": row.created_at
                    })
            else:
                # Fallback to file storage
                table_name = "vector_data"
                if table_name in self.fallback_data:
                    # Simple approach - return first N items
                    for i, data_dict in enumerate(self.fallback_data[table_name]):
                        if i >= limit:
                            break
                        results.append(data_dict)
            
            return results
        except Exception as e:
            self.logger.error(f"Failed to search similar vectors: {e}")
            return []
    
    async def batch_insert_time_series(self, data_list: List[TimeSeriesData]) -> bool:
        """Batch insert time series data for better performance"""
        try:
            if not self.initialized:
                return False
            
            if self.session:
                # Batch insert into Cassandra
                batch = BatchStatement(consistency_level=ConsistencyLevel.LOCAL_QUORUM)
                query = """
                    INSERT INTO market_data 
                    (symbol, timestamp, open, high, low, close, volume, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                statement = self.session.prepare(query)
                
                for data in data_list:
                    metadata_str = json.dumps(data.metadata) if data.metadata else None
                    batch.add(statement, (
                        data.symbol,
                        data.timestamp,
                        data.open,
                        data.high,
                        data.low,
                        data.close,
                        data.volume,
                        metadata_str
                    ))
                
                self.session.execute(batch)
            else:
                # Fallback to file storage
                table_name = "market_data"
                if table_name not in self.fallback_data:
                    self.fallback_data[table_name] = []
                
                # Add all to fallback data
                for data in data_list:
                    data_dict = asdict(data)
                    # Convert datetime to string for JSON serialization
                    if "timestamp" in data_dict and data_dict["timestamp"] is not None:
                        data_dict["timestamp"] = data_dict["timestamp"].isoformat()
                    self.fallback_data[table_name].append(data_dict)
                
                # Save to file
                with open(self.storage_path, "w") as f:
                    json.dump(self.fallback_data, f, default=str)
                
                self.logger.info(f"Fallback batch inserted {len(data_list)} time series data points")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to batch insert time series data: {e}")
            return False
    
    async def close(self):
        """Close Cassandra connection"""
        if self.session:
            self.session.shutdown()
        if self.cluster:
            self.cluster.shutdown()
        self.logger.info("Cassandra connection closed")


# Global Cassandra manager instance
cassandra_manager = CassandraManager()

# Convenience functions
async def init_cassandra(config: Optional[CassandraConfig] = None) -> bool:
    """Initialize Cassandra - convenience function"""
    if config:
        cassandra_manager.config = config
    return await cassandra_manager.initialize()

async def insert_time_series_data(data: TimeSeriesData) -> bool:
    """Insert time series data - convenience function"""
    return await cassandra_manager.insert_time_series_data(data)

async def query_time_series_data(symbol: str, start_time: datetime, 
                               end_time: datetime) -> List[TimeSeriesData]:
    """Query time series data - convenience function"""
    return await cassandra_manager.query_time_series_data(symbol, start_time, end_time)

async def insert_vector_data(data: VectorData) -> bool:
    """Insert vector data - convenience function"""
    return await cassandra_manager.insert_vector_data(data)

async def search_similar_vectors(query_vector: List[float], limit: int = 10) -> List[Dict]:
    """Search similar vectors - convenience function"""
    return await cassandra_manager.search_similar_vectors(query_vector, limit)

async def batch_insert_time_series(data_list: List[TimeSeriesData]) -> bool:
    """Batch insert time series data - convenience function"""
    return await cassandra_manager.batch_insert_time_series(data_list)

if __name__ == "__main__":
    async def main():
        # Initialize Cassandra
        success = await init_cassandra()
        print(f"Cassandra initialization: {'✓' if success else '✗'}")
        
        if success:
            # Test time series data insertion
            ts_data = TimeSeriesData(
                symbol="AAPL",
                timestamp=datetime.now(),
                open=150.0,
                high=155.0,
                low=149.0,
                close=153.0,
                volume=1000000,
                metadata={"source": "test", "interval": "1min"}
            )
            insert_success = await insert_time_series_data(ts_data)
            print(f"Time series data insertion: {'✓' if insert_success else '✗'}")
            
            # Test vector data insertion
            vector_data = VectorData(
                id="test_vector_1",
                vector=[0.1, 0.2, 0.3, 0.4, 0.5],
                metadata={"type": "market_pattern", "symbol": "AAPL"}
            )
            vector_success = await insert_vector_data(vector_data)
            print(f"Vector data insertion: {'✓' if vector_success else '✗'}")
            
            # Close connection
            await cassandra_manager.close()
    
    asyncio.run(main())
