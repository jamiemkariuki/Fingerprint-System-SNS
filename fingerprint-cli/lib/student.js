const { pool } = require('./database');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');
const chalk = require('chalk').default;
const ora = require('ora').default;


async function enrollStudentFingerprint(studentId) {
    const spinner = ora(`Enrolling fingerprint for student ${studentId}...`).start();
    
    try {
        // Verify student exists
        const checkQuery = {
            text: 'SELECT id, name FROM users WHERE id = $1',
            values: [studentId]
        };
        
        const checkResult = await pool.query(checkQuery);
        
        if (checkResult.rowCount === 0) {
            spinner.fail(`Student ID ${studentId} not found!`);
            return null;
        }
        
        const studentName = checkResult.rows[0].name;
        spinner.text = `Place finger on scanner for ${studentName}...`;
        
        // Run Python enrollment script
        const baseDir = path.join(__dirname, '..');
        const enrollScript = path.join(baseDir, 'python', 'enroll.py');
        
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
        
        return new Promise((resolve, reject) => {
            const proc = exec(`"${pythonPath}" "${enrollScript}" ${studentId}`, {
                cwd: baseDir
            }, async (error, stdout, stderr) => {
                if (error) {
                    spinner.fail(`Enrollment failed: ${stderr || error.message}`);
                    reject(error);
                    return;
                }
                
                // The Python script now saves directly to database, so we just check for success
                if (stdout.includes('Fingerprint enrolled successfully')) {
                    spinner.succeed(`Fingerprint enrolled for ${studentName}!`);
                    resolve({ id: studentId, name: studentName });
                } else {
                    spinner.fail('Enrollment did not complete successfully');
                    reject(new Error('Enrollment failed'));
                }
            });
            
            proc.stdout.on('data', (data) => {
                console.log(chalk.blue(`[ENROLL] ${data}`));
            });
            
            proc.stderr.on('data', (data) => {
                console.log(chalk.red(`[ENROLL ERR] ${data}`));
            });
        });
        
    } catch (error) {
        spinner.fail(`Fingerprint enrollment failed: ${error.message}`);
        throw error;
    }
}

async function createStudent(name, username, className) {
    const spinner = ora(`Creating student ${name}...`).start();
    
    try {
        const query = {
            text: 'INSERT INTO users (name, username, class, created_at) VALUES ($1, $2, $3, NOW()) RETURNING *',
            values: [name, username, className]
        };
        
        const result = await pool.query(query);
        spinner.succeed(`Student ${name} created with ID: ${result.rows[0].id}`);
        return result.rows[0];
        
    } catch (error) {
        spinner.fail(`Failed to create student: ${error.message}`);
        throw error;
    }
}

async function listStudents() {
    const spinner = ora('Fetching student list...').start();
    
    try {
        const result = await pool.query('SELECT id, name, username, class, fingerprint_template IS NOT NULL as enrolled FROM users ORDER BY name ASC');
        
        if (result.rows.length === 0) {
            spinner.info('No students found.');
            return [];
        }
        
        spinner.succeed(`Found ${result.rows.length} student(s):`);
        
        result.rows.forEach(s => {
            console.log(`ID: ${s.id} | ${s.name} | ${s.class} | ${s.enrolled ? 'Enrolled' : 'Not enrolled'}`);
        });
        
        return result.rows;
        
    } catch (error) {
        spinner.fail(`Failed to list students: ${error.message}`);
        throw error;
    }
}

module.exports = async function(options) {
    const db = require('./database');
    await db.initialize();
    
    if (options.enroll) {
        await enrollStudentFingerprint(options.enroll);
    } else if (options.list) {
        await listStudents();
    } else if (options.create) {
        const args = options.create.split(' ');
        if (args.length >= 3) {
            await createStudent(args[0], args[1], args[2]);
        } else {
            console.log(chalk.red('Error: create requires name, username, and class'));
            console.log('Usage: fpsns student --create "John Doe" john class10a');
        }
    } else {
        console.log(chalk.yellow('Student operations:'));
        console.log('  --enroll <student_id>      Enroll student fingerprint');
        console.log('  --list                     List all students');
        console.log('  --create <name> <username> <class>  Create new student');
    }
};