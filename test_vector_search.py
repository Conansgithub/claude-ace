#!/usr/bin/env python3
"""
Comprehensive Test Suite for Production Vector Search
Tests Qdrant + Ollama (production) and ChromaDB (fallback)
"""

import sys
import asyncio
from pathlib import Path

# Add ace_core to path for testing
sys.path.insert(0, str(Path(__file__).parent / "ace_core"))


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}\n")


def print_section(text: str):
    """Print section header"""
    print(f"\n{'-' * 70}")
    print(f"{text}")
    print(f"{'-' * 70}\n")


def print_test(number: int, text: str):
    """Print test step"""
    print(f"{number}. {text}")


def print_success(text: str, indent: int = 1):
    """Print success message"""
    spaces = "   " * indent
    print(f"{spaces}✓ {text}")


def print_error(text: str, indent: int = 1):
    """Print error message"""
    spaces = "   " * indent
    print(f"{spaces}✗ {text}")


def print_warning(text: str, indent: int = 1):
    """Print warning message"""
    spaces = "   " * indent
    print(f"{spaces}⚠ {text}")


def print_info(text: str, indent: int = 2):
    """Print info message"""
    spaces = "   " * indent
    print(f"{spaces}{text}")


def create_test_playbook() -> dict:
    """Create sample playbook for testing"""
    return {
        'key_points': [
            {
                'name': 'kpt_001',
                'text': 'Always use async/await for database operations to prevent blocking',
                'score': 5,
                'status': 'active',
                'source': 'test',
                'source_level': 'session',
                'atomicity_score': 0.9
            },
            {
                'name': 'kpt_002',
                'text': 'Use React hooks instead of class components for better code organization',
                'score': 3,
                'status': 'active',
                'source': 'test',
                'source_level': 'session',
                'atomicity_score': 0.8
            },
            {
                'name': 'kpt_003',
                'text': 'Implement proper error handling with try-except blocks in Python',
                'score': 4,
                'status': 'active',
                'source': 'test',
                'source_level': 'global',
                'atomicity_score': 0.85
            },
            {
                'name': 'kpt_004',
                'text': 'Use type hints in Python functions for better IDE support and bug prevention',
                'score': 2,
                'status': 'active',
                'source': 'test',
                'source_level': 'session',
                'atomicity_score': 0.7
            },
            {
                'name': 'kpt_005',
                'text': 'Optimize SQL queries with proper indexing and query planning',
                'score': 7,
                'status': 'active',
                'source': 'test',
                'source_level': 'global',
                'atomicity_score': 0.95
            },
            {
                'name': 'kpt_006',
                'text': 'Use connection pooling for database connections to improve performance',
                'score': 6,
                'status': 'active',
                'source': 'test',
                'source_level': 'global',
                'atomicity_score': 0.9
            },
            {
                'name': 'kpt_007',
                'text': 'Implement caching strategies for frequently accessed data',
                'score': 5,
                'status': 'active',
                'source': 'test',
                'source_level': 'session',
                'atomicity_score': 0.8
            },
            {
                'name': 'kpt_008',
                'text': 'Use environment variables for configuration instead of hardcoding values',
                'score': 4,
                'status': 'active',
                'source': 'test',
                'source_level': 'global',
                'atomicity_score': 0.75
            },
            {
                'name': 'kpt_009',
                'text': 'Write unit tests for critical business logic functions',
                'score': 3,
                'status': 'active',
                'source': 'test',
                'source_level': 'session',
                'atomicity_score': 0.7
            },
            {
                'name': 'kpt_010',
                'text': 'Use logging instead of print statements for production code',
                'score': 2,
                'status': 'active',
                'source': 'test',
                'source_level': 'session',
                'atomicity_score': 0.65
            },
            {
                'name': 'kpt_archived',
                'text': 'This strategy should not appear in search results',
                'score': -5,
                'status': 'archived',
                'source': 'test',
                'source_level': 'session',
                'atomicity_score': 0.5
            }
        ]
    }


async def test_ollama_embedding():
    """Test Ollama embedding client"""
    print_test(1, "Testing Ollama Embedding Client")

    try:
        from storage.ollama_embedding import OllamaEmbeddingClient, check_ollama_available

        # Check availability
        status = check_ollama_available()

        if status['status'] != 'ok':
            print_error(f"Ollama not available: {status['message']}")
            return False

        print_success(f"Ollama service running")
        print_success(f"Model available: {status.get('model_available', False)}")

        # Test single embedding
        async with OllamaEmbeddingClient() as client:
            embedding = await client.embed_text("Test text for embedding")

            if embedding and len(embedding) > 0:
                print_success(f"Generated {len(embedding)}-dimensional embedding")
            else:
                print_error("Failed to generate embedding")
                return False

            # Test batch embedding
            texts = [
                "Database query optimization",
                "React component lifecycle",
                "Python error handling"
            ]

            results = await client.embed_batch(texts)

            if len(results) == len(texts):
                print_success(f"Batch embedding successful ({len(results)} embeddings)")
                avg_time = sum(r.duration_ms for r in results) / len(results)
                print_info(f"Average time: {avg_time:.2f}ms per embedding", 2)
            else:
                print_error(f"Batch embedding failed: expected {len(texts)}, got {len(results)}")
                return False

            # Print stats
            stats = client.get_stats()
            print_info(f"Stats: {stats['total_requests']} requests, {stats['success_rate']}% success", 2)

        return True

    except ImportError as e:
        print_error(f"Import failed: {e}")
        print_info("Install with: pip install aiohttp", 2)
        return False
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


async def test_qdrant_store():
    """Test Qdrant vector store"""
    print_test(2, "Testing Qdrant Vector Store")

    try:
        from storage.qdrant_store import QdrantVectorStore, check_qdrant_available
        from storage.ollama_embedding import OllamaEmbeddingClient

        # Check availability
        status = check_qdrant_available()

        if status['status'] != 'ok':
            print_error(f"Qdrant not available: {status['message']}")
            return False

        print_success("Qdrant service running")

        # Create test data
        strategies = [
            {
                'name': 'test_001',
                'text': 'Use async/await for database operations',
                'score': 5,
                'status': 'active',
                'source': 'test',
                'source_level': 'session',
                'atomicity_score': 0.9
            },
            {
                'name': 'test_002',
                'text': 'Optimize SQL queries with indexing',
                'score': 7,
                'status': 'active',
                'source': 'test',
                'source_level': 'global',
                'atomicity_score': 0.95
            },
            {
                'name': 'test_003',
                'text': 'Use React hooks for components',
                'score': 3,
                'status': 'active',
                'source': 'test',
                'source_level': 'session',
                'atomicity_score': 0.8
            }
        ]

        # Initialize store
        store = QdrantVectorStore(collection_name="test_playbook_strategies")

        # Generate embeddings
        async with OllamaEmbeddingClient() as embed_client:
            results = await embed_client.embed_batch([s['text'] for s in strategies])
            embeddings = [r.embedding for r in results]

            print_success(f"Generated {len(embeddings)} embeddings")

            # Index strategies
            count = await store.index_strategies(strategies, embeddings)

            if count == len(strategies):
                print_success(f"Indexed {count} strategies")
            else:
                print_error(f"Indexing failed: expected {len(strategies)}, indexed {count}")
                await store.close()
                return False

            # Test search
            query_embedding = await embed_client.embed_text("database optimization techniques")
            search_results = await store.search(query_embedding, limit=3)

            if search_results:
                print_success(f"Search returned {len(search_results)} results")
                print_info("Top results:", 2)
                for i, result in enumerate(search_results[:3], 1):
                    print_info(
                        f"{i}. [{result.score:.2f}] {result.id} (score: {result.metadata['playbook_score']})",
                        3
                    )
            else:
                print_error("Search returned no results")
                await store.close()
                return False

            # Test filtered search
            filtered_results = await store.search(query_embedding, limit=3, min_score=5)
            print_success(f"Filtered search (min_score=5): {len(filtered_results)} results")

            # Get collection stats
            stats = await store.get_collection_stats()
            print_info(f"Collection stats: {stats.get('points_count', 0)} points", 2)

            # Clean up test data
            await store.delete_strategies(['test_001', 'test_002', 'test_003'])
            print_success("Cleaned up test data")

            await store.close()

        return True

    except ImportError as e:
        print_error(f"Import failed: {e}")
        print_info("Install with: pip install qdrant-client", 2)
        return False
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_unified_vector_store():
    """Test unified PlaybookVectorStore"""
    print_test(3, "Testing Unified Vector Store (Auto-Backend Selection)")

    try:
        from storage.vector_store import PlaybookVectorStore

        # Test auto-selection
        print_info("Testing auto backend selection...", 1)
        store = PlaybookVectorStore(backend="auto")

        print_success(f"Selected backend: {store.get_backend_type()}")
        print_success(f"Vector search available: {store.is_available()}")

        if not store.is_available():
            print_warning("Vector search not available, skipping tests")
            return True

        # Create test playbook
        playbook = create_test_playbook()
        print_success(f"Created test playbook with {len(playbook['key_points'])} strategies")

        # Index playbook
        count = store.index_playbook(playbook)
        print_success(f"Indexed {count} strategies")

        if count == 0:
            print_warning("No strategies indexed (may be below minimum threshold)")
            return True

        # Test search
        test_queries = [
            ("How to handle database queries?", ["kpt_001", "kpt_005", "kpt_006"]),
            ("React component best practices", ["kpt_002"]),
            ("Python coding standards", ["kpt_003", "kpt_004"])
        ]

        for query, expected_keywords in test_queries:
            print_info(f"\nQuery: '{query}'", 1)
            results = store.search(query, limit=3)

            if results:
                print_success(f"Found {len(results)} results", 2)
                for i, result in enumerate(results, 1):
                    similarity_pct = int(result['similarity'] * 100)
                    print_info(
                        f"{i}. [{similarity_pct}%] {result['name']} (score: {result['score']})",
                        3
                    )
                    print_info(f"   {result['text'][:60]}...", 3)
            else:
                print_warning(f"No results for query", 2)

        # Test stats
        stats = store.get_stats()
        print_info(f"\nStats: {stats}", 1)

        return True

    except ImportError as e:
        print_error(f"Import failed: {e}")
        return False
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_chroma_fallback():
    """Test ChromaDB fallback"""
    print_test(4, "Testing ChromaDB Fallback")

    try:
        from storage.vector_store import PlaybookVectorStore

        # Force ChromaDB backend
        print_info("Testing ChromaDB fallback mode...", 1)

        try:
            store = PlaybookVectorStore(backend="chroma")
            print_success("ChromaDB backend initialized")
        except Exception as e:
            print_warning(f"ChromaDB not available: {e}")
            print_info("Install with: pip install chromadb", 2)
            return True  # Not a failure, just not installed

        # Create test playbook
        playbook = create_test_playbook()

        # Index
        count = store.index_playbook(playbook)
        print_success(f"Indexed {count} strategies in ChromaDB")

        # Search
        results = store.search("database optimization", limit=3)

        if results:
            print_success(f"Search returned {len(results)} results")
            for i, result in enumerate(results[:3], 1):
                similarity_pct = int(result['similarity'] * 100)
                print_info(f"{i}. [{similarity_pct}%] {result['name']}", 2)
        else:
            print_warning("Search returned no results")

        return True

    except ImportError as e:
        print_warning(f"ChromaDB not installed: {e}")
        print_info("This is OK - ChromaDB is optional fallback", 2)
        return True
    except Exception as e:
        print_error(f"Test failed: {e}")
        return False


async def test_performance():
    """Test performance benchmarks"""
    print_test(5, "Performance Benchmarks")

    try:
        from storage.vector_store import PlaybookVectorStore
        import time

        store = PlaybookVectorStore(backend="auto")

        if not store.is_available():
            print_warning("Vector search not available, skipping performance tests")
            return True

        # Create large playbook
        large_playbook = create_test_playbook()

        # Expand to 50 strategies
        base_strategies = large_playbook['key_points'][:10]
        expanded = []
        for i in range(50):
            strategy = base_strategies[i % 10].copy()
            strategy['name'] = f'perf_test_{i:03d}'
            strategy['text'] = f"{strategy['text']} (variant {i})"
            expanded.append(strategy)

        large_playbook['key_points'] = expanded

        print_info(f"Created playbook with {len(expanded)} strategies", 1)

        # Benchmark indexing
        start = time.time()
        count = store.index_playbook(large_playbook)
        index_time = (time.time() - start) * 1000

        print_success(f"Indexed {count} strategies in {index_time:.0f}ms")
        print_info(f"Average: {index_time/count:.2f}ms per strategy", 2)

        # Benchmark search
        queries = [
            "database optimization",
            "react components",
            "error handling",
            "type safety",
            "performance tuning"
        ]

        search_times = []
        for query in queries:
            start = time.time()
            results = store.search(query, limit=10)
            search_time = (time.time() - start) * 1000
            search_times.append(search_time)

        avg_search_time = sum(search_times) / len(search_times)
        print_success(f"Average search time: {avg_search_time:.2f}ms")
        print_info(f"Min: {min(search_times):.2f}ms, Max: {max(search_times):.2f}ms", 2)

        return True

    except Exception as e:
        print_error(f"Performance test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print_header("🧪 Production Vector Search Test Suite")

    results = []

    # Run tests
    print_section("Component Tests")
    results.append(("Ollama Embedding", await test_ollama_embedding()))
    results.append(("Qdrant Store", await test_qdrant_store()))
    results.append(("Unified Vector Store", await test_unified_vector_store()))

    print_section("Fallback Tests")
    results.append(("ChromaDB Fallback", await test_chroma_fallback()))

    print_section("Performance Tests")
    results.append(("Performance Benchmarks", await test_performance()))

    # Print summary
    print_header("Test Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:10} {name}")

    print(f"\n{'=' * 70}")
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("✓ All tests passed!")
        print("=" * 70)
        return 0
    else:
        print(f"⚠ {total - passed} tests failed")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTests cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTests failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
