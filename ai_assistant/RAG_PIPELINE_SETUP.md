# RAG Pipeline Setup and Documentation

## Overview

This document provides comprehensive setup instructions, architecture overview, and usage examples for the RAG (Retrieval-Augmented Generation) pipeline implementation in the AI Assistant service.

The RAG pipeline integrates document processing, embedding generation, vector storage, and intelligent retrieval to enable the AI assistant to answer questions based on a knowledge base of trading-related documents.

## Architecture Overview

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Documents     │    │   Document       │    │   Embedding     │
│   (.md, .pdf,   │───▶│   Processor      │───▶│   Service       │
│    .docx, etc.) │    │  (Unstructured)  │    │ (Transformers)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Query Tool    │    │   RAG Pipeline   │    │  Vector Store   │
│   (LangChain)   │◀───│   (Retrieval)    │◀───│ (Qdrant/PgVec)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Component Details

1. **Document Processor** (`document_processor.py`)
   - Uses Unstructured.io for parsing various document formats
   - Implements multiple chunking strategies (fixed, sliding window, semantic, recursive)
   - Extracts metadata and categorizes content
   - Supports PDF, Word, Markdown, CSV, and text files

2. **Embedding Service** (`embedding_service.py`)
   - Multiple embedding providers: Sentence Transformers, OpenAI, HuggingFace
   - Batch processing and caching capabilities
   - Redis-based caching for performance optimization
   - Configurable embedding dimensions and models

3. **Vector Storage**
   - **Primary**: Qdrant vector database for high-performance similarity search
   - **Fallback**: PostgreSQL with pgvector extension
   - Automatic failover and health monitoring
   - Configurable similarity thresholds and search parameters

4. **RAG Pipeline** (`rag_pipeline.py`)
   - Orchestrates document processing, embedding, and storage
   - Implements RAGFlow enhancements (reranking, query expansion)
   - Provides search functionality with metadata filtering
   - Health monitoring and performance metrics

## Prerequisites

### System Requirements

- Python 3.11+
- Docker and Docker Compose
- At least 4GB RAM (8GB recommended)
- 10GB free disk space

### Dependencies

The following services must be running:
- Qdrant (primary vector database)
- PostgreSQL with pgvector (fallback)
- Redis (caching)

## Installation and Setup

### 1. Environment Configuration

Create or update your `.env` file with RAG-specific settings:

```bash
# RAG Pipeline Configuration
QDRANT_URL=http://localhost:6333
VECTOR_STORE=qdrant
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# Chunking Configuration
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# RAGFlow Configuration
RAGFLOW_TOP_K=10
RAGFLOW_SIMILARITY_THRESHOLD=0.7

# Optional: OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Unstructured.io Configuration
UNSTRUCTURED_API_KEY=your_unstructured_api_key_here
UNSTRUCTURED_API_URL=https://api.unstructured.io
```

### 2. Docker Services

Start the required services using Docker Compose:

```bash
# Start all services
docker-compose up -d

# Or start specific services
docker-compose up -d qdrant postgres redis
```

Verify services are running:

```bash
# Check Qdrant
curl http://localhost:6333/health

# Check PostgreSQL
docker-compose exec postgres pg_isready

# Check Redis
docker-compose exec redis redis-cli ping
```

### 3. Install Python Dependencies

```bash
cd ai_assistant
pip install -r requirements.txt
```

### 4. Initialize the RAG Pipeline

Run the initialization script to process sample documents:

```bash
cd ai_assistant
python initialize_rag.py
```

This script will:
- Validate configuration and dependencies
- Test vector store connections
- Process sample trading documents
- Create embeddings and store in vector database
- Run search functionality tests

## Configuration Options

### Embedding Providers

#### Sentence Transformers (Default)
```python
EMBEDDING_PROVIDER=sentence_transformers
EMBEDDING_MODEL=all-MiniLM-L6-v2  # Fast, good quality
# EMBEDDING_MODEL=all-mpnet-base-v2  # Higher quality, slower
```

#### OpenAI Embeddings
```python
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=your_api_key
EMBEDDING_MODEL=text-embedding-3-small  # Cost-effective
# EMBEDDING_MODEL=text-embedding-3-large  # Higher quality
```

#### HuggingFace Models
```python
EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
HUGGINGFACE_TOKEN=your_hf_token  # Optional for private models
```

### Vector Storage Options

#### Qdrant (Recommended)
```python
VECTOR_STORE=qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_api_key  # Optional
```

#### PostgreSQL with pgvector
```python
VECTOR_STORE=postgresql_pgvector
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=trading_system
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
```

### Chunking Strategies

#### Recursive (Recommended)
```python
CHUNKING_STRATEGY=recursive
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

#### Fixed Size
```python
CHUNKING_STRATEGY=fixed_size
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

#### Sliding Window
```python
CHUNKING_STRATEGY=sliding_window
WINDOW_SIZE=1000
STEP_SIZE=800
```

## Usage Examples

### Basic Document Query

```python
from ai_assistant.tools import query_documents_tool

# Query the document database
result = query_documents_tool(
    query="What are the best risk management techniques?",
    limit=5
)
print(result)
```

### Direct RAG Pipeline Usage

```python
from ai_assistant.rag_pipeline import RAGPipeline
from ai_assistant.rag_config import get_config

# Initialize pipeline
config = get_config()
rag_pipeline = RAGPipeline(config)

# Search for documents
response = rag_pipeline.search(
    query="How to calculate Sharpe ratio?",
    top_k=3
)

# Access results
for result in response.results:
    print(f"Title: {result.chunk.metadata.title}")
    print(f"Score: {result.score:.3f}")
    print(f"Content: {result.chunk.content[:200]}...")
    print("-" * 50)
```

### Adding New Documents

```python
# Process a single document
success = rag_pipeline.process_and_store_documents([
    "/path/to/new_document.pdf"
])

# Process an entire directory
success = rag_pipeline.process_directory(
    "/path/to/documents",
    recursive=True
)
```

### Advanced Search with Filters

```python
# Search with metadata filters
response = rag_pipeline.search(
    query="portfolio optimization",
    top_k=5,
    filters={
        "category": "risk_management",
        "tags": ["portfolio", "optimization"]
    }
)
```

## Performance Tuning

### Embedding Optimization

1. **Model Selection**
   - `all-MiniLM-L6-v2`: Fast, good for most use cases
   - `all-mpnet-base-v2`: Higher quality, slower
   - OpenAI models: Highest quality, API costs

2. **Batch Processing**
   ```python
   EMBEDDING_BATCH_SIZE=32  # Adjust based on memory
   ```

3. **Caching**
   ```python
   CACHE_ENABLED=true
   EMBEDDING_CACHE_TTL=86400  # 24 hours
   ```

### Vector Search Optimization

1. **Qdrant Configuration**
   ```python
   # In rag_config.py
   hnsw_config = {
       "m": 16,              # Number of connections
       "ef_construct": 100,  # Construction parameter
       "full_scan_threshold": 10000
   }
   ```

2. **Search Parameters**
   ```python
   RAGFLOW_TOP_K=10                    # Number of results
   RAGFLOW_SIMILARITY_THRESHOLD=0.7   # Minimum similarity
   ```

### Chunking Optimization

1. **Chunk Size**
   - Smaller chunks (500-800): Better precision, more results
   - Larger chunks (1000-1500): Better context, fewer results

2. **Overlap**
   - 10-20% overlap: Good balance
   - Higher overlap: Better continuity, more storage

## Monitoring and Maintenance

### Health Checks

```python
# Check pipeline health
health = rag_pipeline.health_check()
print(health)

# Check individual components
embedding_health = rag_pipeline.embedding_service.health_check()
```

### Performance Metrics

```python
# Get pipeline information
info = rag_pipeline.get_pipeline_info()
print(f"Vector store: {info['vector_store']}")
print(f"Embedding model: {info['embedding_service']['model_name']}")
```

### Logging Configuration

```python
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable debug logging for specific components
logging.getLogger('ai_assistant.rag_pipeline').setLevel(logging.DEBUG)
```

## Troubleshooting

### Common Issues

1. **Qdrant Connection Failed**
   ```bash
   # Check if Qdrant is running
   docker-compose ps qdrant
   
   # Check logs
   docker-compose logs qdrant
   
   # Restart service
   docker-compose restart qdrant
   ```

2. **Embedding Generation Slow**
   - Reduce batch size
   - Use faster embedding model
   - Enable GPU acceleration (if available)

3. **Out of Memory Errors**
   - Reduce chunk size
   - Lower batch processing size
   - Use smaller embedding model

4. **Poor Search Results**
   - Lower similarity threshold
   - Increase top_k results
   - Try different embedding model
   - Check document quality and chunking

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
import os
os.environ['LOG_LEVEL'] = 'DEBUG'

# Or in configuration
config.log_level = "DEBUG"
```

## API Integration

### FastAPI Endpoints

The RAG pipeline integrates with the AI Assistant's FastAPI service:

```python
# Example endpoint (add to main.py)
@app.get("/api/v1/rag/search")
async def search_documents(
    query: str,
    limit: int = 5,
    category: Optional[str] = None
):
    filters = {"category": category} if category else None
    response = rag_pipeline.search(query, top_k=limit, filters=filters)
    
    return {
        "query": query,
        "results": [
            {
                "title": r.chunk.metadata.title,
                "content": r.chunk.content,
                "score": r.score,
                "source": r.chunk.metadata.source
            }
            for r in response.results
        ],
        "processing_time": response.processing_time
    }
```

## Security Considerations

### API Keys
- Store API keys in environment variables
- Use Docker secrets for production
- Rotate keys regularly

### Access Control
- Implement authentication for document upload
- Restrict access to sensitive documents
- Log all document access

### Data Privacy
- Ensure compliance with data protection regulations
- Implement data retention policies
- Consider on-premises deployment for sensitive data

## Production Deployment

### Scaling Considerations

1. **Horizontal Scaling**
   - Multiple AI assistant instances
   - Load balancer for API requests
   - Shared vector database

2. **Resource Allocation**
   - CPU: 4+ cores for embedding generation
   - Memory: 8GB+ for large document collections
   - Storage: SSD recommended for vector database

3. **Monitoring**
   - Prometheus metrics integration
   - Grafana dashboards
   - Alert on performance degradation

### Backup and Recovery

1. **Vector Database Backup**
   ```bash
   # Qdrant backup
   docker-compose exec qdrant qdrant-backup
   
   # PostgreSQL backup
   docker-compose exec postgres pg_dump trading_system > backup.sql
   ```

2. **Document Backup**
   - Regular backup of source documents
   - Version control for document changes
   - Disaster recovery procedures

## Advanced Features

### Custom Document Processors

Extend the document processor for specialized formats:

```python
from ai_assistant.document_processor import DocumentProcessor

class CustomDocumentProcessor(DocumentProcessor):
    def process_custom_format(self, file_path):
        # Custom processing logic
        pass
```

### Custom Embedding Models

Add support for custom embedding models:

```python
from ai_assistant.embedding_service import EmbeddingService

class CustomEmbeddingService(EmbeddingService):
    def load_custom_model(self):
        # Load custom model
        pass
```

### Query Enhancement

Implement query expansion and enhancement:

```python
def enhance_query(query: str) -> str:
    # Add synonyms, expand abbreviations
    # Use LLM for query rewriting
    return enhanced_query
```

## Support and Maintenance

### Regular Maintenance Tasks

1. **Weekly**
   - Monitor system performance
   - Check error logs
   - Validate search quality

2. **Monthly**
   - Update embedding models
   - Optimize vector database
   - Review and update documents

3. **Quarterly**
   - Performance benchmarking
   - Security audit
   - Dependency updates

### Getting Help

- Check logs for error messages
- Review configuration settings
- Test with simple queries first
- Monitor resource usage

This documentation provides a comprehensive guide for setting up, configuring, and maintaining the RAG pipeline in the AI Assistant service.