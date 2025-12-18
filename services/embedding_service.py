# services/embedding_service.py
"""
Embedding service for generating vector embeddings from text.
Uses sentence-transformers with multilingual model for Russian support.
"""
import logging
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Model configuration
# paraphrase-multilingual-MiniLM-L12-v2: 384 dimensions, supports 50+ languages including Russian
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIMENSION = 384


class EmbeddingService:
    """
    Service for generating text embeddings using sentence-transformers.

    Uses a multilingual model that supports Russian text for the
    CardioVoice supplement knowledge base.
    """

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model_name = model_name
        self._model = None
        logger.info(f"EmbeddingService initialized (model: {model_name})")

    @property
    def model(self):
        """Lazy load the model on first use."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            logger.info(f"Model loaded successfully")
        return self._model

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            return [0.0] * EMBEDDING_DIMENSION

        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def generate_embeddings_batch(
        self, texts: List[str], batch_size: int = 32, show_progress: bool = True
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once
            show_progress: Show progress bar

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Filter empty texts but keep track of indices
        valid_indices = []
        valid_texts = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_indices.append(i)
                valid_texts.append(text)

        if not valid_texts:
            return [[0.0] * EMBEDDING_DIMENSION] * len(texts)

        logger.info(f"Generating embeddings for {len(valid_texts)} texts...")

        embeddings = self.model.encode(
            valid_texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )

        # Reconstruct full results with zeros for empty texts
        result = [[0.0] * EMBEDDING_DIMENSION] * len(texts)
        for i, idx in enumerate(valid_indices):
            result[idx] = embeddings[i].tolist()

        return result

    def compute_similarity(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (0 to 1)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    @staticmethod
    def get_dimension() -> int:
        """Get the embedding dimension for the model."""
        return EMBEDDING_DIMENSION


# Singleton instance
embedding_service = EmbeddingService()
