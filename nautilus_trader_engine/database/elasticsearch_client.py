"""
Elasticsearch Integration for Search/Logs/Metrics/RAG
Implements distributed search and analytics engine for the trading system

This module provides:
- Elasticsearch client for search and analytics
- Log indexing and search capabilities
- Metrics storage and retrieval
- RAG (Retrieval-Augmented Generation) support
- Performance optimization and connection management

Author: Vincent S. Pereira
Version: 1.0.0
Phase: 1 - Core System Validation & Hardening
"""

import asyncio
import logging
import os
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

# Elasticsearch client
try:
    from elasticsearch import AsyncElasticsearch
    from elasticsearch.helpers import async_bulk
    from elasticsearch.exceptions import ConnectionError, RequestError
    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False
    logging.warning("Elasticsearch client not available. Install with: pip install elasticsearch[async]")

logger = logging.getLogger(__name__)

@dataclass
class ElasticsearchConfig:
    """Elasticsearch configuration"""
    hosts: List[str]
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    cloud_id: Optional[str] = None
    use_ssl: bool = True
    verify_certs: bool = True
    ca_certs: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_on_timeout: bool = True

@dataclass
class LogEntry:
    """Structured log entry for Elasticsearch"""
    timestamp: datetime
    level: str
    service: str
    message: str
    module: str
    function: str
    line_number: int
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class MetricEntry:
    """Structured metric entry for Elasticsearch"""
    timestamp: datetime
    metric_name: str
    value: float
    unit: str
    service: str
    tags: Dict[str, str] = None
    metadata: Dict[str, Any] = None

class ElasticsearchManager:
    """
    Elasticsearch manager for search, logs, metrics, and RAG
    """
    
    def __init__(self, config: Optional[ElasticsearchConfig] = None):
        self.config = config or self._default_config()
        self.client = None
        self.initialized = False
        self.logger = logging.getLogger(__name__)
        
        if not ELASTICSEARCH_AVAILABLE:
            self.logger.error("Elasticsearch client not available. Search/logging will be limited.")
    
    def _default_config(self) -> ElasticsearchConfig:
        """Default Elasticsearch configuration"""
        return ElasticsearchConfig(
            hosts=[f"http://{host.strip()}" for host in os.getenv("ELASTICSEARCH_HOSTS", "localhost:9200").split(",")],
            username=os.getenv("ELASTICSEARCH_USERNAME"),
            password=os.getenv("ELASTICSEARCH_PASSWORD"),
            timeout=int(os.getenv("ELASTICSEARCH_TIMEOUT", "30")),
            use_ssl=os.getenv("ELASTICSEARCH_USE_SSL", "false").lower() == "true",
            verify_certs=os.getenv("ELASTICSEARCH_VERIFY_CERTS", "true").lower() == "true"
        )
    
    async def initialize(self) -> bool:
        """Initialize Elasticsearch client and indices"""
        if not ELASTICSEARCH_AVAILABLE:
            self.logger.warning("Elasticsearch not available - using fallback logging")
            return await self._initialize_fallback()
        
        try:
            # Create Elasticsearch client
            client_kwargs = {
                "hosts": self.config.hosts,
                "timeout": self.config.timeout,
                "max_retries": self.config.max_retries,
                "retry_on_timeout": self.config.retry_on_timeout,
                "use_ssl": self.config.use_ssl,
                "verify_certs": self.config.verify_certs
            }
            
            if self.config.username and self.config.password:
                client_kwargs["http_auth"] = (self.config.username, self.config.password)
            elif self.config.api_key:
                client_kwargs["api_key"] = self.config.api_key
            elif self.config.cloud_id:
                client_kwargs["cloud_id"] = self.config.cloud_id
            
            if self.config.ca_certs:
                client_kwargs["ca_certs"] = self.config.ca_certs
            
            self.client = AsyncElasticsearch(**client_kwargs)
            
            # Test connection
            await self.client.ping()
            
            # Create indices
            await self._create_indices()
            
            self.initialized = True
            self.logger.info("Elasticsearch initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Elasticsearch: {e}")
            return await self._initialize_fallback()
    
    async def _initialize_fallback(self) -> bool:
        """Initialize fallback logging without Elasticsearch"""
        try:
            # Use file-based logging as fallback
            import os
            log_dir = "elasticsearch_logs"
            os.makedirs(log_dir, exist_ok=True)
            
            self.log_file_path = os.path.join(log_dir, f"es_fallback_{datetime.now().strftime('%Y%m%d')}.jsonl")
            self.initialized = True
            self.logger.info("Fallback Elasticsearch logging initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize fallback Elasticsearch logging: {e}")
            return False
    
    async def _create_indices(self):
        """Create Elasticsearch indices for different use cases"""
        indices_config = {
            "logs": {
                "settings": {
                    "number_of_shards": 3,
                    "number_of_replicas": 1,
                    "refresh_interval": "30s"
                },
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "level": {"type": "keyword"},
                        "service": {"type": "keyword"},
                        "message": {"type": "text"},
                        "module": {"type": "keyword"},
                        "function": {"type": "keyword"},
                        "line_number": {"type": "integer"},
                        "trace_id": {"type": "keyword"},
                        "span_id": {"type": "keyword"},
                        "user_id": {"type": "keyword"},
                        "session_id": {"type": "keyword"},
                        "correlation_id": {"type": "keyword"},
                        "metadata": {"type": "object", "enabled": False}
                    }
                }
            },
            "metrics": {
                "settings": {
                    "number_of_shards": 2,
                    "number_of_replicas": 1,
                    "refresh_interval": "10s"
                },
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "metric_name": {"type": "keyword"},
                        "value": {"type": "float"},
                        "unit": {"type": "keyword"},
                        "service": {"type": "keyword"},
                        "tags": {"type": "object"},
                        "metadata": {"type": "object", "enabled": False}
                    }
                }
            },
            "documents": {
                "settings": {
                    "number_of_shards": 2,
                    "number_of_replicas": 1,
                    "refresh_interval": "30s",
                    "analysis": {
                        "analyzer": {
                            "default": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": ["lowercase", "stop", "snowball"]
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "title": {"type": "text"},
                        "content": {"type": "text"},
                        "summary": {"type": "text"},
                        "embedding": {"type": "dense_vector", "dims": 1536},
                        "document_type": {"type": "keyword"},
                        "tags": {"type": "keyword"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"},
                        "metadata": {"type": "object", "enabled": False}
                    }
                }
            }
        }
        
        for index_name, config in indices_config.items():
            try:
                exists = await self.client.indices.exists(index=index_name)
                if not exists:
                    await self.client.indices.create(index=index_name, **config)
                    self.logger.info(f"Created Elasticsearch index: {index_name}")
                else:
                    self.logger.info(f"Elasticsearch index already exists: {index_name}")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    self.logger.warning(f"Could not create index {index_name}: {e}")
    
    async def index_log(self, log_entry: LogEntry) -> bool:
        """Index a log entry"""
        try:
            if not self.initialized:
                return False
            
            if self.client:
                doc = asdict(log_entry)
                doc["timestamp"] = log_entry.timestamp.isoformat()
                if log_entry.metadata:
                    doc["metadata"] = json.dumps(log_entry.metadata)
                
                await self.client.index(
                    index="logs",
                    document=doc,
                    refresh=False
                )
            else:
                # Fallback to file logging
                with open(self.log_file_path, "a") as f:
                    f.write(json.dumps(asdict(log_entry)) + "\n")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to index log entry: {e}")
            return False
    
    async def search_logs(self, query: str, service: Optional[str] = None, 
                         level: Optional[str] = None, size: int = 100) -> List[Dict]:
        """Search log entries"""
        try:
            if not self.initialized or not self.client:
                return []
            
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "simple_query_string": {
                                    "query": query
                                }
                            }
                        ]
                    }
                },
                "sort": [{"timestamp": {"order": "desc"}}],
                "size": size
            }
            
            if service:
                search_body["query"]["bool"]["filter"] = [
                    {"term": {"service.keyword": service}}
                ]
            
            if level:
                if "filter" not in search_body["query"]["bool"]:
                    search_body["query"]["bool"]["filter"] = []
                search_body["query"]["bool"]["filter"].append(
                    {"term": {"level.keyword": level}}
                )
            
            response = await self.client.search(
                index="logs",
                body=search_body
            )
            
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as e:
            self.logger.error(f"Failed to search logs: {e}")
            return []
    
    async def index_metric(self, metric_entry: MetricEntry) -> bool:
        """Index a metric entry"""
        try:
            if not self.initialized:
                return False
            
            if self.client:
                doc = asdict(metric_entry)
                doc["timestamp"] = metric_entry.timestamp.isoformat()
                if metric_entry.tags:
                    doc["tags"] = metric_entry.tags
                if metric_entry.metadata:
                    doc["metadata"] = json.dumps(metric_entry.metadata)
                
                await self.client.index(
                    index="metrics",
                    document=doc,
                    refresh=False
                )
            else:
                # Fallback logging
                self.logger.debug(f"Fallback metric logging: {asdict(metric_entry)}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to index metric entry: {e}")
            return False
    
    async def search_documents(self, query: str, document_type: Optional[str] = None, 
                              size: int = 20) -> List[Dict]:
        """Search documents for RAG"""
        try:
            if not self.initialized or not self.client:
                return []
            
            search_body = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^2", "content", "summary"],
                                    "type": "best_fields"
                                }
                            }
                        ]
                    }
                },
                "size": size
            }
            
            if document_type:
                search_body["query"]["bool"]["filter"] = [
                    {"term": {"document_type.keyword": document_type}}
                ]
            
            response = await self.client.search(
                index="documents",
                body=search_body
            )
            
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as e:
            self.logger.error(f"Failed to search documents: {e}")
            return []
    
    async def close(self):
        """Close Elasticsearch connection"""
        if self.client:
            await self.client.close()
            self.logger.info("Elasticsearch connection closed")


# Global Elasticsearch manager instance
elasticsearch_manager = ElasticsearchManager()

# Convenience functions
async def init_elasticsearch(config: Optional[ElasticsearchConfig] = None) -> bool:
    """Initialize Elasticsearch - convenience function"""
    if config:
        elasticsearch_manager.config = config
    return await elasticsearch_manager.initialize()

async def index_log_entry(log_entry: LogEntry) -> bool:
    """Index a log entry - convenience function"""
    return await elasticsearch_manager.index_log(log_entry)

async def search_log_entries(query: str, service: Optional[str] = None, 
                           level: Optional[str] = None, size: int = 100) -> List[Dict]:
    """Search log entries - convenience function"""
    return await elasticsearch_manager.search_logs(query, service, level, size)

async def index_metric_entry(metric_entry: MetricEntry) -> bool:
    """Index a metric entry - convenience function"""
    return await elasticsearch_manager.index_metric(metric_entry)

async def search_documents(query: str, document_type: Optional[str] = None, 
                          size: int = 20) -> List[Dict]:
    """Search documents for RAG - convenience function"""
    return await elasticsearch_manager.search_documents(query, document_type, size)

if __name__ == "__main__":
    async def main():
        # Initialize Elasticsearch
        success = await init_elasticsearch()
        print(f"Elasticsearch initialization: {'✓' if success else '✗'}")
        
        if success:
            # Test log indexing
            log_entry = LogEntry(
                timestamp=datetime.now(),
                level="INFO",
                service="test_service",
                message="Test log entry",
                module="test_module",
                function="test_function",
                line_number=42
            )
            log_success = await index_log_entry(log_entry)
            print(f"Log indexing: {'✓' if log_success else '✗'}")
            
            # Test metric indexing
            metric_entry = MetricEntry(
                timestamp=datetime.now(),
                metric_name="test_metric",
                value=123.45,
                unit="ms",
                service="test_service"
            )
            metric_success = await index_metric_entry(metric_entry)
            print(f"Metric indexing: {'✓' if metric_success else '✗'}")
            
            # Close connection
            await elasticsearch_manager.close()
    
    asyncio.run(main())