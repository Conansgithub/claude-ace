"""
Storage module for ACE
Production-grade vector storage for semantic search

Backends:
- Qdrant + Ollama (Production)
- ChromaDB (Development/Fallback)
"""

from .vector_store import PlaybookVectorStore
from .ollama_embedding import OllamaEmbeddingClient, check_ollama_available
from .qdrant_store import QdrantVectorStore, check_qdrant_available

__all__ = [
    'PlaybookVectorStore',
    'OllamaEmbeddingClient',
    'QdrantVectorStore',
    'check_ollama_available',
    'check_qdrant_available'
]
