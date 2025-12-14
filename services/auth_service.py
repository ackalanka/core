# services/auth_service.py
"""
Authentication service for user management and JWT token handling.
Uses in-memory storage (temporary until Phase 2 Database Migration).
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple

import bcrypt
import jwt

from config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """
    Handles user authentication, registration, and token management.
    
    Note: Uses in-memory storage. This will be replaced with database
    storage in Phase 2. Users are lost on server restart.
    """
    
    def __init__(self):
        # In-memory user storage: {user_id: user_data}
        # Will be replaced with database in Phase 2
        self._users: Dict[str, Dict[str, Any]] = {}
        # Email to user_id index for quick lookups
        self._email_index: Dict[str, str] = {}
        
        logger.info("AuthService initialized with in-memory storage")
    
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
            return bcrypt.checkpw(
                password.encode("utf-8"),
                hashed.encode("utf-8")
            )
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
        now = datetime.now(timezone.utc)
        expiration = now + timedelta(hours=settings.jwt_expiration_hours)
        
        payload = {
            "sub": user_id,
            "email": email,
            "iat": now,
            "exp": expiration,
            "type": "access"
        }
        
        token = jwt.encode(
            payload,
            settings.secret_key,
            algorithm=settings.jwt_algorithm
        )
        
        logger.info(f"Created access token for user: {email}")
        return token
    
    def register_user(self, email: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Register a new user.
        
        Args:
            email: User's email address
            password: User's password (will be hashed)
            
        Returns:
            Tuple of (success, message, user_data)
        """
        # Normalize email
        email = email.lower().strip()
        
        # Check if email already exists
        if email in self._email_index:
            return False, "Email already registered", None
        
        # Validate password strength
        if len(password) < 8:
            return False, "Password must be at least 8 characters", None
        
        # Create user
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        user_data = {
            "id": user_id,
            "email": email,
            "password_hash": self.hash_password(password),
            "created_at": now,
            "updated_at": now
        }
        
        # Store user
        self._users[user_id] = user_data
        self._email_index[email] = user_id
        
        logger.info(f"New user registered: {email}")
        
        # Return user data without password hash
        safe_user = {
            "id": user_id,
            "email": email,
            "created_at": now
        }
        
        return True, "Registration successful", safe_user
    
    def authenticate(self, email: str, password: str) -> Tuple[bool, str, Optional[str]]:
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
        
        # Find user by email
        user_id = self._email_index.get(email)
        if not user_id:
            # Use same message to prevent email enumeration
            return False, "Invalid email or password", None
        
        user = self._users.get(user_id)
        if not user:
            return False, "Invalid email or password", None
        
        # Verify password
        if not self.verify_password(password, user["password_hash"]):
            logger.warning(f"Failed login attempt for: {email}")
            return False, "Invalid email or password", None
        
        # Generate token
        token = self.create_access_token(user_id, email)
        
        logger.info(f"User authenticated: {email}")
        return True, "Login successful", token
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user data by ID (excluding password hash).
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            User data dict or None if not found
        """
        user = self._users.get(user_id)
        if not user:
            return None
        
        # Return without password hash
        return {
            "id": user["id"],
            "email": user["email"],
            "created_at": user["created_at"]
        }
    
    def get_user_count(self) -> int:
        """Get total number of registered users."""
        return len(self._users)


# Singleton instance
auth_service = AuthService()
