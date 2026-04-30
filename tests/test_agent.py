"""
Test Local Agent CLI
Tests the fingerprint-agent CLI in mock mode
"""

import subprocess
import sys
import os
import requests
import base64

SERVER_URL = "http://127.0.0.1:8080/sns"
API_KEY = "test-api-key-12345"


def check_server():
    """Check if server is running"""
    try:
        response = requests.get(
            f"{SERVER_URL}/api/fingerprint/health", headers={"X-API-Key": API_KEY}
        )
        return response.status_code == 200
    except:
        return False


def test_agent_health():
    """Test agent health command"""
    print("\n=== Testing Agent Health ===")

    result = subprocess.run(
        [
            "node",
            "fingerprint-agent/bin/fingerprint-agent.js",
            "health",
            "-s",
            SERVER_URL,
        ],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    return result.returncode == 0


def test_agent_enroll():
    """Test agent enroll command"""
    print("\n=== Testing Agent Enroll ===")

    template = base64.b64encode(bytes(range(512))).decode("utf-8")

    result = subprocess.run(
        [
            "node",
            "fingerprint-agent/bin/fingerprint-agent.js",
            "enroll",
            "-s",
            SERVER_URL,
            "-t",
            "student",
            "-i",
            "999",
            "-n",
            "Test Student",
        ],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    return result.returncode == 0


def test_agent_verify():
    """Test agent verify command"""
    print("\n=== Testing Agent Verify ===")

    result = subprocess.run(
        [
            "node",
            "fingerprint-agent/bin/fingerprint-agent.js",
            "verify",
            "-s",
            SERVER_URL,
        ],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    return result.returncode == 0


def test_agent_sync():
    """Test agent sync command"""
    print("\n=== Testing Agent Sync ===")

    result = subprocess.run(
        [
            "node",
            "fingerprint-agent/bin/fingerprint-agent.js",
            "sync",
            "-s",
            SERVER_URL,
        ],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    return result.returncode == 0


def main():
    print("=== Testing Fingerprint Agent CLI ===")

    if not check_server():
        print("Error: Server not running")
        print("Start server with: python run_production.py")
        return 1

    tests = [
        ("Health", test_agent_health),
        ("Sync", test_agent_sync),
        ("Enroll", test_agent_enroll),
        ("Verify", test_agent_verify),
    ]

    results = []
    for name, test_fn in tests:
        try:
            result = test_fn()
            results.append((name, result))
        except Exception as e:
            print(f"Error: {e}")
            results.append((name, False))

    print("\n=== Results ===")
    passed = 0
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {name}: {status}")
        if result:
            passed += 1

    print(f"\nPassed: {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
