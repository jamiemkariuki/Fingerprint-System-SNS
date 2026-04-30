const bcrypt = require('bcrypt');
const db = require('./db');

class Admin {
  static async create(username, password) {
    const passwordHash = await bcrypt.hash(password, 10);

    const query = `
      INSERT INTO "Admins" (username, password_hash)
      VALUES ($1, $2)
      RETURNING id, username, created_at
    `;

    const result = await db.query(query, [username, passwordHash]);
    return result.rows[0];
  }

  static async findByUsername(username) {
    const query = 'SELECT * FROM "Admins" WHERE username = $1';
    const result = await db.query(query, [username]);
    return result.rows[0];
  }

  static async verifyPassword(username, password) {
    const admin = await this.findByUsername(username);
    if (!admin) return false;
    return await bcrypt.compare(password, admin.password_hash);
  }

  static async getAll() {
    const query = 'SELECT id, username, created_at FROM "Admins" ORDER BY id';
    const result = await db.query(query);
    return result.rows;
  }
}

module.exports = Admin;
