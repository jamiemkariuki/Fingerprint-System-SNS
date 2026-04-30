#!/bin/bash

set -e

echo "=== Fingerprint System SNS - Web Server Deployment ==="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

SERVER_USER="${SERVER_USER:-fingerprint}"
SERVER_HOST="${SERVER_HOST:-fingerprint-web-server}"
SERVER_PORT="${SERVER_PORT:-22}"
SERVER_PATH="${SERVER_PATH:-/opt/fingerprint-sns}"

echo "Configuration:"
echo "  Server: $SERVER_USER@$SERVER_HOST"
echo "  Path: $SERVER_PATH"
echo ""

read -p "Continue deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 1
fi

echo "Building production package..."
cd "$PROJECT_DIR"
mkdir -p dist

tar --exclude='node_modules' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='venv' \
    --exclude='.env' \
    -czf dist/fingerprint-sns.tar.gz .

echo "Copying to server..."
ssh -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" "mkdir -p $SERVER_PATH"

scp -P "$SERVER_PORT" dist/fingerprint-sns.tar.gz "$SERVER_USER@$SERVER_HOST:$SERVER_PATH/"

echo "Installing on server..."
ssh -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" << 'EOF'
    cd /opt/fingerprint-sns
    tar -xzf fingerprint-sns.tar.gz
    
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
    
    echo "Installing Node.js agent dependencies..."
    cd fingerprint-agent
    npm install --production
    
    echo "Setting up environment..."
    if [ ! -f .env ]; then
        cp .env.example .env || true
    fi
    
    echo "Testing server startup..."
    python run_production.py &
    sleep 5
    
    if pgrep -f "run_production.py" > /dev/null; then
        echo "Server started successfully!"
        pkill -f "run_production.py"
    else
        echo "Warning: Server may not have started properly"
    fi
    
    echo "Setting up systemd service..."
    sudo cp deploy/fingerprint-sns.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable fingerprint-sns
    sudo systemctl start fingerprint-sns
    
    echo "Deployment complete!"
    echo "Server URL: http://$(hostname):8080/sns"
EOF

echo ""
echo "=== Deployment Complete ==="
echo "Run 'sudo systemctl status fingerprint-sns' to check status"
echo "Run 'sudo journalctl -u fingerprint-sns -f' to view logs"
