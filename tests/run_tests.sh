#!/bin/bash
#
# Test Runner for Fingerprint System SNS
# Runs tests locally with mock scanner
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Fingerprint System SNS - Test Runner ==="
echo ""

# Check if server is running
if ! curl -s http://127.0.0.1:8080/sns/api/fingerprint/health -H "X-API-Key: test-api-key-12345" > /dev/null 2>&1; then
    echo "Starting local server with mock scanner..."
    cd "$PROJECT_DIR"
    
    # Load test environment
    export FLASK_HOST=127.0.0.1
    export FLASK_PORT=8080
    export FLASK_DEBUG=false
    export SECRET_KEY=test-secret-key
    export FINGERPRINT_API_KEY=test-api-key-12345
    export JWT_SECRET_KEY=test-jwt-secret
    export MOCK_SCANNER=1
    
    # Start server in background
    python run_production.py &
    SERVER_PID=$!
    
    echo "Server started (PID: $SERVER_PID)"
    
    # Wait for server to start
    echo "Waiting for server..."
    for i in {1..30}; do
        if curl -s http://127.0.0.1:8080/sns/api/fingerprint/health -H "X-API-Key: test-api-key-12345" > /dev/null 2>&1; then
            echo "Server ready!"
            break
        fi
        sleep 1
    done
else
    echo "Server already running"
    SERVER_PID=""
fi

# Run tests
echo ""
echo "Running API tests..."
cd "$PROJECT_DIR"
python -m tests.test_api

echo ""
echo "Running E2E tests..."
python -m tests.test_e2e

# Cleanup
if [ -n "$SERVER_PID" ]; then
    echo ""
    echo "Stopping test server..."
    kill $SERVER_PID 2>/dev/null || true
fi

echo ""
echo "=== Tests Complete ==="