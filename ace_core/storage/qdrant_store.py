"""
Qdrant Vector Store
Production-grade vector database integration
"""

import asyncio
import sys
import uuid
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

try:
    from qdrant_client import QdrantClient, AsyncQdrantClient
    from qdrant_client.models import (
        Distance, VectorParams, PointStruct,
        Filter, FieldCondition, Range
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


def _run_async_safe(coro):
    """Safely run async coroutine, handling existing event loops"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        return asyncio.run(coro)
    else:
        print("Warning: Running in existing event loop context", file=sys.stderr)
        return loop.run_until_complete(coro)


@dataclass
class SearchResult:
    """Vector search result"""
    id: str
    score: float
    text: str
    metadata: Dict


class QdrantVectorStore:
    """
    Production-grade Qdrant vector store

    Features:
    - Async operations
    - Batch indexing
    - Filtered search
    - Health monitoring
    - Automatic collection management
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "playbook_strategies",
        vector_size: int = 768,  # qwen3-embedding dimension
        prefer_grpc: bool = False
    ):
        """
        Initialize Qdrant client

        Args:
            host: Qdrant server host
            port: Qdrant server port
            collection_name: Collection name for strategies
            vector_size: Embedding vector dimension
            prefer_grpc: Use gRPC instead of HTTP
        """
        if not QDRANT_AVAILABLE:
            raise ImportError(
                "qdrant-client not installed. "
                "Install with: pip install qdrant-client"
            )

        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.vector_size = vector_size

        # Initialize async client
        self.client = AsyncQdrantClient(
            host=host,
            port=port,
            prefer_grpc=prefer_grpc
        )

        # Stats
        self.stats = {
            'total_indexed': 0,
            'total_searches': 0,
            'total_errors': 0
        }

    async def health_check(self) -> Dict:
        """
        Check Qdrant service health

        Returns:
            Health check result
        """
        try:
            # Check service
            collections = await self.client.get_collections()

            # Check if our collection exists
            collection_exists = any(
                c.name == self.collection_name
                for c in collections.collections
            )

            # Get collection info if exists
            collection_info = None
            if collection_exists:
                info = await self.client.get_collection(self.collection_name)
                collection_info = {
                    'points_count': info.points_count,
                    'vectors_count': info.vectors_count,
                    'status': info.status
                }

            return {
                'status': 'ok',
                'service': 'running',
                'collection_exists': collection_exists,
                'collection_info': collection_info,
                'message': 'OK'
            }

        except Exception as e:
            return {
                'status': 'error',
                'service': 'unreachable',
                'message': f'Cannot connect to Qdrant: {str(e)}'
            }

    async def ensure_collection(self):
        """
        Create collection if it doesn't exist

        Returns:
            True if collection ready
        """
        try:
            # Check if collection exists
            collections = await self.client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)

            if not exists:
                # Create collection
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                print(f"✓ Created Qdrant collection: {self.collection_name}")

            return True

        except Exception as e:
            print(f"✗ Failed to create collection: {e}")
            self.stats['total_errors'] += 1
            return False

    async def index_strategies(
        self,
        strategies: List[Dict],
        embeddings: List[List[float]]
    ) -> int:
        """
        Index strategies with their embeddings

        Args:
            strategies: List of strategy dicts
            embeddings: List of embedding vectors

        Returns:
            Number of successfully indexed strategies
        """
        if len(strategies) != len(embeddings):
            raise ValueError("Strategies and embeddings length mismatch")

        if not strategies:
            return 0

        try:
            # Ensure collection exists
            await self.ensure_collection()

            # Prepare points
            points = []
            for strategy, embedding in zip(strategies, embeddings):
                # Generate UUID from strategy name for consistent ID
                # This allows us to update the same strategy by name
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, strategy['name']))

                points.append(
                    PointStruct(
                        id=point_id,  # Use UUID as ID
                        vector=embedding,
                        payload={
                            'name': strategy['name'],  # Store name in payload
                            'text': strategy['text'],
                            'score': strategy.get('score', 0),
                            'status': strategy.get('status', 'active'),
                            'source': strategy.get('source', 'unknown'),
                            'source_level': strategy.get('source_level', 'unknown'),
                            'atomicity_score': float(strategy.get('atomicity_score', 0))
                        }
                    )
                )

            # Batch upsert
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

            self.stats['total_indexed'] += len(points)
            return len(points)

        except Exception as e:
            print(f"✗ Failed to index strategies: {e}")
            self.stats['total_errors'] += 1
            raise

    async def search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        min_score: Optional[int] = None,
        status_filter: str = "active"
    ) -> List[SearchResult]:
        """
        Search for similar strategies

        Args:
            query_embedding: Query vector
            limit: Max results to return
            min_score: Minimum Playbook score filter
            status_filter: Status to filter by (default: active)

        Returns:
            List of search results
        """
        try:
            # Build filter
            filter_conditions = []

            # Status filter
            if status_filter:
                filter_conditions.append(
                    FieldCondition(
                        key="status",
                        match={"value": status_filter}
                    )
                )

            # Score filter
            if min_score is not None:
                filter_conditions.append(
                    FieldCondition(
                        key="score",
                        range=Range(gte=min_score)
                    )
                )

            # Build filter object
            search_filter = None
            if filter_conditions:
                search_filter = Filter(must=filter_conditions)

            # Execute search
            results = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                query_filter=search_filter
            )

            self.stats['total_searches'] += 1

            # Convert to SearchResult objects
            search_results = []
            for hit in results:
                search_results.append(
                    SearchResult(
                        id=hit.id,
                        score=hit.score,
                        text=hit.payload.get('text', ''),
                        metadata={
                            'playbook_score': hit.payload.get('score', 0),
                            'status': hit.payload.get('status', 'unknown'),
                            'source': hit.payload.get('source', 'unknown'),
                            'source_level': hit.payload.get('source_level', 'unknown'),
                            'atomicity_score': hit.payload.get('atomicity_score', 0)
                        }
                    )
                )

            return search_results

        except Exception as e:
            print(f"✗ Search failed: {e}")
            self.stats['total_errors'] += 1
            raise

    async def delete_strategies(self, strategy_names: List[str]) -> int:
        """
        Delete strategies by names

        Args:
            strategy_names: List of strategy names to delete

        Returns:
            Number of deleted strategies
        """
        try:
            # Convert names to UUIDs
            point_ids = [str(uuid.uuid5(uuid.NAMESPACE_DNS, name)) for name in strategy_names]

            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=point_ids
            )
            return len(point_ids)

        except Exception as e:
            print(f"✗ Failed to delete strategies: {e}")
            self.stats['total_errors'] += 1
            raise

    async def clear_collection(self):
        """Clear all points from collection"""
        try:
            await self.client.delete_collection(self.collection_name)
            await self.ensure_collection()
            print(f"✓ Cleared collection: {self.collection_name}")

        except Exception as e:
            print(f"✗ Failed to clear collection: {e}")
            self.stats['total_errors'] += 1
            raise

    async def get_collection_stats(self) -> Dict:
        """Get collection statistics"""
        try:
            info = await self.client.get_collection(self.collection_name)

            return {
                'points_count': info.points_count,
                'vectors_count': info.vectors_count,
                'indexed_vectors_count': info.indexed_vectors_count,
                'status': info.status,
                'optimizer_status': info.optimizer_status
            }

        except Exception as e:
            return {
                'error': str(e)
            }

    def get_stats(self) -> Dict:
        """Get operation statistics"""
        return {
            **self.stats,
            'collection': self.collection_name,
            'vector_size': self.vector_size
        }

    async def close(self):
        """Close Qdrant client"""
        await self.client.close()


# Sync convenience function
def check_qdrant_available(
    host: str = "localhost",
    port: int = 6333
) -> Dict:
    """
    Synchronous health check

    Returns:
        Health check result
    """
    async def _check():
        store = QdrantVectorStore(host=host, port=port)
        result = await store.health_check()
        await store.close()
        return result

    try:
        return _run_async_safe(_check())
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }
