from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import bcrypt
from ..database import get_db
import logging

logger = logging.getLogger(__name__)

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    return render_template("home.html")


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        flash("Username and password are required", "error")
        return redirect(url_for("main.login"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Check admin credentials
        cursor.execute("SELECT * FROM Admins WHERE username = %s", (username,))
        admin = cursor.fetchone()

        if admin and bcrypt.checkpw(password.encode(), admin["password_hash"].encode()):
            session["admin_id"] = admin["id"]
            return redirect(url_for("admin.admin_dashboard"))

        # Check teacher credentials
        cursor.execute("SELECT * FROM Teachers WHERE username = %s", (username,))
        teacher = cursor.fetchone()

        if teacher and bcrypt.checkpw(
            password.encode(), teacher["password_hash"].encode()
        ):
            session["teacher_id"] = teacher["id"]
            session["teacher_name"] = teacher["name"]
            return redirect(url_for("teacher.teacher_dashboard"))

        # Check student credentials
        cursor.execute("SELECT * FROM Users WHERE username = %s", (username,))
        student = cursor.fetchone()

        if (
            student
            and student.get("password_hash")
            and bcrypt.checkpw(password.encode(), student["password_hash"].encode())
        ):
            session["student_id"] = student["id"]
            session["student_name"] = student["name"]
            return redirect(url_for("student.student_dashboard"))

        # Check parent credentials
        cursor.execute("SELECT * FROM Parents WHERE username = %s", (username,))
        parent = cursor.fetchone()

        if parent and bcrypt.checkpw(
            password.encode(), parent["password_hash"].encode()
        ):
            session["parent_id"] = parent["id"]
            return redirect(url_for("parent.parent_dashboard"))

        # No matching credentials found
        flash("Invalid username or password", "error")
        return redirect(url_for("main.login"))

    except Exception as e:
        logger.exception("Database error during login: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("main.login"))
    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.error("Error closing database connection: %s", e)
