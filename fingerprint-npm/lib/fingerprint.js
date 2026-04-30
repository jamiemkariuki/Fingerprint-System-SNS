const db = require('./db');
const Scanner = require('./scanner');

class Fingerprint {
  static async enroll(personType, personId, template) {
    const table = personType === 'teacher' ? 'Teachers' : 'Users';

    const query = `
      UPDATE "${table}"
      SET fingerprint_template = $1
      WHERE id = $2
      RETURNING *
    `;

    try {
      const result = await db.query(query, [template, personId]);
      if (result.rows.length === 0) {
        return { success: false, error: `${personType} with ID ${personId} not found` };
      }
      return { success: true, data: result.rows[0] };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  static async verify(template) {
    const queries = [
      { table: 'Teachers', type: 'teacher' },
      { table: 'Users', type: 'student' }
    ];

    for (const { table, type } of queries) {
      const result = await db.query(
        `SELECT id, name FROM "${table}" WHERE fingerprint_template IS NOT NULL`
      );

      for (const row of result.rows) {
        // In production, template matching is done via ZK library's Match function
        // This simple equality check works only for mock mode
        // For real matching, use scanner's matchTemplate method
        if (row.fingerprint_template === template) {
          return { matched: true, person_type: type, person_id: row.id, name: row.name, score: 100 };
        }
      }
    }

    return { matched: false };
  }

  static async logAttendance(personType, personId, logType = 'IN') {
    const query = `
      INSERT INTO "FingerprintLogs" (person_type, person_id, log_type)
      VALUES ($1, $2, $3)
      RETURNING *
    `;

    try {
      const result = await db.query(query, [personType, personId, logType]);
      return { success: true, log: result.rows[0] };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  static async getLogs(personType = null, personId = null, limit = 100) {
    let query = 'SELECT * FROM "FingerprintLogs"';
    const params = [];
    const conditions = [];

    if (personType) {
      conditions.push(`person_type = $${params.length + 1}`);
      params.push(personType);
    }
    if (personId) {
      conditions.push(`person_id = $${params.length + 1}`);
      params.push(personId);
    }

    if (conditions.length > 0) {
      query += ' WHERE ' + conditions.join(' AND ');
    }

    query += ` ORDER BY timestamp DESC LIMIT $${params.length + 1}`;
    params.push(limit);

    const result = await db.query(query, params);
    return result.rows;
  }

  static async clearTemplates(personType, personId) {
    const table = personType === 'teacher' ? 'Teachers' : 'Users';
    await db.query(`UPDATE "${table}" SET fingerprint_template = NULL WHERE id = $1`, [personId]);
    return { success: true };
  }

  static async verifyWithScanner(scanner, template) {
    // Get all templates from DB
    const tables = [
      { name: 'Teachers', type: 'teacher' },
      { name: 'Users', type: 'student' }
    ];

    for (const { name, type } of tables) {
      const result = await db.query(
        `SELECT id, name, fingerprint_template FROM "${name}" WHERE fingerprint_template IS NOT NULL`
      );

      for (const row of result.rows) {
        // Use scanner's match function (requires ZK hardware)
        const matchResult = await scanner.matchTemplate(row.fingerprint_template);
        if (matchResult.matched && matchResult.score > 70) {
          return { matched: true, person_type: type, person_id: row.id, name: row.name, score: matchResult.score };
        }
      }
    }

    return { matched: false };
  }
}

module.exports = Fingerprint;
