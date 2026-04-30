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
from ..utils.pdf import generate_exam_results_pdf
import logging

logger = logging.getLogger(__name__)

parent_bp = Blueprint("parent", __name__)


@parent_bp.route("/login", methods=["GET", "POST"])
def parent_login():
    return redirect(url_for("main.login"))


@parent_bp.route("/dashboard")
def parent_dashboard():
    if "parent_id" not in session:
        return redirect(url_for("parent.parent_login"))

    today = datetime.today().date()
    seven_days_ago = today - timedelta(days=7)

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get parent info
        cursor.execute("SELECT * FROM Parents WHERE id = %s", (session["parent_id"],))
        parent_info = cursor.fetchone()

        # Get all children linked to this parent
        cursor.execute(
            """
            SELECT u.*, sp.relationship 
            FROM Users u
            JOIN StudentParents sp ON u.id = sp.student_id
            WHERE sp.parent_id = %s
            ORDER BY u.name
        """,
            (session["parent_id"],),
        )
        children = cursor.fetchall()

        # For each child, get today's status and recent attendance
        for child in children:
            child["status"] = _get_student_attendance_status(cursor, child["id"], today)

            # Get attendance for last 7 days
            cursor.execute(
                """
                SELECT CAST(timestamp AS DATE) as date, COUNT(*) as scan_count
                FROM FingerprintLogs
                WHERE person_type = 'student' AND person_id = %s
                AND CAST(timestamp AS DATE) >= %s
                GROUP BY CAST(timestamp AS DATE)
                ORDER BY date DESC
            """,
                (child["id"], seven_days_ago),
            )
            child["recent_attendance"] = cursor.fetchall()

            # Get all enrolled subjects and clearance status
            cursor.execute(
                """
                SELECT s.name as subject_name, sa.status, sa.notes
                FROM StudentSubjects ss
                JOIN Subjects s ON ss.subject_id = s.id
                LEFT JOIN StudentAudit sa ON (ss.student_id = sa.student_id AND ss.subject_id = sa.subject_id)
                WHERE ss.student_id = %s
                ORDER BY s.name
            """,
                (child["id"],),
            )
            child["audits"] = cursor.fetchall()

            # Get timetable for child's class
            cursor.execute(
                """
                SELECT t.day_of_week, s.name as subject_name, t.start_time, t.end_time, te.name as teacher_name
                FROM Timetable t
                JOIN Subjects s ON t.subject_id = s.id
                LEFT JOIN Teachers te ON t.teacher_id = te.id
                WHERE t.class = %s
                ORDER BY CASE t.day_of_week WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 WHEN 'Sunday' THEN 7 ELSE 8 END, t.start_time
            """,
                (child["class"],),
            )
            child["timetable"] = cursor.fetchall()

            # Get Exam Results
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
                (child["id"],),
            )
            child["results"] = cursor.fetchall()

        return render_template(
            "parent_dashboard.html", parent_info=parent_info, children=children
        )

    except Exception as e:
        logger.exception("MySQL Error on parent dashboard: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("parent.parent_dashboard"))
    finally:
        if conn:
            conn.close()


@parent_bp.route("/child_results_pdf/<int:student_id>")
def child_results_pdf(student_id):
    if "parent_id" not in session:
        return redirect(url_for("parent.parent_login"))

    parent_id = session["parent_id"]
    term = request.args.get("term")
    exam_type = request.args.get("exam_type")

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Security check: verify parent is linked to student
        cursor.execute(
            """
            SELECT id FROM StudentParents 
            WHERE parent_id = %s AND student_id = %s
        """,
            (parent_id, student_id),
        )
        if not cursor.fetchone():
            flash("Unauthorized access.", "error")
            return redirect(url_for("parent.parent_dashboard"))

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
        logger.exception("Error generating parent results PDF: %s", e)
        flash("Could not generate PDF.", "error")
        return redirect(url_for("parent.parent_dashboard"))
    finally:
        if conn:
            conn.close()


@parent_bp.route("/logout")
def parent_logout():
    session.pop("parent_id", None)
    return redirect(url_for("main.home"))


@parent_bp.route("/child_audit_pdf/<int:student_id>")
def child_audit_pdf(student_id):
    if "parent_id" not in session:
        return redirect(url_for("parent.parent_login"))

    parent_id = session["parent_id"]
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Verify relationship
        cursor.execute(
            """
            SELECT u.* FROM Users u
            JOIN StudentParents sp ON u.id = sp.student_id
            WHERE sp.parent_id = %s AND sp.student_id = %s
        """,
            (parent_id, student_id),
        )
        student = cursor.fetchone()

        if not student:
            flash("You are not authorized to view this child's record.", "error")
            return redirect(url_for("parent.parent_dashboard"))

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
            f"attachment; filename=child_clearance_{student_id}.pdf"
        )
        return response

    except Exception as e:
        logger.exception("MySQL Error generating child audit PDF: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("parent.parent_dashboard"))
    finally:
        if conn:
            conn.close()
