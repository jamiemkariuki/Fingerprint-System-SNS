"""
Mock Database for Testing
Provides in-memory storage when MySQL is not available
"""

import threading
import time


class MockDB:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.tables = {
            "Users": {},
            "Teachers": {},
            "FingerprintLogs": [],
            "Admins": {},
        }
        self._id_counters = {
            "Users": 1,
            "Teachers": 1,
            "FingerprintLogs": 1,
        }

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def execute(self, query, params=None):
        query = query.upper()

        if "SELECT" in query and "USERS" in query:
            return self._select_users(params)
        if "SELECT" in query and "TEACHERS" in query:
            return self._select_teachers(params)
        if "SELECT" in query and "FINGERPRINTLOGS" in query:
            return self._select_logs(params)
        if "UPDATE" in query and "USERS" in query:
            return self._update_user(params)
        if "UPDATE" in query and "TEACHERS" in query:
            return self._update_teacher(params)
        if "INSERT" in query and "FINGERPRINTLOGS" in query:
            return self._insert_log(params)

        return MockCursor()

    def _select_users(self, params):
        cursor = MockCursor()
        for uid, data in self.tables["Users"].items():
            if data.get("fingerprint_template"):
                cursor.rows.append(
                    {"id": uid, "fingerprint_template": data["fingerprint_template"]}
                )
        return cursor

    def _select_teachers(self, params):
        cursor = MockCursor()
        for tid, data in self.tables["Teachers"].items():
            if data.get("fingerprint_template"):
                cursor.rows.append(
                    {"id": tid, "fingerprint_template": data["fingerprint_template"]}
                )
        return cursor

    def _select_logs(self, params):
        cursor = MockCursor()
        if params and len(params) >= 2:
            person_type, person_id = params[0], params[1]
            for log in self.tables["FingerprintLogs"]:
                if log["person_type"] == person_type and log["person_id"] == person_id:
                    cursor.rows.append(log)
                    break
        return cursor

    def _update_user(self, params):
        if params and len(params) >= 2:
            template, uid = params
            if uid not in self.tables["Users"]:
                self.tables["Users"][uid] = {}
            self.tables["Users"][uid]["fingerprint_template"] = template
        return MockCursor()

    def _update_teacher(self, params):
        if params and len(params) >= 2:
            template, tid = params
            if tid not in self.tables["Teachers"]:
                self.tables["Teachers"][tid] = {}
            self.tables["Teachers"][tid]["fingerprint_template"] = template
        return MockCursor()

    def _insert_log(self, params):
        if params and len(params) >= 4:
            log = {
                "id": self._id_counters["FingerprintLogs"],
                "person_type": params[0],
                "person_id": params[1],
                "log_type": params[2],
                "timestamp": params[3],
            }
            self.tables["FingerprintLogs"].append(log)
            self._id_counters["FingerprintLogs"] += 1
        return MockCursor()

    def commit(self):
        pass

    def close(self):
        pass


class MockCursor:
    def __init__(self):
        self.rowcount = 0
        self.rows = []

    def execute(self, query, params=None):
        return self

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class MockConnection:
    def __init__(self):
        self.db = MockDB.get_instance()

    def cursor(self, dictionary=False):
        return MockCursor()

    def commit(self):
        pass

    def close(self):
        pass


def patch_database():
    """Patch the database module to use mock when MOCK_DB=1"""
    import os

    if os.getenv("MOCK_DB", "").lower() in ("1", "true", "yes"):
        try:
            from src.main import database
        except ImportError:
            try:
                from main import database
            except ImportError:
                return False

        original_get_db = database.get_db

        def mock_get_db():
            return MockConnection()

        database.get_db = mock_get_db
        import logging

        logger = logging.getLogger(__name__)
        logger.info("Using MOCK database (MOCK_DB=1)")
        return True
    return False
