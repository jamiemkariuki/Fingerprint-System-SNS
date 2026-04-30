const { Pool } = require('pg');
const dotenv = require('dotenv');

dotenv.config();

class Database {
  constructor() {
    this.pool = null;
    this.connectionString = process.env.NEON_DB_URL ||
      `postgres://${process.env.NEON_USER}:${process.env.NEON_PASS}@${process.env.NEON_HOST}/${process.env.NEON_DB}`;
  }

  async connect() {
    try {
      this.pool = new Pool({
        connectionString: this.connectionString,
        ssl: process.env.NEON_SSL === 'true' ? { rejectUnauthorized: false } : false
      });

      await this.pool.query('SELECT NOW()');
      console.log('✓ Connected to NeonDB');
      return this.pool;
    } catch (error) {
      console.error('✗ Database connection failed:', error.message);
      throw error;
    }
  }

  async disconnect() {
    if (this.pool) {
      await this.pool.end();
      console.log('Disconnected from database');
    }
  }

  async query(text, params) {
    if (!this.pool) await this.connect();
    return this.pool.query(text, params);
  }

  async transaction(callback) {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      const result = await callback(client);
      await client.query('COMMIT');
      return result;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }
}

module.exports = new Database();
