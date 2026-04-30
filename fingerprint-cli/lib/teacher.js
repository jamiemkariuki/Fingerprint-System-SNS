const { pool } = require('./database');
const bcrypt = require('bcrypt');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');
const chalk = require('chalk').default;
const ora = require('ora').default;

async function createTeacher(name, email, className, password) {
    const spinner = ora(`Creating teacher ${name}...`).start();
    
    try {
        // Hash password
        const saltRounds = 12;
        const passwordHash = await bcrypt.hash(password, saltRounds);

        const query = {
            text: 'INSERT INTO teachers (name, email, class, password_hash, created_at) VALUES ($1, $2, $3, $4, NOW()) RETURNING *',
            values: [name, email, className, passwordHash]
        };
        
        const result = await pool.query(query);
        spinner.succeed(`Teacher ${name} created with ID: ${result.rows[0].id}`);
        return result.rows[0];
        
    } catch (error) {
        spinner.fail(`Failed to create teacher: ${error.message}`);
        throw error;
    }
}

async function listTeachers() {
    const spinner = ora('Fetching teacher list...').start();
    
    try {
        const result = await pool.query('SELECT id, name, email, class, created_at FROM teachers ORDER BY name ASC');
        
        if (result.rows.length === 0) {
            spinner.info('No teachers found.');
            return [];
        }
        
        spinner.succeed(`Found ${result.rows.length} teacher(s):`);
        console.table(result.rows);
        return result.rows;
        
    } catch (error) {
        spinner.fail(`Failed to list teachers: ${error.message}`);
        throw error;
    }
}

async function enrollTeacherFingerprint(teacherId) {
    const spinner = ora(`Enrolling fingerprint for teacher ${teacherId}...`).start();
    
    try {
        // Verify teacher exists
        const checkQuery = {
            text: 'SELECT id, name FROM teachers WHERE id = $1',
            values: [teacherId]
        };
        
        const checkResult = await pool.query(checkQuery);
        
        if (checkResult.rowCount === 0) {
            spinner.fail(`Teacher ID ${teacherId} not found!`);
            return null;
        }
        
        const teacherName = checkResult.rows[0].name;
        spinner.text = `Place finger on scanner for ${teacherName}...`;
        
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
            const proc = exec(`"${pythonPath}" "${enrollScript}" ${teacherId}`, {
                cwd: baseDir,
                env: { ...process.env, MOCK_SCANNER: '1' } // Use mock for teachers for now
            }, async (error, stdout, stderr) => {
                if (error) {
                    spinner.fail(`Enrollment failed: ${stderr || error.message}`);
                    reject(error);
                    return;
                }
                
                spinner.succeed(`Fingerprint enrolled for ${teacherName}!`);
                resolve(checkResult.rows[0]);
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

module.exports = async function(options) {
    // Initialize database connection
    const db = require('./database');
    await db.initialize();
    
    if (options.create) {
        // Parse create options
        const args = options.create.split(' ');
        if (args.length >= 4) {
            await createTeacher(args[0], args[1], args[2], args[3]);
        } else {
            console.log(chalk.red('Error: create requires name, email, class, and password'));
            console.log('Usage: fpsns teacher --create "Jane Doe" jane@school.edu class10a password123');
        }
    } else if (options.list) {
        await listTeachers();
    } else if (options.enroll) {
        await enrollTeacherFingerprint(options.enroll);
    } else {
        console.log(chalk.yellow('Please specify a teacher operation:'));
        console.log('  --create <name> <email> <class> <password>  Create new teacher');
        console.log('  --list                                      List all teachers');
        console.log('  --enroll <teacher_id>                        Enroll teacher fingerprint');
    }
};
