import os
import logging
from flask import Flask, request, jsonify, send_from_directory
from pydantic import ValidationError

# Load dotenv for local development convenience
from dotenv import load_dotenv
load_dotenv()

# CORS
from flask_cors import CORS

# Swagger UI
from flask_swagger_ui import get_swaggerui_blueprint

# Local imports
from schemas import ProfileModel
from services import KnowledgeBaseService, MockMLService, CardioChatService
from utils import save_upload_securely

# --------------------------
# CONFIG & LOGGING
# --------------------------

UPLOAD_FOLDER = 'temp_uploads'
GIGACHAT_KEY = os.getenv("GIGACHAT_AUTH_KEY")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

import json
import time

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        try:
            from flask import g
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
# FLASK APP INIT
# --------------------------

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

import uuid
from flask import g

@app.before_request
def attach_request_id():
    rid = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    g.request_id = rid
    logger.info(f"[request_id={rid}] {request.method} {request.path} started")

@app.after_request
def add_request_id_header(response):
    rid = getattr(g, "request_id", None)
    if rid:
        response.headers["X-Request-Id"] = rid
    return response

# --------------------------
# CORS configuration (safe dev + production)
# --------------------------
# Requires: pip install flask-cors python-dotenv

FLASK_ENV = os.getenv("FLASK_ENV", "production").lower()
raw_allowed = os.getenv("ALLOWED_ORIGINS", "")

def make_allowed_origins(raw: str, env: str):
    raw = (raw or "").strip()
    if env == "development":
        # default local development origins if none provided
        default_local = ["http://127.0.0.1:5000", "http://localhost:5000", "http://localhost:3000"]
        if not raw:
            return default_local
    # parse comma separated list into cleaned entries
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins

allowed_origins = make_allowed_origins(raw_allowed, FLASK_ENV)

# Safety checks:
# - In production, ALLOWED_ORIGINS must be explicitly set and must not be '*'
if FLASK_ENV != "development":
    if not allowed_origins:
        raise RuntimeError("ALLOWED_ORIGINS is not set. In production you must set ALLOWED_ORIGINS env var.")
    if any(o == "*" for o in allowed_origins):
        raise RuntimeError("Using '*' for ALLOWED_ORIGINS in production is forbidden for security reasons.")

supports_credentials = os.getenv("CORS_CREDENTIALS", "false").lower() in ("1", "true", "yes")

# Register CORS for API routes only (scoped)
CORS(app, resources={r"/api/*": {"origins": allowed_origins}}, supports_credentials=supports_credentials)

# --------------------------
# Determine GigaChat mode & INIT SERVICES
# --------------------------

MOCK_GIGACHAT_MODE = not bool(GIGACHAT_KEY)
if MOCK_GIGACHAT_MODE:
    logger.warning("⚠️ Running in MOCK GigaChat mode (no auth key).")
else:
    logger.info("🔑 GigaChat key detected — running in REAL mode.")

kb_service = KnowledgeBaseService()
ml_service = MockMLService()
chat_service = CardioChatService(GIGACHAT_KEY)

# =====================================================
#  SWAGGER UI  /docs
# =====================================================

# Serve openapi.yaml from static/ to ensure Swagger can fetch it
@app.route('/openapi.yaml')
def serve_openapi():
    return send_from_directory(app.static_folder, 'openapi.yaml', mimetype='text/yaml')

SWAGGER_URL = '/docs'
API_URL = '/openapi.yaml'  # points to the route above

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "CardioVoice API"}
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

# Debug route to list all registered routes
@app.route('/__routes__', methods=['GET'])
def show_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({"endpoint": rule.endpoint, "rule": str(rule)})
    return jsonify(routes)

# =====================================================
#  ROUTES
# =====================================================

@app.route('/api/v1/analyze', methods=['POST'])
def analyze():
    logger.info("📥 New /analyze request received")

    file_path = None

    # ----------- 1. Validate Profile Data -----------
    try:
        form = request.form.to_dict()
        profile = ProfileModel(**form)
        user_profile = profile.dict()
    except ValidationError as ve:
        return jsonify({
            "status": "error",
            "message": "Invalid profile data",
            "errors": ve.errors()
        }), 400
    except Exception as e:
        logger.error(f"Unexpected profile validation error: {e}")
        return jsonify({"status": "error", "message": "Invalid input format."}), 400

    # ----------- 2. Validate & Save Audio File -----------
    if 'audio' not in request.files:
        return jsonify({"status": "error", "message": "Audio file missing"}), 400

    try:
        file_path = save_upload_securely(
            request.files['audio'],
            app.config['UPLOAD_FOLDER']
        )
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"File saving failed: {e}")
        return jsonify({"status": "error", "message": "File upload failed"}), 500

    # ----------- 3. MAIN PIPELINE -----------
    try:
        # Step A — Mock ML or real model
        scores, query = ml_service.get_mock_risk_scores(**user_profile)

        # Step B — RAG Retrieval
        supplements = kb_service.find_relevant_supplements(query)

        # Step C — GigaChat / Mock
        explanation = chat_service.generate_explanation(
            user_profile=user_profile,
            scores=scores,
            supplements_data=supplements
        )

        # ----------- 4. Cleanup Temp File -----------
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"🧹 Deleted temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Cleanup failed for {file_path}: {e}")

        # ----------- 5. Response -----------
        return jsonify({
            "status": "success",
            "data": {
                "risk_scores": scores,
                "ai_explanation": explanation
            }
        })

    except Exception as e:
        logger.error(f"🔥 Internal pipeline error: {e}")

        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

        return jsonify({"status": "error", "message": "Internal Server Error"}), 500


# =====================================================
#  HEALTH
# =====================================================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "mode": "mock" if MOCK_GIGACHAT_MODE else "real"
    })


# =====================================================
#  MAIN
# =====================================================

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv("PORT", 5000)),
        debug=(FLASK_ENV == "development")
    )
