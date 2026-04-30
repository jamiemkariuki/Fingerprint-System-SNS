# Fingerprint SNS NPM Package

Node.js library for managing St. Nicholas Senior School's biometric attendance system.

## Installation

```bash
npm install @fpsns/cli
```

## Quick Start

```javascript
const { init, createAdmin, enrollFingerprint } = require('@fpsns/cli');

// Initialize database connection
await init();

// Create admin account
await createAdmin('adminUsername', 'password');

// Enroll fingerprint
await enrollFingerprint('student', userId, fingerprintTemplate);
```

## API

### Database

```javascript
const { init, query } = require('@fpsns/cli');

await init();
// Run custom queries
const result = await query('SELECT * FROM users');
```

### Admin

```javascript
const { createAdmin, listAdmins, deleteAdmin } = require('@fpsns/cli');

await createAdmin('username', 'password');
const admins = await listAdmins();
await deleteAdmin('username');
```

### Students

```javascript
const { createStudent, listStudents, enrollStudent } = require('@fpsns/cli');

await createStudent('John Doe', 'johndoe', 'Class 10A');
const students = await listStudents();
await enrollStudent(studentId);
```

### Teachers

```javascript
const { createTeacher, listTeachers, enrollTeacher } = require('@fpsns/cli');

await createTeacher('Jane Smith', 'jane@school.edu', 'Class 10A', 'password');
const teachers = await listTeachers();
await enrollTeacher(teacherId);
```

### Fingerprint Scanner

```javascript
const { startListener, stopListener, scanFingerprint } = require('@fpsns/cli');

// Start listener in background
await startListener({ port: 3001, mock: false });

// Or scan single fingerprint
const template = await scanFingerprint();
```

## Configuration

Set environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require

# Optional: Use mock scanner for testing
FP_USE_MOCK=true
```

Or create a `.env` file:

```env
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
```

## CLI Commands

This package also provides CLI commands:

```bash
# Initialize
fpsns setup

# Create admin
fpsns admin --create username --password password

# List records
fpsns student --list
fpsns teacher --list

# Start listener
fpsns listen --mock
```

## Supported Hardware

- ZKTeco SLK20R
- ZKTeco ZK9500
- ZKTeco ZK6500
- ZKTeco ZK8500R

## Requirements

- Node.js 18+
- PostgreSQL (NeonDB recommended)

## License

MIT