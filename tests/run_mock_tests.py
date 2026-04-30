#!/usr/bin/env python
"""
Standalone Test Runner - No Database Required
Tests API endpoints using mock responses
"""

import sys
import os
import base64
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["MOCK_DB"] = "1"
os.environ["MOCK_SCANNER"] = "1"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["FINGERPRINT_API_KEY"] = "test-api-key-12345"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-12345"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_USER"] = "root"
os.environ["DB_PASSWORD"] = ""
os.environ["DB_NAME"] = "fpsnsdb"

# Patch database BEFORE importing app
import tests.mock_db

tests.mock_db.patch_database()


def main():
    print("=" * 50)
    print("Fingerprint System SNS - Tests (Mock Mode)")
    print("=" * 50)

    db = tests.mock_db.MockDB.get_instance()
    print("\n[OK] Mock database initialized")
    print("[OK] Mock scanner enabled")

    from src.main import create_app

    app = create_app()
    print("\n[OK] Flask app created")

    app.testing = True

    with app.test_client() as client:
        api_key = "test-api-key-12345"
        headers = {"X-API-Key": api_key}

        print("\n--- Health Check ---")
        response = client.get("/sns/api/fingerprint/health", headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json}")

        print("\n--- JWT Token ---")
        import jwt

        token = jwt.encode(
            {"agent_id": "test", "timestamp": 1234567890}, api_key, algorithm="HS256"
        )
        response = client.post(
            "/sns/api/auth/token",
            json={"token": token},
            headers={"Content-Type": "application/json"},
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json}")

        print("\n--- Enroll ---")
        template = base64.b64encode(
            bytes([random.randint(0, 255) for _ in range(512)])
        ).decode("utf-8")
        response = client.post(
            "/sns/api/fingerprint/enroll",
            json={"person_type": "student", "person_id": 1, "template": template},
            headers=headers,
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json}")

        print("\n--- Verify ---")
        response = client.post(
            "/sns/api/fingerprint/verify", json={"template": template}, headers=headers
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json}")

        print("\n--- Log Attendance ---")
        response = client.post(
            "/sns/api/fingerprint/log_attendance",
            json={"person_type": "student", "person_id": 1},
            headers=headers,
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json}")

        print("\n--- Cache Refresh ---")
        response = client.get("/sns/api/fingerprint/cache/refresh", headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json}")

        print("\n--- Security (Invalid API Key) ---")
        response = client.get(
            "/sns/api/fingerprint/health", headers={"X-API-Key": "wrong-key"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json}")

    print("\n" + "=" * 50)
    print("All tests completed!")
    print("=" * 50)


if __name__ == "__main__":
    main()
