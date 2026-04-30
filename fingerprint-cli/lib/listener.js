const express = require('express');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');
const chalk = require('chalk').default;
const ora = require('ora').default;

async function startListener(options) {
    const spinner = ora('Starting fingerprint listener...').start();
    
    try {
        const port = options.port || 3001;
        const mockMode = options.mock || false;
        
        const baseDir = path.join(__dirname, '..');
        const listenerPath = path.join(baseDir, 'python', 'listener.py');
        
        // Use virtual environment Python if it exists, otherwise use local Python 3.11
        const venvPython = path.join(baseDir, 'venv', 'Scripts', 'python.exe');
        const localPython311 = path.join(baseDir, 'python311', 'python.exe');
        const userProfile = process.env.USERPROFILE || 'C:\\Users\\USER 1';
        const pythonDefaultPath = `${userProfile}\\AppData\\Local\\Python\\bin\\python.exe`;
        
        let pythonPath;
        if (fs.existsSync(venvPython)) {
            pythonPath = venvPython;
        } else if (fs.existsSync(localPython311)) {
            pythonPath = localPython311;
        } else {
            pythonPath = pythonDefaultPath;
        }
        
        const args = [listenerPath, '--port', port.toString()];
        if (mockMode) {
            args.push('--mock');
        }
        
        console.log(chalk.gray(`Running: ${pythonPath} ${args.join(' ')}`));
        
        console.log(chalk.blue(`\nFingerprint listener started on port ${port}`));
        console.log(chalk.blue(`Mode: ${mockMode ? 'MOCK' : 'REAL'}`));
        console.log(chalk.yellow('Press Ctrl+C to stop the listener\n'));
        
        // Execute the Python listener using exec with proper path handling
        const command = `"${pythonPath}" ${args.map(a => `"${a}"`).join(' ')}`;
        const listener = exec(command, {
            cwd: path.join(__dirname, '..')
        });
        
        listener.stdout.on('data', (data) => {
            console.log(chalk.green(`[LISTENER] ${data}`));
        });
        
        listener.stderr.on('data', (data) => {
            console.log(chalk.red(`[LISTENER ERR] ${data}`));
        });
        
        listener.on('close', (code) => {
            console.log(chalk.blue(`\nFingerprint listener stopped with code ${code}`));
        });
        
        // Handle Ctrl+C
        process.on('SIGINT', () => {
            listener.kill();
            process.exit();
        });
        
        spinner.succeed('Fingerprint listener running!');
        
    } catch (error) {
        spinner.fail(`Failed to start listener: ${error.message}`);
        throw error;
    }
}

module.exports = startListener;
