"""
EmbeddingService -- Azure OpenAI text-embedding-3-large integration

Generates 3072-dimensional embeddings via Azure OpenAI API.
Replaces the previous Ollama-based embedding approach.
"""

import time
import logging
from typing import List, Optional
from openai import AzureOpenAI, OpenAI

from ..config import Config

logger = logging.getLogger('microfish.embedding')


class EmbeddingService:
    """Generate embeddings using Azure OpenAI text-embedding-3-large."""

    def __init__(
        self,
        model: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 60,
    ):
        self.model = model or Config.EMBEDDING_MODEL
        self.dimensions = Config.EMBEDDING_DIMENSIONS
        self.max_retries = max_retries
        self.timeout = timeout

        if Config.AZURE_OPENAI_API_KEY and Config.AZURE_OPENAI_ENDPOINT:
            self._client = AzureOpenAI(
                api_key=Config.AZURE_OPENAI_API_KEY,
                api_version=Config.AZURE_OPENAI_API_VERSION,
                azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
                timeout=timeout,
            )
            self._is_azure = True
        else:
            self._client = OpenAI(
                api_key=Config.LLM_API_KEY,
                base_url=Config.EMBEDDING_BASE_URL,
                timeout=timeout,
            )
            self._is_azure = False

        self._cache: dict[str, List[float]] = {}
        self._cache_max_size = 2000

    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            3072-dimensional float vector

        Raises:
            EmbeddingError: If API request fails after retries
        """
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty text")

        text = text.strip()

        if text in self._cache:
            return self._cache[text]

        vectors = self._request_embeddings([text])
        vector = vectors[0]

        self._cache_put(text, vector)

        return vector

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts
            batch_size: Number of texts per request

        Returns:
            List of embedding vectors (same order as input)
        """
        if not texts:
            return []

        results: List[Optional[List[float]]] = [None] * len(texts)
        uncached_indices: List[int] = []
        uncached_texts: List[str] = []

        for i, text in enumerate(texts):
            text = text.strip() if text else ""
            if text in self._cache:
                results[i] = self._cache[text]
            elif text:
                uncached_indices.append(i)
                uncached_texts.append(text)
            else:
                results[i] = [0.0] * self.dimensions

        if uncached_texts:
            all_vectors: List[List[float]] = []
            for start in range(0, len(uncached_texts), batch_size):
                batch = uncached_texts[start:start + batch_size]
                vectors = self._request_embeddings(batch)
                all_vectors.extend(vectors)

            for idx, vec, text in zip(uncached_indices, all_vectors, uncached_texts):
                results[idx] = vec
                self._cache_put(text, vec)

        return results  # type: ignore

    def _request_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Request embeddings from Azure OpenAI API with retry logic.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self._client.embeddings.create(
                    input=texts,
                    model=self.model,
                    dimensions=self.dimensions,
                )

                embeddings = [item.embedding for item in response.data]
                if len(embeddings) != len(texts):
                    raise EmbeddingError(
                        f"Expected {len(texts)} embeddings, got {len(embeddings)}"
                    )

                return embeddings

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Embedding request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt
                    logger.info(f"Retrying in {wait}s...")
                    time.sleep(wait)

        raise EmbeddingError(
            f"Embedding failed after {self.max_retries} retries: {last_error}"
        )

    def _cache_put(self, text: str, vector: List[float]) -> None:
        """Add to cache, evicting oldest entries if full."""
        if len(self._cache) >= self._cache_max_size:
            keys_to_remove = list(self._cache.keys())[:self._cache_max_size // 10]
            for key in keys_to_remove:
                del self._cache[key]
        self._cache[text] = vector

    def health_check(self) -> bool:
        """Check if embedding endpoint is reachable."""
        try:
            vec = self.embed("health check")
            return len(vec) > 0
        except Exception:
            return False


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""
    pass
