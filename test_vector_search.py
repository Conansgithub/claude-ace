#!/usr/bin/env python3
"""
Test script for vector search functionality
Tests the PlaybookVectorStore with sample data
"""

import sys
from pathlib import Path

# Add ace_core to path
sys.path.insert(0, str(Path(__file__).parent / "ace_core" / "storage"))
sys.path.insert(0, str(Path(__file__).parent / "ace_core" / "hooks"))

def test_vector_search():
    """Test vector search with sample playbook"""
    print("=" * 60)
    print("🧪 Testing Vector Search Functionality")
    print("=" * 60)

    # Step 1: Import vector store
    print("\n1. Importing vector store...")
    try:
        from vector_store import PlaybookVectorStore
        print("   ✓ Vector store module imported")
    except ImportError as e:
        print(f"   ✗ Failed to import: {e}")
        print("\n   Please install chromadb:")
        print("   pip install chromadb")
        return False

    # Step 2: Create sample playbook
    print("\n2. Creating sample playbook...")
    sample_playbook = {
        "version": "1.0",
        "key_points": [
            {
                "name": "kpt_001",
                "text": "Always use async/await for database operations",
                "score": 5,
                "status": "active"
            },
            {
                "name": "kpt_002",
                "text": "Add type hints to all function signatures",
                "score": 3,
                "status": "active"
            },
            {
                "name": "kpt_003",
                "text": "Use React hooks instead of class components",
                "score": 4,
                "status": "active"
            },
            {
                "name": "kpt_004",
                "text": "Handle errors with proper try-except blocks",
                "score": 2,
                "status": "active"
            },
            {
                "name": "kpt_005",
                "text": "Write unit tests for all public functions",
                "score": 6,
                "status": "active"
            },
            {
                "name": "kpt_006",
                "text": "Use environment variables for configuration",
                "score": 1,
                "status": "active"
            },
            {
                "name": "kpt_007",
                "text": "Optimize SQL queries with proper indexing",
                "score": 7,
                "status": "active"
            },
            {
                "name": "kpt_008",
                "text": "Archived strategy example",
                "score": -5,
                "status": "archived"
            }
        ]
    }
    print(f"   ✓ Created sample playbook with {len(sample_playbook['key_points'])} strategies")

    # Step 3: Initialize vector store
    print("\n3. Initializing vector store...")
    try:
        vector_store = PlaybookVectorStore()
        stats = vector_store.get_stats()
        print(f"   ✓ Vector store initialized")
        print(f"   Location: {stats['persist_directory']}")
    except Exception as e:
        print(f"   ✗ Failed to initialize: {e}")
        return False

    # Step 4: Index playbook
    print("\n4. Indexing playbook...")
    try:
        indexed_count = vector_store.index_playbook(sample_playbook)
        print(f"   ✓ Indexed {indexed_count} strategies")
    except Exception as e:
        print(f"   ✗ Failed to index: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 5: Test searches
    print("\n5. Testing semantic search...")
    print("   " + "-" * 56)

    test_queries = [
        ("How to handle database queries?", "Should match database/async strategies"),
        ("React component best practices", "Should match React hooks strategy"),
        ("Testing guidelines", "Should match unit test strategy"),
        ("Error handling in Python", "Should match error handling strategy")
    ]

    for query, expected in test_queries:
        print(f"\n   Query: \"{query}\"")
        print(f"   Expected: {expected}")

        try:
            results = vector_store.search(query, limit=3, min_score=0)

            if results:
                print(f"   Results ({len(results)} found):")
                for i, result in enumerate(results, 1):
                    print(f"      {i}. [{result['similarity']:.0%}] {result['text'][:60]}...")
                    print(f"         (score: {result['score']:+d}, name: {result['name']})")
            else:
                print("   No results found")
        except Exception as e:
            print(f"   ✗ Search failed: {e}")

    print("\n" + "=" * 60)
    print("✓ Vector search test completed!")
    print("=" * 60)

    return True

if __name__ == "__main__":
    success = test_vector_search()
    sys.exit(0 if success else 1)
