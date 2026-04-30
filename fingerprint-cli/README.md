# Fingerprint SNS CLI

Command-line tool for managing St. Nicholas Senior School's biometric attendance system.

## Installation

```bash
npm install -g fingerprint-sns-cli
```

## Quick Start

```bash
# 1. Setup (installs Python venv and dependencies)
fpsns setup

# 2. Create an admin account
fpsns admin --create adminUsername --password "yourPassword"

# 3. List admins
fpsns admin --list

# 4. Start the fingerprint listener
fpsns listen --mock
```

## Commands

### Setup

Initializes the Python environment with required dependencies.

```bash
fpsns setup
```

This command:
- Checks for Python installation
- Creates a virtual environment at `~/.fpsns-venv`
- Installs required Python packages

### Admin Management

```bash
# Create admin account
fpsns admin --create <username> --password <password>

# List all admins
fpsns admin --list

# Delete admin
fpsns admin --delete <username>
```

### Student Management

```bash
# List all students
fpsns student --list

# Enroll student fingerprint
fpsns student --enroll <student_id>
```

### Teacher Management

```bash
# List all teachers
fpsns teacher --list

# Enroll teacher fingerprint
fpsns teacher --enroll <teacher_id>
```

### Fingerprint Listener

```bash
# Start with real fingerprint scanner
fpsns listen

# Start in mock mode (for testing)
fpsns listen --mock

# Custom port
fpsns listen --port 3002
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | NeonDB connection |
| `FPSNS_VENV` | Custom path to Python venv | `~/.fpsns-venv` |

### Database

The CLI connects to NeonDB (PostgreSQL). Default connection:
```
postgresql://neondb_owner:npg_***@ep-***.c-3.us-west-2.aws.neon.tech/neondb?sslmode=require
```

## Hardware Support

### Supported Scanners

- ZKTeco SLK20R
- ZKTeco ZK9500
- ZKTeco ZK6500
- ZKTeco ZK8500R

### Installing ZKFinger SDK

For real hardware support:
1. Download ZKFinger SDK from ZKTeco
2. Install to your system
3. Run: `pip install pyzkfp pythonnet`

## Troubleshooting

### "Python not found"
Run `fpsns setup` to install Python automatically, or install Python 3.12+ manually.

### "Module not found" errors
Re-run setup: `fpsns setup`

### Scanner not detected
- Check USB connection
- Install ZKFinger SDK
- Try mock mode: `fpsns listen --mock`

## Development

```bash
# Clone and setup
cd fingerprint-cli
npm install

# Test locally
node bin/cli.js admin --list
```

## License

MIT