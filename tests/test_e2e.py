"""
End-to-End Tests for Fingerprint System
Simulates full enrollment and verification flows
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_api import FingerprintAPITestClient
from tests.config import TEST_SERVER_URL, TEST_API_KEY


def test_e2e_enrollment_flow():
    """
    Test complete enrollment flow:
    1. Health check
    2. Enroll student
    3. Enroll teacher
    4. Refresh cache
    5. Verify student
    6. Log attendance
    """
    print("\n" + "=" * 50)
    print("E2E Test: Enrollment Flow")
    print("=" * 50)

    client = FingerprintAPITestClient()

    print("\n1. Health Check...")
    health = client.health_check()
    if health.get("status") != "healthy":
        print(f"   ✗ Server not healthy: {health}")
        return False
    print(f"   ✓ Server healthy")

    print("\n2. Enroll Student...")
    student_result = client.enroll_fingerprint("student", 100)
    if not student_result.get("success"):
        print(f"   ✗ Failed: {student_result}")
        return False
    print(f"   ✓ Student enrolled")

    print("\n3. Enroll Teacher...")
    teacher_result = client.enroll_fingerprint("teacher", 50)
    if not teacher_result.get("success"):
        print(f"   ✗ Failed: {teacher_result}")
        return False
    print(f"   ✓ Teacher enrolled")

    print("\n4. Refresh Cache...")
    cache_result = client.refresh_cache()
    if not cache_result.get("success"):
        print(f"   ✗ Failed: {cache_result}")
        return False
    print(f"   ✓ Cache refreshed ({cache_result.get('templates_loaded')} templates)")

    print("\n5. Verify Student...")
    verify_result = client.verify_fingerprint()
    if "matched" not in verify_result:
        print(f"   ✗ Failed: {verify_result}")
        return False
    print(f"   ✓ Verification complete (matched: {verify_result.get('matched')})")

    print("\n6. Log Attendance...")
    log_result = client.log_attendance("student", 100)
    if not log_result.get("success"):
        print(f"   ✗ Failed: {log_result}")
        return False
    print(f"   ✓ Attendance logged: {log_result.get('log_type')}")

    print("\n" + "=" * 50)
    print("E2E Enrollment Flow: PASSED")
    print("=" * 50)
    return True


def test_e2e_attendance_flow():
    """
    Test attendance logging flow:
    1. First scan = IN
    2. Second scan = OUT
    3. Third scan = IN
    """
    print("\n" + "=" * 50)
    print("E2E Test: Attendance Flow")
    print("=" * 50)

    client = FingerprintAPITestClient()
    person_id = 200
    person_type = "student"

    for i in range(3):
        print(f"\nScan {i + 1}...")
        log_result = client.log_attendance(person_type, person_id)

        if not log_result.get("success"):
            print(f"   ✗ Failed: {log_result}")
            return False

        expected_type = "IN" if i % 2 == 0 else "OUT"
        actual_type = log_result.get("log_type")

        if actual_type != expected_type:
            print(f"   ✗ Expected {expected_type}, got {actual_type}")
            return False

        print(f"   ✓ Logged: {actual_type}")

    print("\n" + "=" * 50)
    print("E2E Attendance Flow: PASSED")
    print("=" * 50)
    return True


def test_e2e_cache_sync():
    """
    Test cache synchronization:
    1. Add templates to server
    2. Trigger cache refresh
    3. Verify templates loaded
    """
    print("\n" + "=" * 50)
    print("E2E Test: Cache Synchronization")
    print("=" * 50)

    client = FingerprintAPITestClient()

    print("\n1. Enroll multiple users...")
    for i in range(5):
        result = client.enroll_fingerprint("student", 300 + i)
        if not result.get("success"):
            print(f"   ✗ Failed to enroll student {300 + i}")
            return False
    print(f"   ✓ Enrolled 5 students")

    print("\n2. Refresh cache...")
    cache_result = client.refresh_cache()
    if not cache_result.get("success"):
        print(f"   ✗ Failed: {cache_result}")
        return False

    templates_count = cache_result.get("templates_loaded", 0)
    print(f"   ✓ {templates_count} templates in cache")

    if templates_count < 5:
        print(f"   ✗ Expected at least 5 templates")
        return False

    print("\n3. Verify health shows cache status...")
    health = client.health_check()
    if health.get("templates_in_cache", 0) != templates_count:
        print(f"   ✗ Cache mismatch")
        return False

    print(f"   ✓ Health check shows correct cache")

    print("\n" + "=" * 50)
    print("E2E Cache Sync: PASSED")
    print("=" * 50)
    return True


def test_security_validation():
    """
    Test security features:
    1. Reject invalid API key
    2. Reject invalid JWT
    3. Accept valid credentials
    """
    print("\n" + "=" * 50)
    print("E2E Test: Security Validation")
    print("=" * 50)

    from tests.config import TEST_API_KEY

    print("\n1. Test invalid API key...")
    import requests

    bad_headers = {"X-API-Key": "invalid-key", "Content-Type": "application/json"}
    response = requests.get(
        f"{TEST_SERVER_URL}/api/fingerprint/health", headers=bad_headers
    )

    if response.status_code != 401:
        print(f"   ✗ Expected 401, got {response.status_code}")
        return False
    print(f"   ✓ Rejected invalid API key")

    print("\n2. Test missing API key...")
    response = requests.get(f"{TEST_SERVER_URL}/api/fingerprint/health")

    if response.status_code != 401:
        print(f"   ✗ Expected 401, got {response.status_code}")
        return False
    print(f"   ✓ Rejected missing API key")

    print("\n3. Test valid API key...")
    client = FingerprintAPITestClient(api_key=TEST_API_KEY)
    health = client.health_check()

    if health.get("status") != "healthy":
        print(f"   ✗ Failed: {health}")
        return False
    print(f"   ✓ Accepted valid API key")

    print("\n" + "=" * 50)
    print("Security Validation: PASSED")
    print("=" * 50)
    return True


def run_all_e2e_tests():
    """Run all E2E tests"""
    print("=" * 50)
    print("Fingerprint System SNS - E2E Tests")
    print("=" * 50)

    tests = [
        ("Enrollment Flow", test_e2e_enrollment_flow),
        ("Attendance Flow", test_e2e_attendance_flow),
        ("Cache Sync", test_e2e_cache_sync),
        ("Security", test_security_validation),
    ]

    results = []
    for name, test_fn in tests:
        try:
            result = test_fn()
            results.append((name, result))
        except Exception as e:
            print(f"\n   Error: {e}")
            results.append((name, False))

    print("\n" + "=" * 50)
    print("E2E Test Results")
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
    run_all_e2e_tests()
