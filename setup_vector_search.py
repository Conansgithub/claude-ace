#!/usr/bin/env python3
"""
Setup Script for Production Vector Search
Configures Qdrant + Ollama for Claude ACE
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Optional

# Add .claude/hooks to path so we can import ace_core modules
script_dir = Path(__file__).parent
claude_dir = script_dir.parent
hooks_dir = claude_dir / "hooks"
if hooks_dir.exists():
    sys.path.insert(0, str(hooks_dir))
else:
    # Running from repo root, not installed yet
    sys.path.insert(0, str(Path(__file__).parent / "ace_core"))


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def print_step(step: int, text: str):
    """Print step number"""
    print(f"{step}. {text}")


def print_success(text: str):
    """Print success message"""
    print(f"   ✓ {text}")


def print_error(text: str):
    """Print error message"""
    print(f"   ✗ {text}")


def print_warning(text: str):
    """Print warning message"""
    print(f"   ⚠ {text}")


async def check_qdrant(host: str = "localhost", port: int = 6333) -> Dict:
    """Check Qdrant service availability"""
    try:
        from storage.qdrant_store import QdrantVectorStore

        store = QdrantVectorStore(host=host, port=port)
        result = await store.health_check()
        await store.close()
        return result
    except ImportError as e:
        return {
            'status': 'error',
            'message': f'qdrant-client not installed: {e}'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


async def check_ollama(host: str = "http://localhost:11434", model: str = "qwen3-embedding:0.6b") -> Dict:
    """Check Ollama service and model availability"""
    try:
        from storage.ollama_embedding import OllamaEmbeddingClient

        async with OllamaEmbeddingClient(host=host, model=model) as client:
            # Try to list models to check service availability
            try:
                models = await client.list_models()
                model_available = model in models

                return {
                    'status': 'ok' if model_available else 'warning',
                    'model_available': model_available,
                    'available_models': models[:5] if models else []
                }
            except Exception as e:
                return {
                    'status': 'error',
                    'message': str(e)
                }
    except ImportError as e:
        return {
            'status': 'error',
            'message': f'aiohttp not installed: {e}'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


async def test_embedding_generation(host: str, model: str) -> bool:
    """Test embedding generation"""
    try:
        from storage.ollama_embedding import OllamaEmbeddingClient

        async with OllamaEmbeddingClient(host=host, model=model) as client:
            embedding = await client.embed_text("Test embedding generation")

            if embedding and len(embedding) > 0:
                print_success(f"Generated {len(embedding)}-dimensional embedding")
                return True
            else:
                print_error("Empty embedding returned")
                return False

    except Exception as e:
        print_error(f"Failed to generate embedding: {e}")
        return False


async def test_qdrant_indexing(host: str, port: int, collection: str) -> bool:
    """Test Qdrant collection creation and indexing"""
    try:
        from storage.qdrant_store import QdrantVectorStore
        from storage.ollama_embedding import OllamaEmbeddingClient

        # Create test strategy
        test_strategies = [{
            'name': 'test_strategy_001',
            'text': 'This is a test strategy for vector search setup',
            'score': 0,
            'status': 'active',
            'source': 'setup_test'
        }]

        # Initialize clients
        store = QdrantVectorStore(host=host, port=port, collection_name=collection)

        async with OllamaEmbeddingClient() as embed_client:
            # Generate embedding
            results = await embed_client.embed_batch([s['text'] for s in test_strategies])
            embeddings = [r.embedding for r in results]

            # Index in Qdrant
            count = await store.index_strategies(test_strategies, embeddings)

            if count > 0:
                print_success(f"Successfully indexed {count} test strategy")

                # Test search
                query_embedding = await embed_client.embed_text("test strategy")
                search_results = await store.search(query_embedding, limit=1)

                if search_results:
                    print_success(f"Search working (found {len(search_results)} results)")

                    # Clean up test data
                    await store.delete_strategies(['test_strategy_001'])
                    print_success("Cleaned up test data")

                    await store.close()
                    return True
                else:
                    print_warning("Search returned no results")
                    await store.close()
                    return False
            else:
                print_error("Failed to index test strategy")
                await store.close()
                return False

    except Exception as e:
        print_error(f"Qdrant indexing test failed: {e}")
        return False


def create_config(
    qdrant_host: str = "localhost",
    qdrant_port: int = 6333,
    ollama_host: str = "http://localhost:11434",
    ollama_model: str = "qwen3-embedding:0.6b",
    collection: str = "playbook_strategies"
) -> Dict:
    """Create vector search configuration"""
    return {
        'vector_search': {
            'ollama': {
                'host': ollama_host,
                'model': ollama_model
            },
            'qdrant': {
                'host': qdrant_host,
                'port': qdrant_port,
                'collection': collection
            },
            'min_strategies_for_index': 10,
            'search': {
                'default_limit': 10,
                'similarity_threshold': 0.7
            }
        }
    }


def save_config(config: Dict, config_path: Path) -> bool:
    """Save configuration to file"""
    try:
        # Create directory if needed
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config if exists
        existing_config = {}
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    existing_config = json.load(f)
            except Exception:
                pass

        # Merge configurations
        existing_config.update(config)

        # Save
        with open(config_path, 'w') as f:
            json.dump(existing_config, f, indent=2)

        print_success(f"Configuration saved to {config_path}")
        return True

    except Exception as e:
        print_error(f"Failed to save configuration: {e}")
        return False


async def main():
    """Main setup process"""
    print_header("Production Vector Search Setup")
    print("Configuring Qdrant + Ollama for Claude ACE\n")

    # Configuration
    qdrant_host = "localhost"
    qdrant_port = 6333
    ollama_host = "http://localhost:11434"
    ollama_model = "qwen3-embedding:0.6b"
    collection_name = "playbook_strategies"

    config_path = Path.home() / ".claude" / "ace_config.json"

    success = True

    # Step 1: Check dependencies
    print_step(1, "Checking Python dependencies...")

    try:
        import aiohttp
        print_success("aiohttp installed")
    except ImportError:
        print_error("aiohttp not installed")
        print("   Install with: pip install aiohttp")
        success = False

    try:
        from qdrant_client import QdrantClient
        print_success("qdrant-client installed")
    except ImportError:
        print_error("qdrant-client not installed")
        print("   Install with: pip install qdrant-client")
        success = False

    if not success:
        print("\n" + "=" * 60)
        print("Please install missing dependencies and run again")
        print("=" * 60)
        return 1

    # Step 2: Check Qdrant service
    print_step(2, "Checking Qdrant service...")

    qdrant_status = await check_qdrant(host=qdrant_host, port=qdrant_port)

    if qdrant_status['status'] == 'ok':
        print_success(f"Qdrant running at {qdrant_host}:{qdrant_port}")
        if qdrant_status.get('collection_exists'):
            print_success(f"Collection '{collection_name}' already exists")
            if qdrant_status.get('collection_info'):
                info = qdrant_status['collection_info']
                print(f"      Points: {info.get('points_count', 0)}")
        else:
            print(f"      Collection '{collection_name}' will be created")
    else:
        print_error(f"Qdrant not available: {qdrant_status['message']}")
        print("   Make sure Qdrant is running:")
        print("   docker run -p 6333:6333 qdrant/qdrant")
        success = False

    # Step 3: Check Ollama service
    print_step(3, "Checking Ollama service...")

    ollama_status = await check_ollama(host=ollama_host, model=ollama_model)

    if ollama_status['status'] in ['ok', 'warning']:
        print_success(f"Ollama running at {ollama_host}")

        if ollama_status.get('model_available'):
            print_success(f"Model '{ollama_model}' available")
        else:
            print_warning(f"Model '{ollama_model}' not found")
            print(f"   Install with: ollama pull {ollama_model}")
            available = ollama_status.get('available_models', [])
            if available:
                print(f"   Available models: {', '.join(available[:3])}")
            success = False
    else:
        print_error(f"Ollama not available: {ollama_status['message']}")
        print("   Make sure Ollama is running:")
        print("   ollama serve")
        success = False

    if not success:
        print("\n" + "=" * 60)
        print("Please start required services and run again")
        print("=" * 60)
        return 1

    # Step 4: Test embedding generation
    print_step(4, "Testing embedding generation...")

    if not await test_embedding_generation(ollama_host, ollama_model):
        print_error("Embedding generation test failed")
        return 1

    # Step 5: Test Qdrant indexing
    print_step(5, "Testing Qdrant indexing and search...")

    if not await test_qdrant_indexing(qdrant_host, qdrant_port, collection_name):
        print_error("Qdrant indexing test failed")
        return 1

    # Step 6: Save configuration
    print_step(6, "Saving configuration...")

    config = create_config(
        qdrant_host=qdrant_host,
        qdrant_port=qdrant_port,
        ollama_host=ollama_host,
        ollama_model=ollama_model,
        collection=collection_name
    )

    if not save_config(config, config_path):
        return 1

    # Success!
    print_header("✓ Setup Complete!")

    print("Production vector search is configured and ready to use.\n")
    print("Configuration:")
    print(f"  • Qdrant: {qdrant_host}:{qdrant_port}")
    print(f"  • Ollama: {ollama_host}")
    print(f"  • Model: {ollama_model}")
    print(f"  • Collection: {collection_name}")
    print(f"  • Config: {config_path}\n")

    print("Next steps:")
    print("  1. Run installation: python install.py")
    print("  2. Run test suite: python test_vector_search.py")
    print("  3. Start using Claude Code with ACE!\n")

    print("=" * 60)

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nSetup failed with error: {e}")
        sys.exit(1)
