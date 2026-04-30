const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');
const https = require('https');
const chalk = require('chalk').default;
const ora = require('ora').default;

const EXEC_OPTS = { maxBuffer: 10 * 1024 * 1024 };

async function execAsync(command, options = {}) {
    return new Promise((resolve, reject) => {
        exec(command, { ...EXEC_OPTS, ...options }, (error, stdout, stderr) => {
            if (error) {
                reject(new Error(stderr || error.message));
            } else {
                resolve({ stdout, stderr });
            }
        });
    });
}

function downloadFile(url, dest) {
    return new Promise((resolve, reject) => {
        const file = fs.createWriteStream(dest);
        https.get(url, (response) => {
            if (response.statusCode === 302 || response.statusCode === 301) {
                downloadFile(response.headers.location, dest).then(resolve).catch(reject);
                return;
            }
            response.pipe(file);
            file.on('finish', () => {
                file.close();
                resolve();
            });
        }).on('error', (err) => {
            fs.unlink(dest, () => {});
            reject(err);
        });
    });
}

function getPythonPath() {
    // Check for local Python 3.11 installation first
    const baseDir = path.join(__dirname, '..');
    const localPython311 = path.join(baseDir, 'python311', 'python.exe');
    
    if (fs.existsSync(localPython311)) {
        return localPython311;
    }
    
    // Fallback to system Python
    const userProfile = process.env.USERPROFILE || 'C:\\Users\\USER 1';
    const pythonDefaultPath = `${userProfile}\\AppData\\Local\\Python\\bin\\python.exe`;
    return pythonDefaultPath;
}

async function checkPython() {
    const pythonPath = getPythonPath();
    try {
        const { stdout } = await execAsync(`"${pythonPath}" --version`);
        return { installed: true, version: stdout.trim(), path: pythonPath };
    } catch {
        return { installed: false, version: null, path: null };
    }
}

async function installLocalPython311() {
    const spinner = ora('Installing Python 3.11 locally...').start();
    const baseDir = path.join(__dirname, '..');
    const python311Dir = path.join(baseDir, 'python311');
    const installerPath = path.join(baseDir, 'python311-installer.exe');
    
    try {
        // Create directory
        if (!fs.existsSync(python311Dir)) {
            fs.mkdirSync(python311Dir, { recursive: true });
        }
        
        // Download Python 3.11 full installer
        spinner.text = 'Downloading Python 3.11 installer...';
        const pythonUrl = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe';
        
        await downloadFile(pythonUrl, installerPath);
        spinner.succeed('Python 3.11 installer downloaded!');
        
        // Install Python 3.11 silently to local directory
        spinner.text = 'Installing Python 3.11 locally...';
        await execAsync(`"${installerPath}" /quiet InstallAllUsers=0 TargetDir="${python311Dir}" PrependPath=0 Include_test=0`);
        
        // Clean up installer
        fs.unlinkSync(installerPath);
        
        spinner.succeed('Python 3.11 installed locally!');
        return path.join(python311Dir, 'python.exe');
        
    } catch (error) {
        spinner.fail('Failed to install Python 3.11: ' + error.message);
        // Clean up on failure
        if (fs.existsSync(installerPath)) fs.unlinkSync(installerPath);
        if (fs.existsSync(python311Dir)) fs.rmSync(python311Dir, { recursive: true, force: true });
        throw error;
    }
}

async function setupPythonEnvironment() {
    const spinner = ora('Checking Python...').start();
    
    try {
        const baseDir = path.join(__dirname, '..');
        const localPython311 = path.join(baseDir, 'python311', 'python.exe');
        
        // Check if we have local Python 3.11
        if (!fs.existsSync(localPython311)) {
            spinner.info('Local Python 3.11 not found, installing...');
            await installLocalPython311();
        }
        
        const python = await checkPython();
        
        if (!python.installed) {
            console.log(chalk.yellow('Python not found.'));
            return false;
        }
        
        spinner.succeed(`Python found: ${python.version}`);
        
        // Install venv module in local Python if not available
        spinner.text = 'Ensuring venv module is available...';
        try {
            await execAsync(`"${localPython311}" -m venv --help`);
        } catch {
            // venv not available, install it
            spinner.text = 'Installing venv module...';
            await execAsync(`"${localPython311}" -m pip install virtualenv`);
        }
        spinner.succeed('venv module available!');
        
        // Create virtual environment with local Python 3.11
        spinner.text = 'Creating virtual environment with Python 3.11...';
        const venvPath = path.join(baseDir, 'venv');
        
        // Remove existing venv if it exists
        if (fs.existsSync(venvPath)) {
            fs.rmSync(venvPath, { recursive: true, force: true });
        }
        
        // Try venv first, fall back to virtualenv
        try {
            await execAsync(`"${localPython311}" -m venv "${venvPath}"`);
        } catch {
            await execAsync(`"${localPython311}" -m virtualenv "${venvPath}"`);
        }
        spinner.succeed('Virtual environment created with Python 3.11!');
        
        // Install dependencies in venv
        spinner.text = 'Installing dependencies in virtual environment...';
        const reqPath = path.join(baseDir, 'requirements.txt');
        const venvPython = path.join(venvPath, 'Scripts', 'python.exe');
        
        await execAsync(`"${venvPython}" -m pip install -r "${reqPath}"`);
        
        spinner.succeed('Dependencies installed in virtual environment!');
        return true;
        
    } catch (error) {
        spinner.fail('Setup failed: ' + error.message);
        console.log(chalk.yellow('\n⚠ Setup failed. The CLI will use MOCK mode for fingerprint scanning.'));
        return true; // Continue anyway with MOCK mode
    }
}

module.exports = async function(options) {
    console.log('Setting up fingerprint management system...\n');
    const success = await setupPythonEnvironment();
    
    if (success) {
        console.log(chalk.green('\n✓ Setup complete!'));
        console.log(chalk.blue('\nAvailable commands:'));
        console.log('  fpsns admin --help       # Manage admin accounts');
        console.log('  fpsns student --help   # Manage students');
        console.log('  fpsns teacher --help   # Manage teachers');
        console.log('  fpsns listen --help    # Start fingerprint listener');
    } else {
        console.log(chalk.red('\nSetup incomplete. Please install Python manually.'));
    }
};
