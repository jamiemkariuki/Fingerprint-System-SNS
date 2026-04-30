#!/bin/bash
# Non-interactive deployment script

set -e

SERVER_USER="${SERVER_USER:-fingerprint}"
SERVER_HOST="${SERVER_HOST:-fingerprint-web-server}"
SERVER_PATH="${SERVER_PATH:-/opt/fingerprint-sns}"

echo "=== Deploying to $SERVER_HOST ==="

cd "$(dirname "$0")/.."

echo "Creating distribution package..."
mkdir -p dist
tar --exclude='node_modules' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='venv' \
    --exclude='.env' \
    --exclude='tests' \
    -czf dist/fingerprint-sns.tar.gz .

echo "Uploading to server..."
ssh "$SERVER_USER@$SERVER_HOST" "mkdir -p $SERVER_PATH"
scp dist/fingerprint-sns.tar.gz "$SERVER_USER@$SERVER_HOST:$SERVER_PATH/"

echo "Installing on server..."
ssh "$SERVER_USER@$SERVER_HOST" << 'EOF'
    cd /opt/fingerprint-sns
    tar -xzf fingerprint-sns.tar.gz
    pip install -r requirements.txt
    cd fingerprint-agent && npm install
    cp .env.example .env
    echo "Server deployed successfully"
EOF

echo "Done!"
echo "SSH to server: ssh $SERVER_USER@$SERVER_HOST"