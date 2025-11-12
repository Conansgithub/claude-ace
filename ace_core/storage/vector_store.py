"""
Unified Vector Store Interface
Production-grade vector search for Playbook strategies

Supports multiple backends:
- Qdrant + Ollama (Production)
- ChromaDB (Development/Fallback)
"""

import asyncio
import sys
from typing import List, Dict, Optional
from pathlib import Path


def _run_async_safe(coro):
    """
    Safely run async coroutine, handling existing event loops

    This prevents "RuntimeError: asyncio.run() cannot be called from a running event loop"
    which can happen in Jupyter notebooks or when hooks are called from async contexts.
    """
    try:
        # Try to get the running loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        return asyncio.run(coro)
    else:
        # Event loop already running - this shouldn't happen in normal hook execution
        # but we handle it gracefully by creating a new task
        print("Warning: Running in existing event loop context", file=sys.stderr)
        # Create and run task in existing loop
        return loop.run_until_complete(coro)


class PlaybookVectorStore:
    """
    Unified vector store interface with automatic backend selection

    Priority:
    1. Qdrant + Ollama (if available and configured)
    2. ChromaDB (fallback)
    3. None (disable vector search)
    """

    def __init__(
        self,
        backend: str = "auto",
        config: Optional[Dict] = None
    ):
        """
        Initialize vector store

        Args:
            backend: "auto", "qdrant", "chroma", or "none"
            config: Configuration dict
        """
        self.backend = None
        self.backend_type = backend
        self.config = config or self._load_default_config()

        # Initialize backend
        if backend == "auto":
            self._auto_select_backend()
        elif backend == "qdrant":
            self._init_qdrant()
        elif backend == "chroma":
            self._init_chroma()
        elif backend == "none":
            self.backend = None
        else:
            raise ValueError(f"Unknown backend: {backend}")

    def _load_default_config(self) -> Dict:
        """Load default configuration"""
        from pathlib import Path
        import json

        config_path = Path.home() / ".claude" / "ace_config.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    return json.load(f).get('vector_search', {})
            except Exception as e:
                print(f"Warning: Failed to load vector search config: {e}", file=sys.stderr)

        # Default config
        return {
            'ollama': {
                'host': 'http://localhost:11434',
                'model': 'qwen3-embedding:0.6b'
            },
            'qdrant': {
                'host': 'localhost',
                'port': 6333,
                'collection': 'playbook_strategies'
            },
            'min_strategies_for_index': 10
        }

    def _auto_select_backend(self):
        """Automatically select best available backend"""
        # Try Qdrant + Ollama first (production)
        try:
            self._init_qdrant()
            if self.backend:
                print("✓ Using Qdrant + Ollama for vector search", file=sys.stderr)
                self.backend_type = "qdrant"
                return
        except Exception as e:
            print(f"Qdrant not available: {e}", file=sys.stderr)

        # Fall back to ChromaDB
        try:
            self._init_chroma()
            if self.backend:
                print("✓ Using ChromaDB for vector search (fallback)", file=sys.stderr)
                self.backend_type = "chroma"
                return
        except Exception as e:
            print(f"ChromaDB not available: {e}", file=sys.stderr)

        # No backend available
        print("⚠ Vector search disabled (no backend available)", file=sys.stderr)
        self.backend = None
        self.backend_type = "none"

    def _init_qdrant(self):
        """Initialize Qdrant backend"""
        from .qdrant_store import QdrantVectorStore, check_qdrant_available
        from .ollama_embedding import OllamaEmbeddingClient, check_ollama_available

        # Check services
        qdrant_status = check_qdrant_available(
            host=self.config['qdrant']['host'],
            port=self.config['qdrant']['port']
        )

        if qdrant_status['status'] != 'ok':
            raise Exception(f"Qdrant not available: {qdrant_status['message']}")

        ollama_status = check_ollama_available(
            host=self.config['ollama']['host'],
            model=self.config['ollama']['model']
        )

        if ollama_status['status'] not in ['ok', 'warning']:
            raise Exception(f"Ollama not available: {ollama_status['message']}")

        # Initialize clients
        self.backend = {
            'type': 'qdrant',
            'store': QdrantVectorStore(
                host=self.config['qdrant']['host'],
                port=self.config['qdrant']['port'],
                collection_name=self.config['qdrant']['collection']
            ),
            'embedding': OllamaEmbeddingClient(
                host=self.config['ollama']['host'],
                model=self.config['ollama']['model']
            )
        }

    def _init_chroma(self):
        """Initialize ChromaDB backend (fallback)"""
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            raise Exception("chromadb not installed")

        persist_dir = str(Path.home() / ".claude" / "vector_db")
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        client = chromadb.Client(Settings(
            persist_directory=persist_dir,
            anonymized_telemetry=False
        ))

        self.backend = {
            'type': 'chroma',
            'client': client,
            'collection': client.get_or_create_collection(
                name="playbook_strategies",
                metadata={"hnsw:space": "cosine"}
            )
        }

    def is_available(self) -> bool:
        """Check if vector search is available"""
        return self.backend is not None

    def get_backend_type(self) -> str:
        """Get current backend type"""
        return self.backend_type

    def index_playbook(self, playbook: Dict) -> int:
        """
        Index playbook strategies

        Args:
            playbook: Playbook dictionary

        Returns:
            Number of strategies indexed
        """
        if not self.backend:
            return 0

        # Extract active strategies
        strategies = [
            kp for kp in playbook.get('key_points', [])
            if kp.get('status') == 'active'
        ]

        if not strategies:
            return 0

        # Check minimum threshold
        min_strategies = self.config.get('min_strategies_for_index', 10)
        if len(strategies) < min_strategies:
            print(f"Only {len(strategies)} strategies, need {min_strategies} for indexing", file=sys.stderr)
            return 0

        # Index based on backend
        if self.backend['type'] == 'qdrant':
            return self._index_qdrant(strategies)
        elif self.backend['type'] == 'chroma':
            return self._index_chroma(strategies)

        return 0

    def _index_qdrant(self, strategies: List[Dict]) -> int:
        """Index strategies using Qdrant"""
        async def _do_index():
            # Generate embeddings
            texts = [s['text'] for s in strategies]

            async with self.backend['embedding'] as embed_client:
                results = await embed_client.embed_batch(texts)

            if len(results) != len(strategies):
                raise Exception(f"Embedding count mismatch: {len(results)} vs {len(strategies)}")

            # Extract embeddings
            embeddings = [r.embedding for r in results]

            # Index in Qdrant
            count = await self.backend['store'].index_strategies(strategies, embeddings)

            return count

        try:
            return _run_async_safe(_do_index())
        except Exception as e:
            print(f"Qdrant indexing failed: {e}", file=sys.stderr)
            return 0

    def _index_chroma(self, strategies: List[Dict]) -> int:
        """Index strategies using ChromaDB"""
        try:
            # Clear existing
            collection = self.backend['collection']
            try:
                self.backend['client'].delete_collection("playbook_strategies")
                collection = self.backend['client'].create_collection(
                    name="playbook_strategies",
                    metadata={"hnsw:space": "cosine"}
                )
                self.backend['collection'] = collection
            except Exception as e:
                print(f"Warning: Could not recreate collection, using existing: {e}", file=sys.stderr)

            # Add strategies
            ids = [s['name'] for s in strategies]
            texts = [s['text'] for s in strategies]
            metadatas = [{
                'score': s.get('score', 0),
                'status': s.get('status', 'active'),
                'source': s.get('source', 'unknown')
            } for s in strategies]

            collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )

            return len(strategies)

        except Exception as e:
            print(f"ChromaDB indexing failed: {e}", file=sys.stderr)
            return 0

    def search(
        self,
        query: str,
        limit: int = 10,
        min_score: Optional[int] = None
    ) -> List[Dict]:
        """
        Search for relevant strategies

        Args:
            query: Query text
            limit: Max results
            min_score: Minimum Playbook score filter

        Returns:
            List of strategy dicts with similarity scores
        """
        if not self.backend:
            return []

        if self.backend['type'] == 'qdrant':
            return self._search_qdrant(query, limit, min_score)
        elif self.backend['type'] == 'chroma':
            return self._search_chroma(query, limit, min_score)

        return []

    def _search_qdrant(self, query: str, limit: int, min_score: Optional[int]) -> List[Dict]:
        """Search using Qdrant"""
        async def _do_search():
            # Generate query embedding
            async with self.backend['embedding'] as embed_client:
                query_embedding = await embed_client.embed_text(query)

            if not query_embedding:
                raise Exception("Failed to generate query embedding")

            # Search
            results = await self.backend['store'].search(
                query_embedding=query_embedding,
                limit=limit,
                min_score=min_score
            )

            # Format results
            return [{
                'name': r.id,
                'text': r.text,
                'similarity': r.score,
                'score': r.metadata['playbook_score'],
                'status': r.metadata['status'],
                'source': r.metadata['source']
            } for r in results]

        try:
            return _run_async_safe(_do_search())
        except Exception as e:
            print(f"Qdrant search failed: {e}", file=sys.stderr)
            return []

    def _search_chroma(self, query: str, limit: int, min_score: Optional[int]) -> List[Dict]:
        """Search using ChromaDB"""
        try:
            where = {}
            if min_score is not None:
                where = {"score": {"$gte": min_score}}

            results = self.backend['collection'].query(
                query_texts=[query],
                n_results=limit,
                where=where if where else None
            )

            if not results['ids'][0]:
                return []

            # Format results
            strategies = []
            for i, strategy_id in enumerate(results['ids'][0]):
                strategies.append({
                    'name': strategy_id,
                    'text': results['documents'][0][i],
                    'similarity': 1 - results['distances'][0][i],
                    'score': results['metadatas'][0][i].get('score', 0),
                    'status': results['metadatas'][0][i].get('status', 'active'),
                    'source': results['metadatas'][0][i].get('source', 'unknown')
                })

            return strategies

        except Exception as e:
            print(f"ChromaDB search failed: {e}", file=sys.stderr)
            return []

    def is_indexed(self) -> bool:
        """Check if vector store has been indexed"""
        if not self.backend:
            return False

        try:
            if self.backend['type'] == 'qdrant':
                async def _check():
                    stats = await self.backend['store'].get_collection_stats()
                    return stats.get('points_count', 0) > 0
                return _run_async_safe(_check())
            elif self.backend['type'] == 'chroma':
                return self.backend['collection'].count() > 0
        except Exception as e:
            print(f"Warning: Failed to check if indexed: {e}", file=sys.stderr)
            return False

        return False

    def get_stats(self) -> Dict:
        """Get statistics"""
        if not self.backend:
            return {'backend': 'none', 'indexed': False}

        stats = {
            'backend': self.backend_type,
            'indexed': self.is_indexed()
        }

        try:
            if self.backend['type'] == 'qdrant':
                async def _get_stats():
                    store_stats = await self.backend['store'].get_collection_stats()
                    return {**stats, **store_stats}
                return _run_async_safe(_get_stats())
            elif self.backend['type'] == 'chroma':
                stats['points_count'] = self.backend['collection'].count()
        except Exception as e:
            print(f"Warning: Failed to get detailed stats: {e}", file=sys.stderr)

        return stats
