"""
RAG Pipeline Implementation
Main RAG (Retrieval-Augmented Generation) pipeline that integrates document processing,
embedding generation, vector storage (Qdrant/PostgreSQL), and RAGFlow for enhanced retrieval.
"""

import os
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
import json

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import psycopg2
from psycopg2.extras import RealDictCursor
import sqlalchemy
from sqlalchemy import create_engine, text
from sentence_transformers import CrossEncoder

from .rag_config import RAGPipelineConfig, VectorStore, get_config
from .document_processor import DocumentProcessor, DocumentChunk, DocumentMetadata
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result from vector similarity search"""
    chunk: DocumentChunk
    score: float
    rank: int


@dataclass
class RAGResponse:
    """Complete RAG response with context and metadata"""
    query: str
    results: List[SearchResult]
    context: str
    processing_time: float
    total_chunks_searched: int
    reranked: bool = False
    hybrid_search: bool = False


class QdrantVectorStore:
    """Qdrant vector database implementation"""
    
    def __init__(self, config: RAGPipelineConfig):
        """
        Initialize Qdrant vector store
        
        Args:
            config: RAG pipeline configuration
        """
        self.config = config
        self.qdrant_config = config.qdrant
        
        # Initialize Qdrant client
        self.client = QdrantClient(
            url=self.qdrant_config.url,
            api_key=self.qdrant_config.api_key
        )
        
        self.collection_name = self.qdrant_config.collection_name
        self.vector_size = self.qdrant_config.vector_size
        
        logger.info(f"QdrantVectorStore initialized: {self.qdrant_config.url}")
    
    def create_collection(self) -> bool:
        """
        Create Qdrant collection if it doesn't exist
        
        Returns:
            True if collection was created or already exists
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name in collection_names:
                logger.info(f"Collection '{self.collection_name}' already exists")
                return True
            
            # Create collection
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                ),
                hnsw_config=models.HnswConfigDiff(**self.qdrant_config.hnsw_config)
            )
            
            logger.info(f"Created Qdrant collection: {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating Qdrant collection: {e}")
            return False
    
    def add_chunks(self, chunks: List[DocumentChunk]) -> bool:
        """
        Add document chunks to Qdrant collection
        
        Args:
            chunks: List of document chunks with embeddings
            
        Returns:
            True if successful
        """
        try:
            if not chunks:
                return True
            
            # Prepare points for insertion
            points = []
            for chunk in chunks:
                if chunk.embedding is None:
                    logger.warning(f"Chunk {chunk.chunk_id} has no embedding, skipping")
                    continue
                
                # Prepare payload with metadata
                payload = {
                    "content": chunk.content,
                    "title": chunk.metadata.title,
                    "source": chunk.metadata.source,
                    "category": chunk.metadata.category,
                    "tags": chunk.metadata.tags,
                    "file_type": chunk.metadata.file_type,
                    "chunk_index": chunk.chunk_index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "created_date": chunk.metadata.created_date.isoformat() if chunk.metadata.created_date else None,
                    "word_count": chunk.metadata.word_count,
                    "checksum": chunk.metadata.checksum
                }
                
                point = PointStruct(
                    id=hash(chunk.chunk_id) % (2**63),  # Convert string ID to int
                    vector=chunk.embedding,
                    payload=payload
                )
                points.append(point)
            
            # Insert points in batches
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch_points = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch_points
                )
            
            logger.info(f"Added {len(points)} chunks to Qdrant collection")
            return True
            
        except Exception as e:
            logger.error(f"Error adding chunks to Qdrant: {e}")
            return False
    
    def search(self, query_embedding: List[float], top_k: int = 10, 
               filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """
        Search for similar chunks using vector similarity
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filters: Optional filters for metadata
            
        Returns:
            List of search results
        """
        try:
            # Prepare filter conditions
            query_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    if isinstance(value, list):
                        conditions.append(models.FieldCondition(
                            key=key,
                            match=models.MatchAny(any=value)
                        ))
                    else:
                        conditions.append(models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        ))
                
                if conditions:
                    query_filter = models.Filter(must=conditions)
            
            # Perform search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True
            )
            
            # Convert to SearchResult objects
            results = []
            for i, result in enumerate(search_results):
                payload = result.payload
                
                # Reconstruct DocumentMetadata
                metadata = DocumentMetadata(
                    title=payload.get("title", ""),
                    source=payload.get("source", ""),
                    file_type=payload.get("file_type", ""),
                    file_size=0,  # Not stored in payload
                    created_date=datetime.fromisoformat(payload["created_date"]) if payload.get("created_date") else None,
                    category=payload.get("category", "general"),
                    tags=payload.get("tags", []),
                    word_count=payload.get("word_count", 0),
                    checksum=payload.get("checksum", "")
                )
                
                # Reconstruct DocumentChunk
                chunk = DocumentChunk(
                    content=payload.get("content", ""),
                    metadata=metadata,
                    chunk_id=str(result.id),
                    chunk_index=payload.get("chunk_index", 0),
                    start_char=payload.get("start_char", 0),
                    end_char=payload.get("end_char", 0)
                )
                
                search_result = SearchResult(
                    chunk=chunk,
                    score=result.score,
                    rank=i + 1
                )
                results.append(search_result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching Qdrant: {e}")
            return []
    
    def delete_collection(self) -> bool:
        """Delete the collection"""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Deleted Qdrant collection: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting Qdrant collection: {e}")
            return False
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {}


class PostgreSQLVectorStore:
    """PostgreSQL with pgvector implementation"""
    
    def __init__(self, config: RAGPipelineConfig):
        """
        Initialize PostgreSQL vector store
        
        Args:
            config: RAG pipeline configuration
        """
        self.config = config
        self.pg_config = config.postgresql
        
        # Create connection string
        self.connection_string = (
            f"postgresql://{self.pg_config.username}:{self.pg_config.password}"
            f"@{self.pg_config.host}:{self.pg_config.port}/{self.pg_config.database}"
        )
        
        # Create SQLAlchemy engine
        self.engine = create_engine(
            self.connection_string,
            pool_size=self.pg_config.pool_size,
            max_overflow=self.pg_config.max_overflow,
            pool_timeout=self.pg_config.pool_timeout
        )
        
        logger.info(f"PostgreSQLVectorStore initialized: {self.pg_config.host}:{self.pg_config.port}")
    
    def create_table(self) -> bool:
        """
        Create the embeddings table if it doesn't exist
        
        Returns:
            True if table was created or already exists
        """
        try:
            with self.engine.connect() as conn:
                # Enable pgvector extension
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                
                # Create table
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.pg_config.table_name} (
                    id SERIAL PRIMARY KEY,
                    chunk_id VARCHAR(255) UNIQUE NOT NULL,
                    content TEXT NOT NULL,
                    {self.pg_config.vector_column} vector({self.pg_config.dimension}),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_{self.pg_config.table_name}_vector 
                ON {self.pg_config.table_name} 
                USING ivfflat ({self.pg_config.vector_column} vector_cosine_ops);
                
                CREATE INDEX IF NOT EXISTS idx_{self.pg_config.table_name}_metadata 
                ON {self.pg_config.table_name} 
                USING gin (metadata);
                """
                
                conn.execute(text(create_table_sql))
                conn.commit()
            
            logger.info(f"Created PostgreSQL table: {self.pg_config.table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating PostgreSQL table: {e}")
            return False
    
    def add_chunks(self, chunks: List[DocumentChunk]) -> bool:
        """
        Add document chunks to PostgreSQL table
        
        Args:
            chunks: List of document chunks with embeddings
            
        Returns:
            True if successful
        """
        try:
            if not chunks:
                return True
            
            with self.engine.connect() as conn:
                for chunk in chunks:
                    if chunk.embedding is None:
                        logger.warning(f"Chunk {chunk.chunk_id} has no embedding, skipping")
                        continue
                    
                    # Prepare metadata as JSON
                    metadata = {
                        "title": chunk.metadata.title,
                        "source": chunk.metadata.source,
                        "category": chunk.metadata.category,
                        "tags": chunk.metadata.tags,
                        "file_type": chunk.metadata.file_type,
                        "chunk_index": chunk.chunk_index,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                        "created_date": chunk.metadata.created_date.isoformat() if chunk.metadata.created_date else None,
                        "word_count": chunk.metadata.word_count,
                        "checksum": chunk.metadata.checksum
                    }
                    
                    # Insert or update chunk
                    insert_sql = f"""
                    INSERT INTO {self.pg_config.table_name} 
                    (chunk_id, content, {self.pg_config.vector_column}, metadata)
                    VALUES (:chunk_id, :content, :embedding, :metadata)
                    ON CONFLICT (chunk_id) 
                    DO UPDATE SET 
                        content = EXCLUDED.content,
                        {self.pg_config.vector_column} = EXCLUDED.{self.pg_config.vector_column},
                        metadata = EXCLUDED.metadata,
                        updated_at = CURRENT_TIMESTAMP
                    """
                    
                    conn.execute(text(insert_sql), {
                        "chunk_id": chunk.chunk_id,
                        "content": chunk.content,
                        "embedding": str(chunk.embedding),  # Convert to string for pgvector
                        "metadata": json.dumps(metadata)
                    })
                
                conn.commit()
            
            logger.info(f"Added {len(chunks)} chunks to PostgreSQL")
            return True
            
        except Exception as e:
            logger.error(f"Error adding chunks to PostgreSQL: {e}")
            return False
    
    def search(self, query_embedding: List[float], top_k: int = 10,
               filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """
        Search for similar chunks using vector similarity
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filters: Optional filters for metadata
            
        Returns:
            List of search results
        """
        try:
            with self.engine.connect() as conn:
                # Build WHERE clause for filters
                where_clause = ""
                params = {
                    "query_embedding": str(query_embedding),
                    "limit": top_k
                }
                
                if filters:
                    conditions = []
                    for key, value in filters.items():
                        if isinstance(value, list):
                            conditions.append(f"metadata->>'{key}' = ANY(:filter_{key})")
                            params[f"filter_{key}"] = value
                        else:
                            conditions.append(f"metadata->>'{key}' = :filter_{key}")
                            params[f"filter_{key}"] = value
                    
                    if conditions:
                        where_clause = "WHERE " + " AND ".join(conditions)
                
                # Search query using cosine similarity
                search_sql = f"""
                SELECT 
                    chunk_id,
                    content,
                    metadata,
                    1 - ({self.pg_config.vector_column} <=> :query_embedding::vector) as similarity_score
                FROM {self.pg_config.table_name}
                {where_clause}
                ORDER BY {self.pg_config.vector_column} <=> :query_embedding::vector
                LIMIT :limit
                """
                
                result = conn.execute(text(search_sql), params)
                rows = result.fetchall()
                
                # Convert to SearchResult objects
                results = []
                for i, row in enumerate(rows):
                    metadata_dict = json.loads(row.metadata) if row.metadata else {}
                    
                    # Reconstruct DocumentMetadata
                    metadata = DocumentMetadata(
                        title=metadata_dict.get("title", ""),
                        source=metadata_dict.get("source", ""),
                        file_type=metadata_dict.get("file_type", ""),
                        file_size=0,
                        created_date=datetime.fromisoformat(metadata_dict["created_date"]) if metadata_dict.get("created_date") else None,
                        category=metadata_dict.get("category", "general"),
                        tags=metadata_dict.get("tags", []),
                        word_count=metadata_dict.get("word_count", 0),
                        checksum=metadata_dict.get("checksum", "")
                    )
                    
                    # Reconstruct DocumentChunk
                    chunk = DocumentChunk(
                        content=row.content,
                        metadata=metadata,
                        chunk_id=row.chunk_id,
                        chunk_index=metadata_dict.get("chunk_index", 0),
                        start_char=metadata_dict.get("start_char", 0),
                        end_char=metadata_dict.get("end_char", 0)
                    )
                    
                    search_result = SearchResult(
                        chunk=chunk,
                        score=float(row.similarity_score),
                        rank=i + 1
                    )
                    results.append(search_result)
                
                return results
                
        except Exception as e:
            logger.error(f"Error searching PostgreSQL: {e}")
            return []


class RAGPipeline:
    """
    Main RAG pipeline that coordinates document processing, embedding generation,
    vector storage, and retrieval with RAGFlow enhancements.
    """
    
    def __init__(self, config: Optional[RAGPipelineConfig] = None):
        """
        Initialize RAG pipeline
        
        Args:
            config: RAG pipeline configuration
        """
        self.config = config or get_config()
        
        # Initialize components
        self.document_processor = DocumentProcessor(self.config)
        self.embedding_service = EmbeddingService(self.config)
        
        # Initialize vector store
        if self.config.vector_store == VectorStore.QDRANT:
            self.vector_store = QdrantVectorStore(self.config)
            self.fallback_store = PostgreSQLVectorStore(self.config) if self.config.enable_fallback else None
        else:
            self.vector_store = PostgreSQLVectorStore(self.config)
            self.fallback_store = None
        
        # Initialize reranker if enabled
        self.reranker = None
        if self.config.ragflow.rerank_enabled:
            try:
                self.reranker = CrossEncoder(self.config.ragflow.rerank_model)
                logger.info(f"Reranker initialized: {self.config.ragflow.rerank_model}")
            except Exception as e:
                logger.warning(f"Failed to initialize reranker: {e}")
        
        logger.info("RAG Pipeline initialized successfully")
    
    def initialize_storage(self) -> bool:
        """
        Initialize vector storage (create collections/tables)
        
        Returns:
            True if successful
        """
        try:
            # Initialize primary vector store
            if isinstance(self.vector_store, QdrantVectorStore):
                success = self.vector_store.create_collection()
            else:
                success = self.vector_store.create_table()
            
            if not success:
                logger.error("Failed to initialize primary vector store")
                return False
            
            # Initialize fallback store if enabled
            if self.fallback_store:
                fallback_success = self.fallback_store.create_table()
                if not fallback_success:
                    logger.warning("Failed to initialize fallback vector store")
            
            logger.info("Vector storage initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing storage: {e}")
            return False
    
    def process_and_store_documents(self, file_paths: List[str]) -> bool:
        """
        Process documents and store them in vector database
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Processing {len(file_paths)} documents")
            
            all_chunks = []
            
            # Process each document
            for file_path in file_paths:
                try:
                    chunks = self.document_processor.process_file(file_path)
                    all_chunks.extend(chunks)
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    continue
            
            if not all_chunks:
                logger.warning("No chunks were created from the documents")
                return False
            
            # Generate embeddings
            chunks_with_embeddings = self.embedding_service.embed_chunks_batch(all_chunks)
            
            # Store in vector database
            success = self.vector_store.add_chunks(chunks_with_embeddings)
            
            # Store in fallback if enabled and primary failed
            if not success and self.fallback_store:
                logger.info("Primary storage failed, trying fallback")
                success = self.fallback_store.add_chunks(chunks_with_embeddings)
            
            if success:
                logger.info(f"Successfully processed and stored {len(chunks_with_embeddings)} chunks")
            else:
                logger.error("Failed to store chunks in vector database")
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing and storing documents: {e}")
            return False
    
    def process_directory(self, directory_path: str, recursive: bool = True) -> bool:
        """
        Process all documents in a directory
        
        Args:
            directory_path: Path to directory containing documents
            recursive: Whether to process subdirectories
            
        Returns:
            True if successful
        """
        try:
            # Get all chunks from directory
            all_chunks = self.document_processor.process_directory(directory_path, recursive)
            
            if not all_chunks:
                logger.warning("No chunks were created from the directory")
                return False
            
            # Generate embeddings
            chunks_with_embeddings = self.embedding_service.embed_chunks_batch(all_chunks)
            
            # Store in vector database
            success = self.vector_store.add_chunks(chunks_with_embeddings)
            
            # Store in fallback if enabled and primary failed
            if not success and self.fallback_store:
                logger.info("Primary storage failed, trying fallback")
                success = self.fallback_store.add_chunks(chunks_with_embeddings)
            
            if success:
                logger.info(f"Successfully processed directory and stored {len(chunks_with_embeddings)} chunks")
            else:
                logger.error("Failed to store chunks in vector database")
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing directory: {e}")
            return False
    
    def search(self, query: str, top_k: Optional[int] = None, 
               filters: Optional[Dict[str, Any]] = None) -> RAGResponse:
        """
        Search for relevant documents using the query
        
        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            RAG response with search results and context
        """
        start_time = datetime.now()
        top_k = top_k or self.config.ragflow.top_k
        
        try:
            logger.info(f"Searching for: '{query}' (top_k={top_k})")
            
            # Generate query embedding
            query_embedding = self.embedding_service.embed_text(query)
            
            # Perform vector search
            try:
                results = self.vector_store.search(query_embedding, top_k, filters)
            except Exception as e:
                logger.error(f"Primary vector store search failed: {e}")
                if self.fallback_store:
                    logger.info("Trying fallback vector store")
                    results = self.fallback_store.search(query_embedding, top_k, filters)
                else:
                    raise e
            
            # Filter by similarity threshold
            filtered_results = [
                result for result in results 
                if result.score >= self.config.ragflow.similarity_threshold
            ]
            
            # Rerank if enabled
            reranked = False
            if self.reranker and len(filtered_results) > 1:
                try:
                    filtered_results = self._rerank_results(query, filtered_results)
                    reranked = True
                except Exception as e:
                    logger.warning(f"Reranking failed: {e}")
            
            # Generate context
            context = self._generate_context(filtered_results)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            response = RAGResponse(
                query=query,
                results=filtered_results,
                context=context,
                processing_time=processing_time,
                total_chunks_searched=len(results),
                reranked=reranked,
                hybrid_search=False  # TODO: Implement hybrid search
            )
            
            logger.info(f"Search completed in {processing_time:.2f}s, found {len(filtered_results)} relevant results")
            return response
            
        except Exception as e:
            logger.error(f"Error during search: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()
            return RAGResponse(
                query=query,
                results=[],
                context="",
                processing_time=processing_time,
                total_chunks_searched=0
            )
    
    def _rerank_results(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """
        Rerank search results using cross-encoder
        
        Args:
            query: Original query
            results: Search results to rerank
            
        Returns:
            Reranked search results
        """
        if not self.reranker or len(results) <= 1:
            return results
        
        # Prepare query-document pairs
        pairs = [(query, result.chunk.content) for result in results]
        
        # Get reranking scores
        rerank_scores = self.reranker.predict(pairs)
        
        # Update scores and re-sort
        for result, new_score in zip(results, rerank_scores):
            result.score = float(new_score)
        
        # Sort by new scores
        reranked_results = sorted(results, key=lambda x: x.score, reverse=True)
        
        # Update ranks
        for i, result in enumerate(reranked_results):
            result.rank = i + 1
        
        return reranked_results
    
    def _generate_context(self, results: List[SearchResult]) -> str:
        """
        Generate context string from search results
        
        Args:
            results: Search results
            
        Returns:
            Formatted context string
        """
        if not results:
            return ""
        
        context_parts = []
        max_length = self.config.ragflow.max_context_length
        current_length = 0
        
        for result in results:
            chunk_text = f"[Source: {result.chunk.metadata.title}]\n{result.chunk.content}\n"
            
            if current_length + len(chunk_text) > max_length:
                # Truncate if needed
                remaining_length = max_length - current_length
                if remaining_length > 100:  # Only add if there's meaningful space
                    chunk_text = chunk_text[:remaining_length] + "..."
                    context_parts.append(chunk_text)
                break
            
            context_parts.append(chunk_text)
            current_length += len(chunk_text)
        
        return "\n---\n".join(context_parts)
    
    def get_pipeline_info(self) -> Dict[str, Any]:
        """
        Get information about the RAG pipeline
        
        Returns:
            Pipeline information dictionary
        """
        info = {
            "vector_store": self.config.vector_store.value,
            "embedding_service": self.embedding_service.get_embedding_info(),
            "reranker_enabled": self.config.ragflow.rerank_enabled,
            "fallback_enabled": self.config.enable_fallback,
            "chunking_strategy": self.config.chunking.strategy.value,
            "chunk_size": self.config.chunking.chunk_size,
            "chunk_overlap": self.config.chunking.chunk_overlap
        }
        
        # Add vector store specific info
        if isinstance(self.vector_store, QdrantVectorStore):
            info["qdrant_collection"] = self.vector_store.get_collection_info()
        
        return info
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the RAG pipeline
        
        Returns:
            Health check results
        """
        health = {
            "status": "healthy",
            "components": {}
        }
        
        # Check embedding service
        embedding_health = self.embedding_service.health_check()
        health["components"]["embedding_service"] = embedding_health
        
        # Check vector store
        try:
            if isinstance(self.vector_store, QdrantVectorStore):
                collection_info = self.vector_store.get_collection_info()
                health["components"]["vector_store"] = {
                    "status": "healthy",
                    "type": "qdrant",
                    "collection_info": collection_info
                }
            else:
                # Simple connection test for PostgreSQL
                with self.vector_store.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                health["components"]["vector_store"] = {
                    "status": "healthy",
                    "type": "postgresql"
                }
        except Exception as e:
            health["components"]["vector_store"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health["status"] = "degraded"
        
        # Check reranker
        if self.reranker:
            try:
                # Simple test
                test_pairs = [("test query", "test document")]
                self.reranker.predict(test_pairs)
                health["components"]["reranker"] = {"status": "healthy"}
            except Exception as e:
                health["components"]["reranker"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        return health


# Export main classes
__all__ = [
    "RAGPipeline",
    "SearchResult",
    "RAGResponse",
    "QdrantVectorStore",
    "PostgreSQLVectorStore"
]