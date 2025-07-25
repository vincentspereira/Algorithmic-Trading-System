"""
RAG Pipeline Configuration
Configuration settings for the RAG (Retrieval-Augmented Generation) pipeline
including document processing, embeddings, vector storage, and RAGFlow integration.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from enum import Enum


class EmbeddingProvider(Enum):
    """Supported embedding providers"""
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"


class VectorStore(Enum):
    """Supported vector storage backends"""
    QDRANT = "qdrant"
    POSTGRESQL_PGVECTOR = "postgresql_pgvector"


class ChunkingStrategy(Enum):
    """Document chunking strategies"""
    FIXED_SIZE = "fixed_size"
    SLIDING_WINDOW = "sliding_window"
    SEMANTIC = "semantic"
    RECURSIVE = "recursive"


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation"""
    provider: EmbeddingProvider = EmbeddingProvider.SENTENCE_TRANSFORMERS
    model_name: str = "all-MiniLM-L6-v2"
    dimension: int = 384
    batch_size: int = 32
    max_length: int = 512
    normalize_embeddings: bool = True
    
    # OpenAI specific settings
    openai_api_key: Optional[str] = None
    openai_model: str = "text-embedding-3-small"
    
    # HuggingFace specific settings
    hf_token: Optional[str] = None
    device: str = "cpu"  # or "cuda" if GPU available


@dataclass
class ChunkingConfig:
    """Configuration for document chunking"""
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_chunk_size: int = 100
    max_chunk_size: int = 2000
    
    # Semantic chunking specific
    semantic_threshold: float = 0.5
    
    # Sliding window specific
    window_size: int = 1000
    step_size: int = 800


@dataclass
class QdrantConfig:
    """Configuration for Qdrant vector database"""
    url: str = "http://localhost:6333"
    api_key: Optional[str] = None
    collection_name: str = "trading_documents"
    vector_size: int = 384
    distance_metric: str = "Cosine"
    
    # Performance settings
    hnsw_config: Dict = field(default_factory=lambda: {
        "m": 16,
        "ef_construct": 100,
        "full_scan_threshold": 10000
    })
    
    # Indexing settings
    payload_schema: Dict = field(default_factory=lambda: {
        "title": "keyword",
        "category": "keyword", 
        "source": "keyword",
        "date": "datetime",
        "tags": "keyword"
    })


@dataclass
class PostgreSQLConfig:
    """Configuration for PostgreSQL with pgvector"""
    host: str = "localhost"
    port: int = 5432
    database: str = "trading_system"
    username: str = "postgres"
    password: str = "postgres"
    table_name: str = "document_embeddings"
    vector_column: str = "embedding"
    dimension: int = 384
    
    # Connection pool settings
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30


@dataclass
class DocumentProcessingConfig:
    """Configuration for document processing"""
    supported_formats: List[str] = field(default_factory=lambda: [
        ".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".xlsx", ".xls"
    ])
    
    # Unstructured.io settings
    unstructured_api_key: Optional[str] = None
    unstructured_url: Optional[str] = None
    
    # Processing options
    extract_images: bool = False
    extract_tables: bool = True
    ocr_languages: List[str] = field(default_factory=lambda: ["eng"])
    
    # Content filtering
    min_content_length: int = 50
    max_content_length: int = 50000
    remove_headers_footers: bool = True
    clean_whitespace: bool = True


@dataclass
class RAGFlowConfig:
    """Configuration for RAGFlow integration"""
    enabled: bool = True
    
    # Retrieval settings
    top_k: int = 10
    similarity_threshold: float = 0.7
    rerank_enabled: bool = True
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # Query expansion
    query_expansion_enabled: bool = True
    expansion_terms: int = 3
    
    # Hybrid search
    hybrid_search_enabled: bool = True
    semantic_weight: float = 0.7
    keyword_weight: float = 0.3
    
    # Response generation
    max_context_length: int = 4000
    context_overlap: int = 100


@dataclass
class CacheConfig:
    """Configuration for caching"""
    enabled: bool = True
    cache_type: str = "redis"  # redis, memory, disk
    
    # Redis settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 1
    redis_password: Optional[str] = None
    
    # Cache TTL settings (in seconds)
    embedding_cache_ttl: int = 86400  # 24 hours
    document_cache_ttl: int = 3600    # 1 hour
    query_cache_ttl: int = 1800       # 30 minutes
    
    # Memory cache settings
    max_memory_cache_size: int = 1000


@dataclass
class RAGPipelineConfig:
    """Main RAG pipeline configuration"""
    # Core components
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    vector_store: VectorStore = VectorStore.QDRANT
    
    # Vector store configurations
    qdrant: QdrantConfig = field(default_factory=QdrantConfig)
    postgresql: PostgreSQLConfig = field(default_factory=PostgreSQLConfig)
    
    # Processing and RAGFlow
    document_processing: DocumentProcessingConfig = field(default_factory=DocumentProcessingConfig)
    ragflow: RAGFlowConfig = field(default_factory=RAGFlowConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    
    # General settings
    batch_processing_size: int = 100
    max_concurrent_requests: int = 10
    enable_monitoring: bool = True
    log_level: str = "INFO"
    
    # Fallback settings
    enable_fallback: bool = True
    fallback_vector_store: VectorStore = VectorStore.POSTGRESQL_PGVECTOR


def load_config_from_env() -> RAGPipelineConfig:
    """
    Load configuration from environment variables
    
    Returns:
        RAGPipelineConfig: Configuration loaded from environment
    """
    config = RAGPipelineConfig()
    
    # Embedding configuration
    if os.getenv("EMBEDDING_PROVIDER"):
        config.embedding.provider = EmbeddingProvider(os.getenv("EMBEDDING_PROVIDER"))
    
    config.embedding.model_name = os.getenv("EMBEDDING_MODEL", config.embedding.model_name)
    config.embedding.openai_api_key = os.getenv("OPENAI_API_KEY")
    config.embedding.hf_token = os.getenv("HUGGINGFACE_TOKEN")
    
    if os.getenv("EMBEDDING_DIMENSION"):
        config.embedding.dimension = int(os.getenv("EMBEDDING_DIMENSION"))
    
    # Vector store configuration
    if os.getenv("VECTOR_STORE"):
        config.vector_store = VectorStore(os.getenv("VECTOR_STORE"))
    
    # Qdrant configuration
    config.qdrant.url = os.getenv("QDRANT_URL", config.qdrant.url)
    config.qdrant.api_key = os.getenv("QDRANT_API_KEY")
    config.qdrant.collection_name = os.getenv("QDRANT_COLLECTION", config.qdrant.collection_name)
    
    # PostgreSQL configuration
    config.postgresql.host = os.getenv("POSTGRES_HOST", config.postgresql.host)
    config.postgresql.port = int(os.getenv("POSTGRES_PORT", config.postgresql.port))
    config.postgresql.database = os.getenv("POSTGRES_DB", config.postgresql.database)
    config.postgresql.username = os.getenv("POSTGRES_USER", config.postgresql.username)
    config.postgresql.password = os.getenv("POSTGRES_PASSWORD", config.postgresql.password)
    
    # Document processing
    config.document_processing.unstructured_api_key = os.getenv("UNSTRUCTURED_API_KEY")
    config.document_processing.unstructured_url = os.getenv("UNSTRUCTURED_API_URL")
    
    # Cache configuration
    config.cache.redis_host = os.getenv("REDIS_HOST", config.cache.redis_host)
    config.cache.redis_port = int(os.getenv("REDIS_PORT", config.cache.redis_port))
    config.cache.redis_password = os.getenv("REDIS_PASSWORD")
    
    # Chunking configuration
    if os.getenv("CHUNK_SIZE"):
        config.chunking.chunk_size = int(os.getenv("CHUNK_SIZE"))
    
    if os.getenv("CHUNK_OVERLAP"):
        config.chunking.chunk_overlap = int(os.getenv("CHUNK_OVERLAP"))
    
    # RAGFlow configuration
    if os.getenv("RAGFLOW_TOP_K"):
        config.ragflow.top_k = int(os.getenv("RAGFLOW_TOP_K"))
    
    if os.getenv("RAGFLOW_SIMILARITY_THRESHOLD"):
        config.ragflow.similarity_threshold = float(os.getenv("RAGFLOW_SIMILARITY_THRESHOLD"))
    
    return config


def get_default_config() -> RAGPipelineConfig:
    """
    Get default configuration for development/testing
    
    Returns:
        RAGPipelineConfig: Default configuration
    """
    return RAGPipelineConfig()


def validate_config(config: RAGPipelineConfig) -> List[str]:
    """
    Validate configuration and return list of issues
    
    Args:
        config: Configuration to validate
        
    Returns:
        List of validation error messages
    """
    errors = []
    
    # Validate embedding configuration
    if config.embedding.provider == EmbeddingProvider.OPENAI and not config.embedding.openai_api_key:
        errors.append("OpenAI API key is required when using OpenAI embeddings")
    
    if config.embedding.dimension <= 0:
        errors.append("Embedding dimension must be positive")
    
    # Validate chunking configuration
    if config.chunking.chunk_size <= 0:
        errors.append("Chunk size must be positive")
    
    if config.chunking.chunk_overlap >= config.chunking.chunk_size:
        errors.append("Chunk overlap must be less than chunk size")
    
    # Validate vector store configuration
    if config.vector_store == VectorStore.QDRANT:
        if not config.qdrant.url:
            errors.append("Qdrant URL is required")
        if config.qdrant.vector_size != config.embedding.dimension:
            errors.append("Qdrant vector size must match embedding dimension")
    
    elif config.vector_store == VectorStore.POSTGRESQL_PGVECTOR:
        if not config.postgresql.host:
            errors.append("PostgreSQL host is required")
        if config.postgresql.dimension != config.embedding.dimension:
            errors.append("PostgreSQL vector dimension must match embedding dimension")
    
    # Validate RAGFlow configuration
    if config.ragflow.top_k <= 0:
        errors.append("RAGFlow top_k must be positive")
    
    if not 0 <= config.ragflow.similarity_threshold <= 1:
        errors.append("RAGFlow similarity threshold must be between 0 and 1")
    
    return errors


# Global configuration instance
_config: Optional[RAGPipelineConfig] = None


def get_config() -> RAGPipelineConfig:
    """
    Get the global configuration instance
    
    Returns:
        RAGPipelineConfig: Global configuration
    """
    global _config
    if _config is None:
        _config = load_config_from_env()
    return _config


def set_config(config: RAGPipelineConfig) -> None:
    """
    Set the global configuration instance
    
    Args:
        config: Configuration to set as global
    """
    global _config
    _config = config


# Export main classes and functions
__all__ = [
    "RAGPipelineConfig",
    "EmbeddingConfig", 
    "ChunkingConfig",
    "QdrantConfig",
    "PostgreSQLConfig",
    "DocumentProcessingConfig",
    "RAGFlowConfig",
    "CacheConfig",
    "EmbeddingProvider",
    "VectorStore", 
    "ChunkingStrategy",
    "load_config_from_env",
    "get_default_config",
    "validate_config",
    "get_config",
    "set_config"
]