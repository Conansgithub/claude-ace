"""
Ollama Embedding Client
Production-grade local embedding service integration
"""

import asyncio
import aiohttp
import sys
import time
from typing import List, Dict, Optional
from dataclasses import dataclass


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
class EmbeddingResult:
    """Result from embedding generation"""
    text: str
    embedding: List[float]
    model: str
    duration_ms: float


class OllamaEmbeddingClient:
    """
    Production-grade Ollama embedding client

    Features:
    - Async batch processing
    - Connection pooling
    - Error handling with retry
    - Health checking
    - Performance monitoring
    """

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "qwen3-embedding:0.6b",
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize Ollama client

        Args:
            host: Ollama server URL
            model: Embedding model name
            timeout: Request timeout in seconds
            max_retries: Max retry attempts on failure
        """
        self.host = host.rstrip('/')
        self.model = model
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None

        # Performance stats
        self.stats = {
            'total_requests': 0,
            'total_embeddings': 0,
            'total_failures': 0,
            'total_duration_ms': 0
        }

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def _ensure_session(self):
        """Ensure HTTP session exists"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def health_check(self) -> Dict:
        """
        Check Ollama service health

        Returns:
            Dict with status and details
        """
        try:
            await self._ensure_session()

            # Check if service is running
            async with self._session.get(f"{self.host}/api/tags") as resp:
                if resp.status != 200:
                    return {
                        'status': 'error',
                        'message': f'Ollama service returned {resp.status}'
                    }

                data = await resp.json()

                # Check if our model is available
                models = [m['name'] for m in data.get('models', [])]
                model_available = self.model in models

                return {
                    'status': 'ok' if model_available else 'warning',
                    'service': 'running',
                    'model_available': model_available,
                    'available_models': models,
                    'message': 'OK' if model_available else f'Model {self.model} not found'
                }

        except aiohttp.ClientError as e:
            return {
                'status': 'error',
                'service': 'unreachable',
                'message': f'Cannot connect to Ollama: {str(e)}'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Health check failed: {str(e)}'
            }

    async def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text

        Args:
            text: Input text

        Returns:
            Embedding vector or None on failure
        """
        result = await self.embed_batch([text])
        if result and len(result) > 0:
            return result[0].embedding
        return None

    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 10
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts with batching

        Args:
            texts: List of input texts
            batch_size: Number of concurrent requests

        Returns:
            List of embedding results
        """
        if not texts:
            return []

        await self._ensure_session()

        # Process in batches for better performance
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_results = await self._process_batch(batch)
            results.extend(batch_results)

        return results

    async def _process_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """Process a batch of texts concurrently"""
        tasks = [self._embed_single(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions, keep successful results
        valid_results = []
        for result in results:
            if isinstance(result, EmbeddingResult):
                valid_results.append(result)
            elif isinstance(result, Exception):
                self.stats['total_failures'] += 1
                print(f"Warning: Embedding failed: {result}")

        return valid_results

    async def _embed_single(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for single text with retry

        Args:
            text: Input text

        Returns:
            EmbeddingResult

        Raises:
            Exception on failure after retries
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                # Call Ollama API
                async with self._session.post(
                    f"{self.host}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text
                    }
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(f"API returned {resp.status}: {error_text}")

                    data = await resp.json()
                    embedding = data.get('embedding')

                    if not embedding:
                        raise Exception("No embedding in response")

                    duration_ms = (time.time() - start_time) * 1000

                    # Update stats
                    self.stats['total_requests'] += 1
                    self.stats['total_embeddings'] += 1
                    self.stats['total_duration_ms'] += duration_ms

                    return EmbeddingResult(
                        text=text,
                        embedding=embedding,
                        model=self.model,
                        duration_ms=duration_ms
                    )

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
                    continue

        # All retries failed
        raise last_error

    def get_stats(self) -> Dict:
        """Get performance statistics"""
        avg_duration = 0
        if self.stats['total_embeddings'] > 0:
            avg_duration = self.stats['total_duration_ms'] / self.stats['total_embeddings']

        return {
            **self.stats,
            'avg_duration_ms': round(avg_duration, 2),
            'success_rate': round(
                (self.stats['total_embeddings'] / max(self.stats['total_requests'], 1)) * 100,
                2
            )
        }


# Convenience functions for sync usage
def check_ollama_available(
    host: str = "http://localhost:11434",
    model: str = "qwen3-embedding:0.6b"
) -> Dict:
    """
    Synchronous health check

    Returns:
        Health check result dict
    """
    async def _check():
        async with OllamaEmbeddingClient(host=host, model=model) as client:
            return await client.health_check()

    try:
        return _run_async_safe(_check())
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }
