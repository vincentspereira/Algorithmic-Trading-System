"""
Embedding Service for RAG Pipeline
Provides embedding generation using multiple providers including sentence-transformers,
OpenAI, and HuggingFace models with caching and batch processing capabilities.
"""

import os
import logging
import hashlib
import pickle
from typing import List, Optional, Dict, Any, Union, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

import numpy as np
import redis
from sentence_transformers import SentenceTransformer
import openai
from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn.functional as F

from .rag_config import RAGPipelineConfig, EmbeddingProvider, get_config
from .document_processor import DocumentChunk

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding generation"""
    embeddings: List[List[float]]
    model_name: str
    dimension: int
    processing_time: float
    cached_count: int = 0
    generated_count: int = 0


class EmbeddingCache:
    """Cache for embeddings using Redis or in-memory storage"""
    
    def __init__(self, config: RAGPipelineConfig):
        """
        Initialize embedding cache
        
        Args:
            config: RAG pipeline configuration
        """
        self.config = config
        self.cache_enabled = config.cache.enabled
        self.ttl = config.cache.embedding_cache_ttl
        
        if self.cache_enabled and config.cache.cache_type == "redis":
            try:
                self.redis_client = redis.Redis(
                    host=config.cache.redis_host,
                    port=config.cache.redis_port,
                    db=config.cache.redis_db,
                    password=config.cache.redis_password,
                    decode_responses=False  # We'll handle binary data
                )
                # Test connection
                self.redis_client.ping()
                self.cache_type = "redis"
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache: {e}, falling back to memory cache")
                self.cache_type = "memory"
                self.memory_cache = {}
        else:
            self.cache_type = "memory"
            self.memory_cache = {}
            logger.info("Memory cache initialized")
    
    def _generate_cache_key(self, text: str, model_name: str) -> str:
        """Generate cache key for text and model combination"""
        content = f"{model_name}:{text}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get(self, text: str, model_name: str) -> Optional[List[float]]:
        """
        Get embedding from cache
        
        Args:
            text: Text to get embedding for
            model_name: Model name used for embedding
            
        Returns:
            Cached embedding or None if not found
        """
        if not self.cache_enabled:
            return None
        
        cache_key = self._generate_cache_key(text, model_name)
        
        try:
            if self.cache_type == "redis":
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    return pickle.loads(cached_data)
            else:
                return self.memory_cache.get(cache_key)
        except Exception as e:
            logger.warning(f"Error retrieving from cache: {e}")
        
        return None
    
    def set(self, text: str, model_name: str, embedding: List[float]) -> None:
        """
        Store embedding in cache
        
        Args:
            text: Text that was embedded
            model_name: Model name used for embedding
            embedding: Generated embedding
        """
        if not self.cache_enabled:
            return
        
        cache_key = self._generate_cache_key(text, model_name)
        
        try:
            if self.cache_type == "redis":
                serialized_embedding = pickle.dumps(embedding)
                self.redis_client.setex(cache_key, self.ttl, serialized_embedding)
            else:
                # Simple memory cache with size limit
                if len(self.memory_cache) >= self.config.cache.max_memory_cache_size:
                    # Remove oldest entry (simple FIFO)
                    oldest_key = next(iter(self.memory_cache))
                    del self.memory_cache[oldest_key]
                
                self.memory_cache[cache_key] = embedding
        except Exception as e:
            logger.warning(f"Error storing in cache: {e}")
    
    def clear(self) -> None:
        """Clear all cached embeddings"""
        try:
            if self.cache_type == "redis":
                # Clear only embedding cache keys (be careful not to clear other data)
                pattern = "*"  # In production, use a more specific pattern
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            else:
                self.memory_cache.clear()
            logger.info("Embedding cache cleared")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")


class SentenceTransformerEmbedder:
    """Sentence Transformers embedding provider"""
    
    def __init__(self, config: RAGPipelineConfig):
        """
        Initialize Sentence Transformers embedder
        
        Args:
            config: RAG pipeline configuration
        """
        self.config = config
        self.model_name = config.embedding.model_name
        self.device = config.embedding.device
        self.normalize = config.embedding.normalize_embeddings
        
        logger.info(f"Loading Sentence Transformers model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name, device=self.device)
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        logger.info(f"Sentence Transformers model loaded, dimension: {self.dimension}")
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings
        """
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=self.config.embedding.batch_size,
                normalize_embeddings=self.normalize,
                show_progress_bar=len(texts) > 10
            )
            
            # Convert to list of lists
            return embeddings.tolist()
            
        except Exception as e:
            logger.error(f"Error generating embeddings with Sentence Transformers: {e}")
            raise


class OpenAIEmbedder:
    """OpenAI embedding provider"""
    
    def __init__(self, config: RAGPipelineConfig):
        """
        Initialize OpenAI embedder
        
        Args:
            config: RAG pipeline configuration
        """
        self.config = config
        self.model_name = config.embedding.openai_model
        self.api_key = config.embedding.openai_api_key
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required for OpenAI embeddings")
        
        openai.api_key = self.api_key
        self.client = openai.OpenAI(api_key=self.api_key)
        
        # Set dimension based on model
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }
        self.dimension = model_dimensions.get(self.model_name, 1536)
        
        logger.info(f"OpenAI embedder initialized with model: {self.model_name}")
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts using OpenAI API
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings
        """
        try:
            # OpenAI has rate limits, so we process in smaller batches
            batch_size = min(self.config.embedding.batch_size, 100)
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=batch_texts
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                
                # Add small delay to respect rate limits
                if len(texts) > batch_size:
                    time.sleep(0.1)
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings with OpenAI: {e}")
            raise


class HuggingFaceEmbedder:
    """HuggingFace transformers embedding provider"""
    
    def __init__(self, config: RAGPipelineConfig):
        """
        Initialize HuggingFace embedder
        
        Args:
            config: RAG pipeline configuration
        """
        self.config = config
        self.model_name = config.embedding.model_name
        self.device = config.embedding.device
        self.max_length = config.embedding.max_length
        self.normalize = config.embedding.normalize_embeddings
        
        logger.info(f"Loading HuggingFace model: {self.model_name}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            token=config.embedding.hf_token
        )
        self.model = AutoModel.from_pretrained(
            self.model_name,
            token=config.embedding.hf_token
        ).to(self.device)
        
        # Get dimension from model config
        self.dimension = self.model.config.hidden_size
        
        logger.info(f"HuggingFace model loaded, dimension: {self.dimension}")
    
    def _mean_pooling(self, model_output, attention_mask):
        """Apply mean pooling to get sentence embeddings"""
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts using HuggingFace transformers
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings
        """
        try:
            all_embeddings = []
            batch_size = self.config.embedding.batch_size
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                # Tokenize
                encoded_input = self.tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=self.max_length,
                    return_tensors='pt'
                ).to(self.device)
                
                # Generate embeddings
                with torch.no_grad():
                    model_output = self.model(**encoded_input)
                    embeddings = self._mean_pooling(model_output, encoded_input['attention_mask'])
                    
                    if self.normalize:
                        embeddings = F.normalize(embeddings, p=2, dim=1)
                    
                    batch_embeddings = embeddings.cpu().numpy().tolist()
                    all_embeddings.extend(batch_embeddings)
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings with HuggingFace: {e}")
            raise


class EmbeddingService:
    """
    Main embedding service that coordinates different embedding providers
    and provides caching, batch processing, and error handling.
    """
    
    def __init__(self, config: Optional[RAGPipelineConfig] = None):
        """
        Initialize embedding service
        
        Args:
            config: RAG pipeline configuration
        """
        self.config = config or get_config()
        self.cache = EmbeddingCache(self.config)
        
        # Initialize the appropriate embedder
        self.provider = self.config.embedding.provider
        
        if self.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
            self.embedder = SentenceTransformerEmbedder(self.config)
        elif self.provider == EmbeddingProvider.OPENAI:
            self.embedder = OpenAIEmbedder(self.config)
        elif self.provider == EmbeddingProvider.HUGGINGFACE:
            self.embedder = HuggingFaceEmbedder(self.config)
        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")
        
        self.model_name = self.embedder.model_name
        self.dimension = self.embedder.dimension
        
        logger.info(f"EmbeddingService initialized with {self.provider.value} provider")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        embeddings = self.embed_texts([text])
        return embeddings[0]
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with caching
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        start_time = time.time()
        
        # Check cache for existing embeddings
        cached_embeddings = {}
        texts_to_generate = []
        text_indices = {}
        
        for i, text in enumerate(texts):
            cached_embedding = self.cache.get(text, self.model_name)
            if cached_embedding is not None:
                cached_embeddings[i] = cached_embedding
            else:
                texts_to_generate.append(text)
                text_indices[len(texts_to_generate) - 1] = i
        
        # Generate embeddings for non-cached texts
        generated_embeddings = []
        if texts_to_generate:
            generated_embeddings = self.embedder.embed_texts(texts_to_generate)
            
            # Cache the generated embeddings
            for j, embedding in enumerate(generated_embeddings):
                text = texts_to_generate[j]
                self.cache.set(text, self.model_name, embedding)
        
        # Combine cached and generated embeddings in correct order
        final_embeddings = [None] * len(texts)
        
        # Fill in cached embeddings
        for i, embedding in cached_embeddings.items():
            final_embeddings[i] = embedding
        
        # Fill in generated embeddings
        for j, embedding in enumerate(generated_embeddings):
            original_index = text_indices[j]
            final_embeddings[original_index] = embedding
        
        processing_time = time.time() - start_time
        
        logger.info(
            f"Generated embeddings for {len(texts)} texts in {processing_time:.2f}s "
            f"(cached: {len(cached_embeddings)}, generated: {len(generated_embeddings)})"
        )
        
        return final_embeddings
    
    def embed_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """
        Generate embeddings for document chunks
        
        Args:
            chunks: List of document chunks
            
        Returns:
            List of chunks with embeddings added
        """
        if not chunks:
            return chunks
        
        logger.info(f"Generating embeddings for {len(chunks)} document chunks")
        
        # Extract texts from chunks
        texts = [chunk.content for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.embed_texts(texts)
        
        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        logger.info(f"Successfully added embeddings to {len(chunks)} chunks")
        return chunks
    
    def embed_chunks_batch(self, chunks: List[DocumentChunk], batch_size: Optional[int] = None) -> List[DocumentChunk]:
        """
        Generate embeddings for document chunks in batches
        
        Args:
            chunks: List of document chunks
            batch_size: Batch size for processing (uses config default if None)
            
        Returns:
            List of chunks with embeddings added
        """
        if not chunks:
            return chunks
        
        batch_size = batch_size or self.config.batch_processing_size
        
        logger.info(f"Generating embeddings for {len(chunks)} chunks in batches of {batch_size}")
        
        # Process in batches
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_texts = [chunk.content for chunk in batch_chunks]
            
            # Generate embeddings for batch
            batch_embeddings = self.embed_texts(batch_texts)
            
            # Add embeddings to chunks
            for chunk, embedding in zip(batch_chunks, batch_embeddings):
                chunk.embedding = embedding
            
            logger.info(f"Processed batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}")
        
        return chunks
    
    def get_embedding_info(self) -> Dict[str, Any]:
        """
        Get information about the embedding service
        
        Returns:
            Dictionary with embedding service information
        """
        return {
            "provider": self.provider.value,
            "model_name": self.model_name,
            "dimension": self.dimension,
            "cache_enabled": self.cache.cache_enabled,
            "cache_type": self.cache.cache_type,
            "batch_size": self.config.embedding.batch_size
        }
    
    def clear_cache(self) -> None:
        """Clear the embedding cache"""
        self.cache.clear()
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on embedding service
        
        Returns:
            Health check results
        """
        try:
            # Test embedding generation
            test_text = "This is a test sentence for health check."
            start_time = time.time()
            embedding = self.embed_text(test_text)
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "provider": self.provider.value,
                "model_name": self.model_name,
                "dimension": len(embedding),
                "response_time": response_time,
                "cache_enabled": self.cache.cache_enabled
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "provider": self.provider.value
            }


# Export main classes
__all__ = [
    "EmbeddingService",
    "EmbeddingResult",
    "EmbeddingCache",
    "SentenceTransformerEmbedder",
    "OpenAIEmbedder", 
    "HuggingFaceEmbedder"
]