# config.py
"""
Centralized configuration module for CardioVoice Backend.
Uses Pydantic Settings for validation and type safety.
"""

import os
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Flask Configuration
    flask_env: str = Field(default="development", description="Flask environment")
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT signing",
    )
    port: int = Field(default=5000, description="Server port")

    # CORS Configuration
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:5000,http://localhost:5173,http://localhost:5174",
        description="Comma-separated CORS origins",
    )
    cors_credentials: bool = Field(default=False, description="Allow CORS credentials")

    # GigaChat API
    gigachat_auth_key: str | None = Field(default=None, description="GigaChat API key")

    # Security Settings
    max_upload_size_mb: int = Field(default=10, description="Max audio file size in MB")
    rate_limit_per_minute: int = Field(default=100, description="Global rate limit")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")

    # JWT Settings - Access Token
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_access_expiration_minutes: int = Field(
        default=15, description="Access token expiration in minutes"
    )
    # JWT Settings - Refresh Token
    jwt_refresh_expiration_days: int = Field(
        default=7, description="Refresh token expiration in days"
    )
    # Legacy setting (deprecated, use jwt_access_expiration_minutes)
    jwt_expiration_hours: int = Field(
        default=24, description="Legacy JWT token expiration in hours (deprecated)"
    )

    # Database Settings
    db_host: str = Field(default="localhost", description="Database host")
    db_port: int = Field(default=5432, description="Database port")
    db_name: str = Field(default="cardiovoice", description="Database name")
    db_user: str = Field(default="cardiovoice", description="Database user")
    db_password: str = Field(
        default="cardiovoice_dev_password", description="Database password"
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Warn if using default secret key in production."""
        # We can't access other fields easily here, so we check env directly
        flask_env = os.getenv("FLASK_ENV", "development")
        if flask_env == "production" and v == "dev-secret-key-change-in-production":
            raise ValueError(
                "SECRET_KEY must be set to a secure value in production. "
                'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        return v

    @field_validator("allowed_origins")
    @classmethod
    def validate_origins(cls, v: str, info) -> str:
        """Validate CORS origins in production."""
        flask_env = os.getenv("FLASK_ENV", "development")
        if flask_env == "production":
            if not v or v.strip() == "":
                raise ValueError("ALLOWED_ORIGINS must be set in production")
            if "*" in v:
                raise ValueError(
                    "Wildcard '*' is not allowed in production ALLOWED_ORIGINS"
                )
        return v

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse allowed origins into a list."""
        if not self.allowed_origins:
            return []
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        """Get max upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.flask_env.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.flask_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()


# Convenience function for quick access
settings = get_settings()
