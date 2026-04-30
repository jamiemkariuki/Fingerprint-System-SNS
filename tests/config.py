"""
Test Configuration for Fingerprint System SNS
Uses mock fingerprint scanner for testing without hardware
"""

import os
import sys

os.environ["FLASK_DEBUG"] = "false"
os.environ["LOG_LEVEL"] = "DEBUG"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_CONFIG = {
    "SECRET_KEY": "test-secret-key-do-not-use-in-production",
    "SECRET_KEY": "test-secret-key",
    "DB_HOST": "localhost",
    "DB_PORT": 3306,
    "DB_USER": "root",
    "DB_PASSWORD": "",
    "DB_NAME": "fpsnsdb",
    "DB_POOL_SIZE": 2,
    "SESSION_COOKIE_SECURE": False,
    "SESSION_COOKIE_SAMESITE": "Lax",
    "LOG_LEVEL": "DEBUG",
    "FINGERPRINT_API_KEY": "test-api-key-12345",
    "JWT_SECRET_KEY": "test-jwt-secret-12345",
}

TEST_SERVER_URL = "http://localhost:8080/sns"
TEST_API_KEY = "test-api-key-12345"
