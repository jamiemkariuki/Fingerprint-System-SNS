const { Pool } = require('pg');
const chalk = require('chalk').default;
const ora = require('ora').default;

const dbPool = new Pool({
    connectionString: process.env.DATABASE_URL || 'postgresql://neondb_owner:npg_hnBPkldL2W9i@ep-raspy-base-akq29c7r.c-3.us-west-2.aws.neon.tech/neondb?sslmode=require',
    ssl: {
        rejectUnauthorized: false
    }
});

async function initializeDatabase() {
    const spinner = ora('Initializing database connection...').start();
    
    try {
        await dbPool.query('SELECT 1');
        spinner.succeed('Database connected successfully!');
        return dbPool;
    } catch (error) {
        spinner.fail(`Database connection failed: ${error.message}`);
        throw error;
    }
}

module.exports = {
    pool: dbPool,
    initialize: initializeDatabase
};