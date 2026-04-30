"""
Test client for Fingerprint API
Tests all API endpoints with mock data
"""

import requests
import base64
import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.config import TEST_SERVER_URL, TEST_API_KEY


class FingerprintAPITestClient:
    def __init__(self, base_url=None, api_key=None):
        self.base_url = base_url or TEST_SERVER_URL
        self.api_key = api_key or TEST_API_KEY
        self.session = requests.Session()
        self.session.headers.update(
            {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        )

    def enroll_fingerprint(self, person_type, person_id, template_b64=None):
        """Enroll a fingerprint template"""
        if template_b64 is None:
            template_b64 = base64.b64encode(bytes(range(512))).decode("utf-8")

        url = f"{self.base_url}/api/fingerprint/enroll"
        data = {
            "person_type": person_type,
            "person_id": person_id,
            "template": template_b64,
        }

        response = self.session.post(url, json=data)
        return response.json()

    def verify_fingerprint(self, template_b64=None):
        """Verify a fingerprint"""
        if template_b64 is None:
            template_b64 = base64.b64encode(bytes(range(512))).decode("utf-8")

        url = f"{self.base_url}/api/fingerprint/verify"
        data = {"template": template_b64}

        response = self.session.post(url, json=data)
        return response.json()

    def log_attendance(self, person_type, person_id):
        """Log attendance"""
        url = f"{self.base_url}/api/fingerprint/log_attendance"
        data = {"person_type": person_type, "person_id": person_id}

        response = self.session.post(url, json=data)
        return response.json()

    def refresh_cache(self):
        """Refresh the fingerprint cache"""
        url = f"{self.base_url}/api/fingerprint/cache/refresh"
        response = self.session.get(url)
        return response.json()

    def health_check(self):
        """Check server health"""
        url = f"{self.base_url}/api/fingerprint/health"
        response = self.session.get(url)
        return response.json()

    def get_jwt_token(self, agent_id="test-agent"):
        """Get JWT token"""
        import jwt

        payload = {
            "agent_id": agent_id,
            "timestamp": int(time.time()),
            "nonce": "testnonce123",
        }
        token = jwt.encode(payload, self.api_key, algorithm="HS256")

        url = f"{self.base_url}/api/auth/token"
        response = self.session.post(url, json={"token": token})
        return response.json()


def test_enrollment():
    """Test fingerprint enrollment"""
    print("\n=== Testing Enrollment ===")
    client = FingerprintAPITestClient()

    for person_type in ["student", "teacher"]:
        result = client.enroll_fingerprint(person_type, 1)
        print(f"  {person_type} enrollment: {result}")

        if result.get("success"):
            print(f"    ✓ Enrolled successfully")
        else:
            print(f"    ✗ Failed: {result.get('error')}")

    return True


def test_verification():
    """Test fingerprint verification"""
    print("\n=== Testing Verification ===")
    client = FingerprintAPITestClient()

    result = client.verify_fingerprint()
    print(f"  Verify result: {result}")

    if "matched" in result:
        print(f"    ✓ Verification endpoint working")
        return True
    return False


def test_attendance_logging():
    """Test attendance logging"""
    print("\n=== Testing Attendance Logging ===")
    client = FingerprintAPITestClient()

    result = client.log_attendance("student", 1)
    print(f"  Attendance log: {result}")

    if result.get("success"):
        print(f"    ✓ Logged: {result.get('log_type')}")
        return True
    return False


def test_cache_refresh():
    """Test cache refresh"""
    print("\n=== Testing Cache Refresh ===")
    client = FingerprintAPITestClient()

    result = client.refresh_cache()
    print(f"  Cache refresh: {result}")

    if result.get("success"):
        print(f"    ✓ Loaded {result.get('templates_loaded')} templates")
        return True
    return False


def test_jwt_authentication():
    """Test JWT authentication"""
    print("\n=== Testing JWT Authentication ===")
    client = FingerprintAPITestClient()

    result = client.get_jwt_token("test-agent-001")
    print(f"  JWT token: {result}")

    if "access_token" in result:
        print(f"    ✓ Token issued")
        return True
    return False


def test_health_check():
    """Test health check endpoint"""
    print("\n=== Testing Health Check ===")
    client = FingerprintAPITestClient()

    result = client.health_check()
    print(f"  Health: {result}")

    if "status" in result:
        print(f"    ✓ Status: {result.get('status')}")
        return True
    return False


def test_security():
    """Test security (invalid API key)"""
    print("\n=== Testing Security ===")

    bad_client = FingerprintAPITestClient(api_key="wrong-key")
    result = bad_client.health_check()
    print(f"  Invalid API key: {result}")

    if result.get("error") == "Invalid API key":
        print(f"    ✓ API key validation working")
        return True
    return False


def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("Fingerprint System SNS - API Tests")
    print("=" * 50)

    tests = [
        ("Health Check", test_health_check),
        ("JWT Authentication", test_jwt_authentication),
        ("Enrollment", test_enrollment),
        ("Verification", test_verification),
        ("Attendance Logging", test_attendance_logging),
        ("Cache Refresh", test_cache_refresh),
        ("Security", test_security),
    ]

    results = []
    for name, test_fn in tests:
        try:
            result = test_fn()
            results.append((name, result))
        except Exception as e:
            print(f"  Error: {e}")
            results.append((name, False))

    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)

    passed = 0
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {name}: {status}")
        if result:
            passed += 1

    print(f"\nPassed: {passed}/{len(results)}")

    return passed == len(results)


if __name__ == "__main__":
    run_all_tests()
