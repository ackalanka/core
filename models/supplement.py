# models/supplement.py
"""
Supplement and Condition models for knowledge base storage.
Includes vector embeddings for RAG semantic search.
"""

import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from database.connection import Base

# Embedding dimension for paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIMENSION = 384


class Condition(Base):
    """
    Medical condition category for supplements.

    Examples: АГ (Hypertension), СД2 (Diabetes), ИБС (Heart Disease)
    """

    __tablename__ = "conditions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Short code like АГ, СД2, ИБС",
    )
    name = Column(String(255), nullable=False, comment="Full name in Russian")
    name_en = Column(String(255), nullable=True, comment="Full name in English")
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationship to supplements
    supplements = relationship("Supplement", back_populates="condition")

    def __repr__(self) -> str:
        return f"<Condition {self.code}>"


class Supplement(Base):
    """
    Supplement/nutrient recommendation for a condition.

    Contains dosage, mechanism, keywords for search, warnings,
    and vector embeddings for semantic RAG search.
    """

    __tablename__ = "supplements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    condition_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conditions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False, index=True)
    dosage = Column(String(100), nullable=True)
    mechanism = Column(
        Text, nullable=True, comment="How the supplement helps (in Russian)"
    )
    keywords = Column(
        ARRAY(String), nullable=True, comment="Search keywords for retrieval"
    )  # type: ignore
    warnings = Column(Text, nullable=True, comment="Precautions and warnings")
    # Vector embedding for semantic search (RAG)
    embedding = Column(
        Vector(EMBEDDING_DIMENSION),
        nullable=True,
        comment="384-dim vector from sentence-transformers",
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationship to condition
    condition = relationship("Condition", back_populates="supplements")

    # Indexes
    __table_args__ = (
        Index("ix_supplements_keywords", "keywords", postgresql_using="gin"),
        # Note: HNSW index for vector similarity will be added via migration
    )

    def __repr__(self) -> str:
        return f"<Supplement {self.name}>"

    def get_embedding_text(self) -> str:
        """
        Get text representation for embedding generation.
        Combines name, mechanism, and keywords for richer context.
        """
        from typing import cast

        parts: list[str] = [cast(str, self.name)]
        if self.mechanism:
            parts.append(cast(str, self.mechanism))
        if self.keywords:
            keywords_list = cast(list[str], self.keywords)
            parts.append(" ".join(keywords_list))
        return " ".join(parts)

    def to_dict(self) -> dict:
        """Convert supplement to dictionary for API responses."""
        return {
            "id": str(self.id),
            "name": self.name,
            "dosage": self.dosage,
            "mechanism": self.mechanism,
            "keywords": self.keywords or [],
            "warnings": self.warnings,
            "has_embedding": self.embedding is not None,
        }
