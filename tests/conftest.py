# tests/conftest.py
"""
Pytest fixtures for CardioVoice Backend tests.
"""
import os
import sys


import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment before importing app
# Set test environment before importing app
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key-12345678")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_NAME", "cardiovoice")  # Default to main if not set


@pytest.fixture(scope="session")
def app():
    """Create Flask test application."""
    from app import app as flask_app

    flask_app.config.update(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "RATELIMIT_ENABLED": False,  # Disable rate limiting for tests
        }
    )

    yield flask_app


@pytest.fixture(scope="function")
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
    """Create Flask CLI test runner."""
    return app.test_cli_runner()


@pytest.fixture
def sample_profile():
    """Sample user profile data."""
    return {
        "age": 45,
        "gender": "male",
        "smoking_status": "non-smoker",
        "activity_level": "moderate",
    }


@pytest.fixture
def sample_user_credentials():
    """Sample user credentials for auth tests."""
    return {"email": "test@example.com", "password": "SecurePass123"}


@pytest.fixture
def auth_headers(client, sample_user_credentials):
    """
    Get authentication headers for protected endpoint tests.
    Registers a user and returns JWT token in headers.
    """
    # Try to register (may already exist)
    client.post(
        "/api/v1/auth/register",
        json=sample_user_credentials,
        content_type="application/json",
    )

    # Login to get token
    response = client.post(
        "/api/v1/auth/login",
        json=sample_user_credentials,
        content_type="application/json",
    )

    if response.status_code == 200:
        data = response.get_json()
        token = data.get("data", {}).get("access_token")
        if token:
            return {"Authorization": f"Bearer {token}"}

    # Fallback for tests that don't need real auth
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def sample_audio_bytes():
    """Sample WAV file bytes for upload tests."""
    # Minimal valid WAV header
    return bytes(
        [
            0x52,
            0x49,
            0x46,
            0x46,  # "RIFF"
            0x24,
            0x00,
            0x00,
            0x00,  # File size
            0x57,
            0x41,
            0x56,
            0x45,  # "WAVE"
            0x66,
            0x6D,
            0x74,
            0x20,  # "fmt "
            0x10,
            0x00,
            0x00,
            0x00,  # Chunk size
            0x01,
            0x00,  # Audio format (PCM)
            0x01,
            0x00,  # Channels
            0x44,
            0xAC,
            0x00,
            0x00,  # Sample rate
            0x88,
            0x58,
            0x01,
            0x00,  # Byte rate
            0x02,
            0x00,  # Block align
            0x10,
            0x00,  # Bits per sample
            0x64,
            0x61,
            0x74,
            0x61,  # "data"
            0x00,
            0x00,
            0x00,
            0x00,  # Data size
        ]
    )
