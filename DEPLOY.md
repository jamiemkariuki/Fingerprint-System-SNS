# Fingerprint System SNS - Deployment Guide

## Prerequisites

### 1. Web Server Setup (SSH: fingerprint-web-server)

You need:
- A server with SSH access (e.g., Ubuntu/Debian VPS)
- MySQL database installed
- Python 3.8+
- Node.js 16+

### 2. SSH Configuration

Add to `~/.ssh/config`:
```bash
Host fingerprint-web-server
    HostName <your-server-ip>
    User fingerprint
    Port 22
    IdentityFile ~/.ssh/fingerprint_id_rsa
```

## Deployment Commands

### Deploy Web Server

```bash
# Set environment variables
export SERVER_USER=fingerprint
export SERVER_HOST=fingerprint-web-server
export SERVER_PATH=/opt/fingerprint-sns

# Run deployment script
bash deploy/deploy-web-server.sh
```

### Manual Web Server Setup

```bash
# SSH into server
ssh fingerprint-web-server

# Create directory
sudo mkdir -p /opt/fingerprint-sns
sudo chown fingerprint:fingerprint /opt/fingerprint-sns

# Upload files
scp dist/fingerprint-sns.tar.gz fingerprint-web-server:/opt/fingerprint-sns/

# SSH and extract
ssh fingerprint-web-server "cd /opt/fingerprint-sns && tar -xzf fingerprint-sns.tar.gz"

# Install dependencies
ssh fingerprint-web-server "cd /opt/fingerprint-sns && pip install -r requirements.txt"

# Configure environment
ssh fingerprint-web-server "cp /opt/fingerprint-sns/.env.example /opt/fingerprint-sns/.env"
# Edit .env with production values

# Start server
ssh fingerprint-web-server "cd /opt/fingerprint-sns && python run_production.py"
```

---

## Local Machine Agent Deployment

### Prerequisites

- Node.js 16+
- Python 3.8+ (for ZK9500 scanner)
- npm

### Installation

```bash
# Navigate to agent directory
cd fingerprint-agent

# Install dependencies
npm install

# Install globally
npm install -g .
```

### Configuration

```bash
# Configure the agent
fpsns-agent config

# Enter:
# - Server URL: http://your-server:8080/sns
# - API Key: (from server .env)
```

### Usage

```bash
# Enroll a new fingerprint
fpsns-agent enroll --type student --id 123 --name "John Doe"

# Verify a fingerprint
fpsns-agent verify

# Continuous listening mode (attendance)
fpsns-agent listen

# Sync cache from server
fpsns-agent sync

# Check server health
fpsns-agent health
```

---

## Environment Variables

### Server (.env)

```bash
SECRET_KEY=<generate-strong-key>
FLASK_HOST=0.0.0.0
FLASK_PORT=80
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=<strong-password>
DB_NAME=fpsnsdb
FINGERPRINT_API_KEY=<generate-strong-key>
JWT_SECRET_KEY=<generate-strong-key>
```

### Local Agent (~/.fpsns-agent/.env)

```bash
FP_SERVER_URL=http://server:8080/sns
FP_API_KEY=<from-server>
```

---

## Testing

```bash
# Server tests (mock mode)
MOCK_SCANNER=1 MOCK_DB=1 python tests/run_mock_tests.py
```