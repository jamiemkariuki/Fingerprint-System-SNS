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
import bcrypt
from ..database import get_db
from ..utils.common import _get_student_attendance_status
from ..utils.pdf import generate_exam_results_pdf
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

student_bp = Blueprint("student", __name__)


@student_bp.route("/login", methods=["GET", "POST"])
def student_login():
    return redirect(url_for("main.login"))


@student_bp.route("/dashboard")
def student_dashboard():
    if "student_id" not in session:
        return redirect(url_for("student.student_login"))

    student_id = session["student_id"]
    today = datetime.today().date()

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Student info
        cursor.execute("SELECT * FROM Users WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        # All enrolled subjects and their clearance status
        cursor.execute(
            """
            SELECT ss.subject_id, sa.id as audit_id, s.name as subject_name, sa.status, sa.notes, sa.updated_at
            FROM StudentSubjects ss
            JOIN Subjects s ON ss.subject_id = s.id
            LEFT JOIN StudentAudit sa ON (ss.student_id = sa.student_id AND ss.subject_id = sa.subject_id)
            WHERE ss.student_id = %s
            ORDER BY s.name
        """,
            (student_id,),
        )
        audit_records = cursor.fetchall()
        enrolled_subject_ids = [r["subject_id"] for r in audit_records]

        # Attendance today
        status = _get_student_attendance_status(cursor, student_id, today)

        # Weekly attendance summary
        cutoff = datetime.now() - timedelta(days=7)
        cursor.execute(
            """
            SELECT CAST(timestamp AS DATE) as date, COUNT(*) as count
            FROM FingerprintLogs
            WHERE person_type = 'student' AND person_id = %s
            AND timestamp >= %s
            GROUP BY CAST(timestamp AS DATE)
            ORDER BY date DESC
        """,
            (student_id, cutoff),
        )
        history = cursor.fetchall()
        # Fetch Timetable for student's class
        cursor.execute(
            """
            SELECT t.day_of_week, s.name as subject_name, t.start_time, t.end_time, te.name as teacher_name, t.subject_id
            FROM Timetable t
            JOIN Subjects s ON t.subject_id = s.id
            LEFT JOIN Teachers te ON t.teacher_id = te.id
            WHERE t.class = %s
            ORDER BY CASE t.day_of_week WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 WHEN 'Sunday' THEN 7 ELSE 8 END, t.start_time
        """,
            (student["class"],),
        )
        timetable = cursor.fetchall()

        # Fetch Exam Results
        cursor.execute(
            """
            SELECT er.exam_type, er.term, s.name as subject_name, er.score, er.max_score, er.grade, er.remarks, te.name as teacher_name
            FROM ExamResults er
            JOIN Subjects s ON er.subject_id = s.id
            LEFT JOIN Teachers te ON er.teacher_id = te.id
            JOIN PublishedExams pe ON (er.term = pe.term AND er.exam_type = pe.exam_type)
             WHERE er.student_id = %s AND pe.is_published = TRUE
            ORDER BY er.term DESC, er.exam_type ASC
        """,
            (student_id,),
        )
        exam_results = cursor.fetchall()

        return render_template(
            "student_dashboard.html",
            student=student,
            audit_records=audit_records,
            enrolled_subject_ids=enrolled_subject_ids,
            status=status,
            history=history,
            timetable=timetable,
            exam_results=exam_results,
        )

    except Exception as e:
        logger.exception("Error loading student dashboard: %s", e)
        flash(f"Database error: {e}", "error")
        return "Internal Server Error", 500
    finally:
        if conn:
            conn.close()


@student_bp.route("/download_results")
def download_results():
    if "student_id" not in session:
        return redirect(url_for("student.student_login"))

    student_id = session["student_id"]
    term = request.args.get("term")
    exam_type = request.args.get("exam_type")

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Student info
        cursor.execute("SELECT * FROM Users WHERE id = %s", (student_id,))
        student = cursor.fetchone()

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

        pdf_content = generate_exam_results_pdf(student, exam_results)

        filename = f"exam_results_{student_id}"
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
        logger.exception("Error generating results PDF: %s", e)
        flash("Could not generate PDF.", "error")
        return redirect(url_for("student.student_dashboard"))
    finally:
        if conn:
            conn.close()


@student_bp.route("/logout")
def student_logout():
    session.pop("student_id", None)
    session.pop("student_name", None)
    return redirect(url_for("main.home"))


@student_bp.route("/audit_note/<int:audit_id>", methods=["POST"])
def audit_note(audit_id):
    if "student_id" not in session:
        return redirect(url_for("student.student_login"))
    note = request.form.get("note", "").strip()
    if not note:
        flash("Note cannot be empty", "error")
        return redirect(request.referrer or url_for("student.student_dashboard"))
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, notes FROM StudentAudit WHERE id = %s AND student_id = %s",
            (audit_id, session["student_id"]),
        )
        audit = cursor.fetchone()
        if not audit:
            flash("Audit not found", "error")
            return redirect(url_for("student.student_dashboard"))
        current_notes = audit.get("notes")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_notes = (
            current_notes + "\n" if current_notes else ""
        ) + f"{timestamp} {note}"
        cursor.execute(
            "UPDATE StudentAudit SET notes = %s WHERE id = %s", (new_notes, audit_id)
        )
        conn.commit()
        flash("Note added to audit record", "success")
    except Exception as e:
        logger.exception("MySQL Error adding note to audit: %s", e)
        flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()
    return redirect(url_for("student.student_dashboard"))


@student_bp.route("/my_audit_pdf")
def my_audit_pdf():
    if "student_id" not in session:
        return redirect(url_for("student.student_login"))

    student_id = session["student_id"]
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM Users WHERE id = %s", (student_id,))
        student = cursor.fetchone()

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
            "attachment; filename=my_clearance.pdf"
        )
        return response

    except Exception as e:
        logger.exception("MySQL Error generating student audit PDF: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("student.student_dashboard"))
    finally:
        if conn:
            conn.close()
