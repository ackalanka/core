# models/supplement.py
"""
Supplement and Condition models for knowledge base storage.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from database.connection import Base


class Condition(Base):
    """
    Medical condition category for supplements.
    
    Examples: АГ (Hypertension), СД2 (Diabetes), ИБС (Heart Disease)
    """
    __tablename__ = "conditions"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Short code like АГ, СД2, ИБС"
    )
    name = Column(
        String(255),
        nullable=False,
        comment="Full name in Russian"
    )
    name_en = Column(
        String(255),
        nullable=True,
        comment="Full name in English"
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    # Relationship to supplements
    supplements = relationship("Supplement", back_populates="condition")
    
    def __repr__(self) -> str:
        return f"<Condition {self.code}>"


class Supplement(Base):
    """
    Supplement/nutrient recommendation for a condition.
    
    Contains dosage, mechanism, keywords for search, and warnings.
    The embedding column is reserved for future RAG vector search.
    """
    __tablename__ = "supplements"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    condition_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conditions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = Column(
        String(255),
        nullable=False,
        index=True
    )
    dosage = Column(
        String(100),
        nullable=True
    )
    mechanism = Column(
        Text,
        nullable=True,
        comment="How the supplement helps (in Russian)"
    )
    keywords = Column(
        ARRAY(String),
        nullable=True,
        comment="Search keywords for retrieval"
    )
    warnings = Column(
        Text,
        nullable=True,
        comment="Precautions and warnings"
    )
    # Reserved for RAG vector embeddings (Phase 2.5)
    # Will be: embedding = Column(Vector(384), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    # Relationship to condition
    condition = relationship("Condition", back_populates="supplements")
    
    # Index for keyword search
    __table_args__ = (
        Index('ix_supplements_keywords', 'keywords', postgresql_using='gin'),
    )
    
    def __repr__(self) -> str:
        return f"<Supplement {self.name}>"
    
    def to_dict(self) -> dict:
        """Convert supplement to dictionary for API responses."""
        return {
            "id": str(self.id),
            "name": self.name,
            "dosage": self.dosage,
            "mechanism": self.mechanism,
            "keywords": self.keywords or [],
            "warnings": self.warnings
        }
