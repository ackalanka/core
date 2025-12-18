# tests/integration/test_auth_endpoints.py
"""Integration tests for authentication API endpoints."""
import pytest


class TestRegisterEndpoint:
    """Tests for POST /api/v1/auth/register."""

    def test_register_success(self, client):
        """Test successful user registration."""
        import uuid

        unique_email = f"newuser_{uuid.uuid4().hex[:8]}@example.com"

        response = client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": "SecurePass123"},
            content_type="application/json",
        )

        assert response.status_code == 201

        data = response.get_json()
        assert data["status"] == "success"
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "SecurePass123"},
            content_type="application/json",
        )

        # Should fail validation
        assert response.status_code in [400, 422]

    def test_register_short_password(self, client):
        """Test registration with short password."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "short"},
            content_type="application/json",
        )

        # Should fail validation
        assert response.status_code in [400, 422]

    def test_register_missing_fields(self, client):
        """Test registration with missing fields."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com"},
            content_type="application/json",
        )

        assert response.status_code in [400, 422]


class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login."""

    def test_login_success(self, client):
        """Test successful login."""
        import uuid

        unique_email = f"logintest_{uuid.uuid4().hex[:8]}@example.com"
        password = "SecurePass123"

        # First register
        reg_response = client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": password},
            content_type="application/json",
        )
        assert reg_response.status_code == 201

        # Then login
        response = client.post(
            "/api/v1/auth/login",
            json={"email": unique_email, "password": password},
            content_type="application/json",
        )

        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "success"
        assert "access_token" in data["data"]

    def test_login_wrong_password(self, client):
        """Test login with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "WrongPassword123"},
            content_type="application/json",
        )

        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "SomePass123"},
            content_type="application/json",
        )

        assert response.status_code == 401


class TestMeEndpoint:
    """Tests for GET /api/v1/auth/me."""

    def test_me_with_valid_token(self, client):
        """Test /me endpoint with valid token."""
        import uuid

        unique_email = f"metest_{uuid.uuid4().hex[:8]}@example.com"
        password = "SecurePass123"

        # Register to get token
        reg_response = client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": password},
            content_type="application/json",
        )
        assert reg_response.status_code == 201

        token = reg_response.get_json()["data"]["access_token"]

        # Use token to access /me
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["email"] == unique_email

    def test_me_without_token(self, client):
        """Test /me endpoint without token."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

        data = response.get_json()
        assert data["code"] == "AUTH_REQUIRED"

    def test_me_with_invalid_token(self, client):
        """Test /me endpoint with invalid token."""
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 401
