# services/auth_service.py
"""
Authentication service for user management and JWT token handling.
Uses PostgreSQL database for persistent storage.
"""
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from sqlalchemy.exc import IntegrityError

from config import settings
from database.connection import get_db_session
from models import User

logger = logging.getLogger(__name__)


class AuthService:
    """
    Handles user authentication, registration, and token management.
    Uses PostgreSQL database for persistent user storage.
    """

    def __init__(self):
        logger.info("AuthService initialized with PostgreSQL storage")

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: Plain text password to verify
            hashed: Stored password hash

        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def create_access_token(self, user_id: str, email: str) -> str:
        """
        Create a JWT access token for a user.

        Args:
            user_id: Unique user identifier
            email: User's email address

        Returns:
            JWT token string
        """
        now = datetime.now(UTC)
        expiration = now + timedelta(hours=settings.jwt_expiration_hours)

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

        logger.info(f"Created access token for user: {email}")
        return token

    def register_user(
        self, email: str, password: str
    ) -> tuple[bool, str, dict[str, Any] | None]:
        """
        Register a new user in the database.

        Args:
            email: User's email address
            password: User's password (will be hashed)

        Returns:
            Tuple of (success, message, user_data)
        """
        # Normalize email
        email = email.lower().strip()

        # Validate password strength
        if len(password) < 8:
            return False, "Password must be at least 8 characters", None

        try:
            with get_db_session() as db:
                # Check if email already exists
                existing = db.query(User).filter(User.email == email).first()
                if existing:
                    return False, "Email already registered", None

                # Create new user
                user = User(email=email, password_hash=self.hash_password(password))
                db.add(user)
                db.flush()  # Get the ID before commit

                user_data = user.to_dict()
                logger.info(f"New user registered: {email}")

                return True, "Registration successful", user_data

        except IntegrityError:
            logger.warning(f"Email already exists: {email}")
            return False, "Email already registered", None
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False, "Registration failed", None

    def authenticate(self, email: str, password: str) -> tuple[bool, str, str | None]:
        """
        Authenticate a user and return an access token.

        Args:
            email: User's email address
            password: User's password

        Returns:
            Tuple of (success, message, token)
        """
        # Normalize email
        email = email.lower().strip()

        try:
            with get_db_session() as db:
                # Find user by email
                user = db.query(User).filter(User.email == email).first()

                if not user:
                    # Use same message to prevent email enumeration
                    return False, "Invalid email or password", None

                if not user.is_active:
                    return False, "Account is disabled", None

                # Verify password
                if not self.verify_password(password, user.password_hash):
                    logger.warning(f"Failed login attempt for: {email}")
                    return False, "Invalid email or password", None

                # Generate token
                token = self.create_access_token(str(user.id), email)

                logger.info(f"User authenticated: {email}")
                return True, "Login successful", token

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False, "Login failed", None

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        """
        Get user data by ID (excluding password hash).

        Args:
            user_id: User's unique identifier

        Returns:
            User data dict or None if not found
        """
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
