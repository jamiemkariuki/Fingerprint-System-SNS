from datetime import datetime
from ..database import get_db
import logging
from ..config import Config

logger = logging.getLogger(__name__)


def get_setting(key):
    """Fetches a setting value from the database."""
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT value FROM Settings WHERE key = %s", (key,))
        result = cursor.fetchone()
        return result["value"] if result else None
    except Exception as e:
        logger.exception("Database error in get_setting: %s", e)
        return None
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def update_setting(key, value):
    """Updates a setting value in the database."""
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor()
        if Config.USE_POSTGRES:
            cursor.execute(
                "INSERT INTO Settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                (key, value),
            )
        else:
            cursor.execute(
                "INSERT INTO Settings (key, value) VALUES (%s, %s) ON DUPLICATE KEY UPDATE value = %s",
                (key, value, value),
            )
        db.commit()
        return True
    except Exception as e:
        logger.exception("Database error in update_setting: %s", e)
        if db:
            db.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


def _get_student_attendance_status(cursor, student_id, today):
    cursor.execute(
        """
        SELECT log_type FROM FingerprintLogs
        WHERE person_type = 'student'
        AND person_id = %s
        AND CAST(timestamp AS DATE) = %s
        AND CAST(timestamp AS TIME) BETWEEN '05:00:00' AND '22:00:00'
        ORDER BY timestamp DESC
        LIMIT 1
    """,
        (student_id, today),
    )
    log = cursor.fetchone()

    if log:
        return "Checked In" if log["log_type"] == "IN" else "Checked Out"
    return "Checked Out"
