# middleware/security_headers.py
"""
Security headers middleware for Flask application.
Adds protective HTTP headers to all responses.
"""
from flask import Flask


def add_security_headers(app: Flask) -> None:
    """
    Register security headers middleware with Flask app.

    Headers added:
    - X-Content-Type-Options: Prevents MIME-type sniffing
    - X-Frame-Options: Prevents clickjacking
    - X-XSS-Protection: Legacy XSS protection (for older browsers)
    - Strict-Transport-Security: Forces HTTPS (only in production)
    - Content-Security-Policy: Controls resource loading
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Controls browser features
    """

    @app.after_request
    def set_security_headers(response):
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS Protection (legacy, but still useful for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Restrict browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        # Content Security Policy - adjust based on your frontend needs
        # This is a restrictive default; modify if you need to load external resources
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "  # Allow Swagger UI
            "style-src 'self' 'unsafe-inline'; "  # Allow Swagger UI styles
            "img-src 'self' data:; "
            "font-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # HSTS - only add in production with HTTPS
        # Uncomment when deploying with HTTPS:
        # if app.config.get('ENV') == 'production':
        #     response.headers["Strict-Transport-Security"] = (
        #         "max-age=31536000; includeSubDomains; preload"
        #     )

        return response
