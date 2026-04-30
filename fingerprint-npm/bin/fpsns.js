#!/usr/bin/env node
const { program } = require('commander');
const inquirer = require('inquirer');
const chalk = require('chalk');
const ora = require('ora');
const path = require('path');
const fs = require('fs');
const os = require('os');

const db = require('../lib/db');
const Admin = require('../lib/admin');
const Fingerprint = require('../lib/fingerprint');
const Scanner = require('../lib/scanner');
const Listener = require('../lib/listener');
const { initializeDatabase } = require('../lib/setup');

program
  .name('fpsns')
  .description('Fingerprint System SNS - NPM CLI')
  .version('1.0.0');

program
  .command('setup')
  .description('Initialize database and create tables')
  .action(async () => {
    console.log(chalk.cyan('=== Fingerprint SNS Database Setup ===\n'));

    const dbUrl = process.env.NEON_DB_URL;
    if (!dbUrl) {
      console.log(chalk.yellow('Database connection config:'));
      console.log(chalk.gray('  Use NEON_DB_URL or NEON_HOST, NEON_USER, NEON_PASS, NEON_DB\n'));
    }

    const success = await initializeDatabase();
    if (!success) process.exit(1);
  });

program
  .command('admin-create')
  .description('Create an admin account')
  .option('-u, --username <username>', 'Admin username')
  .option('-p, --password <password>', 'Admin password')
  .action(async (options) => {
    console.log(chalk.cyan('=== Create Admin Account ===\n'));

    let username = options.username;
    let password = options.password;

    if (!username || !password) {
      const answers = await inquirer.prompt([
        {
          type: 'input',
          name: 'username',
          message: 'Enter admin username:',
          validate: v => v.length > 0 || 'Username required'
        },
        {
          type: 'password',
          name: 'password',
          message: 'Enter admin password:',
          validate: v => v.length >= 6 || 'Password must be at least 6 characters'
        },
        {
          type: 'password',
          name: 'confirm',
          message: 'Confirm password:',
          validate: (v, a) => v === a.password || 'Passwords do not match'
        }
      ]);
      username = answers.username;
      password = answers.confirm;
    }

    const spinner = ora('Creating admin...').start();

    try {
      await db.connect();
      const admin = await Admin.create(username, password);
      spinner.succeed(`Admin created: ID ${admin.id}, username: ${admin.username}`);
    } catch (error) {
      spinner.fail(`Failed to create admin: ${error.message}`);
      process.exit(1);
    }
  });

program
  .command('enroll')
  .description('Enroll fingerprint for student or teacher')
  .option('-t, --type <type>', 'Person type: student|teacher', 'student')
  .option('-i, --id <id>', 'Person ID')
  .option('-n, --name <name>', 'Person name')
  .action(async (options) => {
    console.log(chalk.cyan('=== Fingerprint Enrollment ===\n'));

    let personType = options.type;
    let personId = options.id;
    let personName = options.name;

    if (!personId || !personName) {
      const answers = await inquirer.prompt([
        {
          type: 'list',
          name: 'type',
          message: 'Person type:',
          choices: ['student', 'teacher'],
          default: personType
        },
        {
          type: 'input',
          name: 'id',
          message: 'Enter person ID:',
          validate: v => v.length > 0 || 'ID required'
        },
        {
          type: 'input',
          name: 'name',
          message: 'Enter person name:',
          validate: v => v.length > 0 || 'Name required'
        }
      ]);
      personType = answers.type;
      personId = answers.id;
      personName = answers.name;
    }

    const spinner = ora('Initializing scanner...').start();

    try {
      await db.connect();
      const scanner = new Scanner({ mock: true });
      await scanner.startProcess();

      spinner.start('Place finger on scanner...');
      const template = await scanner.captureTemplate(30000);

      if (!template) {
        spinner.fail('Fingerprint capture failed or timed out');
        process.exit(1);
      }

      spinner.start('Saving fingerprint...');
      const result = await Fingerprint.enroll(personType, parseInt(personId), template);

      if (result.success) {
        spinner.succeed(`Fingerprint enrolled for ${personType} ${personName} (ID: ${personId})`);
      } else {
        spinner.fail(result.error);
        process.exit(1);
      }

      scanner.close();
    } catch (error) {
      spinner.fail(error.message);
      process.exit(1);
    }
  });

program
  .command('listen')
  .description('Run fingerprint listener for attendance')
  .option('-m, --mode <mode>', 'Mode: attendance|verify', 'attendance')
  .option('--mock', 'Use mock scanner', false)
  .action(async (options) => {
    console.log(chalk.cyan('=== Fingerprint SNS Listener Mode ===\n'));

    const cleanup = async () => {
      console.log(chalk.yellow('\nShutting down...'));
      await db.disconnect();
      process.exit(0);
    };

    process.on('SIGINT', cleanup);
    process.on('SIGTERM', cleanup);

    try {
      await db.connect();
      const listener = new Listener({ mode: options.mode, mock: options.mock });
      await listener.start();
    } catch (error) {
      console.error(chalk.red('Error:'), error.message);
      await db.disconnect();
      process.exit(1);
    }
  });

program
  .command('logs')
  .description('View fingerprint logs')
  .option('-t, --type <type>', 'Filter by person type (student|teacher)')
  .option('-i, --id <id>', 'Filter by person ID')
  .option('-l, --limit <limit>', 'Number of records', '50')
  .action(async (options) => {
    try {
      await db.connect();
      const logs = await Fingerprint.getLogs(
        options.type,
        options.id ? parseInt(options.id) : null,
        parseInt(options.limit)
      );

      if (logs.length === 0) {
        console.log(chalk.yellow('No logs found'));
        return;
      }

      console.log(chalk.cyan(`\nRecent Fingerprint Logs (${logs.length} entries):`));
      console.log(chalk.gray('─'.repeat(80)));

      logs.forEach((log) => {
        const date = new Date(log.timestamp);
        const timeStr = date.toLocaleString();
        console.log(chalk.white(`${log.person_type.toUpperCase()} ID ${log.person_id}`),
          chalk.green(`[${log.log_type}]`),
          chalk.gray(` ${timeStr}`));
      });
    } catch (error) {
      console.error(chalk.red('Error:'), error.message);
      process.exit(1);
    }
  });

program
  .command('clear')
  .description('Clear fingerprint template')
  .option('-t, --type <type>', 'Person type: student|teacher', 'student')
  .option('-i, --id <id>', 'Person ID')
  .action(async (options) => {
    const answers = await inquirer.prompt([
      {
        type: 'input',
        name: 'id',
        message: 'Enter person ID:',
        default: options.id
      }
    ]);

    const { confirm } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'confirm',
        message: `Clear fingerprint for ${options.type} ID ${answers.id}?`,
        default: false
      }
    ]);

    if (confirm) {
      try {
        await db.connect();
        const result = await Fingerprint.clearTemplates(options.type, parseInt(answers.id));
        console.log(chalk.green('✓ Fingerprint cleared'));
      } catch (error) {
        console.error(chalk.red('Error:'), error.message);
        process.exit(1);
      }
    }
  });

program.parse();
