const { exec } = require('child_process');
const path = require('path');
const bcrypt = require('bcrypt');
const { pool } = require('./database');
const chalk = require('chalk').default;
const ora = require('ora').default;

async function createAdmin(username, password) {
    const spinner = ora(`Creating admin ${username}...`).start();
    
    try {
        const saltRounds = 10;
        const passwordHash = await bcrypt.hash(password, saltRounds);

        const query = {
            text: 'INSERT INTO admins (username, password_hash) VALUES ($1, $2) RETURNING *',
            values: [username, passwordHash]
        };

        const result = await pool.query(query);
        spinner.succeed(`Admin ${username} created successfully!`);
        return result.rows[0];
        
    } catch (error) {
        spinner.fail(`Failed to create admin: ${error.message}`);
        throw error;
    }
}

async function listAdmins() {
    const spinner = ora('Fetching admins...').start();
    
    try {
        const result = await pool.query('SELECT id, username, created_at FROM admins ORDER BY created_at DESC');
        spinner.succeed(`Found ${result.rowCount} admin(s)`);
        
        if (result.rows.length > 0) {
            console.log('\nAdmins:');
            console.log('ID\tUsername\tCreated At');
            console.log('-'.repeat(50));
            result.rows.forEach(admin => {
                console.log(`${admin.id}\t${admin.username}\t${admin.created_at}`);
            });
        }
        
        return result.rows;
        
    } catch (error) {
        spinner.fail(`Failed to list admins: ${error.message}`);
        throw error;
    }
}

async function deleteAdmin(username) {
    const spinner = ora(`Deleting admin ${username}...`).start();
    
    try {
        const result = await pool.query('DELETE FROM admins WHERE username = $1 RETURNING *', [username]);
        
        if (result.rowCount > 0) {
            spinner.succeed(`Admin ${username} deleted!`);
        } else {
            spinner.fail(`Admin ${username} not found`);
        }
        
        return result.rows[0];
        
    } catch (error) {
        spinner.fail(`Failed to delete admin: ${error.message}`);
        throw error;
    }
}

async function adminCommand(options) {
    if (options.create && options.password) {
        await createAdmin(options.create, options.password);
    } else if (options.list) {
        await listAdmins();
    } else if (options.delete) {
        await deleteAdmin(options.delete);
    } else {
        console.log(chalk.yellow('\nUsage:'));
        console.log('  fpsns admin --create <username> --password <password>  Create admin');
        console.log('  fpsns admin --list                                 List admins');
        console.log('  fpsns admin --delete <username>                    Delete admin');
    }
}

module.exports = adminCommand;