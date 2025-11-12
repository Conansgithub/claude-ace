#!/usr/bin/env python3
"""
Diagnose why playbook strategies are not indexed in Qdrant
"""
import json
import sys
import asyncio
from pathlib import Path

# Add .claude/hooks to path so we can import storage modules
script_dir = Path(__file__).parent
claude_dir = script_dir.parent
hooks_dir = claude_dir / "hooks"
if hooks_dir.exists():
    sys.path.insert(0, str(hooks_dir))
else:
    # Running from repo root, not installed yet
    sys.path.insert(0, str(Path(__file__).parent / "ace_core"))

from storage.qdrant_store import QdrantVectorStore
from storage.ollama_embedding import OllamaEmbeddingClient


async def diagnose(playbook_path: str = None, project_dir: str = None):
    """Diagnose vector indexing issues"""

    print("=" * 60)
    print("ACE Vector Search Diagnostic Tool")
    print("=" * 60)
    print()

    # 1. Find playbook.json
    if playbook_path:
        pb_path = Path(playbook_path)
    elif project_dir:
        pb_path = Path(project_dir) / ".claude" / "playbook.json"
    else:
        # Check common locations
        locations = [
            Path.home() / ".claude" / "playbook.json",
            Path.cwd() / ".claude" / "playbook.json",
        ]
        pb_path = None
        for loc in locations:
            if loc.exists():
                pb_path = loc
                break

    if not pb_path or not pb_path.exists():
        print(f"❌ Playbook not found!")
        print(f"   Checked locations:")
        if playbook_path:
            print(f"   - {playbook_path}")
        else:
            for loc in locations:
                print(f"   - {loc}")
        print()
        print("💡 Solution: Create playbook.json first or specify path with --playbook")
        return

    print(f"✓ Found playbook: {pb_path}")
    print()

    # 2. Load and analyze playbook
    try:
        with open(pb_path, 'r') as f:
            playbook = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load playbook: {e}")
        return

    key_points = playbook.get('key_points', [])
    print(f"📊 Playbook Statistics:")
    print(f"   Total key points: {len(key_points)}")

    # Count by status
    status_counts = {}
    for kp in key_points:
        status = kp.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1

    for status, count in status_counts.items():
        print(f"   - {status}: {count}")

    active_strategies = [kp for kp in key_points if kp.get('status') == 'active']
    print(f"   Active strategies: {len(active_strategies)}")
    print()

    # 3. Check minimum threshold
    MIN_STRATEGIES = 10
    if len(active_strategies) < MIN_STRATEGIES:
        print(f"⚠️  WARNING: Not enough active strategies!")
        print(f"   Current: {len(active_strategies)}")
        print(f"   Required: {MIN_STRATEGIES}")
        print()
        print(f"💡 Solution: Add more strategies to playbook or change")
        print(f"   'min_strategies_for_index' in ace_config.json")
        print()
        if len(active_strategies) > 0:
            print("   Current active strategies:")
            for i, kp in enumerate(active_strategies[:5], 1):
                text = kp.get('text', '')[:60]
                print(f"   {i}. {text}...")
        return

    print(f"✓ Enough active strategies ({len(active_strategies)} >= {MIN_STRATEGIES})")
    print()

    # 4. Check Qdrant connection
    print("🔍 Checking Qdrant connection...")
    try:
        store = QdrantVectorStore(host='localhost', port=6333, collection_name='playbook_strategies')
        health = await store.health_check()

        if health.get('status') == 'ok':
            print(f"✓ Qdrant connected")
            print(f"   Status: {health.get('service', 'running')}")

            if health.get('collection_exists'):
                collection_info = health.get('collection_info', {})
                print(f"✓ Collection 'playbook_strategies' exists")
                print(f"   Points count: {collection_info.get('points_count', 0)}")
                print(f"   Status: {collection_info.get('status', 'unknown')}")
            else:
                print(f"⚠️  Collection 'playbook_strategies' does not exist")
                print(f"   Will be created on first index")
        else:
            print(f"❌ Qdrant not connected")
            print(f"   Error: {health.get('message', 'Unknown error')}")
            await store.close()
            return

        print()

        # 5. Check Ollama
        print("🔍 Checking Ollama embedding service...")
        try:
            async with OllamaEmbeddingClient() as embed_client:
                embed_health = await embed_client.health_check()

                if embed_health.get('status') == 'ok' or embed_health.get('status') == 'warning':
                    print(f"✓ Ollama connected")
                    print(f"   Status: {embed_health.get('service', 'running')}")
                    print(f"   Model: {embed_client.model}")

                    # Get vector dimension by testing
                    test_embedding = await embed_client.embed_text("test")
                    if test_embedding:
                        print(f"   Vector dimension: {len(test_embedding)}")
                    else:
                        print(f"   ⚠️  Could not determine vector dimension")
                else:
                    print(f"❌ Ollama not connected")
                    print(f"   Error: {embed_health.get('message', 'Unknown error')}")
                    await store.close()
                    return
        except Exception as e:
            print(f"❌ Ollama check failed: {e}")
            import traceback
            traceback.print_exc()
            await store.close()
            return

        print()

        # 6. Try to index
        print("🚀 Attempting to index strategies...")
        try:
            # Get embeddings and test search in same context
            texts = [kp['text'] for kp in active_strategies]

            async with OllamaEmbeddingClient() as embed_client:
                results = await embed_client.embed_batch(texts)
                embeddings = [r.embedding for r in results]

                # Index
                count = await store.index_strategies(active_strategies, embeddings)

                if count > 0:
                    print(f"✅ Successfully indexed {count} strategies!")
                    print()

                    # Verify
                    health_after = await store.health_check()
                    collection_info = health_after.get('collection_info', {})
                    print(f"📊 Qdrant collection after indexing:")
                    print(f"   Points count: {collection_info.get('points_count', 0)}")

                    # Test search (within same async context to reuse session)
                    print()
                    print("🔍 Testing vector search...")
                    query_embedding = await embed_client.embed_text("handle errors")
                    search_results = await store.search(query_embedding, limit=3)

                    if search_results:
                        print(f"✓ Search working! Found {len(search_results)} results:")
                        for i, result in enumerate(search_results, 1):
                            name = result.metadata.get('name', 'unknown')
                            text = result.text[:60] if len(result.text) > 60 else result.text
                            score = result.score
                            print(f"   {i}. [{name}] (score: {score:.3f})")
                            print(f"      {text}...")
                    else:
                        print(f"⚠️  Search returned no results")
                else:
                    print(f"❌ Indexing failed (returned 0 count)")

        except Exception as e:
            print(f"❌ Indexing failed: {e}")
            import traceback
            traceback.print_exc()

        await store.close()

    except Exception as e:
        print(f"❌ Qdrant connection failed: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 60)
    print("Diagnosis complete!")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Diagnose ACE vector indexing')
    parser.add_argument('--playbook', help='Path to playbook.json')
    parser.add_argument('--project', help='Path to project directory (will look for .claude/playbook.json)')

    args = parser.parse_args()

    asyncio.run(diagnose(playbook_path=args.playbook, project_dir=args.project))
