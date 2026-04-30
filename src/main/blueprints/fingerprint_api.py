"""
Fingerprint API Blueprint
Handles fingerprint operations from local agent (enrollment, verification, cache sync)
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import logging
import os

from ..database import get_db
from ..hardware.fingerprint import get_scanner
import jwt

logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "change-me-in-production")

# Create blueprint with CSRF exempt
fingerprint_api_bp = Blueprint("fingerprint_api", __name__)

# API Key for local agent authentication
# Should be set in .env as FINGERPRINT_API_KEY
API_KEY = os.getenv("FINGERPRINT_API_KEY", "change-me-in-production")


def require_api_key(f):
    """Decorator to validate API key from local agent"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != API_KEY:
            logger.warning(f"Invalid API key attempt from {request.remote_addr}")
            return jsonify({"error": "Invalid API key"}), 401
        return f(*args, **kwargs)

    return decorated_function


# Exempt all routes in this blueprint from CSRF
from flask_wtf.csrf import CSRFProtect


@fingerprint_api_bp.before_request
def exempt_csrf():
    """Skip CSRF validation for API endpoints"""
    pass


@fingerprint_api_bp.route("/api/auth/token", methods=["POST"])
def get_jwt_token():
    """
    Authenticate agent and issue JWT token.

    Request JSON:
    {
        "token": "signed_jwt_token"
    }
    """
    try:
        data = request.get_json()
        if not data or "token" not in data:
            return jsonify({"error": "Missing token"}), 400

        try:
            payload = jwt.decode(data["token"], API_KEY, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        agent_id = payload.get("agent_id")
        if not agent_id:
            return jsonify({"error": "Invalid token payload"}), 401

        access_token = jwt.encode(
            {
                "agent_id": agent_id,
                "type": "access",
                "exp": datetime.utcnow() + timedelta(hours=1),
                "iat": datetime.utcnow(),
            },
            JWT_SECRET,
            algorithm="HS256",
        )

        return jsonify({"access_token": access_token, "expires_in": 3600000})

    except Exception as e:
        logger.exception(f"Error issuing JWT: {e}")
        return jsonify({"error": "Authentication failed"}), 500


@fingerprint_api_bp.route("/api/fingerprint/enroll", methods=["POST"])
@require_api_key
def enroll_fingerprint():
    """
    Enroll a new fingerprint template.
    Receives template bytes from local agent and saves to database.

    Request JSON:
    {
        "person_type": "student" | "teacher",
        "person_id": 123,
        "template": "base64_encoded_template_bytes"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400

        person_type = data.get("person_type")
        person_id = data.get("person_id")
        template_b64 = data.get("template")

        if not all([person_type, person_id, template_b64]):
            return jsonify(
                {"error": "Missing required fields: person_type, person_id, template"}
            ), 400

        if person_type not in ["student", "teacher"]:
            return jsonify(
                {"error": 'Invalid person_type. Must be "student" or "teacher"'}
            ), 400

        import base64

        template_bytes = base64.b64decode(template_b64)

        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor()

            table = "Users" if person_type == "student" else "Teachers"
            cursor.execute(
                f"UPDATE {table} SET fingerprint_template = %s WHERE id = %s",
                (template_bytes, person_id),
            )
            conn.commit()

            if cursor.rowcount == 0:
                return jsonify(
                    {"error": f"{person_type} with ID {person_id} not found"}
                ), 404

            logger.info(f"Enrolled fingerprint for {person_type} ID {person_id}")

            # Trigger cache refresh
            try:
                scanner = get_scanner()
                # Reload cache in background
                from threading import Thread

                Thread(target=_refresh_cache_async, daemon=True).start()
            except Exception as e:
                logger.warning(f"Cache refresh failed: {e}")

            return jsonify(
                {
                    "success": True,
                    "message": f"Fingerprint enrolled for {person_type} ID {person_id}",
                }
            )

        finally:
            if conn:
                conn.close()

    except Exception as e:
        logger.exception(f"Error enrolling fingerprint: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@fingerprint_api_bp.route("/api/fingerprint/verify", methods=["POST"])
@require_api_key
def verify_fingerprint():
    """
    Verify a scanned fingerprint template against the database.

    Request JSON:
    {
        "template": "base64_encoded_template_bytes"
    }

    Response JSON:
    {
        "matched": true,
        "person_type": "student",
        "person_id": 123,
        "score": 95
    }
    """
    try:
        data = request.get_json()
        if not data or "template" not in data:
            return jsonify({"error": "Missing template"}), 400

        import base64

        template_bytes = base64.b64decode(data["template"])

        scanner = get_scanner()
        match_id, score = scanner.match_template(template_bytes)

        if match_id:
            # Parse match_id (format: "type_id")
            parts = match_id.split("_", 1)
            if len(parts) == 2:
                p_type, p_id_str = parts
                try:
                    p_id = int(p_id_str)
                    return jsonify(
                        {
                            "matched": True,
                            "person_type": p_type,
                            "person_id": p_id,
                            "score": score,
                        }
                    )
                except ValueError:
                    pass

        return jsonify({"matched": False, "message": "Fingerprint not recognized"})

    except Exception as e:
        logger.exception(f"Error verifying fingerprint: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@fingerprint_api_bp.route("/api/fingerprint/log_attendance", methods=["POST"])
@require_api_key
def log_attendance():
    """
    Log attendance for a matched person.

    Request JSON:
    {
        "person_type": "student",
        "person_id": 123
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400

        person_type = data.get("person_type")
        person_id = data.get("person_id")

        if not all([person_type, person_id]):
            return jsonify({"error": "Missing person_type or person_id"}), 400

        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)

            # Determine IN or OUT
            cursor.execute(
                "SELECT log_type FROM FingerprintLogs WHERE person_type = %s AND person_id = %s ORDER BY id DESC LIMIT 1",
                (person_type, person_id),
            )
            last_log = cursor.fetchone()

            new_type = "IN"
            if last_log and last_log["log_type"] == "IN":
                new_type = "OUT"

            # Insert log
            cursor.execute(
                "INSERT INTO FingerprintLogs (person_type, person_id, log_type, timestamp) VALUES (%s, %s, %s, %s)",
                (person_type, person_id, new_type, datetime.now()),
            )
            conn.commit()

            logger.info(f"Logged {new_type} for {person_type} ID {person_id}")

            return jsonify(
                {
                    "success": True,
                    "log_type": new_type,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        finally:
            if conn:
                conn.close()

    except Exception as e:
        logger.exception(f"Error logging attendance: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@fingerprint_api_bp.route("/api/fingerprint/cache/refresh", methods=["GET"])
@require_api_key
def refresh_cache():
    """
    Trigger cache refresh on the server.
    Returns count of loaded templates.
    """
    try:
        scanner = get_scanner()

        # Load cache from database
        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT id, fingerprint_template FROM Users WHERE fingerprint_template IS NOT NULL"
            )
            users = cursor.fetchall()

            cursor.execute(
                "SELECT id, fingerprint_template FROM Teachers WHERE fingerprint_template IS NOT NULL"
            )
            teachers = cursor.fetchall()

            cache = {}
            for u in users:
                if u["fingerprint_template"]:
                    cache[f"student_{u['id']}"] = u["fingerprint_template"]
            for t in teachers:
                if t["fingerprint_template"]:
                    cache[f"teacher_{t['id']}"] = t["fingerprint_template"]

            scanner.load_users(cache)

            return jsonify({"success": True, "templates_loaded": len(cache)})

        finally:
            if conn:
                conn.close()

    except Exception as e:
        logger.exception(f"Error refreshing cache: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@fingerprint_api_bp.route("/api/fingerprint/health", methods=["GET"])
@require_api_key
def health_check():
    """Health check endpoint for local agent"""
    try:
        scanner = get_scanner()

        # Test DB connection
        conn = get_db()
        conn.close()

        return jsonify(
            {
                "status": "healthy",
                "scanner_connected": scanner.is_connected,
                "templates_in_cache": len(scanner.users_cache),
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


def _refresh_cache_async():
    """Async cache refresh (runs in background thread)"""
    import time

    time.sleep(2)  # Wait for DB commit to complete
    try:
        from src.main.hardware.fingerprint_listener import FingerprintListener

        # This will trigger a cache reload in the listener
        logger.info("Background cache refresh triggered")
    except Exception as e:
        logger.error(f"Background cache refresh failed: {e}")
