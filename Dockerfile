# ============================================
# CardioVoice Backend - Production Dockerfile
# ============================================
# Multi-stage build for optimized image size

# --------------------------
# Stage 1: Builder
# --------------------------
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# --------------------------
# Stage 2: Production
# --------------------------
FROM python:3.12-slim as production

# Labels
LABEL maintainer="CardioVoice Team"
LABEL version="1.0.0"
LABEL description="CardioVoice Backend API"

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PATH="/home/appuser/.local/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Create temp_uploads directory and make entrypoint executable
RUN mkdir -p temp_uploads && chown appuser:appuser temp_uploads \
    && chmod +x scripts/entrypoint.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check - extended start-period for DB initialization
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Use entrypoint for DB initialization, CMD for the actual server
ENTRYPOINT ["scripts/entrypoint.sh"]
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "app:app"]
