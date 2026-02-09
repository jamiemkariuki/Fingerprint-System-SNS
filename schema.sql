-- The database name is managed by docker-compose environment variables (MYSQL_DATABASE)


-- Admins Table
CREATE TABLE IF NOT EXISTS `Admins` (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_admin_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Teachers Table
CREATE TABLE IF NOT EXISTS `Teachers` (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(128) NOT NULL,
  username VARCHAR(64) NOT NULL,
  email VARCHAR(128) NOT NULL,
  class VARCHAR(64) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  fingerprint_id INT UNSIGNED NULL, -- Kept for legacy compatible (optional)
  fingerprint_template BLOB NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_teacher_username (username),
  UNIQUE KEY uniq_teacher_email (email),
  UNIQUE KEY uniq_teacher_fingerprint_id (fingerprint_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Users (Students)
CREATE TABLE IF NOT EXISTS `Users` (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(128) NOT NULL,
  username VARCHAR(64) NOT NULL,
  password_hash VARCHAR(255) NULL,
  class VARCHAR(64) NOT NULL,
  fingerprint_id INT UNSIGNED NULL,
  fingerprint_template BLOB NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_user_username (username),
  KEY idx_users_class (class),
  UNIQUE KEY uniq_user_fingerprint_id (fingerprint_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Fingerprint Logs
CREATE TABLE IF NOT EXISTS `FingerprintLogs` (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  person_type ENUM('student','teacher') NOT NULL,
  person_id INT UNSIGNED NOT NULL,
  log_type ENUM('IN', 'OUT') NOT NULL DEFAULT 'IN',
  timestamp DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_logs_person_day (person_type, person_id, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Parents Table
CREATE TABLE IF NOT EXISTS `Parents` (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(128) NOT NULL,
  email VARCHAR(128) NOT NULL,
  phone VARCHAR(50),
  username VARCHAR(64) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_parent_username (username),
  UNIQUE KEY uniq_parent_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Student-Parent Relationship Table
CREATE TABLE IF NOT EXISTS `StudentParents` (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  student_id INT UNSIGNED NOT NULL,
  parent_id INT UNSIGNED NOT NULL,
  relationship VARCHAR(50) DEFAULT 'Parent/Guardian',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  FOREIGN KEY (student_id) REFERENCES `Users`(id) ON DELETE CASCADE,
  FOREIGN KEY (parent_id) REFERENCES `Parents`(id) ON DELETE CASCADE,
  UNIQUE KEY uniq_student_parent (student_id, parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Subjects Table
CREATE TABLE IF NOT EXISTS `Subjects` (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(128) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_subject_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Student Audit Table (Subject Clearance)
CREATE TABLE IF NOT EXISTS `StudentAudit` (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  student_id INT UNSIGNED NOT NULL,
  subject_id INT UNSIGNED NOT NULL,
  status ENUM('Pending', 'Cleared', 'Not Cleared') DEFAULT 'Pending',
  notes TEXT,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  FOREIGN KEY (student_id) REFERENCES `Users`(id) ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES `Subjects`(id) ON DELETE CASCADE,
  UNIQUE KEY uniq_student_subject (student_id, subject_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Timetable Table
CREATE TABLE IF NOT EXISTS `Timetable` (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  class VARCHAR(64) NOT NULL,
  subject_id INT UNSIGNED NOT NULL,
  teacher_id INT UNSIGNED,
  day_of_week VARCHAR(20) NOT NULL, -- Monday, Tuesday, etc.
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  FOREIGN KEY (subject_id) REFERENCES `Subjects`(id) ON DELETE CASCADE,
  FOREIGN KEY (teacher_id) REFERENCES `Teachers`(id) ON DELETE SET NULL,
  KEY idx_timetable_class (class)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Teacher Subject Assignments Table (Admin assigns subjects+classes to teachers)
CREATE TABLE IF NOT EXISTS `TeacherSubjectAssignments` (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  teacher_id INT UNSIGNED NOT NULL,
  subject_id INT UNSIGNED NOT NULL,
  class VARCHAR(64) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  FOREIGN KEY (teacher_id) REFERENCES `Teachers`(id) ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES `Subjects`(id) ON DELETE CASCADE,
  UNIQUE KEY uniq_teacher_subject_class (teacher_id, subject_id, class)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Student Subject Enrollment Table
CREATE TABLE IF NOT EXISTS `StudentSubjects` (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  student_id INT UNSIGNED NOT NULL,
  subject_id INT UNSIGNED NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  FOREIGN KEY (student_id) REFERENCES `Users`(id) ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES `Subjects`(id) ON DELETE CASCADE,
  UNIQUE KEY uniq_student_subject_enroll (student_id, subject_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Settings Table
CREATE TABLE IF NOT EXISTS `Settings` (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `key` VARCHAR(255) NOT NULL,
  `value` TEXT,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_setting_key (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Exam Results Table
CREATE TABLE IF NOT EXISTS `ExamResults` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `student_id` INT UNSIGNED NOT NULL,
  `subject_id` INT UNSIGNED NOT NULL,
  `teacher_id` INT UNSIGNED,
  `exam_type` VARCHAR(50) NOT NULL, -- e.g., 'Midterm', 'Final', 'Quiz'
  `term` VARCHAR(20) NOT NULL,      -- e.g., 'Term 1', 'Term 2'
  `score` DECIMAL(5,2) NOT NULL,
  `max_score` DECIMAL(5,2) DEFAULT 100.00,
  `grade` VARCHAR(5) DEFAULT NULL,
  `remarks` TEXT,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`student_id`) REFERENCES `Users`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`subject_id`) REFERENCES `Subjects`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`teacher_id`) REFERENCES `Teachers`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Exam Types Table (Dynamic exam type management)
CREATE TABLE IF NOT EXISTS `ExamTypes` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(50) NOT NULL UNIQUE,
  `is_active` BOOLEAN DEFAULT TRUE,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Published Exams Table (Controls result visibility)
CREATE TABLE IF NOT EXISTS `PublishedExams` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `term` VARCHAR(20) NOT NULL,
  `exam_type` VARCHAR(50) NOT NULL,
  `is_published` BOOLEAN DEFAULT FALSE,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `unique_exam_publish` (`term`, `exam_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert default settings
INSERT INTO Settings (`key`, `value`)
VALUES 
('send_days', '0,1,2,3,4'),
('send_time', '08:00'),
('last_report_sent_date', NULL),
('fingerprint_listener_enabled', '1')
ON DUPLICATE KEY UPDATE `key`=`key`;

-- Insert default exam types
INSERT INTO ExamTypes (`name`) VALUES 
('Mid Term'), ('End of Term'), ('Mock'), ('Final')
ON DUPLICATE KEY UPDATE `name`=`name`;

