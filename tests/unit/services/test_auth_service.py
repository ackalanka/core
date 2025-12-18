# tests/unit/services/test_auth_service.py
"""Unit tests for authentication service."""
import pytest


class TestAuthServicePasswordHashing:
    """Tests for password hashing functionality."""

    def test_hash_password(self):
        """Test password hashing."""
        from services.auth_service import AuthService

        service = AuthService()
        password = "SecurePass123"

        hashed = service.hash_password(password)

        assert hashed != password
        assert len(hashed) > 20
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Test correct password verification."""
        from services.auth_service import AuthService

        service = AuthService()
        password = "SecurePass123"
        hashed = service.hash_password(password)

        assert service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test incorrect password verification."""
        from services.auth_service import AuthService

        service = AuthService()
        password = "SecurePass123"
        wrong_password = "WrongPass456"
        hashed = service.hash_password(password)

        assert service.verify_password(wrong_password, hashed) is False


class TestAuthServiceTokens:
    """Tests for JWT token functionality."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        from services.auth_service import AuthService

        service = AuthService()
        user_id = "test-user-id"
        email = "test@example.com"

        token = service.create_access_token(user_id, email)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50
        assert "." in token  # JWT format

    def test_token_contains_claims(self):
        """Test JWT token contains correct claims."""
        import jwt

        from config import settings
        from services.auth_service import AuthService

        service = AuthService()
        user_id = "test-user-id"
        email = "test@example.com"

        token = service.create_access_token(user_id, email)

        # Decode and verify claims
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )

        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload


class TestAuthServicePasswordValidation:
    """Tests for password strength validation."""

    def test_password_too_short(self):
        """Test password minimum length validation."""
        from services.auth_service import AuthService

        service = AuthService()

        # Attempt to register with short password
        success, message, _ = service.register_user("test@example.com", "short")

        assert success is False
        assert "8 characters" in message
