#!/usr/bin/env node

const { program } = require('commander');
const packageJson = require('../package.json');

// Display header
console.log('========================================');
console.log('FPSNS CLI - Fingerprint Management System');
console.log(`v${packageJson.version}`);
console.log('St. Nicholas Senior School');
console.log('========================================\n');

// Configure CLI
program
  .name('fpsns')
  .description('CLI for managing St. Nicholas Senior School fingerprint attendance system')
  .version(packageJson.version);

// Setup command
program.command('setup')
  .description('Initialize the fingerprint system and database')
  .option('-f, --force', 'Force reinitialization')
  .action(require('../lib/setup'));

// Admin commands
program.command('admin')
  .description('Manage admin accounts')
  .option('-c, --create <username>', 'Create new admin account')
  .option('-p, --password <password>', 'Admin password')
  .option('-l, --list', 'List all admin accounts')
  .option('-d, --delete <username>', 'Delete admin account')
  .action(require('../lib/admin'));

// Student commands
program.command('student')
  .description('Manage student accounts and fingerprints')
  .option('-e, --enroll <student_id>', 'Enroll student fingerprint')
  .option('-l, --list', 'List all students')
  .option('-c, --create <name> <username> <class>', 'Create new student')
  .option('-p, --password <password>', 'Student password')
  .action(require('../lib/student'));

// Teacher commands
program.command('teacher')
  .description('Manage teacher accounts')
  .option('-c, --create <name> <email> <class> <password>', 'Create new teacher')
  .option('-l, --list', 'List all teachers')
  .option('-e, --enroll <teacher_id>', 'Enroll teacher fingerprint')
  .action(require('../lib/teacher'));

// Fingerprint listener
program.command('listen')
  .description('Start fingerprint listener for attendance tracking')
  .option('-m, --mock', 'Use mock scanner (no hardware required)')
  .option('-p, --port <port>', 'API port for fingerprint events', '3001')
  .action(require('../lib/listener'));

// Database commands
program.command('db')
  .description('Database management')
  .option('-i, --init', 'Initialize database schema')
  .option('-c, --clear', 'Clear fingerprint templates')
  .option('-b, --backup', 'Backup database')
  .action(require('../lib/database'));

// Parse arguments
program.parse(process.argv);