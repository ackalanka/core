# models/refresh_token.py
"""
Refresh token model for secure token rotation and revocation.
Implements industry-standard token family tracking for theft detection.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.connection import Base


class RefreshToken(Base):
    """
    Refresh token model for secure session management.

    Attributes:
        id: Unique token identifier (UUID)
        user_id: Foreign key to users table
        token_hash: SHA-256 hash of the refresh token (never store plain text)
        family_id: Token family for rotation tracking (detect theft)
        expires_at: Token expiration timestamp
        revoked: Whether the token has been revoked
        revoked_at: When the token was revoked (if applicable)
        created_at: Token creation timestamp
        user_agent: Client user agent string (optional, for device tracking)
        ip_address: Client IP address (optional, for auditing)
    """

    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    family_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length

    # Relationship to User
    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self) -> str:
        return f"<RefreshToken {self.id} user={self.user_id} revoked={self.revoked}>"

    def is_valid(self) -> bool:
        """Check if token is valid (not revoked and not expired)."""
        if self.revoked:
            return False
        if datetime.now(UTC) > self.expires_at:
            return False
        return True

    from typing import Any

    def to_dict(self) -> dict[str, Any]:
        """Convert token to dictionary (safe, no hash)."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "family_id": str(self.family_id),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked": self.revoked,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
