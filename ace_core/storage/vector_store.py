"""
Vector Store for Playbook Strategies
Enables semantic search of strategies based on user queries
"""

from typing import List, Dict, Tuple
from pathlib import Path
import sys

# Check for ChromaDB availability
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("Warning: chromadb not available. Install with: pip install chromadb", file=sys.stderr)


class PlaybookVectorStore:
    """
    Vector storage for Playbook strategies using ChromaDB
    Enables semantic search to find relevant strategies
    """

    def __init__(self, persist_directory: str = None):
        """
        Initialize vector store

        Args:
            persist_directory: Path to store vector database
        """
        if not CHROMA_AVAILABLE:
            raise ImportError("chromadb is required. Install with: pip install chromadb")

        # Default to project data directory
        if persist_directory is None:
            persist_directory = str(Path.home() / ".claude" / "vector_db")

        self.persist_directory = persist_directory

        # Create directory if not exists
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

        # Create ChromaDB client
        self.client = chromadb.Client(Settings(
            persist_directory=self.persist_directory,
            anonymized_telemetry=False
        ))

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="playbook_strategies",
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )

    def index_playbook(self, playbook: Dict) -> int:
        """
        Index entire Playbook to vector database

        Args:
            playbook: Playbook dictionary

        Returns:
            Number of strategies indexed
        """
        # Clear existing index
        try:
            self.client.delete_collection("playbook_strategies")
            self.collection = self.client.create_collection(
                name="playbook_strategies",
                metadata={"hnsw:space": "cosine"}
            )
        except Exception:
            pass

        # Extract active strategies
        strategies = []
        ids = []
        metadatas = []

        for kp in playbook.get("key_points", []):
            # Only index active strategies
            if kp.get("status") != "active":
                continue

            strategies.append(kp["text"])
            ids.append(kp["name"])
            metadatas.append({
                "score": kp.get("score", 0),
                "atomicity_score": float(kp.get("atomicity_score", 0)) if kp.get("atomicity_score") else 0.0,
                "source": kp.get("source", "unknown"),
                "source_level": kp.get("source_level", "unknown")
            })

        # Add to collection
        if strategies:
            self.collection.add(
                documents=strategies,
                ids=ids,
                metadatas=metadatas
            )

            return len(strategies)

        return 0

    def search(
        self,
        query: str,
        limit: int = 10,
        min_score: int = None
    ) -> List[Dict]:
        """
        Search for relevant strategies using semantic similarity

        Args:
            query: User query text
            limit: Maximum number of results
            min_score: Minimum Playbook score filter (optional)

        Returns:
            List of strategy dictionaries with similarity scores
        """
        # Build filter conditions
        where = {}
        if min_score is not None:
            where["score"] = {"$gte": min_score}

        # Execute search
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where=where if where else None
            )
        except Exception as e:
            print(f"Vector search failed: {e}", file=sys.stderr)
            return []

        if not results['ids'][0]:
            return []

        # Format results
        strategies = []
        for i, strategy_id in enumerate(results['ids'][0]):
            strategies.append({
                "name": strategy_id,
                "text": results['documents'][0][i],
                "similarity": 1 - results['distances'][0][i],  # Convert distance to similarity
                "score": results['metadatas'][0][i].get('score', 0),
                "atomicity_score": results['metadatas'][0][i].get('atomicity_score', 0),
                "source": results['metadatas'][0][i].get('source', 'unknown'),
                "source_level": results['metadatas'][0][i].get('source_level', 'unknown')
            })

        return strategies

    def get_stats(self) -> Dict:
        """
        Get vector store statistics

        Returns:
            Dictionary with store statistics
        """
        try:
            count = self.collection.count()
        except Exception:
            count = 0

        return {
            "total_strategies": count,
            "collection_name": "playbook_strategies",
            "persist_directory": self.persist_directory
        }

    def is_indexed(self) -> bool:
        """Check if vector store has been indexed"""
        stats = self.get_stats()
        return stats['total_strategies'] > 0
