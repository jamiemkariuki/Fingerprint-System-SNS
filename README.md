# St. Nicholas Senior School - Biometric Attendance System

A comprehensive biometric attendance management system for schools, featuring a Flask web application deployed on Vercel and a Node.js CLI tool for system management.

## Overview

This system enables St. Nicholas Senior School to manage student attendance using ZKTeco USB fingerprint scanners. It provides both a web-based dashboard for administrators, teachers, and parents, as well as a command-line interface for system administration.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Application                          │
│                      (Flask/Vercel)                        │
│  https://fingerprint-system-sns.vercel.app                 │
├─────────────────────────────────────────────────────────────┤
│                    PostgreSQL (NeonDB)                     │
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
│  Admin CLI   │  │  Student    │  │  Hardware   │
│  (Node.js)  │  │  Portal     │  │  Listener   │
└─────────────┘  └─────────────┘  └─────────────┘
```

## Features

### Web Application

- **Role-Based Dashboards**
  - Admin Dashboard: Manage teachers, students, subjects, parents, timetables, exam results
  - Teacher Dashboard: Class management, attendance clearance, student records
  - Student Dashboard: View attendance, timetable, exam results
  - Parent Dashboard: Monitor children's attendance

- **Attendance Management**
  - Real-time fingerprint-based attendance logging
  - Manual attendance entry
  - Audit approval workflow for students

- **Academic Management**
  - Subject management
  - Timetable scheduling
  - Exam types and results publishing
  - Student-parent linking

- **Mobile Responsive**
  - Touch-friendly interface
  - Collapsible hamburger menus on mobile
  - Responsive tables and forms

### CLI Tool (`fingerprint-sns-cli`)

A command-line tool for system administration:

```bash
# Install
npm install -g fingerprint-sns-cli

# Setup (installs Python environment)
fpsns setup

# Admin management
fpsns admin --create <username> --password <password>
fpsns admin --list
fpsns admin --delete <username>

# Student management
fpsns student --list
fpsns student --enroll <student_id>

# Teacher management  
fpsns teacher --list
fpsns teacher --enroll <teacher_id>

# Fingerprint listener
fpsns listen              # Real scanner mode
fpsns listen --mock       # Mock mode for testing
fpsns listen --port 3002  # Custom port
```

## Installation

### Web Application

```bash
# Clone the repository
git clone https://github.com/your-repo/Fingerprint-System-SNS.git
cd Fingerprint-System-SNS

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with your database URL and secrets

# Run locally
npm run dev
```

Deploy to Vercel with zero configuration.

### CLI Tool

```bash
# Install globally
npm install -g fingerprint-sns-cli

# Run setup to install Python dependencies
fpsns setup
```

## Supported Hardware

| Model | Interface | Notes |
|-------|------------|-------|
| ZKTeco SLK20R | USB | Most common |
| ZKTeco ZK9500 | USB | Budget option |
| ZKTeco ZK6500 | USB | Mid-range |
| ZKTeco ZK8500R | USB | High-end |

For real scanner support, install the ZKFinger SDK from ZKTeco.

## Database Schema

### Core Tables

- **users** - Student records
- **teachers** - Teacher accounts
- **parents** - Parent accounts  
- **admins** - Administrator accounts
- **subjects** - Academic subjects
- **timetable** - Class schedules
- **ExamTypes** - Exam categories
- **ExamResults** - Student exam scores
- **PublishedExams** - Published results visibility
- **FingerprintLogs** - Attendance records
- **AuditRequests** - Student audit requests

### Relationships

- Students belong to classes
- Teachers assigned to subjects and classes
- Parents linked to students
- Attendance logged via fingerprint scans

## Project Structure

```
Fingerprint-System-SNS/
├── src/
│   └── main/
│       ├── blueprints/       # Flask route handlers
│       │   ├── admin.py
│       │   ├── main.py
│       │   ├── student.py
│       │   ├── teacher.py
│       │   └── parent.py
│       ├── config.py        # Configuration
│       ├── database.py      # Database connection
│       └── __init__.py      # App initialization
├── templates/                # HTML templates
│   ├── base.html           # Base template
│   ├── admin_dashboard.html
│   ├── teacher_dashboard.html
│   ├── student_dashboard.html
│   ├── parent_dashboard.html
│   └── login.html
├── static/
│   ├── style.css          # Main stylesheet
│   ├── logo.jpg          # School logo
│   └── ...               # Other static assets
├── fingerprint-cli/       # CLI package
│   ├── bin/cli.js         # CLI entry point
│   ├── lib/               # Command modules
│   └── python/            # Python listener
├── fingerprint-npm/       # NPM library
├── package.json
├── vercel.json
└── requirements.txt       # Python dependencies
```

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sns/login` | User login |
| POST | `/sns/<role>/logout` | User logout |

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sns/admin/dashboard` | Admin dashboard |
| POST | `/sns/admin/create_teacher` | Create teacher |
| POST | `/sns/admin/create_student` | Create student |
| POST | `/sns/admin/create_subject` | Create subject |

### Teachers

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sns/teacher/dashboard` | Teacher dashboard |
| POST | `/sns/teacher/audit_student` | Clear student audit |

### Students

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sns/student/dashboard` | Student dashboard |
| GET | `/sns/student/attendance` | View attendance |

### Parents

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sns/parent/dashboard` | Parent dashboard |
| GET | `/sns/parent/children` | View linked children |

## Configuration

### Environment Variables

```env
# Database (PostgreSQL/NeonDB)
DATABASE_URL=postgresql://user:password@host.db?sslmode=require

# Flask
FLASK_SECRET_KEY=your-secret-key
FLASK_DEBUG=true
FLASK_PORT=5000
```

### CLI Configuration

The CLI uses NeonDB by default. Set custom database:
```bash
export DATABASE_URL="postgresql://..."
fpsns admin --list
```

## Troubleshooting

### CLI

**"Python not found"**
```bash
fpsns setup
```

**"Scanner not detected"**
- Check USB connection
- Install ZKFinger SDK
- Use mock mode: `fpsns listen --mock`

**"Database connection failed"**
- Verify DATABASE_URL is set correctly
- Check network connectivity

### Web Application

**"Module not found"**
```bash
npm install
```

**"Database error"**
- Check DATABASE_URL in .env
- Verify NeonDB is accessible

## Usage Guide

### Admin Workflow

1. Login to admin dashboard
2. Create subjects (Subjects tab)
3. Create teachers (Teachers tab)
4. Create students (Students tab)
5. Link parents to students (Parents tab)
6. Set up timetable (Timetable tab)
7. Manage exam results (Exam Results tab)

### Teacher Workflow

1. Login to teacher dashboard
2. View class overview
3. Clear student audit requests
4. Manage exam results

### Attendance Recording

1. Start the fingerprint listener:
   ```bash
   fpsns listen
   ```
2. Students scan fingerprints
3. Attendance logged automatically to database

## Tech Stack

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Flask (Python)
- **Database**: PostgreSQL (NeonDB)
- **Deployment**: Vercel
- **CLI**: Node.js

## License

MIT