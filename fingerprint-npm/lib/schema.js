/*
Schema for fingerprint system tables
Tables: Admins, Teachers, Users, FingerprintLogs, Parents, StudentParents, Subjects,
        StudentAudit, Timetable, TeacherSubjectAssignments, StudentSubjects, Settings,
        ExamResults, ExamTypes, PublishedExams
*/

const createAdminsTable = `
CREATE TABLE IF NOT EXISTS "Admins" (
  id SERIAL PRIMARY KEY,
  username VARCHAR(64) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);`;

const createTeachersTable = `
CREATE TABLE IF NOT EXISTS "Teachers" (
  id SERIAL PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  username VARCHAR(64) NOT NULL UNIQUE,
  email VARCHAR(128) NOT NULL UNIQUE,
  class VARCHAR(64) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  fingerprint_id INTEGER UNIQUE,
  fingerprint_template TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);`;

const createUsersTable = `
CREATE TABLE IF NOT EXISTS "Users" (
  id SERIAL PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  username VARCHAR(64) NOT NULL UNIQUE,
  password_hash VARCHAR(255),
  class VARCHAR(64) NOT NULL,
  fingerprint_id INTEGER UNIQUE,
  fingerprint_template TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);`;

const createFingerprintLogsTable = `
CREATE TABLE IF NOT EXISTS "FingerprintLogs" (
  id BIGSERIAL PRIMARY KEY,
  person_type TEXT NOT NULL CHECK (person_type IN ('student', 'teacher')),
  person_id INTEGER NOT NULL,
  log_type TEXT NOT NULL CHECK (log_type IN ('IN', 'OUT')),
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_logs_person ON FingerprintLogs (person_type, person_id, timestamp DESC);`;

const createParentsTable = `
CREATE TABLE IF NOT EXISTS "Parents" (
  id SERIAL PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  email VARCHAR(128) NOT NULL UNIQUE,
  phone VARCHAR(50),
  username VARCHAR(64) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);`;

const createStudentParentsTable = `
CREATE TABLE IF NOT EXISTS "StudentParents" (
  id SERIAL PRIMARY KEY,
  student_id INTEGER NOT NULL,
  parent_id INTEGER NOT NULL,
  relationship VARCHAR(50) DEFAULT 'Parent/Guardian',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (student_id) REFERENCES "Users"(id) ON DELETE CASCADE,
  FOREIGN KEY (parent_id) REFERENCES "Parents"(id) ON DELETE CASCADE,
  UNIQUE (student_id, parent_id)
);`;

const createSubjectsTable = `
CREATE TABLE IF NOT EXISTS "Subjects" (
  id SERIAL PRIMARY KEY,
  name VARCHAR(128) NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);`;

const createStudentAuditTable = `
CREATE TABLE IF NOT EXISTS "StudentAudit" (
  id SERIAL PRIMARY KEY,
  student_id INTEGER NOT NULL,
  subject_id INTEGER NOT NULL,
  status VARCHAR(20) DEFAULT 'Pending' CHECK (status IN ('Pending', 'Cleared', 'Not Cleared')),
  notes TEXT,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (student_id) REFERENCES "Users"(id) ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES "Subjects"(id) ON DELETE CASCADE,
  UNIQUE (student_id, subject_id)
);`;

const createTimetableTable = `
CREATE TABLE IF NOT EXISTS "Timetable" (
  id SERIAL PRIMARY KEY,
  class VARCHAR(64) NOT NULL,
  subject_id INTEGER NOT NULL,
  teacher_id INTEGER,
  day_of_week VARCHAR(20) NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (subject_id) REFERENCES "Subjects"(id) ON DELETE CASCADE,
  FOREIGN KEY (teacher_id) REFERENCES "Teachers"(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_timetable_class ON Timetable (class);`;

const createTeacherSubjectAssignmentsTable = `
CREATE TABLE IF NOT EXISTS "TeacherSubjectAssignments" (
  id SERIAL PRIMARY KEY,
  teacher_id INTEGER NOT NULL,
  subject_id INTEGER NOT NULL,
  class VARCHAR(64) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (teacher_id) REFERENCES "Teachers"(id) ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES "Subjects"(id) ON DELETE CASCADE,
  UNIQUE (teacher_id, subject_id, class)
);`;

const createStudentSubjectsTable = `
CREATE TABLE IF NOT EXISTS "StudentSubjects" (
  id SERIAL PRIMARY KEY,
  student_id INTEGER NOT NULL,
  subject_id INTEGER NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (student_id) REFERENCES "Users"(id) ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES "Subjects"(id) ON DELETE CASCADE,
  UNIQUE (student_id, subject_id)
);`;

const createSettingsTable = `
CREATE TABLE IF NOT EXISTS "Settings" (
  id SERIAL PRIMARY KEY,
  "key" VARCHAR(255) NOT NULL UNIQUE,
  "value" TEXT
);`;

const createExamResultsTable = `
CREATE TABLE IF NOT EXISTS "ExamResults" (
  id SERIAL PRIMARY KEY,
  student_id INTEGER NOT NULL,
  subject_id INTEGER NOT NULL,
  teacher_id INTEGER,
  exam_type VARCHAR(50) NOT NULL,
  term VARCHAR(20) NOT NULL,
  score DECIMAL(5,2) NOT NULL,
  max_score DECIMAL(5,2) DEFAULT 100.00,
  grade VARCHAR(5),
  remarks TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (student_id) REFERENCES "Users"(id) ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES "Subjects"(id) ON DELETE CASCADE,
  FOREIGN KEY (teacher_id) REFERENCES "Teachers"(id) ON DELETE SET NULL
);`;

const createExamTypesTable = `
CREATE TABLE IF NOT EXISTS "ExamTypes" (
  id SERIAL PRIMARY KEY,
  name VARCHAR(50) NOT NULL UNIQUE,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);`;

const createPublishedExamsTable = `
CREATE TABLE IF NOT EXISTS "PublishedExams" (
  id SERIAL PRIMARY KEY,
  term VARCHAR(20) NOT NULL,
  exam_type VARCHAR(50) NOT NULL,
  is_published BOOLEAN DEFAULT FALSE,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (term, exam_type)
);`;

const seedDefaultSettings = `
INSERT INTO Settings ("key", "value") VALUES
  ('send_days', '0,1,2,3,4'),
  ('send_time', '08:00'),
  ('last_report_sent_date', NULL),
  ('fingerprint_listener_enabled', '1')
ON CONFLICT ("key") DO UPDATE SET "key" = EXCLUDED."key";`;

const seedDefaultExamTypes = `
INSERT INTO ExamTypes (name) VALUES
  ('Mid Term'), ('End of Term'), ('Mock'), ('Final')
ON CONFLICT (name) DO NOTHING;`;

module.exports = {
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
  createPublishedExamsTable,
  seedDefaultSettings,
  seedDefaultExamTypes
};
