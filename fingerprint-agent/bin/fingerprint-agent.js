#!/usr/bin/env node
const { program } = require('commander');
const inquirer = require('inquirer');
const chalk = require('chalk');
const ora = require('ora');
const fs = require('fs');
const path = require('path');
const os = require('os');

const ApiClient = require('../lib/api-client');
const Scanner = require('../lib/scanner');

program
  .name('fpsns-agent')
  .description('Fingerprint System SNS - Local Agent')
  .version('1.0.0');

program
  .command('enroll')
  .description('Enroll a new fingerprint')
  .option('-t, --type <type>', 'Person type (student|teacher)', 'student')
  .option('-i, --id <id>', 'Person ID')
  .option('-n, --name <name>', 'Person name')
  .option('-s, --server <url>', 'Server URL', process.env.FP_SERVER_URL || 'http://localhost:8080')
  .action(async (options) => {
    const spinner = ora();
    
    try {
      const config = loadConfig(options.server);
      const apiClient = new ApiClient(config);
      
      let personType = options.type;
      let personId = options.id;
      let personName = options.name;
      
      if (!personId || !personName) {
        const answers = await inquirer.prompt([
          {
            type: 'list',
            name: 'personType',
            message: 'Select person type:',
            choices: ['student', 'teacher'],
            default: personType || 'student',
            when: !personType
          },
          {
            type: 'input',
            name: 'personId',
            message: 'Enter person ID:',
            validate: (val) => val.length > 0 || 'ID is required'
          },
          {
            type: 'input',
            name: 'personName',
            message: 'Enter person name:',
            validate: (val) => val.length > 0 || 'Name is required'
          }
        ]);
        personType = personType || answers.personType;
        personId = personId || answers.personId;
        personName = personName || answers.personName;
      }

      spinner.start('Connecting to scanner...');
      const scanner = new Scanner();
      
      spinner.start('Place finger on scanner for enrollment...');
      const template = await scanner.captureTemplate(30000);
      
      if (!template) {
        spinner.fail('Failed to capture fingerprint');
        process.exit(1);
      }
      
      spinner.start('Sending to server...');
      const result = await apiClient.enrollFingerprint({
        person_type: personType,
        person_id: parseInt(personId),
        person_name: personName,
        template: template
      });
      
      if (result.success) {
        spinner.succeed(`Fingerprint enrolled for ${personType} ${personName} (ID: ${personId})`);
      } else {
        spinner.fail(result.error || 'Enrollment failed');
        process.exit(1);
      }
      
    } catch (error) {
      spinner.fail(error.message);
      process.exit(1);
    }
  });

program
  .command('verify')
  .description('Verify a fingerprint scan')
  .option('-s, --server <url>', 'Server URL', process.env.FP_SERVER_URL || 'http://localhost:8080')
  .action(async (options) => {
    const spinner = ora();
    
    try {
      const config = loadConfig(options.server);
      const apiClient = new ApiClient(config);
      
      spinner.start('Place finger on scanner...');
      const scanner = new Scanner();
      const template = await scanner.captureTemplate(15000);
      
      if (!template) {
        spinner.fail('No fingerprint captured');
        process.exit(1);
      }
      
      spinner.start('Verifying...');
      const result = await apiClient.verifyFingerprint(template);
      
      if (result.matched) {
        spinner.succeed(`Matched: ${result.person_type} ID ${result.person_id} (score: ${result.score})`);
      } else {
        spinner.fail('Fingerprint not recognized');
      }
      
    } catch (error) {
      spinner.fail(error.message);
      process.exit(1);
    }
  });

program
  .command('listen')
  .description('Run in continuous listening mode for attendance')
  .option('-s, --server <url>', 'Server URL', process.env.FP_SERVER_URL || 'http://localhost:8080')
  .option('-m, --mode <mode>', 'Mode: attendance|verify', 'attendance')
  .action(async (options) => {
    console.log(chalk.cyan('=== Fingerprint System SNS - Listener Mode ==='));
    console.log(chalk.gray('Press Ctrl+C to exit\n'));
    
    const config = loadConfig(options.server);
    const apiClient = new ApiClient(config);
    const scanner = new Scanner();
    
    console.log(chalk.blue('Syncing cache from server...'));
    try {
      await apiClient.refreshCache();
      console.log(chalk.green('Cache synced successfully'));
    } catch (e) {
      console.log(chalk.yellow('Warning: Could not sync cache, using local'));
    }
    
    const scannerStatus = scanner.getStatus();
    console.log(chalk.blue(`Scanner status: ${scannerStatus.connected ? 'Connected' : 'Disconnected'}`));
    
    if (!scannerStatus.connected) {
      console.log(chalk.red('Scanner not connected. Exiting.'));
      process.exit(1);
    }
    
    console.log(chalk.cyan('\nListening for fingerprints...\n'));
    
    let lastScanTime = 0;
    const cooldownMs = 3000;
    
    while (true) {
      try {
        const template = await scanner.captureTemplate(5000);
        
        if (template) {
          const now = Date.now();
          if (now - lastScanTime < cooldownMs) {
            continue;
          }
          lastScanTime = now;
          
          console.log(chalk.blue('Fingerprint detected, verifying...'));
          const result = await apiClient.verifyFingerprint(template);
          
          if (result.matched) {
            const type = result.person_type === 'teacher' ? 'Teacher' : 'Student';
            console.log(chalk.green(`✓ Matched: ${type} ID ${result.person_id} (score: ${result.score})`));
            
            if (options.mode === 'attendance') {
              const logResult = await apiClient.logAttendance(result.person_type, result.person_id);
              if (logResult.success) {
                console.log(chalk.green(`  Attendance logged: ${logResult.log_type} at ${logResult.timestamp}`));
              }
            }
          } else {
            console.log(chalk.red('✗ Not recognized'));
          }
        }
      } catch (error) {
        console.log(chalk.yellow(`Error: ${error.message}`));
        await sleep(1000);
      }
    }
  });

program
  .command('sync')
  .description('Manually sync cache from server')
  .option('-s, --server <url>', 'Server URL', process.env.FP_SERVER_URL || 'http://localhost:8080')
  .action(async (options) => {
    const spinner = ora();
    
    try {
      const config = loadConfig(options.server);
      const apiClient = new ApiClient(config);
      
      spinner.start('Syncing cache...');
      const result = await apiClient.refreshCache();
      
      spinner.succeed(`Synced ${result.templates_loaded} templates`);
    } catch (error) {
      spinner.fail(error.message);
      process.exit(1);
    }
  });

program
  .command('config')
  .description('Configure agent settings')
  .action(async () => {
    const answers = await inquirer.prompt([
      {
        type: 'input',
        name: 'serverUrl',
        message: 'Server URL:',
        default: process.env.FP_SERVER_URL || 'http://localhost:8080'
      },
      {
        type: 'input',
        name: 'apiKey',
        message: 'API Key:',
        default: process.env.FP_API_KEY || ''
      }
    ]);
    
    const configPath = path.join(os.homedir(), '.fpsns-agent', '.env');
    const configDir = path.dirname(configPath);
    
    if (!fs.existsSync(configDir)) {
      fs.mkdirSync(configDir, { recursive: true });
    }
    
    fs.writeFileSync(configPath, 
      `FP_SERVER_URL=${answers.serverUrl}\nFP_API_KEY=${answers.apiKey}\n`
    );
    
    console.log(chalk.green('Configuration saved!'));
  });

program
  .command('health')
  .description('Check server health')
  .option('-s, --server <url>', 'Server URL', process.env.FP_SERVER_URL || 'http://localhost:8080')
  .action(async (options) => {
    const spinner = ora();
    
    try {
      const config = loadConfig(options.server);
      const apiClient = new ApiClient(config);
      
      spinner.start('Checking health...');
      const result = await apiClient.healthCheck();
      
      if (result.status === 'healthy') {
        spinner.succeed('Server is healthy');
        console.log(chalk.gray(`  Scanner: ${result.scanner_connected ? 'Connected' : 'Disconnected'}`));
        console.log(chalk.gray(`  Templates in cache: ${result.templates_in_cache}`));
      } else {
        spinner.fail(`Server unhealthy: ${result.error}`);
      }
    } catch (error) {
      spinner.fail(error.message);
      process.exit(1);
    }
  });

function loadConfig(serverUrl) {
  const configFile = path.join(os.homedir(), '.fpsns-agent', '.env');
  let envConfig = {};
  
  if (fs.existsSync(configFile)) {
    const content = fs.readFileSync(configFile, 'utf8');
    content.split('\n').forEach(line => {
      const [key, ...values] = line.split('=');
      if (key && values.length > 0) {
        envConfig[key.trim()] = values.join('=').trim();
      }
    });
  }
  
  return {
    serverUrl: serverUrl || envConfig.FP_SERVER_URL || 'http://localhost:8080',
    apiKey: envConfig.FP_API_KEY || process.env.FP_API_KEY || ''
  };
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

program.parse();
