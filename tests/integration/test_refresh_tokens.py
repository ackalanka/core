# tests/integration/test_refresh_tokens.py
"""Integration tests for refresh token functionality."""

import uuid


class TestRefreshTokenFlow:
    """Tests for the complete refresh token flow."""

    def test_register_returns_both_tokens(self, client):
        """Test that registration returns both access and refresh tokens."""
        unique_email = f"refresh_test_{uuid.uuid4().hex[:8]}@example.com"

        response = client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": "SecurePass123"},
            content_type="application/json",
        )

        assert response.status_code == 201

        data = response.get_json()
        assert data["status"] == "success"
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
        assert data["data"]["access_token_expires_in"] == 900  # 15 minutes
        assert data["data"]["refresh_token_expires_in"] == 604800  # 7 days

    def test_login_returns_both_tokens(self, client):
        """Test that login returns both access and refresh tokens."""
        unique_email = f"login_refresh_{uuid.uuid4().hex[:8]}@example.com"
        password = "SecurePass123"

        # Register first
        client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": password},
            content_type="application/json",
        )

        # Login
        response = client.post(
            "/api/v1/auth/login",
            json={"email": unique_email, "password": password},
            content_type="application/json",
        )

        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "success"
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

    def test_refresh_with_valid_token(self, client):
        """Test refreshing tokens with a valid refresh token."""
        unique_email = f"refresh_valid_{uuid.uuid4().hex[:8]}@example.com"

        # Register to get tokens
        reg_response = client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": "SecurePass123"},
            content_type="application/json",
        )
        assert reg_response.status_code == 201

        refresh_token = reg_response.get_json()["data"]["refresh_token"]

        # Refresh the token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
            content_type="application/json",
        )

        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "success"
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        # New tokens should be different from old ones
        assert data["data"]["refresh_token"] != refresh_token

    def test_refresh_rotates_token(self, client):
        """Test that refreshing invalidates the old refresh token."""
        unique_email = f"rotate_test_{uuid.uuid4().hex[:8]}@example.com"

        # Register to get tokens
        reg_response = client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": "SecurePass123"},
            content_type="application/json",
        )
        old_refresh_token = reg_response.get_json()["data"]["refresh_token"]

        # Refresh once
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token},
            content_type="application/json",
        )
        assert refresh_response.status_code == 200

        # Try to use the old token again - should fail
        retry_response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token},
            content_type="application/json",
        )

        assert retry_response.status_code == 401
        assert retry_response.get_json()["code"] == "REFRESH_FAILED"

    def test_refresh_with_invalid_token(self, client):
        """Test refresh with an invalid token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token_here"},
            content_type="application/json",
        )

        assert response.status_code == 401
        assert response.get_json()["status"] == "error"

    def test_refresh_without_token(self, client):
        """Test refresh without providing a token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={},
            content_type="application/json",
        )

        assert response.status_code == 400
        assert response.get_json()["code"] == "INVALID_REQUEST"


class TestLogoutEndpoint:
    """Tests for POST /api/v1/auth/logout."""

    def test_logout_revokes_token(self, client):
        """Test that logout revokes the refresh token."""
        unique_email = f"logout_test_{uuid.uuid4().hex[:8]}@example.com"

        # Register to get tokens
        reg_response = client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": "SecurePass123"},
            content_type="application/json",
        )
        refresh_token = reg_response.get_json()["data"]["refresh_token"]

        # Logout
        logout_response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            content_type="application/json",
        )

        assert logout_response.status_code == 200
        assert logout_response.get_json()["status"] == "success"

        # Try to use the revoked token - should fail
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
            content_type="application/json",
        )

        assert refresh_response.status_code == 401

    def test_logout_without_token(self, client):
        """Test logout without providing a token."""
        response = client.post(
            "/api/v1/auth/logout",
            json={},
            content_type="application/json",
        )

        assert response.status_code == 400


class TestLogoutAllEndpoint:
    """Tests for POST /api/v1/auth/logout-all."""

    def test_logout_all_requires_auth(self, client):
        """Test that logout-all requires authentication."""
        response = client.post("/api/v1/auth/logout-all")

        assert response.status_code == 401

    def test_logout_all_revokes_all_tokens(self, client):
        """Test that logout-all revokes all user tokens."""
        unique_email = f"logout_all_{uuid.uuid4().hex[:8]}@example.com"
        password = "SecurePass123"

        # Register to get first token pair
        reg_response = client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": password},
            content_type="application/json",
        )
        first_access_token = reg_response.get_json()["data"]["access_token"]
        first_refresh_token = reg_response.get_json()["data"]["refresh_token"]

        # Login again to simulate a second device
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": unique_email, "password": password},
            content_type="application/json",
        )
        second_refresh_token = login_response.get_json()["data"]["refresh_token"]

        # Logout all using the first access token
        logout_all_response = client.post(
            "/api/v1/auth/logout-all",
            headers={"Authorization": f"Bearer {first_access_token}"},
        )

        assert logout_all_response.status_code == 200
        data = logout_all_response.get_json()
        assert data["status"] == "success"
        assert data["data"]["revoked_tokens"] >= 2

        # Both refresh tokens should now be revoked
        for token in [first_refresh_token, second_refresh_token]:
            refresh_response = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": token},
                content_type="application/json",
            )
            assert refresh_response.status_code == 401
