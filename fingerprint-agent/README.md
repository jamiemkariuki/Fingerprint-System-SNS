# Fingerprint System SNS - Local Agent

Cross-platform CLI for fingerprint enrollment and verification.

## Installation

```bash
npm install -g @fpsns/agent
```

## Configuration

```bash
fpsns-agent config
```

Enter your server URL and API key when prompted.

## Usage

### Enroll a new fingerprint

```bash
fpsns-agent enroll --type student --id 123 --name "John Doe"
```

### Verify a fingerprint

```bash
fpsns-agent verify
```

### Continuous listening mode (for attendance)

```bash
fpsns-agent listen
```

### Sync cache from server

```bash
fpsns-agent sync
```

### Check server health

```bash
fpsns-agent health
```

## Options

- `--server, -s`: Server URL (default: from config or http://localhost:8080)
- `--type, -t`: Person type (student|teacher) for enrollment
- `--id, -i`: Person ID for enrollment
- `--name, -n`: Person name for enrollment
- `--mode, -m`: Mode for listen command (attendance|verify)

## Commands

- `enroll` - Enroll a new fingerprint
- `verify` - Verify a single fingerprint
- `listen` - Continuous listening mode
- `sync` - Manually sync cache from server
- `config` - Configure agent settings
- `health` - Check server health

## Requirements

- Node.js 16+
- Python 3.8+ (for ZK9500 scanner driver)
- ZK9500 fingerprint scanner (optional, for local scanning)

## License

ISC
