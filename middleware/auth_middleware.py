# middleware/auth_middleware.py
"""
JWT Authentication middleware for protected routes.
"""

import logging
from functools import wraps
from typing import Any

import jwt
from flask import g, jsonify, request

from config import settings

logger = logging.getLogger(__name__)


def get_token_from_header() -> str | None:
    """
    Extract JWT token from Authorization header.
    Expected format: 'Bearer <token>'
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]


def decode_token(token: str) -> dict[str, Any] | None:
    """
    Decode and validate JWT token.
    Returns payload if valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        from typing import cast

        return cast(dict[str, Any], payload)
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None


def get_current_user() -> dict[str, Any] | None:
    """
    Get current authenticated user from Flask g object.
    Returns None if not authenticated.
    """
    return getattr(g, "current_user", None)


def require_auth(f):
    """
    Decorator to protect routes requiring authentication.

    Usage:
        @app.route('/protected')
        @require_auth
        def protected_route():
            user = get_current_user()
            return jsonify(user)
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()

        if not token:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Authentication required. Please provide a valid token.",
                        "code": "AUTH_REQUIRED",
                    }
                ),
                401,
            )

        payload = decode_token(token)

        if not payload:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Invalid or expired token. Please login again.",
                        "code": "INVALID_TOKEN",
                    }
                ),
                401,
            )

        # Store user info in Flask's g object for access in route handlers
        g.current_user = {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "exp": payload.get("exp"),
        }

        logger.info(f"Authenticated request from user: {payload.get('email')}")

        return f(*args, **kwargs)

    return decorated


def optional_auth(f):
    """
    Decorator for routes where authentication is optional.
    If token is provided and valid, user info is stored in g.current_user.
    If no token or invalid token, request proceeds without user context.

    Usage:
        @app.route('/public-or-private')
        @optional_auth
        def mixed_route():
            user = get_current_user()
            if user:
                return jsonify({"message": f"Hello {user['email']}"})
            return jsonify({"message": "Hello anonymous"})
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()

        if token:
            payload = decode_token(token)
            if payload:
                g.current_user = {
                    "user_id": payload.get("sub"),
                    "email": payload.get("email"),
                    "exp": payload.get("exp"),
                }

        return f(*args, **kwargs)

    return decorated
