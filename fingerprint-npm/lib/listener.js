const Scanner = require('./scanner');
const Fingerprint = require('./fingerprint');
const chalk = require('chalk');
const ora = require('ora');

class Listener {
  constructor(options = {}) {
    this.scanner = new Scanner(options);
    this.mode = options.mode || 'attendance';
    this.running = false;
    this.cooldownMs = options.cooldown || 3000;
    this.lastScanTime = 0;
  }

  async start() {
    console.log(chalk.cyan('=== Fingerprint SNS Listener ==='));
    console.log(chalk.gray('Press Ctrl+C to exit\n'));

    const spinner = ora();
    try {
      spinner.start('Initializing scanner...');
      await this.scanner.startProcess();
      spinner.succeed('Scanner initialized');

      console.log(chalk.blue(`Status: ${this.scanner.connected ? 'Connected' : 'Disconnected'}`));

      if (!this.scanner.connected) {
        console.log(chalk.red('Scanner not connected. Exiting.'));
        process.exit(1);
      }

      console.log(chalk.cyan('\nListening for fingerprints...\n'));
      this.running = true;

      while (this.running) {
        try {
          const template = await this.scanner.captureTemplate(5000);

          if (template) {
            const now = Date.now();
            if (now - this.lastScanTime < this.cooldownMs) continue;
            this.lastScanTime = now;

            console.log(chalk.blue('Fingerprint detected, verifying...'));
            const result = await Fingerprint.verify(template);

            if (result.matched) {
              const type = result.person_type === 'teacher' ? 'Teacher' : 'Student';
              console.log(chalk.green(`✓ Matched: ${type} ID ${result.person_id} (${result.name})`));

              if (this.mode === 'attendance') {
                const logResult = await Fingerprint.logAttendance(result.person_type, result.person_id);
                if (logResult.success) {
                  console.log(chalk.green(`  Attendance: ${logResult.log.log_type} at ${logResult.log.timestamp}`));
                }
              }
            } else {
              console.log(chalk.red('✗ Not recognized'));
            }
          }
        } catch (error) {
          console.log(chalk.yellow(`Error: ${error.message}`));
          await new Promise(r => setTimeout(r, 1000));
        }
      }
    } catch (error) {
      spinner.fail(error.message);
      process.exit(1);
    }
  }

  stop() {
    this.running = false;
    this.scanner.close();
  }
}

module.exports = Listener;
