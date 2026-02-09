from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import bcrypt
import mysql.connector
from ..database import get_db
from ..utils.common import _get_student_attendance_status
from ..utils.email import generate_and_send_reports
import logging

logger = logging.getLogger(__name__)

# Admin blueprint
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
def admin_dashboard():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    today = datetime.today().date()

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Core data
        cursor.execute("SELECT * FROM Teachers")
        teachers = cursor.fetchall()

        cursor.execute("SELECT * FROM Users")
        users = cursor.fetchall()

        for user in users:
            user["status"] = _get_student_attendance_status(cursor, user["id"], today)

        cursor.execute("SELECT `value` FROM Settings WHERE `key` = 'send_days'")
        send_days_setting = cursor.fetchone()
        send_days = send_days_setting['value'].split(',') if send_days_setting else []

        cursor.execute("SELECT `value` FROM `Settings` WHERE `key` = 'fingerprint_listener_enabled'")
        listener_setting = cursor.fetchone()
        listener_enabled = listener_setting['value'] == '1' if listener_setting else True

        cursor.execute("SELECT `value` FROM Settings WHERE `key` = 'send_time'")
        send_time_setting = cursor.fetchone()
        send_time = send_time_setting['value'] if send_time_setting else '08:00'

        cursor.execute("SELECT * FROM Parents ORDER BY name")
        parents = cursor.fetchall()

        cursor.execute("""
            SELECT sp.id, sp.relationship, u.name as student_name, p.name as parent_name
            FROM StudentParents sp
            JOIN Users u ON sp.student_id = u.id
            JOIN Parents p ON sp.parent_id = p.id
            ORDER BY u.name
        """)
        student_parent_links = cursor.fetchall()

        cursor.execute("SELECT * FROM Subjects ORDER BY name")
        subjects = cursor.fetchall()

        cursor.execute("SELECT * FROM ExamTypes ORDER BY created_at DESC")
        exam_types = cursor.fetchall()

        # Fetch unique Exam Sets (Term + Type) and their publish status
        cursor.execute("""
            SELECT DISTINCT er.term, er.exam_type, 
                   COALESCE(pe.is_published, 0) as is_published
            FROM ExamResults er
            LEFT JOIN PublishedExams pe ON er.term = pe.term AND er.exam_type = pe.exam_type
            ORDER BY er.term DESC, er.exam_type ASC
        """)
        exam_publishing_list = cursor.fetchall()

        cursor.execute("""
            SELECT ss.id, u.name as student_name, s.name as subject_name, u.id as student_id, s.id as subject_id
            FROM StudentSubjects ss
            JOIN Users u ON ss.student_id = u.id
            JOIN Subjects s ON ss.subject_id = s.id
            ORDER BY u.name
        """)
        student_subject_links = cursor.fetchall()

        cursor.execute("""
            SELECT sa.id, u.name as student_name, s.name as subject_name, sa.status, sa.notes
            FROM StudentAudit sa
            JOIN Users u ON sa.student_id = u.id
            JOIN Subjects s ON sa.subject_id = s.id
            ORDER BY u.name
        """)
        audit_links = cursor.fetchall()

        # Metrics for overview bar
        student_count = len(users)
        teacher_count = len(teachers)
        subject_count = len(subjects)
        audit_count = len(audit_links)

        cursor.execute("SELECT COUNT(*) as cnt FROM StudentAudit")
        total_audit = cursor.fetchone().get("cnt", 0)
        cursor.execute("SELECT COUNT(*) as cnt FROM StudentAudit WHERE status = 'Pending'")
        pending_count = cursor.fetchone().get("cnt", 0)

        # Fetch Timetables
        cursor.execute("""
            SELECT t.id, t.class, s.name as subject_name, t.subject_id, t.teacher_id, te.name as teacher_name, t.day_of_week, t.start_time, t.end_time
            FROM Timetable t
            JOIN Subjects s ON t.subject_id = s.id
            LEFT JOIN Teachers te ON t.teacher_id = te.id
            ORDER BY t.class, FIELD(t.day_of_week, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'), t.start_time
        """)
        timetables = cursor.fetchall()

        # Fetch Teacher Subject Assignments
        cursor.execute("""
            SELECT tsa.id, te.name as teacher_name, s.name as subject_name, tsa.class, tsa.teacher_id, tsa.subject_id
            FROM TeacherSubjectAssignments tsa
            JOIN Teachers te ON tsa.teacher_id = te.id
            JOIN Subjects s ON tsa.subject_id = s.id
            ORDER BY te.name
        """)
        teacher_assignments = cursor.fetchall()

        # Fetch Exam Results
        cursor.execute("""
            SELECT er.id, u.name as student_name, s.name as subject_name, te.name as teacher_name, 
                   er.exam_type, er.term, er.score, er.max_score, er.grade, er.remarks, 
                   er.student_id, er.subject_id, er.teacher_id
            FROM ExamResults er
            JOIN Users u ON er.student_id = u.id
            JOIN Subjects s ON er.subject_id = s.id
            LEFT JOIN Teachers te ON er.teacher_id = te.id
            ORDER BY u.name, er.term, er.exam_type
        """)
        exam_results = cursor.fetchall()

        return render_template(
            "admin_dashboard.html",
            teachers=teachers,
            users=users,
            parents=parents,
            student_parent_links=student_parent_links,
            student_subject_links=student_subject_links,
            subjects=subjects,
            audit_links=audit_links,
            timetables=timetables,
            teacher_assignments=teacher_assignments,
            exam_results=exam_results,
            send_days=send_days,
            send_time=send_time,
            listener_enabled=listener_enabled,
            student_count=student_count,
            teacher_count=teacher_count,
            subject_count=subject_count,
            audit_count=audit_count,
            pending_count=pending_count,
            total_audit=total_audit,
            exam_types=exam_types,
            exam_publishing_list=exam_publishing_list
        )

    except mysql.connector.Error as e:
        logger.exception("MySQL Error on admin dashboard: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin.admin_dashboard"))
    except Exception as e:
        # Catch-all to avoid crashing the admin dashboard; log and show a friendly error
        logger.exception("Unhandled error on admin dashboard: %s", e)
        flash("An unexpected error occurred while loading the admin dashboard.", "error")
        return redirect(url_for("admin.admin_dashboard"))
    finally:
        if conn:
            conn.close()

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    return redirect(url_for("main.login"))

@admin_bp.route('/logout')
def admin_logout():
    session.pop("admin_id", None)
    return redirect(url_for("main.home"))

@admin_bp.route('/send_reports', methods=['POST'])
def send_reports():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    try:
        flash("Sending reports... This may take a moment.", "info")
        generate_and_send_reports()
        flash("Reports sent successfully!", "success")
    except Exception as e:
        logger.exception(f"Error sending reports: {e}")
        flash(f"An error occurred while sending the reports: {e}", "error")

    return redirect(url_for("admin.admin_dashboard"))

@admin_bp.route('/create_teacher', methods=['POST'])
def create_teacher():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    name = request.form.get("name")
    username = request.form.get("username")
    email = request.form.get("email")
    teacher_class = request.form.get("class")
    password = request.form.get("password")

    if not name or not username or not email or not teacher_class or not password:
        flash("Missing fields", "error")
        return redirect(url_for("admin.admin_dashboard"))

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Teachers (name, username, email, class, password_hash) VALUES (%s, %s, %s, %s, %s)",
            (name, username, email, teacher_class, password_hash)
        )
        conn.commit()
        flash("Teacher created successfully!", "success")
        return redirect(url_for("admin.admin_dashboard"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error creating teacher: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin.admin_dashboard"))
    finally:
        if conn:
            conn.close()

@admin_bp.route('/fingerprint_listener/toggle', methods=['POST'])
def toggle_fingerprint_listener():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT `value` FROM `Settings` WHERE `key` = 'fingerprint_listener_enabled'")
        setting = cursor.fetchone()

        new_value = '0'
        if setting is None or setting['value'] == '0':
            new_value = '1'

        cursor.execute(
            "INSERT INTO `Settings` (`key`, `value`) VALUES ('fingerprint_listener_enabled', %s) ON DUPLICATE KEY UPDATE `value` = %s",
            (new_value, new_value)
        )
        conn.commit()
        flash(f"Fingerprint listener {'enabled' if new_value == '1' else 'disabled'}!", "success")
    except mysql.connector.Error as e:
        logger.exception("MySQL Error toggling listener: %s", e)
        flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for("admin.admin_dashboard"))

@admin_bp.route('/save_settings', methods=['POST'])
def save_settings():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    send_days = request.form.getlist("send_days")
    send_days_str = ",".join(send_days)
    send_time = request.form.get("send_time", "08:00")

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Settings (`key`, `value`) VALUES ('send_days', %s) ON DUPLICATE KEY UPDATE `value` = %s", (send_days_str, send_days_str))
        cursor.execute("INSERT INTO Settings (`key`, `value`) VALUES ('send_time', %s) ON DUPLICATE KEY UPDATE `value` = %s", (send_time, send_time))
        conn.commit()
        flash("Settings saved successfully!", "success")
    except mysql.connector.Error as e:
        logger.exception("MySQL Error saving settings: %s", e)
        flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for("admin.admin_dashboard"))

@admin_bp.route('/delete/student/<int:user_id>', methods=['POST'])
def delete_student(user_id):
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT fingerprint_id FROM Users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        if user and user["fingerprint_id"]:
            fid = user["fingerprint_id"]
            try:
                from ..hardware.fingerprint import finger
                if finger and finger.delete_model(fid) == 0:
                    logger.info("Fingerprint ID %s deleted from sensor.", fid)
            except Exception as e:
                logger.warning("Could not delete fingerprint from sensor: %s", e)

        cursor.execute("DELETE FROM Users WHERE id = %s", (user_id,))
        conn.commit()
        flash("Student deleted successfully!", "success")
        return redirect(url_for("admin.admin_dashboard"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error deleting student: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin.admin_dashboard"))
    finally:
        if conn:
            conn.close()

@admin_bp.route('/delete/teacher/<int:teacher_id>', methods=['POST'])
def delete_teacher(teacher_id):
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT fingerprint_id FROM Teachers WHERE id = %s", (teacher_id,))
        teacher = cursor.fetchone()

        if teacher and teacher["fingerprint_id"]:
            fid = teacher["fingerprint_id"]
            try:
                from ..hardware.fingerprint import finger
                if finger and finger.delete_model(fid) == 0:
                    logger.info("Fingerprint ID %s deleted from sensor.", fid)
            except Exception as e:
                logger.warning("Could not delete fingerprint from sensor: %s", e)

        cursor.execute("DELETE FROM Teachers WHERE id = %s", (teacher_id,))
        conn.commit()
        flash("Teacher deleted successfully!", "success")
        return redirect(url_for("admin.admin_dashboard"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error deleting teacher: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin.admin_dashboard"))
    finally:
        if conn:
            conn.close()

@admin_bp.route('/manage_subjects', methods=['POST'])
def manage_subjects():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))
    
    name = request.form.get("name")
    action = request.form.get("action", "add")
    subject_id = request.form.get("subject_id")

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        if action == "add" and name:
            cursor.execute("INSERT INTO Subjects (name) VALUES (%s)", (name,))
            flash(f"Subject '{name}' added.", "success")
        elif action == "delete" and subject_id:
            cursor.execute("DELETE FROM Subjects WHERE id = %s", (subject_id,))
            flash("Subject deleted.", "success")
        conn.commit()
    except mysql.connector.Error as e:
        logger.exception("MySQL Error managing subjects: %s", e)
        flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()
    return redirect(url_for("admin.admin_dashboard"))

@admin_bp.route('/link_subject', methods=['POST'])
def link_subject():
    if "admin_id" not in session and "teacher_id" not in session:
        return redirect(url_for("admin.admin_login"))
    
    student_id = request.form.get("student_id")
    subject_id = request.form.get("subject_id")

    if not student_id or not subject_id:
        flash("Student and Subject are required.", "error")
        return redirect(request.referrer or url_for("admin.admin_dashboard"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        if "teacher_id" in session:
            teacher_id = session["teacher_id"]
            cursor.execute("SELECT class FROM Users WHERE id = %s", (student_id,))
            student = cursor.fetchone()
            if not student:
                flash("Student not found.", "error")
                return redirect(request.referrer or url_for("teacher.teacher_dashboard"))

            # GLOBAL SUBJECT AUTHORITY: Authorized if:
            # 1. They teach this SUBJECT (to any class)
            # 2. OR they are authorized for the STUDENT'S class
            cursor.execute("""
                SELECT id FROM Teachers WHERE id = %s AND class = %s
                UNION
                SELECT teacher_id FROM TeacherSubjectAssignments WHERE teacher_id = %s AND class = %s
                UNION
                SELECT teacher_id FROM TeacherSubjectAssignments WHERE teacher_id = %s AND subject_id = %s
            """, (teacher_id, student['class'], teacher_id, student['class'], teacher_id, subject_id))
            if not cursor.fetchone():
                flash("You are not authorized to manage this subject for this student. You must either teach this subject or manage the student's class.", "error")
                return redirect(request.referrer or url_for("teacher.teacher_dashboard"))

        cursor.execute("INSERT INTO StudentSubjects (student_id, subject_id) VALUES (%s, %s)", (student_id, subject_id))
        conn.commit()
        flash("Student linked to subject successfully.", "success")
    except mysql.connector.Error as e:
        if "Duplicate entry" in str(e):
            flash("Student is already linked to this subject.", "warning")
        else:
            logger.exception("Error linking subject: %s", e)
            flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()
    
    return redirect(request.referrer or url_for("admin.admin_dashboard"))

@admin_bp.route('/unlink_subject', methods=['POST'])
def unlink_subject():
    if "admin_id" not in session and "teacher_id" not in session:
        return redirect(url_for("admin.admin_login"))
    
    student_id = request.form.get("student_id")
    subject_id = request.form.get("subject_id")

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        if "teacher_id" in session:
            teacher_id = session["teacher_id"]
            cursor.execute("SELECT class FROM Users WHERE id = %s", (student_id,))
            student = cursor.fetchone()
            
            # GLOBAL SUBJECT AUTHORITY
            cursor.execute("""
                SELECT id FROM Teachers WHERE id = %s AND class = %s
                UNION
                SELECT teacher_id FROM TeacherSubjectAssignments WHERE teacher_id = %s AND class = %s
                UNION
                SELECT teacher_id FROM TeacherSubjectAssignments WHERE teacher_id = %s AND subject_id = %s
            """, (teacher_id, student['class'], teacher_id, student['class'], teacher_id, subject_id))
            if not cursor.fetchone():
                flash("Unauthorized.", "error")
                return redirect(request.referrer or url_for("teacher.teacher_dashboard"))

        # Manually delete audit as well since StudentAudit doesn't FK to StudentSubjects
        cursor.execute("DELETE FROM StudentAudit WHERE student_id = %s AND subject_id = %s", (student_id, subject_id))
        cursor.execute("DELETE FROM StudentSubjects WHERE student_id = %s AND subject_id = %s", (student_id, subject_id))
        conn.commit()
        flash("Student unlinked from subject and associated audit removed.", "success")
    except mysql.connector.Error as e:
        logger.exception("Error unlinking subject: %s", e)
        flash("Database error.", "error")
    finally:
        if conn:
            conn.close()
    return redirect(request.referrer or url_for("admin.admin_dashboard"))

@admin_bp.route('/create_audit', methods=['POST'])
def create_audit():
    if "admin_id" not in session and "teacher_id" not in session:
        return redirect(url_for("admin.admin_login"))
    
    student_id = request.form.get("student_id")
    subject_id = request.form.get("subject_id")

    if not student_id or not subject_id:
        flash("Student and Subject are required.", "error")
        return redirect(request.referrer or url_for("admin.admin_dashboard"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # SECURITY CHECK FOR TEACHERS
        if "teacher_id" in session:
            teacher_id = session["teacher_id"]
            
            # Fetch student's class and teacher's home class
            cursor.execute("""
                SELECT u.class as student_class, t.class as teacher_home_class
                FROM Users u
                CROSS JOIN Teachers t ON t.id = %s
                WHERE u.id = %s
            """, (teacher_id, student_id))
            info = cursor.fetchone()
            
            if not info:
                flash("Information not found.", "error")
                return redirect(request.referrer or url_for("teacher.teacher_dashboard"))

            authorized = False
            # GLOBAL SUBJECT AUTHORITY
            cursor.execute("""
                SELECT id FROM Teachers WHERE id = %s AND class = %s
                UNION
                SELECT teacher_id FROM TeacherSubjectAssignments WHERE teacher_id = %s AND class = %s
                UNION
                SELECT teacher_id FROM TeacherSubjectAssignments WHERE teacher_id = %s AND subject_id = %s
            """, (teacher_id, info['student_class'], teacher_id, info['student_class'], teacher_id, subject_id))
            if cursor.fetchone():
                authorized = True
            
            if not authorized:
                flash("You are not authorized to initialize audits for this student. You must either teach this subject or manage the student's class.", "error")
                return redirect(request.referrer or url_for("teacher.teacher_dashboard"))

        # VERIFY ENROLLMENT FIRST
        cursor.execute("SELECT id FROM StudentSubjects WHERE student_id = %s AND subject_id = %s", (student_id, subject_id))
        if not cursor.fetchone():
            flash("Student must be enrolled (linked) in the subject before creating an audit.", "error")
            return redirect(request.referrer or url_for("admin.admin_dashboard"))

        cursor.execute("INSERT INTO StudentAudit (student_id, subject_id) VALUES (%s, %s)", (student_id, subject_id))
        conn.commit()
        flash("Clearance audit initialized.", "success")
    except mysql.connector.Error as e:
        if "Duplicate entry" in str(e):
            flash("This subject is already assigned to this student.", "warning")
        else:
            logger.exception("MySQL Error assigning subject: %s", e)
            flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()
    
    return redirect(request.referrer or url_for("admin.admin_dashboard"))

@admin_bp.route('/delete_audit', methods=['POST'])
def delete_audit():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))
    
    audit_id = request.form.get("audit_id")
    if not audit_id:
        flash("Audit ID is required.", "error")
        return redirect(request.referrer or url_for("admin.admin_dashboard"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM StudentAudit WHERE id = %s", (audit_id,))
        conn.commit()
        flash("Audit record deleted successfully!", "success")
    except mysql.connector.Error as e:
        logger.exception("MySQL Error deleting audit (admin): %s", e)
        flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()
    
    return redirect(request.referrer or url_for("admin.admin_dashboard"))


@admin_bp.route('/create_parent', methods=['POST'])
def create_parent():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    name = request.form.get("name")
    username = request.form.get("username")
    email = request.form.get("email")
    phone = request.form.get("phone", "")
    password = request.form.get("password")

    if not name or not username or not email or not password:
        flash("Missing required fields", "error")
        return redirect(url_for("admin.admin_dashboard"))

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Parents (name, username, email, phone, password_hash) VALUES (%s, %s, %s, %s, %s)",
            (name, username, email, phone, password_hash)
        )
        conn.commit()
        flash(f"Parent account created successfully! Username: {username}", "success")
        return redirect(url_for("admin.admin_dashboard"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error creating parent: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin.admin_dashboard"))
    finally:
        if conn:
            conn.close()

@admin_bp.route('/link_student_parent', methods=['POST'])
def link_student_parent():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    student_id = request.form.get("student_id")
    parent_id = request.form.get("parent_id")
    relationship = request.form.get("relationship", "Parent/Guardian")

    if not student_id or not parent_id:
        flash("Missing student or parent", "error")
        return redirect(url_for("admin.admin_dashboard"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO StudentParents (student_id, parent_id, relationship) VALUES (%s, %s, %s)",
            (student_id, parent_id, relationship)
        )
        conn.commit()
        flash("Student linked to parent successfully!", "success")
        return redirect(url_for("admin.admin_dashboard"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error linking student to parent: %s", e)
        if "Duplicate entry" in str(e):
            flash("This student is already linked to this parent.", "warning")
        else:
            flash(f"Database error: {e}", "error")
        return redirect(url_for("admin.admin_dashboard"))
    finally:
        if conn:
            conn.close()

@admin_bp.route('/unlink_student_parent/<int:link_id>', methods=['POST'])
def unlink_student_parent(link_id):
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM StudentParents WHERE id = %s", (link_id,))
        conn.commit()
        flash("Student-parent link removed successfully!", "success")
        return redirect(url_for("admin.admin_dashboard"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error unlinking student from parent: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin.admin_dashboard"))
    finally:
        if conn:
            conn.close()

@admin_bp.route('/manage_timetable', methods=['POST'])
def manage_timetable():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    action = request.form.get("action", "add")
    
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        if action == "add":
            class_name = request.form.get("class")
            subject_id = request.form.get("subject_id")
            teacher_id = request.form.get("teacher_id")
            day_of_week = request.form.get("day_of_week")
            start_time = request.form.get("start_time")
            end_time = request.form.get("end_time")

            if class_name and subject_id and day_of_week and start_time and end_time:
                # Handle empty teacher_id (None if not provided)
                t_id = teacher_id if teacher_id and teacher_id.strip() else None
                cursor.execute(
                    "INSERT INTO Timetable (class, subject_id, teacher_id, day_of_week, start_time, end_time) VALUES (%s, %s, %s, %s, %s, %s)",
                    (class_name, subject_id, t_id, day_of_week, start_time, end_time)
                )
                flash("Timetable entry added successfully.", "success")
            else:
                flash("Missing required fields.", "error")

        elif action == "update":
            timetable_id = request.form.get("timetable_id")
            class_name = request.form.get("class")
            subject_id = request.form.get("subject_id")
            teacher_id = request.form.get("teacher_id")
            day_of_week = request.form.get("day_of_week")
            start_time = request.form.get("start_time")
            end_time = request.form.get("end_time")

            if timetable_id and class_name and subject_id and day_of_week and start_time and end_time:
                t_id = teacher_id if teacher_id and teacher_id.strip() else None
                cursor.execute("""
                    UPDATE Timetable 
                    SET class = %s, subject_id = %s, teacher_id = %s, day_of_week = %s, start_time = %s, end_time = %s
                    WHERE id = %s
                """, (class_name, subject_id, t_id, day_of_week, start_time, end_time, timetable_id))
                flash("Timetable entry updated successfully.", "success")
            else:
                flash("Missing required fields for update.", "error")

        elif action == "delete":
            timetable_id = request.form.get("timetable_id")
            if timetable_id:
                cursor.execute("DELETE FROM Timetable WHERE id = %s", (timetable_id,))
                flash("Timetable entry deleted.", "success")

        conn.commit()
    except mysql.connector.Error as e:
        logger.exception("MySQL Error managing timetable: %s", e)
        flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for("admin.admin_dashboard"))

@admin_bp.route('/assign_teacher_subject', methods=['POST'])
def assign_teacher_subject():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    teacher_id = request.form.get("teacher_id")
    subject_id = request.form.get("subject_id")
    class_name = request.form.get("class")

    if not teacher_id or not subject_id or not class_name:
        flash("Teacher, Subject, and Class are required.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO TeacherSubjectAssignments (teacher_id, subject_id, class) VALUES (%s, %s, %s)",
            (teacher_id, subject_id, class_name)
        )
        conn.commit()
        flash("Subject assigned to teacher successfully!", "success")
    except mysql.connector.Error as e:
        if "Duplicate entry" in str(e):
            flash("This teacher already has this subject assigned for this class.", "warning")
        else:
            logger.exception("MySQL Error assigning teacher subject: %s", e)
            flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for("admin.admin_dashboard"))

@admin_bp.route('/unassign_teacher_subject/<int:assignment_id>', methods=['POST'])
def unassign_teacher_subject(assignment_id):
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM TeacherSubjectAssignments WHERE id = %s", (assignment_id,))
        conn.commit()
        flash("Teacher subject assignment removed.", "success")
    except mysql.connector.Error as e:
        logger.exception("MySQL Error unassigning teacher subject: %s", e)
        flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for("admin.admin_dashboard"))

@admin_bp.route('/manage_exam_results', methods=['POST'])
def manage_exam_results():
    if "admin_id" not in session and "teacher_id" not in session:
        return redirect(url_for("admin.admin_login"))

    action = request.form.get("action")
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        if action == "add" or action == "update":
            student_id = request.form.get("student_id")
            subject_id = request.form.get("subject_id")
            teacher_id = request.form.get("teacher_id") or None
            exam_type = request.form.get("exam_type")
            term = request.form.get("term")
            score = request.form.get("score")
            max_score = request.form.get("max_score", 100)
            grade = request.form.get("grade")
            remarks = request.form.get("remarks")

            if action == "add":
                cursor.execute("""
                    INSERT INTO ExamResults (student_id, subject_id, teacher_id, exam_type, term, score, max_score, grade, remarks)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (student_id, subject_id, teacher_id, exam_type, term, score, max_score, grade, remarks))
            else:
                res_id = request.form.get("result_id")
                cursor.execute("""
                    UPDATE ExamResults 
                    SET student_id=%s, subject_id=%s, teacher_id=%s, exam_type=%s, term=%s, score=%s, max_score=%s, grade=%s, remarks=%s
                    WHERE id=%s
                """, (student_id, subject_id, teacher_id, exam_type, term, score, max_score, grade, remarks, res_id))
            
            conn.commit()
            flash(f"Exam result {'added' if action == 'add' else 'updated'} successfully.", "success")

        elif action == "delete":
            res_id = request.form.get("result_id")
            cursor.execute("DELETE FROM ExamResults WHERE id = %s", (res_id,))
            conn.commit()
            flash("Exam result deleted successfully.", "success")

    except mysql.connector.Error as e:
        logger.exception("Error managing exam results: %s", e)
        flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(request.referrer or url_for("admin.admin_dashboard"))

@admin_bp.route('/manage_exam_types', methods=['POST'])
def manage_exam_types():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    action = request.form.get("action")
    logger.info(f"manage_exam_types called with action: {action}")
    
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        if action == "add":
            name = request.form.get("name")
            if not name:
                flash("Exam type name is required", "error")
            else:
                try:
                    cursor.execute("INSERT INTO ExamTypes (name) VALUES (%s)", (name,))
                    conn.commit()
                    flash(f"Exam type '{name}' added successfully", "success")
                except mysql.connector.Error as err:
                    if err.errno == 1062: # Duplicate entry
                         flash(f"Exam type '{name}' already exists", "error")
                    else:
                        flash(f"Error adding exam type: {err}", "error")

        elif action == "toggle":
            type_id = request.form.get("type_id")
            current_status = request.form.get("current_status")
            new_status = 0 if current_status == '1' else 1
            
            cursor.execute("UPDATE ExamTypes SET is_active = %s WHERE id = %s", (new_status, type_id))
            conn.commit()
            flash("Exam type status updated", "success")

    except mysql.connector.Error as e:
        logger.exception("MySQL Error managing exam types: %s", e)
        flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/manage_publishing', methods=['POST'])
def manage_publishing():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    term = request.form.get("term")
    exam_type = request.form.get("exam_type")
    logger.info(f"manage_publishing called for term: {term}, type: {exam_type}")
    
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Check if record exists
        cursor.execute("SELECT id, is_published FROM PublishedExams WHERE term = %s AND exam_type = %s", (term, exam_type))
        record = cursor.fetchone()

        if record:
            # Toggle
            new_status = 0 if record[1] == 1 else 1
            cursor.execute("UPDATE PublishedExams SET is_published = %s WHERE id = %s", (new_status, record[0]))
        else:
            # Create as Published (since the user clicked "Publish")
            cursor.execute("INSERT INTO PublishedExams (term, exam_type, is_published) VALUES (%s, %s, 1)", (term, exam_type))
        
        conn.commit()
        flash(f"Updated status for {term} - {exam_type}", "success")

    except mysql.connector.Error as e:
        logger.exception("MySQL Error managing publishing: %s", e)
        flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for('admin.admin_dashboard'))
