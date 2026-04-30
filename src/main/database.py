import os
import sqlite3
import logging

logger = logging.getLogger(__name__)

USE_MOCK = os.getenv("MOCK_DB", "").lower() in ("1", "true", "yes")
USE_SQLITE = os.getenv("USE_SQLITE", "").lower() in ("1", "true", "yes")
USE_POSTGRES = os.getenv("USE_POSTGRES", "").lower() in ("1", "true", "yes")

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import pool as psycopg2_pool

    def get_postgres_connection_string():
        return os.getenv("DATABASE_URL") or os.getenv("DB_URL") or ""

    _pg_pool = None

    def _init_postgres_pool():
        global _pg_pool
        conn_str = get_postgres_connection_string()
        if conn_str:
            try:
                _pg_pool = psycopg2_pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=int(os.getenv("DB_POOL_SIZE", "5")),
                    dsn=conn_str,
                )
                logger.info("PostgreSQL connection pool initialized")
            except Exception as e:
                logger.error("PostgreSQL pool init failed: %s", e)
                _pg_pool = None

    class PostgresConnection:
        def __init__(self):
            if _pg_pool:
                self.conn = _pg_pool.getconn()
            else:
                conn_str = get_postgres_connection_string()
                self.conn = psycopg2.connect(dsn=conn_str)
                logger.warning(
                    "Using direct PostgreSQL connection (pool not available)."
                )

        def cursor(self, dictionary=True):
            if dictionary:
                return self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            return self.conn.cursor()

        def commit(self):
            self.conn.commit()

        def close(self):
            if _pg_pool:
                _pg_pool.putconn(self.conn)
            else:
                self.conn.close()

    def get_db():
        return PostgresConnection()

    _init_postgres_pool()

elif not USE_SQLITE and not USE_POSTGRES:
    import mysql.connector
    from mysql.connector import pooling

    DB_CONFIG = {
        "host": os.getenv("DB_HOST", "localhost"),
        "user": os.getenv("DB_USER", "fp_user"),
        "password": os.getenv("DB_PASSWORD", "fp_pass"),
        "database": os.getenv("DB_NAME", "fpsnsdb"),
        "port": int(os.getenv("DB_PORT", "3306")),
    }

    db_pool = None
    if not USE_MOCK:
        try:
            db_pool = pooling.MySQLConnectionPool(
                pool_name="fp_pool",
                pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
                **DB_CONFIG,
            )
        except Exception as e:
            logger.error("DB pool init failed: %s", e)

    class MockConnection:
        """Mock database connection for testing"""

        def __init__(self):
            self._data = {
                "Users": {},
                "Teachers": {},
                "FingerprintLogs": [],
            }

        def cursor(self, dictionary=True):
            return MockCursor(self._data)

        def commit(self):
            pass

        def close(self):
            pass

    class MockCursor:
        def __init__(self, data):
            self._data = data
            self._rows = []
            self.rowcount = 0

        def execute(self, query, params=None):
            q = query.upper()
            if "SELECT" in q and "USERS" in q and "FINGERPRINT_TEMPLATE" in q:
                for uid, d in self._data["Users"].items():
                    if d.get("fingerprint_template"):
                        self._rows.append(
                            {
                                "id": uid,
                                "fingerprint_template": d["fingerprint_template"],
                            }
                        )
            elif "SELECT" in q and "TEACHERS" in q and "FINGERPRINT_TEMPLATE" in q:
                for tid, d in self._data["Teachers"].items():
                    if d.get("fingerprint_template"):
                        self._rows.append(
                            {
                                "id": tid,
                                "fingerprint_template": d["fingerprint_template"],
                            }
                        )
            elif "SELECT" in q and "FINGERPRINTLOGS" in q and "LOG_TYPE" in q:
                if params and len(params) >= 2:
                    for log in self._data["FingerprintLogs"]:
                        if (
                            log["person_type"] == params[0]
                            and log["person_id"] == params[1]
                        ):
                            self._rows.append(log)
                            break
            elif "UPDATE" in q and "USERS" in q and "FINGERPRINT_TEMPLATE" in q:
                if params and len(params) >= 2:
                    self._data["Users"][params[1]] = {"fingerprint_template": params[0]}
            elif "UPDATE" in q and "TEACHERS" in q and "FINGERPRINT_TEMPLATE" in q:
                if params and len(params) >= 2:
                    self._data["Teachers"][params[1]] = {
                        "fingerprint_template": params[0]
                    }
            elif "INSERT" in q and "FINGERPRINTLOGS" in q:
                if params and len(params) >= 4:
                    self._data["FingerprintLogs"].append(
                        {
                            "id": len(self._data["FingerprintLogs"]) + 1,
                            "person_type": params[0],
                            "person_id": params[1],
                            "log_type": params[2],
                            "timestamp": params[3],
                        }
                    )
            elif "SELECT" in q and "ADMINS" in q:
                pass
            return self

        def fetchall(self):
            return self._rows

        def fetchone(self):
            return self._rows[0] if self._rows else None

    def get_db():
        if USE_MOCK:
            return MockConnection()

        try:
            if db_pool:
                return db_pool.get_connection()
            else:
                conn = mysql.connector.connect(**DB_CONFIG)
                logger.warning("Using direct DB connection (pool not available).")
                return conn
        except Exception as e:
            logger.exception("Failed to get database connection: %s", e)
            raise


if USE_SQLITE:
    DB_PATH = os.getenv(
        "DB_PATH",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fpsns.db"
        ),
    )

    def init_sqlite():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS Admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(64) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(128) NOT NULL,
                username VARCHAR(64) NOT NULL UNIQUE,
                password_hash VARCHAR(255),
                class VARCHAR(64) NOT NULL,
                fingerprint_id INTEGER UNIQUE,
                fingerprint_template BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS Teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(128) NOT NULL,
                username VARCHAR(64) NOT NULL UNIQUE,
                email VARCHAR(128) NOT NULL UNIQUE,
                class VARCHAR(64) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                fingerprint_id INTEGER UNIQUE,
                fingerprint_template BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS FingerprintLogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_type TEXT NOT NULL CHECK(person_type IN ('student', 'teacher')),
                person_id INTEGER NOT NULL,
                log_type TEXT NOT NULL CHECK(log_type IN ('IN', 'OUT')),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS Parents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(128) NOT NULL,
                email VARCHAR(128) NOT NULL UNIQUE,
                phone VARCHAR(50),
                username VARCHAR(64) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()
        logger.info(f"SQLite database initialized at {DB_PATH}")

    init_sqlite()

    class SQLiteConnection:
        def __init__(self):
            self.conn = sqlite3.connect(DB_PATH)
            self.conn.row_factory = sqlite3.Row

        def cursor(self, dictionary=True):
            return self.conn.cursor()

        def commit(self):
            self.conn.commit()

        def close(self):
            self.conn.close()

    def get_db():
        return SQLiteConnection()
