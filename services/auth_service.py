# services/auth_service.py
"""
Authentication service for user management and JWT token handling.
Uses PostgreSQL database for persistent storage.
Implements refresh token rotation with family tracking for security.
"""

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from sqlalchemy.exc import IntegrityError

from config import settings
from database.connection import get_db_session
from models import RefreshToken, User

logger = logging.getLogger(__name__)


class AuthService:
    """
    Handles user authentication, registration, and token management.
    Uses PostgreSQL database for persistent user storage.
    Implements refresh token rotation for enhanced security.
    """

    def __init__(self):
        logger.info("AuthService initialized with PostgreSQL storage")

    # ========================================
    # Password Handling
    # ========================================

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt with 12 rounds."""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bool(
                bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
            )
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    # ========================================
    # Token Hashing (for refresh tokens)
    # ========================================

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a token using SHA-256 for secure storage."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    # ========================================
    # Access Token Management
    # ========================================

    def create_access_token(self, user_id: str, email: str) -> str:
        """
        Create a short-lived JWT access token (15 minutes by default).

        Args:
            user_id: Unique user identifier
            email: User's email address

        Returns:
            JWT token string
        """
        now = datetime.now(UTC)
        expiration = now + timedelta(minutes=settings.jwt_access_expiration_minutes)

        payload = {
            "sub": user_id,
            "email": email,
            "iat": now,
            "exp": expiration,
            "type": "access",
        }

        token = jwt.encode(
            payload, settings.secret_key, algorithm=settings.jwt_algorithm
        )

        logger.debug(f"Created access token for user: {email}")
        return str(token)

    # ========================================
    # Refresh Token Management
    # ========================================

    def create_refresh_token(
        self,
        user_id: str,
        family_id: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, RefreshToken]:
        """
        Create a refresh token and store its hash in the database.

        Args:
            user_id: User's unique identifier
            family_id: Token family ID (None for new family, otherwise rotation)
            user_agent: Client user agent string (optional)
            ip_address: Client IP address (optional)

        Returns:
            Tuple of (raw_token, RefreshToken model instance)
        """
        # Generate a secure random token
        raw_token = secrets.token_urlsafe(64)
        token_hash = self._hash_token(raw_token)

        # Use existing family or create new one
        if family_id is None:
            family_id = str(uuid.uuid4())

        # Calculate expiration
        expires_at = datetime.now(UTC) + timedelta(
            days=settings.jwt_refresh_expiration_days
        )

        # Create the database record
        with get_db_session() as db:
            refresh_token = RefreshToken(
                user_id=uuid.UUID(user_id),
                token_hash=token_hash,
                family_id=uuid.UUID(family_id),
                expires_at=expires_at,
                user_agent=user_agent,
                ip_address=ip_address,
            )
            db.add(refresh_token)
            db.flush()

            logger.info(f"Created refresh token for user: {user_id}")
            return raw_token, refresh_token

    def verify_refresh_token(
        self, raw_token: str
    ) -> tuple[bool, str, RefreshToken | None]:
        """
        Verify a refresh token and check if it's valid.

        Args:
            raw_token: The raw refresh token string

        Returns:
            Tuple of (is_valid, message, RefreshToken or None)
        """
        token_hash = self._hash_token(raw_token)

        try:
            with get_db_session() as db:
                refresh_token = (
                    db.query(RefreshToken)
                    .filter(RefreshToken.token_hash == token_hash)
                    .first()
                )

                if not refresh_token:
                    return False, "Invalid refresh token", None

                # Check if token is revoked (possible theft detected)
                if refresh_token.revoked:
                    # Token was revoked - possible theft!
                    # Revoke all tokens in the family as a security measure
                    self._revoke_token_family(db, str(refresh_token.family_id))
                    logger.warning(
                        f"Revoked token used! Family {refresh_token.family_id} compromised. "
                        f"Revoking entire family."
                    )
                    return False, "Token has been revoked. Please login again.", None

                # Check if token is expired
                if datetime.now(UTC) > refresh_token.expires_at:
                    return False, "Refresh token has expired", None

                # Check if user is still active
                user = db.query(User).filter(User.id == refresh_token.user_id).first()
                if not user or not user.is_active:
                    return False, "User account is disabled", None

                return True, "Token is valid", refresh_token

        except Exception as e:
            logger.error(f"Error verifying refresh token: {e}")
            return False, "Token verification failed", None

    def rotate_refresh_token(
        self,
        old_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[bool, str, dict[str, Any] | None]:
        """
        Rotate a refresh token: verify old token, revoke it, issue new token pair.

        This implements token rotation for enhanced security.

        Args:
            old_token: The current refresh token to rotate
            user_agent: Client user agent string (optional)
            ip_address: Client IP address (optional)

        Returns:
            Tuple of (success, message, token_data or None)
        """
        # Verify the old token
        is_valid, message, old_refresh_token = self.verify_refresh_token(old_token)

        if not is_valid or old_refresh_token is None:
            return False, message, None

        try:
            with get_db_session() as db:
                # Re-fetch the token within this session
                token_to_revoke = (
                    db.query(RefreshToken)
                    .filter(RefreshToken.id == old_refresh_token.id)
                    .first()
                )

                if token_to_revoke:
                    # Revoke the old token
                    token_to_revoke.revoked = True  # type: ignore[assignment]
                    token_to_revoke.revoked_at = datetime.now(UTC)  # type: ignore[assignment]

                # Get user info for access token
                user = db.query(User).filter(User.id == token_to_revoke.user_id).first()
                if not user:
                    return False, "User not found", None

                user_id = str(user.id)
                email = str(user.email)
                family_id = str(token_to_revoke.family_id)

            # Create new token pair (outside the session to avoid nesting)
            new_refresh_token_raw, new_refresh_token_obj = self.create_refresh_token(
                user_id=user_id,
                family_id=family_id,  # Keep the same family
                user_agent=user_agent,
                ip_address=ip_address,
            )

            # Create new access token
            new_access_token = self.create_access_token(user_id, email)

            logger.info(f"Rotated refresh token for user: {email}")

            return (
                True,
                "Token rotated successfully",
                {
                    "access_token": new_access_token,
                    "refresh_token": new_refresh_token_raw,
                    "token_type": "bearer",
                    "access_token_expires_in": settings.jwt_access_expiration_minutes
                    * 60,
                    "refresh_token_expires_in": settings.jwt_refresh_expiration_days
                    * 86400,
                },
            )

        except Exception as e:
            logger.error(f"Error rotating refresh token: {e}")
            return False, "Token rotation failed", None

    def revoke_refresh_token(self, raw_token: str) -> tuple[bool, str]:
        """
        Revoke a specific refresh token (logout from single device).

        Args:
            raw_token: The refresh token to revoke

        Returns:
            Tuple of (success, message)
        """
        token_hash = self._hash_token(raw_token)

        try:
            with get_db_session() as db:
                refresh_token = (
                    db.query(RefreshToken)
                    .filter(RefreshToken.token_hash == token_hash)
                    .first()
                )

                if not refresh_token:
                    return False, "Token not found"

                if refresh_token.revoked:
                    return True, "Token already revoked"

                refresh_token.revoked = True  # type: ignore[assignment]
                refresh_token.revoked_at = datetime.now(UTC)  # type: ignore[assignment]

                logger.info(f"Revoked refresh token: {refresh_token.id}")
                return True, "Token revoked successfully"

        except Exception as e:
            logger.error(f"Error revoking refresh token: {e}")
            return False, "Failed to revoke token"

    def revoke_all_user_tokens(self, user_id: str) -> tuple[bool, str, int]:
        """
        Revoke all refresh tokens for a user (logout from all devices).

        Args:
            user_id: User's unique identifier

        Returns:
            Tuple of (success, message, count of revoked tokens)
        """
        try:
            with get_db_session() as db:
                now = datetime.now(UTC)
                result = (
                    db.query(RefreshToken)
                    .filter(
                        RefreshToken.user_id == uuid.UUID(user_id),
                        RefreshToken.revoked == False,  # noqa: E712
                    )
                    .update({"revoked": True, "revoked_at": now})
                )

                logger.info(f"Revoked {result} tokens for user: {user_id}")
                return True, f"Revoked {result} tokens", result

        except Exception as e:
            logger.error(f"Error revoking all user tokens: {e}")
            return False, "Failed to revoke tokens", 0

    def _revoke_token_family(self, db, family_id: str) -> int:
        """
        Revoke all tokens in a family (used when theft is detected).

        Args:
            db: Database session
            family_id: Token family ID

        Returns:
            Number of tokens revoked
        """
        now = datetime.now(UTC)
        result = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.family_id == uuid.UUID(family_id),
                RefreshToken.revoked == False,  # noqa: E712
            )
            .update({"revoked": True, "revoked_at": now})
        )

        logger.warning(f"Revoked {result} tokens in family: {family_id}")
        return result

    def cleanup_expired_tokens(self, days_old: int = 30) -> int:
        """
        Remove old expired/revoked tokens from the database.
        Should be run periodically as a background job.

        Args:
            days_old: Delete tokens older than this many days

        Returns:
            Number of tokens deleted
        """
        try:
            cutoff = datetime.now(UTC) - timedelta(days=days_old)

            with get_db_session() as db:
                result = (
                    db.query(RefreshToken)
                    .filter(
                        RefreshToken.created_at < cutoff,
                        (RefreshToken.revoked == True)  # noqa: E712
                        | (RefreshToken.expires_at < datetime.now(UTC)),
                    )
                    .delete()
                )

                logger.info(f"Cleaned up {result} expired/revoked tokens")
                return result

        except Exception as e:
            logger.error(f"Error cleaning up tokens: {e}")
            return 0

    # ========================================
    # User Registration
    # ========================================

    def register_user(
        self,
        email: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[bool, str, dict[str, Any] | None]:
        """
        Register a new user and return tokens.

        Args:
            email: User's email address
            password: User's password (will be hashed)
            user_agent: Client user agent string (optional)
            ip_address: Client IP address (optional)

        Returns:
            Tuple of (success, message, data with tokens and user)
        """
        email = email.lower().strip()

        if len(password) < 8:
            return False, "Password must be at least 8 characters", None

        try:
            with get_db_session() as db:
                existing = db.query(User).filter(User.email == email).first()
                if existing:
                    return False, "Email already registered", None

                user = User(email=email, password_hash=self.hash_password(password))
                db.add(user)
                db.flush()

                user_data = user.to_dict()
                user_id = str(user.id)

            # Create tokens (outside the session)
            access_token = self.create_access_token(user_id, email)
            refresh_token_raw, _ = self.create_refresh_token(
                user_id=user_id,
                user_agent=user_agent,
                ip_address=ip_address,
            )

            logger.info(f"New user registered: {email}")

            return (
                True,
                "Registration successful",
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token_raw,
                    "token_type": "bearer",
                    "access_token_expires_in": settings.jwt_access_expiration_minutes
                    * 60,
                    "refresh_token_expires_in": settings.jwt_refresh_expiration_days
                    * 86400,
                    "user": user_data,
                },
            )

        except IntegrityError:
            logger.warning(f"Email already exists: {email}")
            return False, "Email already registered", None
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False, "Registration failed", None

    # ========================================
    # User Authentication
    # ========================================

    def authenticate(
        self,
        email: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[bool, str, dict[str, Any] | None]:
        """
        Authenticate a user and return tokens.

        Args:
            email: User's email address
            password: User's password
            user_agent: Client user agent string (optional)
            ip_address: Client IP address (optional)

        Returns:
            Tuple of (success, message, data with tokens)
        """
        email = email.lower().strip()

        try:
            with get_db_session() as db:
                user = db.query(User).filter(User.email == email).first()

                if not user:
                    return False, "Invalid email or password", None

                if not user.is_active:
                    return False, "Account is disabled", None

                from typing import cast

                if not self.verify_password(password, cast(str, user.password_hash)):
                    logger.warning(f"Failed login attempt for: {email}")
                    return False, "Invalid email or password", None

                user_id = str(user.id)

            # Create tokens (outside the session)
            access_token = self.create_access_token(user_id, email)
            refresh_token_raw, _ = self.create_refresh_token(
                user_id=user_id,
                user_agent=user_agent,
                ip_address=ip_address,
            )

            logger.info(f"User authenticated: {email}")

            return (
                True,
                "Login successful",
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token_raw,
                    "token_type": "bearer",
                    "access_token_expires_in": settings.jwt_access_expiration_minutes
                    * 60,
                    "refresh_token_expires_in": settings.jwt_refresh_expiration_days
                    * 86400,
                },
            )

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False, "Login failed", None

    # ========================================
    # User Retrieval
    # ========================================

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Get user data by ID (excluding password hash)."""
        try:
            with get_db_session() as db:
                user = db.query(User).filter(User.id == user_id).first()

                if not user:
                    return None

                return user.to_dict()

        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None

    def get_user_count(self) -> int:
        """Get total number of registered users."""
        try:
            with get_db_session() as db:
                return db.query(User).count()
        except Exception:
            return 0


# Singleton instance
auth_service = AuthService()
