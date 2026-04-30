const { Pool } = require('pg');
const pool = new Pool({
    connectionString: process.env.DATABASE_URL || 'postgresql://neondb_owner:npg_hnBPkldL2W9i@ep-raspy-base-akq29c7r.c-3.us-west-2.aws.neon.tech/neondb?sslmode=require',
    ssl: { rejectUnauthorized: false }
});

async function check() {
    const teachers = await pool.query('SELECT id, name FROM teachers');
    console.log('Teachers:', teachers.rows);

    const students = await pool.query('SELECT id, name, class FROM users');
    console.log('\nStudents:', students.rows);

    const parents = await pool.query('SELECT id, name FROM parents');
    console.log('\nParents:', parents.rows);

    await pool.end();
}

check();