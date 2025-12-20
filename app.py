"""
CardioVoice Backend API
=======================
Flask application with authentication, rate limiting, and security headers.
"""

# Load dotenv for local development convenience
from dotenv import load_dotenv

load_dotenv()

import json
import logging
import os
import uuid

from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_swagger_ui import get_swaggerui_blueprint
from pydantic import ValidationError

from config import settings
from middleware import add_security_headers, get_current_user, require_auth
from schemas import ProfileModel, UserLoginModel, UserRegisterModel
from services import (
    CardioChatService,
    KnowledgeBaseService,
    MockMLService,
    auth_service,
)
from utils import save_upload_securely

# --------------------------
# LOGGING CONFIGURATION
# --------------------------

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        try:
            log_record["request_id"] = getattr(g, "request_id", None)
        except Exception:
            log_record["request_id"] = None
        return json.dumps(log_record)


# Replace root logger handlers with JSON formatter
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.getLogger().handlers = [handler]
logging.getLogger().setLevel(logging.INFO)

# Disable Werkzeug's default access logger
logging.getLogger("werkzeug").setLevel(logging.ERROR)

# --------------------------
# FLASK APP INITIALIZATION
# --------------------------

app = Flask(__name__)

# Configuration from centralized config
app.config["UPLOAD_FOLDER"] = "temp_uploads"
app.config["SECRET_KEY"] = settings.secret_key
app.config["MAX_CONTENT_LENGTH"] = settings.max_upload_size_bytes  # Request size limit

# --------------------------
# SECURITY HEADERS
# --------------------------

add_security_headers(app)

# --------------------------
# RATE LIMITING
# --------------------------

# Disable rate limiting in test environment
if os.environ.get("FLASK_ENV") == "testing":
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        enabled=False,  # Disable in tests
    )
else:
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=[f"{settings.rate_limit_per_minute} per minute"],
        storage_uri="memory://",
        strategy="fixed-window",
    )


# Custom rate limit error handler
@app.errorhandler(429)
def ratelimit_handler(e):
    return (
        jsonify(
            {
                "status": "error",
                "message": "Rate limit exceeded. Please slow down.",
                "code": "RATE_LIMIT_EXCEEDED",
            }
        ),
        429,
    )


# --------------------------
# REQUEST ID MIDDLEWARE
# --------------------------


@app.before_request
def attach_request_id():
    """Attach a unique request ID for tracing."""
    rid = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    g.request_id = rid
    logger.info(f"[request_id={rid}] {request.method} {request.path} started")


@app.after_request
def add_request_id_header(response):
    """Add request ID to response headers."""
    rid = getattr(g, "request_id", None)
    if rid:
        response.headers["X-Request-Id"] = rid
    return response


# --------------------------
# CORS CONFIGURATION
# --------------------------

allowed_origins = settings.allowed_origins_list

# Safety checks for production
if settings.is_production:
    if not allowed_origins:
        raise RuntimeError(
            "ALLOWED_ORIGINS is not set. In production you must set ALLOWED_ORIGINS env var."
        )
    if any(o == "*" for o in allowed_origins):
        raise RuntimeError(
            "Using '*' for ALLOWED_ORIGINS in production is forbidden for security reasons."
        )

# In development, ensure Vite dev server ports are always included
if settings.is_development:
    vite_origins = ["http://localhost:5173", "http://localhost:5174"]
    for origin in vite_origins:
        if origin not in allowed_origins:
            allowed_origins.append(origin)

# Register CORS for API routes only (scoped)
CORS(
    app,
    resources={r"/api/*": {"origins": allowed_origins}},
    supports_credentials=settings.cors_credentials,
)

# --------------------------
# INITIALIZE SERVICES
# --------------------------

MOCK_GIGACHAT_MODE = not bool(settings.gigachat_auth_key)
if MOCK_GIGACHAT_MODE:
    logger.warning("⚠️ Running in MOCK GigaChat mode (no auth key).")
else:
    logger.info("🔑 GigaChat key detected — running in REAL mode.")

kb_service = KnowledgeBaseService()
ml_service = MockMLService()
chat_service = CardioChatService(settings.gigachat_auth_key)

# =====================================================
#  SWAGGER UI  /docs
# =====================================================


@app.route("/openapi.yaml")
def serve_openapi():
    """Serve OpenAPI specification."""
    return send_from_directory(app.static_folder, "openapi.yaml", mimetype="text/yaml")


SWAGGER_URL = "/docs"
API_URL = "/openapi.yaml"

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL, API_URL, config={"app_name": "CardioVoice API"}
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)


# Debug route to list all registered routes (development only)
if settings.is_development:

    @app.route("/__routes__", methods=["GET"])
    def show_routes():
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({"endpoint": rule.endpoint, "rule": str(rule)})
        return jsonify(routes)


# =====================================================
#  AUTHENTICATION ROUTES
# =====================================================


@app.route("/api/v1/auth/register", methods=["POST"])
@limiter.limit("5 per minute")  # Prevent registration spam
def register():
    """
    Register a new user.

    Returns JWT access token and refresh token on successful registration.
    """
    try:
        data = request.get_json()
        if not data:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Request body is required",
                        "code": "INVALID_REQUEST",
                    }
                ),
                400,
            )

        # Validate input
        user_data = UserRegisterModel(**data)

        # Get client info for token tracking
        user_agent = request.headers.get("User-Agent")
        ip_address = request.remote_addr

        # Register user (now returns both tokens)
        success, message, result = auth_service.register_user(
            email=user_data.email,
            password=user_data.password,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        if not success:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": message,
                        "code": "REGISTRATION_FAILED",
                    }
                ),
                400,
            )

        logger.info(f"New user registered: {user_data.email}")

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Registration successful",
                    "data": result,  # Contains access_token, refresh_token, user
                }
            ),
            201,
        )

    except ValidationError as ve:
        # Convert validation errors to serializable format
        errors_list = []
        for err in ve.errors():
            errors_list.append(
                {
                    "field": ".".join(str(loc) for loc in err.get("loc", [])),
                    "message": err.get("msg", "Validation error"),
                    "type": err.get("type", "unknown"),
                }
            )
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Invalid input data",
                    "errors": errors_list,
                    "code": "VALIDATION_ERROR",
                }
            ),
            400,
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Registration failed",
                    "code": "INTERNAL_ERROR",
                }
            ),
            500,
        )


@app.route("/api/v1/auth/login", methods=["POST"])
@limiter.limit("5 per minute")  # Brute force protection
def login():
    """
    Authenticate user and return JWT access token + refresh token.
    """
    try:
        data = request.get_json()
        if not data:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Request body is required",
                        "code": "INVALID_REQUEST",
                    }
                ),
                400,
            )

        # Validate input
        login_data = UserLoginModel(**data)

        # Get client info for token tracking
        user_agent = request.headers.get("User-Agent")
        ip_address = request.remote_addr

        # Authenticate (now returns both tokens)
        success, message, result = auth_service.authenticate(
            email=login_data.email,
            password=login_data.password,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        if not success:
            return (
                jsonify({"status": "error", "message": message, "code": "AUTH_FAILED"}),
                401,
            )

        return jsonify(
            {
                "status": "success",
                "message": "Login successful",
                "data": result,  # Contains access_token, refresh_token, etc.
            }
        )

    except ValidationError as ve:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Invalid input data",
                    "errors": ve.errors(),
                    "code": "VALIDATION_ERROR",
                }
            ),
            400,
        )
    except Exception as e:
        logger.error(f"Login error: {e}")
        return (
            jsonify(
                {"status": "error", "message": "Login failed", "code": "INTERNAL_ERROR"}
            ),
            500,
        )


@app.route("/api/v1/auth/me", methods=["GET"])
@require_auth
def get_me():
    """
    Get current authenticated user info.
    Requires valid JWT token.
    """
    user = get_current_user()
    user_data = auth_service.get_user_by_id(user["user_id"])

    if not user_data:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "User not found",
                    "code": "USER_NOT_FOUND",
                }
            ),
            404,
        )

    return jsonify({"status": "success", "data": user_data})


@app.route("/api/v1/auth/refresh", methods=["POST"])
@limiter.limit("10 per minute")  # Reasonable limit for token refresh
def refresh_token():
    """
    Refresh access token using a valid refresh token.

    Implements token rotation: old refresh token is invalidated,
    new access + refresh tokens are returned.
    """
    try:
        data = request.get_json()
        if not data or "refresh_token" not in data:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "refresh_token is required",
                        "code": "INVALID_REQUEST",
                    }
                ),
                400,
            )

        # Get client info for token tracking
        user_agent = request.headers.get("User-Agent")
        ip_address = request.remote_addr

        # Rotate the refresh token
        success, message, result = auth_service.rotate_refresh_token(
            old_token=data["refresh_token"],
            user_agent=user_agent,
            ip_address=ip_address,
        )

        if not success:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": message,
                        "code": "REFRESH_FAILED",
                    }
                ),
                401,
            )

        return jsonify(
            {
                "status": "success",
                "message": "Token refreshed successfully",
                "data": result,
            }
        )

    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Token refresh failed",
                    "code": "INTERNAL_ERROR",
                }
            ),
            500,
        )


@app.route("/api/v1/auth/logout", methods=["POST"])
def logout():
    """
    Logout from current device by revoking the refresh token.

    Revokes only the provided refresh token (single device logout).
    """
    try:
        data = request.get_json()
        if not data or "refresh_token" not in data:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "refresh_token is required",
                        "code": "INVALID_REQUEST",
                    }
                ),
                400,
            )

        success, message = auth_service.revoke_refresh_token(data["refresh_token"])

        if not success:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": message,
                        "code": "LOGOUT_FAILED",
                    }
                ),
                400,
            )

        return jsonify(
            {
                "status": "success",
                "message": "Logged out successfully",
            }
        )

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Logout failed",
                    "code": "INTERNAL_ERROR",
                }
            ),
            500,
        )


@app.route("/api/v1/auth/logout-all", methods=["POST"])
@require_auth
def logout_all():
    """
    Logout from all devices by revoking all refresh tokens.

    Requires authentication. Revokes all refresh tokens for the current user.
    """
    try:
        user = get_current_user()
        success, message, count = auth_service.revoke_all_user_tokens(user["user_id"])

        if not success:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": message,
                        "code": "LOGOUT_FAILED",
                    }
                ),
                400,
            )

        return jsonify(
            {
                "status": "success",
                "message": f"Logged out from {count} device(s)",
                "data": {"revoked_tokens": count},
            }
        )

    except Exception as e:
        logger.error(f"Logout-all error: {e}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Logout failed",
                    "code": "INTERNAL_ERROR",
                }
            ),
            500,
        )


# =====================================================
#  MAIN ANALYSIS ROUTE (PROTECTED)
# =====================================================


@app.route("/api/v1/analyze", methods=["POST"])
@require_auth  # Now requires authentication
@limiter.limit("10 per minute")  # Heavy endpoint, stricter limit
def analyze():
    """
    Analyze voice recording and user profile.

    Requires authentication via JWT token.
    Returns risk scores and AI-generated explanation.
    """
    logger.info("📥 New /analyze request received")

    # Get authenticated user
    current_user = get_current_user()
    logger.info(f"Analysis requested by user: {current_user['email']}")

    file_path = None

    # ----------- 1. Validate Profile Data -----------
    try:
        form = request.form.to_dict()
        profile = ProfileModel(**form)
        user_profile = profile.model_dump()
    except ValidationError as ve:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Invalid profile data",
                    "errors": ve.errors(),
                    "code": "VALIDATION_ERROR",
                }
            ),
            400,
        )
    except Exception as e:
        logger.error(f"Unexpected profile validation error: {e}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Invalid input format.",
                    "code": "INVALID_FORMAT",
                }
            ),
            400,
        )

    # ----------- 2. Validate & Save Audio File -----------
    if "audio" not in request.files:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Audio file missing",
                    "code": "AUDIO_MISSING",
                }
            ),
            400,
        )

    try:
        file_path = save_upload_securely(
            request.files["audio"], app.config["UPLOAD_FOLDER"]
        )
    except ValueError as e:
        return (
            jsonify(
                {"status": "error", "message": str(e), "code": "FILE_VALIDATION_ERROR"}
            ),
            400,
        )
    except Exception as e:
        logger.error(f"File saving failed: {e}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "File upload failed",
                    "code": "UPLOAD_FAILED",
                }
            ),
            500,
        )

    # ----------- 3. MAIN PIPELINE -----------
    try:
        # Step A — Mock ML or real model
        scores, query = ml_service.get_mock_risk_scores(**user_profile)

        # Step B — RAG Retrieval
        supplements = kb_service.find_relevant_supplements(query)

        # Step C — GigaChat / Mock
        explanation = chat_service.generate_explanation(
            user_profile=user_profile, scores=scores, supplements_data=supplements
        )

        # ----------- 4. Cleanup Temp File -----------
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"🧹 Deleted temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Cleanup failed for {file_path}: {e}")

        # ----------- 5. Response -----------
        return jsonify(
            {
                "status": "success",
                "data": {"risk_scores": scores, "ai_explanation": explanation},
            }
        )

    except Exception as e:
        logger.error(f"🔥 Internal pipeline error: {e}")

        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Internal Server Error",
                    "code": "INTERNAL_ERROR",
                }
            ),
            500,
        )


# =====================================================
#  HEALTH CHECK
# =====================================================


@app.route("/health", methods=["GET"])
@limiter.exempt  # Don't rate limit health checks
def health():
    """
    Health check endpoint.
    Returns service status and mode (mock/real).
    """
    return jsonify(
        {
            "status": "ok",
            "mode": "mock" if MOCK_GIGACHAT_MODE else "real",
            "version": "1.0.0",
        }
    )


# =====================================================
#  ERROR HANDLERS
# =====================================================


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large errors."""
    return (
        jsonify(
            {
                "status": "error",
                "message": f"Request too large. Maximum size is {settings.max_upload_size_mb}MB",
                "code": "REQUEST_TOO_LARGE",
            }
        ),
        413,
    )


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return (
        jsonify(
            {"status": "error", "message": "Resource not found", "code": "NOT_FOUND"}
        ),
        404,
    )


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return (
        jsonify(
            {
                "status": "error",
                "message": "Internal server error",
                "code": "INTERNAL_ERROR",
            }
        ),
        500,
    )


# =====================================================
#  MAIN
# =====================================================

if __name__ == "__main__":
    logger.info(f"🚀 Starting CardioVoice Backend in {settings.flask_env} mode")
    logger.info(f"📊 Rate limit: {settings.rate_limit_per_minute} req/min")
    logger.info(f"📁 Max upload size: {settings.max_upload_size_mb}MB")
    logger.info(f"🔐 JWT expiration: {settings.jwt_expiration_hours} hours")

    app.run(host="0.0.0.0", port=settings.port, debug=settings.is_development)
