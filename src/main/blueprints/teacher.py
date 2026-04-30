from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    Response,
)
from datetime import datetime, timedelta
import bcrypt

from ..database import get_db
from ..utils.common import _get_student_attendance_status
from ..utils.pdf import generate_attendance_pdf, generate_exam_results_pdf
import logging
from ..config import Config

logger = logging.getLogger(__name__)

teacher_bp = Blueprint("teacher", __name__)


@teacher_bp.route("/dashboard")
def teacher_dashboard():
    if "teacher_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    teacher_id = session["teacher_id"]
    today = datetime.today().date()

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get teacher info
        cursor.execute("SELECT * FROM Teachers WHERE id = %s", (teacher_id,))
        teacher = cursor.fetchone()

        # Get classes this teacher is assigned to for specific subjects
        cursor.execute(
            "SELECT tsa.subject_id, s.name as subject_name, tsa.class FROM TeacherSubjectAssignments tsa JOIN Subjects s ON tsa.subject_id = s.id WHERE tsa.teacher_id = %s",
            (teacher_id,),
        )
        teacher_assignments = cursor.fetchall()
        assigned_classes = list(set([row["class"] for row in teacher_assignments]))

        # Combine with home class
        all_relevant_classes = list(set([teacher["class"]] + assigned_classes))

        # GLOBAL SUBJECT AUTHORITY: If they teach a subject, they can link it to ANY student.
        # So we show all students if they have at least one assignment.
        if teacher_assignments or teacher["class"]:
            cursor.execute("SELECT * FROM Users ORDER BY name")
            users = cursor.fetchall()
        else:
            users = []

        for user in users:
            user["status"] = _get_student_attendance_status(cursor, user["id"], today)

        # Get parents
        cursor.execute("SELECT * FROM Parents ORDER BY name")
        parents = cursor.fetchall()

        # Get ALL subjects (for the "Assign Subject to Student" form)
        cursor.execute("SELECT * FROM Subjects ORDER BY name")
        all_subjects = cursor.fetchall()

        # Get Active Exam Types
        cursor.execute(
            "SELECT * FROM ExamTypes WHERE is_active = TRUE ORDER BY created_at DESC"
        )
        exam_types = cursor.fetchall()

        # Build query for audits this teacher can manage
        # 1. Global Subjects: Any student taking a subject this teacher is assigned to teach.
        # 2. Class Authority: Any student in a class the teacher is authorized for.
        cursor.execute(
            """
            SELECT sa.id, u.name as student_name, s.name as subject_name, sa.status, sa.notes
            FROM StudentAudit sa
            JOIN Users u ON sa.student_id = u.id
            JOIN Subjects s ON sa.subject_id = s.id
            WHERE 
                u.class = %s -- Home Class
                OR sa.subject_id IN (SELECT subject_id FROM TeacherSubjectAssignments WHERE teacher_id = %s)
                OR u.class IN (SELECT class FROM TeacherSubjectAssignments WHERE teacher_id = %s)
            ORDER BY u.name
        """,
            (teacher["class"], teacher_id, teacher_id),
        )
        audit_links = cursor.fetchall()

        # Get timetable for all relevant classes
        if all_relevant_classes:
            placeholders = ",".join(["%s"] * len(all_relevant_classes))
            cursor.execute(
                f"""
                SELECT t.id, t.class, s.name as subject_name, t.day_of_week, t.start_time, t.end_time, t.subject_id, t.teacher_id, te.name as teacher_name
                FROM Timetable t
                JOIN Subjects s ON t.subject_id = s.id
                LEFT JOIN Teachers te ON t.teacher_id = te.id
                WHERE t.class IN ({placeholders})
                ORDER BY t.class, CASE t.day_of_week WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 WHEN 'Sunday' THEN 7 ELSE 8 END, t.start_time
            """,
                tuple(all_relevant_classes),
            )
            timetables = cursor.fetchall()
        else:
            timetables = []

        # Get enrollment records (StudentSubjects) for students this teacher can manage
        cursor.execute(
            """
            SELECT ss.id, u.name as student_name, s.name as subject_name, u.id as student_id, s.id as subject_id
            FROM StudentSubjects ss
            JOIN Users u ON ss.student_id = u.id
            JOIN Subjects s ON ss.subject_id = s.id
            WHERE 
                u.class = %s -- Home Class
                OR ss.subject_id IN (SELECT subject_id FROM TeacherSubjectAssignments WHERE teacher_id = %s)
                OR u.class IN (SELECT class FROM TeacherSubjectAssignments WHERE teacher_id = %s)
            ORDER BY u.name
        """,
            (teacher["class"], teacher_id, teacher_id),
        )
        enrollment_links = cursor.fetchall()

        # Get Exam Results this teacher can manage
        cursor.execute(
            """
            SELECT er.id, u.name as student_name, s.name as subject_name, te.name as teacher_name, 
                   er.exam_type, er.term, er.score, er.max_score, er.grade, er.remarks, 
                   er.student_id, er.subject_id, er.teacher_id
            FROM ExamResults er
            JOIN Users u ON er.student_id = u.id
            JOIN Subjects s ON er.subject_id = s.id
            LEFT JOIN Teachers te ON er.teacher_id = te.id
            WHERE 
                u.class = %s -- Home Class
                OR er.subject_id IN (SELECT subject_id FROM TeacherSubjectAssignments WHERE teacher_id = %s)
                OR u.class IN (SELECT class FROM TeacherSubjectAssignments WHERE teacher_id = %s)
            ORDER BY u.name, er.term, er.exam_type
        """,
            (teacher["class"], teacher_id, teacher_id),
        )
        exam_results = cursor.fetchall()

        cursor.execute("SELECT id, name FROM Teachers ORDER BY name")
        teachers_list = cursor.fetchall()

        return render_template(
            "teacher_dashboard.html",
            teacher=teacher,
            users=users,
            parents=parents,
            subjects=all_subjects,
            audit_links=audit_links,
            enrollment_links=enrollment_links,
            timetables=timetables,
            teachers=teachers_list,
            exam_results=exam_results,
            exam_types=exam_types,
        )

    except Exception as e:
        logger.exception("MySQL Error on teacher dashboard: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("teacher.teacher_dashboard"))
    finally:
        if conn:
            conn.close()


@teacher_bp.route("/login", methods=["GET", "POST"])
def teacher_login():
    return redirect(url_for("main.login"))


@teacher_bp.route("/logout")
def teacher_logout():
    session.pop("teacher_id", None)
    session.pop("teacher_name", None)
    return redirect(url_for("main.home"))


@teacher_bp.route("/create_parent", methods=["POST"])
def create_parent():
    if "teacher_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    name = request.form.get("name")
    username = request.form.get("username")
    email = request.form.get("email")
    phone = request.form.get("phone", "")
    password = request.form.get("password")

    if not name or not username or not email or not password:
        flash("Missing required fields", "error")
        return redirect(url_for("teacher.teacher_dashboard"))

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Parents (name, username, email, phone, password_hash) VALUES (%s, %s, %s, %s, %s)",
            (name, username, email, phone, password_hash),
        )
        conn.commit()
        flash(f"Parent account created successfully! Username: {username}", "success")
        return redirect(url_for("teacher.teacher_dashboard"))
    except Exception as e:
        logger.exception("MySQL Error creating parent: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("teacher.teacher_dashboard"))
    finally:
        if conn:
            conn.close()


@teacher_bp.route("/create_student", methods=["POST"])
def create_student():
    if "teacher_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    name = request.form.get("name")
    username = request.form.get("username")
    class_ = request.form.get("class")
    password = request.form.get("password")
    fingerprint = request.form.get("fingerprint")  # '1' means enroll now

    if not name or not username or not class_ or not password:
        flash("Missing required fields", "error")
        return redirect(url_for("teacher.teacher_dashboard"))

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Users (name, username, class, password_hash) VALUES (%s, %s, %s, %s)",
            (name, username, class_, password_hash),
        )
        conn.commit()
        user_id = cursor.lastrowid
        flash(f"Student account created successfully! Username: {username}", "success")

        if fingerprint == "1":
            try:
                from ..hardware.fingerprint import enroll_fingerprint

                # Enrolls returns BYTES (the template) or None
                template_bytes = enroll_fingerprint()

                if template_bytes:
                    cursor.execute(
                        "UPDATE Users SET fingerprint_template = %s WHERE id = %s",
                        (template_bytes, user_id),
                    )
                    conn.commit()
                    flash("Fingerprint enrolled and saved to database.", "success")
                else:
                    flash("Fingerprint enrollment failed or timed out.", "warning")
            except Exception as e:
                logger.exception("Fingerprint enrollment error: %s", e)
                flash("Fingerprint enrollment failed: {}".format(e), "error")

        return redirect(url_for("teacher.teacher_dashboard"))
    except Exception as e:
        logger.exception("MySQL Error creating student: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("teacher.teacher_dashboard"))
    finally:
        if conn:
            conn.close()


@teacher_bp.route("/link_student_parent", methods=["POST"])
def link_student_parent():
    if "teacher_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    student_id = request.form.get("student_id")
    parent_id = request.form.get("parent_id")
    relationship = request.form.get("relationship", "Parent/Guardian")

    if not student_id or not parent_id:
        flash("Missing student or parent", "error")
        return redirect(url_for("teacher.teacher_dashboard"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO StudentParents (student_id, parent_id, relationship) VALUES (%s, %s, %s)",
            (student_id, parent_id, relationship),
        )
        conn.commit()
        flash("Student linked to parent successfully!", "success")
        return redirect(url_for("teacher.teacher_dashboard"))
    except Exception as e:
        logger.exception("MySQL Error linking student to parent: %s", e)
        if "Duplicate entry" in str(e):
            flash("This student is already linked to this parent.", "warning")
        else:
            flash(f"Database error: {e}", "error")
        return redirect(url_for("teacher.teacher_dashboard"))
    finally:
        if conn:
            conn.close()


@teacher_bp.route("/update_audit_status", methods=["POST"])
def update_audit_status():
    if "teacher_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    teacher_id = session["teacher_id"]
    audit_id = request.form.get("audit_id")
    status = request.form.get("status")
    notes = request.form.get("notes", "")

    if not audit_id or not status:
        flash("Audit ID and status are required.", "error")
        return redirect(url_for("teacher.teacher_dashboard"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # SECURITY CHECK: Verify teacher has authority over this audit
        # Must be in their home class OR assigned to this subject+class
        cursor.execute(
            """
            SELECT sa.subject_id, u.class as student_class, t.class as teacher_home_class
            FROM StudentAudit sa
            JOIN Users u ON sa.student_id = u.id
            CROSS JOIN Teachers t ON t.id = %s
            WHERE sa.id = %s
        """,
            (teacher_id, audit_id),
        )
        audit_info = cursor.fetchone()

        if not audit_info:
            flash("Audit record not found.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        authorized = False
        # GLOBAL SUBJECT AUTHORITY: Can update if it's "their subject" anywhere
        # OR if they have class-based authority over the student (already checked by existing logic flow)
        cursor.execute(
            """
            SELECT id FROM Teachers WHERE id = %s AND class = %s
            UNION
            SELECT teacher_id FROM TeacherSubjectAssignments WHERE teacher_id = %s AND class = %s
            UNION
            SELECT teacher_id FROM TeacherSubjectAssignments WHERE teacher_id = %s AND subject_id = %s
        """,
            (
                teacher_id,
                audit_info["student_class"],
                teacher_id,
                audit_info["student_class"],
                teacher_id,
                audit_info["subject_id"],
            ),
        )
        if cursor.fetchone():
            authorized = True

        if not authorized:
            flash(
                "You are not authorized to update this clearance status. You must be explicitly assigned to this subject and class.",
                "error",
            )
            return redirect(url_for("teacher.teacher_dashboard"))

        cursor.execute(
            "UPDATE StudentAudit SET status = %s, notes = %s WHERE id = %s",
            (status, notes, audit_id),
        )
        conn.commit()
        flash("Audit status updated successfully!", "success")
    except Exception as e:
        logger.exception("MySQL Error updating audit status: %s", e)
        flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for("teacher.teacher_dashboard"))


@teacher_bp.route("/delete_audit", methods=["POST"])
def delete_audit():
    if "teacher_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    teacher_id = session["teacher_id"]
    audit_id = request.form.get("audit_id")

    if not audit_id:
        flash("Audit ID is required.", "error")
        return redirect(url_for("teacher.teacher_dashboard"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # SECURITY CHECK: Verify teacher has authority over this audit
        cursor.execute(
            """
            SELECT sa.subject_id, u.class as student_class
            FROM StudentAudit sa
            JOIN Users u ON sa.student_id = u.id
            WHERE sa.id = %s
        """,
            (audit_id,),
        )
        audit_info = cursor.fetchone()

        if not audit_info:
            flash("Audit record not found.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        # Strict check: teacher must be assigned to this subject+class
        cursor.execute(
            """
            SELECT id FROM TeacherSubjectAssignments
            WHERE teacher_id = %s AND subject_id = %s AND class = %s
        """,
            (teacher_id, audit_info["subject_id"], audit_info["student_class"]),
        )

        if not cursor.fetchone():
            flash(
                "You are not authorized to delete this clearance record. You must be explicitly assigned to this subject and class.",
                "error",
            )
            return redirect(url_for("teacher.teacher_dashboard"))

        cursor.execute("DELETE FROM StudentAudit WHERE id = %s", (audit_id,))
        conn.commit()
        flash("Audit record deleted successfully!", "success")
    except Exception as e:
        logger.exception("MySQL Error deleting audit: %s", e)
        flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for("teacher.teacher_dashboard"))


@teacher_bp.route("/student_attendance_pdf/<int:student_id>")
def student_attendance_pdf(student_id):
    if (
        "teacher_id" not in session
        and "admin_id" not in session
        and "parent_id" not in session
    ):
        return redirect(url_for("teacher.teacher_login"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM Users WHERE id = %s", (student_id,))
        student = cursor.fetchone()
        if not student:
            flash("Student not found", "error")
            return redirect(request.referrer or url_for("main.home"))

        cutoff = datetime.now() - timedelta(days=30)
        # Get attendance logs for the last 30 days
        cursor.execute(
            """
            SELECT CAST(timestamp AS DATE) as date, COUNT(*) as scan_count,
                   MIN(CAST(timestamp AS TIME)) as first_scan, MAX(CAST(timestamp AS TIME)) as last_scan
            FROM FingerprintLogs
            WHERE person_type = 'student' AND person_id = %s
            AND timestamp >= %s
            GROUP BY CAST(timestamp AS DATE)
            ORDER BY date DESC
        """,
            (student_id, cutoff),
        )
        attendance_logs = cursor.fetchall()

        pdf_data = generate_attendance_pdf(student, attendance_logs)

        from flask import Response

        response = Response(pdf_data, mimetype="application/pdf")
        response.headers["Content-Disposition"] = (
            f"attachment; filename=student_{student_id}_attendance.pdf"
        )
        return response

    except Exception as e:
        logger.exception("MySQL Error generating PDF: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(request.referrer or url_for("main.home"))
    finally:
        if conn:
            conn.close()


@teacher_bp.route("/student_audit_pdf/<int:student_id>")
def student_audit_pdf(student_id):
    if "teacher_id" not in session and "admin_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get student info
        cursor.execute("SELECT * FROM Users WHERE id = %s", (student_id,))
        student = cursor.fetchone()
        if not student:
            flash("Student not found", "error")
            return redirect(request.referrer or url_for("teacher.teacher_dashboard"))

        # SECURITY CHECK FOR TEACHERS
        if "teacher_id" in session:
            teacher_id = session["teacher_id"]
            cursor.execute("SELECT class FROM Teachers WHERE id = %s", (teacher_id,))
            teacher = cursor.fetchone()

            # Use home class or assigned classes check
            cursor.execute(
                "SELECT class FROM TeacherSubjectAssignments WHERE teacher_id = %s",
                (teacher_id,),
            )
            assigned_classes = [row["class"] for row in cursor.fetchall()]

            if (
                student["class"] != teacher["class"]
                and student["class"] not in assigned_classes
            ):
                flash(
                    "You are not authorized to view this student's audit report.",
                    "error",
                )
                return redirect(
                    request.referrer or url_for("teacher.teacher_dashboard")
                )

        # Get audit records for the student
        cursor.execute(
            """
            SELECT s.name as subject_name, sa.status, sa.notes
            FROM StudentAudit sa
            JOIN Subjects s ON sa.subject_id = s.id
            WHERE sa.student_id = %s
            ORDER BY s.name
        """,
            (student_id,),
        )
        audit_records = cursor.fetchall()

        from ..utils.pdf import generate_audit_report_pdf

        pdf_data = generate_audit_report_pdf(student, audit_records)

        from flask import Response

        response = Response(pdf_data, mimetype="application/pdf")
        response.headers["Content-Disposition"] = (
            f"attachment; filename=student_{student_id}_clearance.pdf"
        )
        return response

    except Exception as e:
        logger.exception("MySQL Error generating audit PDF: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(request.referrer or url_for("teacher.teacher_dashboard"))
    finally:
        if conn:
            conn.close()


@teacher_bp.route("/manage_timetable", methods=["POST"])
def manage_timetable():
    if "teacher_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    # Verify teacher class
    teacher_class = None
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT class FROM Teachers WHERE id = %s", (session["teacher_id"],)
        )
        result = cursor.fetchone()
        if result:
            teacher_class = result["class"]
    except Exception as e:
        logger.error(f"Error getting teacher class: {e}")
    finally:
        if conn:
            conn.close()

    if not teacher_class:
        flash("Could not determine your class.", "error")
        return redirect(url_for("teacher.teacher_dashboard"))

    action = request.form.get("action", "add")

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        if action == "add":
            subject_id = request.form.get("subject_id")
            teacher_id = request.form.get("teacher_id")
            day_of_week = request.form.get("day_of_week")
            start_time = request.form.get("start_time")
            end_time = request.form.get("end_time")

            if subject_id and day_of_week and start_time and end_time:
                t_id = teacher_id if teacher_id and teacher_id.strip() else None
                cursor.execute(
                    "INSERT INTO Timetable (class, subject_id, teacher_id, day_of_week, start_time, end_time) VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        teacher_class,
                        subject_id,
                        t_id,
                        day_of_week,
                        start_time,
                        end_time,
                    ),
                )
                conn.commit()
                flash("Timetable entry added successfully.", "success")
            else:
                flash("Missing required fields.", "error")

        elif action == "update":
            timetable_id = request.form.get("timetable_id")
            subject_id = request.form.get("subject_id")
            teacher_id = request.form.get("teacher_id")
            day_of_week = request.form.get("day_of_week")
            start_time = request.form.get("start_time")
            end_time = request.form.get("end_time")

            if timetable_id and subject_id and day_of_week and start_time and end_time:
                t_id = teacher_id if teacher_id and teacher_id.strip() else None
                # Verify this timetable entry belongs to teacher's class
                cursor.execute(
                    "SELECT id FROM Timetable WHERE id = %s AND class = %s",
                    (timetable_id, teacher_class),
                )
                if not cursor.fetchone():
                    flash("Unauthorized to edit this timetable entry.", "error")
                    return redirect(url_for("teacher.teacher_dashboard"))

                cursor.execute(
                    """
                    UPDATE Timetable
                    SET subject_id = %s, teacher_id = %s, day_of_week = %s, start_time = %s, end_time = %s
                    WHERE id = %s AND class = %s
                """,
                    (
                        subject_id,
                        t_id,
                        day_of_week,
                        start_time,
                        end_time,
                        timetable_id,
                        teacher_class,
                    ),
                )
                conn.commit()
                flash("Timetable entry updated successfully.", "success")
            else:
                flash("Missing required fields for update.", "error")

        elif action == "delete":
            timetable_id = request.form.get("timetable_id")
            if timetable_id:
                # Verify this timetable entry belongs to teacher's class
                cursor.execute(
                    "DELETE FROM Timetable WHERE id = %s AND class = %s",
                    (timetable_id, teacher_class),
                )
                if cursor.rowcount > 0:
                    conn.commit()
                    flash("Timetable entry deleted.", "success")
                else:
                    flash("Could not delete entry or unauthorized access.", "error")

    except Exception as e:
        logger.exception("MySQL Error managing timetable: %s", e)
        flash(f"Database error: {e}", "error")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

    return redirect(url_for("teacher.teacher_dashboard"))


@teacher_bp.route("/student_results_pdf/<int:student_id>")
def student_results_pdf(student_id):
    if "teacher_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    teacher_id = session["teacher_id"]
    term = request.args.get("term")
    exam_type = request.args.get("exam_type")

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get teacher info for authority check
        cursor.execute("SELECT class FROM Teachers WHERE id = %s", (teacher_id,))
        teacher = cursor.fetchone()

        # Authority Check (Same as manage_exam_results)
        cursor.execute("SELECT class FROM Users WHERE id = %s", (student_id,))
        student_data = cursor.fetchone()
        if not student_data:
            flash("Student not found.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        cursor.execute(
            """
            SELECT id FROM Teachers WHERE id = %s AND class = %s
            UNION
            SELECT teacher_id FROM TeacherSubjectAssignments WHERE teacher_id = %s AND class = %s
            UNION
            SELECT teacher_id FROM TeacherSubjectAssignments WHERE teacher_id = %s AND EXISTS (
                SELECT 1 FROM ExamResults WHERE student_id = %s AND subject_id = TeacherSubjectAssignments.subject_id
            )
        """,
            (
                teacher_id,
                student_data["class"],
                teacher_id,
                student_data["class"],
                teacher_id,
                student_id,
            ),
        )

        if not cursor.fetchone():
            flash("You are not authorized to view results for this student.", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        # Build dynamic query for Exam Results
        query = """
            SELECT er.exam_type, er.term, s.name as subject_name, er.score, er.max_score, er.grade, er.remarks
            FROM ExamResults er
            JOIN Subjects s ON er.subject_id = s.id
            WHERE er.student_id = %s
        """
        params = [student_id]

        if term:
            query += " AND er.term = %s"
            params.append(term)
        if exam_type:
            query += " AND er.exam_type = %s"
            params.append(exam_type)

        query += " ORDER BY er.term DESC, er.exam_type ASC"

        cursor.execute(query, tuple(params))
        exam_results = cursor.fetchall()

        # Student info full
        cursor.execute("SELECT * FROM Users WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        pdf_content = generate_exam_results_pdf(student, exam_results)

        filename = f"results_{student['name'].replace(' ', '_')}"
        if term:
            filename += f"_{term.replace(' ', '_')}"
        if exam_type:
            filename += f"_{exam_type.replace(' ', '_')}"

        return Response(
            pdf_content,
            mimetype="application/pdf",
            headers={"Content-disposition": f"attachment; filename={filename}.pdf"},
        )
    except Exception as e:
        logger.exception("Error generating teacher student results PDF: %s", e)
        flash("Could not generate PDF.", "error")
        return redirect(url_for("teacher.teacher_dashboard"))
    finally:
        if conn:
            conn.close()


@teacher_bp.route("/manage_exam_results", methods=["POST"])
def manage_exam_results():
    if "teacher_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    teacher_id = session["teacher_id"]
    action = request.form.get("action")
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get teacher info for authority check
        cursor.execute("SELECT class FROM Teachers WHERE id = %s", (teacher_id,))
        teacher = cursor.fetchone()

        if action == "add" or action == "update":
            student_id = request.form.get("student_id")
            subject_id = request.form.get("subject_id")
            res_teacher_id = request.form.get("teacher_id") or teacher_id
            exam_type = request.form.get("exam_type")
            term = request.form.get("term")
            score = request.form.get("score")
            max_score = request.form.get("max_score", 100)
            grade = request.form.get("grade")
            remarks = request.form.get("remarks")

            # Authority Check
            cursor.execute("SELECT class FROM Users WHERE id = %s", (student_id,))
            student = cursor.fetchone()
            if not student:
                flash("Student not found.", "error")
                return redirect(url_for("teacher.teacher_dashboard"))

            cursor.execute(
                """
                SELECT id FROM Teachers WHERE id = %s AND class = %s
                UNION
                SELECT teacher_id FROM TeacherSubjectAssignments WHERE teacher_id = %s AND class = %s
                UNION
                SELECT teacher_id FROM TeacherSubjectAssignments WHERE teacher_id = %s AND subject_id = %s
            """,
                (
                    teacher_id,
                    student["class"],
                    teacher_id,
                    student["class"],
                    teacher_id,
                    subject_id,
                ),
            )

            if not cursor.fetchone():
                flash(
                    "You are not authorized to manage results for this student/subject combination.",
                    "error",
                )
                return redirect(url_for("teacher.teacher_dashboard"))

            if action == "add":
                cursor.execute(
                    """
                    INSERT INTO ExamResults (student_id, subject_id, teacher_id, exam_type, term, score, max_score, grade, remarks)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        student_id,
                        subject_id,
                        res_teacher_id,
                        exam_type,
                        term,
                        score,
                        max_score,
                        grade,
                        remarks,
                    ),
                )
            else:
                res_id = request.form.get("result_id")
                cursor.execute("SELECT id FROM ExamResults WHERE id = %s", (res_id,))
                if not cursor.fetchone():
                    flash("Result record not found.", "error")
                    return redirect(url_for("teacher.teacher_dashboard"))

                cursor.execute(
                    """
                    UPDATE ExamResults 
                    SET student_id=%s, subject_id=%s, teacher_id=%s, exam_type=%s, term=%s, score=%s, max_score=%s, grade=%s, remarks=%s
                    WHERE id=%s
                """,
                    (
                        student_id,
                        subject_id,
                        res_teacher_id,
                        exam_type,
                        term,
                        score,
                        max_score,
                        grade,
                        remarks,
                        res_id,
                    ),
                )

            conn.commit()
            flash(
                f"Exam result {'added' if action == 'add' else 'updated'} successfully.",
                "success",
            )

        elif action == "delete":
            res_id = request.form.get("result_id")
            cursor.execute(
                """
                SELECT er.id FROM ExamResults er
                JOIN Users u ON er.student_id = u.id
                WHERE er.id = %s AND (
                    u.class = %s 
                    OR er.subject_id IN (SELECT subject_id FROM TeacherSubjectAssignments WHERE teacher_id = %s)
                    OR u.class IN (SELECT class FROM TeacherSubjectAssignments WHERE teacher_id = %s)
                )
            """,
                (res_id, teacher["class"], teacher_id, teacher_id),
            )

            if cursor.fetchone():
                cursor.execute("DELETE FROM ExamResults WHERE id = %s", (res_id,))
                conn.commit()
                flash("Exam result deleted successfully.", "success")
            else:
                flash("Unauthorized to delete this record.", "error")

    except Exception as e:
        logger.exception("Error managing exam results: %s", e)
        flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()

    return redirect(url_for("teacher.teacher_dashboard"))
