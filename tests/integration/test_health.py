# tests/integration/test_health.py
"""Integration tests for health endpoint."""
import pytest


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check_returns_ok(self, client):
        """Test health endpoint returns OK status."""
        response = client.get("/health")

        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "ok"

    def test_health_check_has_version(self, client):
        """Test health endpoint includes version."""
        response = client.get("/health")

        data = response.get_json()
        assert "version" in data
        assert data["version"] == "1.0.0"

    def test_health_check_has_mode(self, client):
        """Test health endpoint includes mode."""
        response = client.get("/health")

        data = response.get_json()
        assert "mode" in data
        assert data["mode"] in ["real", "mock"]

    def test_health_check_no_rate_limit(self, client):
        """Test health endpoint is exempt from rate limiting."""
        # Make many requests - should all succeed
        for _ in range(10):
            response = client.get("/health")
            assert response.status_code == 200
