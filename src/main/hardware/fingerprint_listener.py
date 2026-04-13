import os
import logging
from dotenv import load_dotenv
import time
import mysql.connector
from ..database import get_db as connect_db
# from ..hardware.lcd import lcd # LCD not supported
from ..hardware.fingerprint import get_scanner
from datetime import datetime, timedelta
import threading
import queue

load_dotenv()

# --- Constants ---
PERSON_TYPE_STUDENT = 'student'
PERSON_TYPE_TEACHER = 'teacher'

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("fingerprint_listener")

class FingerprintListener(threading.Thread):
    def __init__(self, app, scan_queue):
        super().__init__()
        self.daemon = True
        self.app = app
        self.scan_queue = scan_queue
        self._first_scan_cache = {}
        self.scanner = get_scanner()

    def _refresh_cache_from_db(self):
        """Loads all student/teacher templates from DB into the scanner cache."""
        with self.app.app_context():
            conn = None
            try:
                conn = connect_db()
                cursor = conn.cursor(dictionary=True)
                
                # Fetch Users
                cursor.execute("SELECT id, fingerprint_template FROM Users WHERE fingerprint_template IS NOT NULL")
                users = cursor.fetchall()
                
                # Fetch Teachers
                cursor.execute("SELECT id, fingerprint_template FROM Teachers WHERE fingerprint_template IS NOT NULL")
                teachers = cursor.fetchall()

                # Merge into a single dict: { 'student_123': bytes, 'teacher_456': bytes }
                # We prefix IDs to distinguish types
                cache = {}
                for u in users:
                    if u['fingerprint_template']:
                        cache[f"student_{u['id']}"] = u['fingerprint_template']
                for t in teachers:
                    if t['fingerprint_template']:
                        cache[f"teacher_{t['id']}"] = t['fingerprint_template']
                
                self.scanner.load_users(cache)
                
            except Exception as e:
                logger.error(f"Failed to refresh fingerprint cache: {e}")
            finally:
                if conn: conn.close()

    def _clear_old_scans(self):
        now = datetime.now()
        keys_to_remove = []
        for key, scan_time in self._first_scan_cache.items():
            if (now - scan_time) > timedelta(hours=24) or \
               (now.hour >= 22 and scan_time.date() < now.date()):
                keys_to_remove.append(key)
        for key in keys_to_remove:
            self._first_scan_cache.pop(key)

    def log_fingerprint(self, person_type, person_id):
        with self.app.app_context():
            conn = None
            try:
                conn = connect_db()
                cursor = conn.cursor(dictionary=True)
                
                # Determine IN or OUT
                # Check the very last log for this person
                cursor.execute(
                    "SELECT log_type FROM FingerprintLogs WHERE person_type = %s AND person_id = %s ORDER BY id DESC LIMIT 1",
                    (person_type, person_id)
                )
                last_log = cursor.fetchone()
                
                new_type = 'IN'
                if last_log and last_log['log_type'] == 'IN':
                    new_type = 'OUT'
                
                # Insert
                cursor.execute(
                    "INSERT INTO FingerprintLogs (person_type, person_id, log_type) VALUES (%s, %s, %s)",
                    (person_type, person_id, new_type)
                )
                conn.commit()
                
                action = "Checked IN" if new_type == 'IN' else "Checked OUT"
                logger.info(f"[LOG] {person_type} ID {person_id} - {action}")
                
                self.scan_queue.put({
                    "person_type": person_type,
                    "person_id": person_id,
                    "type": new_type,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"DB error during logging: {e}")
            finally:
                if conn: conn.close()

    def run(self):
        logger.info("Fingerprint listener started.")

        # Initial Cache Load
        self._refresh_cache_from_db()

        last_cache_refresh = time.time()

        while True:
            # Refresh cache every 60 seconds to pick up new enrollments
            if time.time() - last_cache_refresh > 60:
                self._refresh_cache_from_db()
                last_cache_refresh = time.time()

            # Clear old scans to prevent memory leak
            self._clear_old_scans()

            try:
                # 1. Check if allowed to run
                # (Skipping DB check every loop for performance, relies on periodic refresh or restart if settings change)

                # 2. Capture
                # We use a short timeout so we can check other conditions
                template = self.scanner.capture_template(timeout=1)

                if template:
                    # 3. Match
                    match_id, score = self.scanner.match_template(template)

                    if match_id:
                        # match_id is string "student_123" or "teacher_456"
                        # Parse safely to handle edge cases
                        parts = match_id.split('_', 1)
                        if len(parts) != 2:
                            logger.warning(f"Invalid match_id format: {match_id}")
                            continue
                        
                        p_type, p_id_str = parts
                        try:
                            p_id = int(p_id_str)
                        except ValueError:
                            logger.warning(f"Invalid person ID in match_id: {match_id}")
                            continue

                        logger.info(f"Matched {p_type} {p_id} (Score: {score})")

                        # Logic for "First Scan" vs "Log" (from original app)
                        # Original app logic: If scan is new -> "Scan again". If cached -> "Logged".
                        # Simplification for ZK: Just log it, but utilize debounce.

                        cache_key = (p_type, p_id)
                        now = datetime.now()

                        # Check debounce (e.g., don't log same person within 1 minute)
                        last_scan = self._first_scan_cache.get(cache_key)
                        if last_scan and (now - last_scan) < timedelta(minutes=1):
                            logger.info("Debounced scan.")
                            continue

                        self._first_scan_cache[cache_key] = now
                        self.log_fingerprint(p_type, p_id)

                        # Visual feedback delay
                        time.sleep(1)
                    else:
                        logger.info("Finger not recognized.")
                        time.sleep(1)

            except Exception as e:
                logger.error(f"Listener loop error: {e}")
                time.sleep(1)
