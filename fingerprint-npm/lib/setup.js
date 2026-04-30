const db = require('./db');
const { createAdminsTable, createTeachersTable, createUsersTable, createFingerprintLogsTable, createParentsTable, createStudentParentsTable, createSubjectsTable, createStudentAuditTable, createTimetableTable, createTeacherSubjectAssignmentsTable, createStudentSubjectsTable, createSettingsTable, createExamResultsTable, createExamTypesTable, createPublishedExamsTable, seedDefaultSettings, seedDefaultExamTypes } = require('./schema');

async function initializeDatabase() {
  const ora = require('ora');
  const spinner = ora();

  try {
    spinner.start('Connecting to database...');
    await db.connect();

    spinner.start('Creating tables...');
    const queries = [
      createAdminsTable,
      createTeachersTable,
      createUsersTable,
      createFingerprintLogsTable,
      createParentsTable,
      createStudentParentsTable,
      createSubjectsTable,
      createStudentAuditTable,
      createTimetableTable,
      createTeacherSubjectAssignmentsTable,
      createStudentSubjectsTable,
      createSettingsTable,
      createExamResultsTable,
      createExamTypesTable,
      createPublishedExamsTable
    ];

    for (const query of queries) {
      await db.query(query);
    }

    spinner.start('Seeding default data...');
    await db.query(seedDefaultSettings);
    await db.query(seedDefaultExamTypes);

    spinner.succeed('Database initialized successfully');
    return true;
  } catch (error) {
    spinner.fail(`Database initialization failed: ${error.message}`);
    return false;
  }
}

module.exports = { initializeDatabase };
