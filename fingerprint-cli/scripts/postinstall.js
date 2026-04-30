#!/usr/bin/env node

// Post-install script to set up Python environment
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log('Running post-install setup...');

try {
    // Use PYTHON environment variable or default to 'python'
    const pythonCmd = process.env.PYTHON || 'python';
    
    // Check if Python is available
    try {
        execSync(`${pythonCmd} --version`, { stdio: 'ignore' });
    } catch (error) {
        console.log('⚠️  Python not found. Please install Python 3.10+');
        console.log('Download from: https://www.python.org/downloads/');
        console.log('After installing, set PYTHON environment variable and rerun npm install');
        process.exit(0); // Don't fail the install, just skip Python setup
    }

    // Create venv directory if it doesn't exist
    const venvPath = path.join(__dirname, 'venv');
    if (!fs.existsSync(venvPath)) {
        console.log('Creating Python virtual environment...');
        execSync(`${pythonCmd} -m venv venv`, { 
            stdio: 'inherit',
            cwd: __dirname,
            env: process.env
        });
    }

    // Install Python dependencies
    console.log('Installing Python dependencies...');
    const pipPath = path.join(venvPath, 'Scripts', 'pip');
    const requirementsPath = path.join(__dirname, '..', 'requirements.txt');
    
    if (fs.existsSync(requirementsPath)) {
        execSync(`"${pipPath}" install -r "${requirementsPath}"`, { 
            stdio: 'inherit',
            cwd: path.join(__dirname, '..'),
            env: { ...process.env, PATH: `${path.join(venvPath, 'Scripts')};${process.env.PATH}` }
        });
    } else {
        console.log('⚠️  requirements.txt not found, skipping Python dependencies');
    }

    console.log('✅ Setup complete!');
    
} catch (error) {
    console.error('❌ Setup failed:', error.message);
    console.log('You can still use the CLI without Python features.');
    console.log('To fix: Install Python 3.10+ and rerun npm install');
    // Don't fail the install - CLI can work without Python for basic features
    process.exit(0);
}
