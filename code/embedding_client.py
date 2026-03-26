#!/usr/bin/env python3
"""
Embedding Client Module
Interface with Ollama for embedding generation.
"""

import time
import logging
from typing import List, Optional
import numpy as np
import ollama
from tqdm import tqdm

logger = logging.getLogger(__name__)

class EmbeddingClient:
    """Client for generating embeddings via Ollama."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        host: str = "http://localhost:11434",
        timeout: int = 120,
        max_retries: int = 3
    ):
        """
        Args:
            model: Ollama model name
            host: Ollama API host
            timeout: Request timeout in seconds
            max_retries: Number of retry attempts on failure
        """
        self.model = model
        self.host = host
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = ollama.Client(host=host)

        # Verify connection
        try:
            self.client.list()
            logger.info(f"Connected to Ollama at {host}")
        except Exception as e:
            logger.error(f"Cannot connect to Ollama at {host}: {e}")
            raise

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            List of embedding values, or None on failure
        """
        if not text or len(text.strip()) == 0:
            logger.warning("Empty text provided for embedding")
            return None

        for attempt in range(self.max_retries):
            try:
                response = self.client.embed(model=self.model, input=text)
                # ollama returns dict with 'embeddings' key
                embedding = response.get('embeddings')
                if embedding and len(embedding) > 0:
                    return embedding[0]  # First (and only) embedding
                else:
                    logger.error(f"No embedding returned: {response}")
                    return None

            except Exception as e:
                logger.warning(f"Embedding attempt {attempt+1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    backoff = 2 ** attempt
                    time.sleep(backoff)
                else:
                    logger.error(f"All embedding attempts failed for text (length={len(text)})")
                    return None

    def generate_embeddings_batch(self, texts: List[str], show_progress: bool = True) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            show_progress: Show tqdm progress bar

        Returns:
            List of embeddings (None for failures)
        """
        embeddings = []
        iterator = tqdm(texts, desc="Generating embeddings") if show_progress else texts

        for text in iterator:
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)
            # Small delay to avoid overwhelming Ollama
            time.sleep(0.1)

        return embeddings

    def generate_embedding_from_chunks(self, chunks: List[str], batch_size: int = 10) -> Optional[List[float]]:
        """
        Generate embedding by averaging embeddings from multiple chunks.
        Uses batch embedding for efficiency when dealing with many chunks.

        Args:
            chunks: List of text chunks
            batch_size: Number of chunks to embed in parallel per API call

        Returns:
            Averaged embedding vector, or None if all chunks fail
        """
        if not chunks:
            logger.warning("No chunks provided for embedding")
            return None

        embeddings = []

        # Process in batches for better performance (Ollama can handle multiple inputs)
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            batch_embeddings = self._generate_embeddings_batch_ollama(batch)
            embeddings.extend([emb for emb in batch_embeddings if emb is not None])
            time.sleep(0.05)  # Small pause between batches

        if not embeddings:
            logger.error("All chunks failed to generate embeddings")
            return None

        # Average embeddings element-wise
        if len(embeddings) == 1:
            # Still normalize single vectors to ensure unit length
            emb_array = np.array(embeddings[0])
            norm = np.linalg.norm(emb_array)
            if norm > 0:
                return (emb_array / norm).tolist()
            return embeddings[0]

        # Average all embeddings
        dim = len(embeddings[0])
        summed = [0.0] * dim
        for emb in embeddings:
            for i, val in enumerate(emb):
                summed[i] += val

        averaged = np.array([val / len(embeddings) for val in summed])

        # NORMALIZE: The average of unit vectors is not necessarily unit length.
        # Normalize to ensure cosine similarity works correctly (cosine = dot product of normalized vectors).
        norm = np.linalg.norm(averaged)
        if norm > 0:
            averaged = averaged / norm

        logger.info(f"Averaged {len(embeddings)} chunk embeddings into final vector (normalized)")
        return averaged.tolist()

    def _generate_embeddings_batch_ollama(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Send batch request to Ollama embed endpoint.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings (may contain None for failures)
        """
        if not texts:
            return []

        for attempt in range(self.max_retries):
            try:
                response = self.client.embed(model=self.model, input=texts)
                embeddings = response.get('embeddings', [])
                if embeddings and len(embeddings) >= len(texts):
                    return embeddings
                else:
                    logger.warning(f"Batch returned {len(embeddings)} embeddings for {len(texts)} inputs")
                    # Pad with None for missing embeddings
                    result = embeddings + [None] * (len(texts) - len(embeddings))
                    return result
            except Exception as e:
                logger.warning(f"Batch embed attempt {attempt+1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    backoff = 2 ** attempt
                    time.sleep(backoff)
                else:
                    logger.error(f"All batch embed attempts failed for {len(texts)} texts")
                    return [None] * len(texts)

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings from the model."""
        # nomic-embed-text produces 768-dimensional embeddings
        # We could probe this by embedding a test string
        test_embed = self.generate_embedding("test")
        if test_embed:
            return len(test_embed)
        return 768  # Known dimension for nomic-embed-text
