import os
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import logging
from dotenv import load_dotenv
import mysql.connector

from ..database import get_db
from ..utils.common import _get_student_attendance_status
from ..utils.pdf import generate_class_attendance_pdf

# Load environment variables from .env file
load_dotenv()

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Email Constants ---
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_email(recipient_email, subject, body, attachment_data, attachment_filename):
    if not all([SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD]):
        logger.error("SMTP settings are not configured. Cannot send email.")
        return

    message = MIMEMultipart()
    message["From"] = SMTP_USERNAME
    message["To"] = recipient_email
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))

    part = MIMEApplication(attachment_data, Name=attachment_filename)
    part['Content-Disposition'] = f'attachment; filename="{attachment_filename}"'
    message.attach(part)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, recipient_email, message.as_string())
            logger.info(f"Successfully sent email to {recipient_email}")
    except Exception as e:
        logger.exception(f"Failed to send email to {recipient_email}: {e}")

def generate_and_send_reports():
    """
    Generate and send daily attendance reports to teachers.
    Checks configured send_days, send_time, and prevents duplicate sends on the same day.
    """
    logger.info("Starting daily report generation check...")
    now = datetime.now()
    today = now.date()
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # --- Check 1: Is today a configured send day? ---
        cursor.execute("SELECT `value` FROM Settings WHERE `key` = 'send_days'")
        send_days_setting = cursor.fetchone()
        send_days = []
        if send_days_setting and isinstance(send_days_setting, dict) and 'value' in send_days_setting:
            raw = str(send_days_setting['value'])
            for part in raw.split(','):
                part = part.strip()
                if not part:
                    continue
                try:
                    d = int(part)
                except ValueError:
                    continue
                if 0 <= d <= 6:
                    send_days.append(str(d))
                elif 1 <= d <= 7:
                    send_days.append(str(d - 1))

        today_num = now.weekday()
        if str(today_num) not in send_days:
            logger.info("Today (%s, weekday %s) is not a scheduled send day. Skipping.", today, today_num)
            return

        # --- Check 2: Has the configured time passed? ---
        cursor.execute("SELECT `value` FROM Settings WHERE `key` = 'send_time'")
        send_time_setting = cursor.fetchone()
        send_time_str = send_time_setting['value'] if send_time_setting else '08:00'
        try:
            send_time = datetime.strptime(send_time_str, "%H:%M").time()
        except ValueError:
            logger.warning("Invalid send_time format '%s'. Defaulting to 08:00.", send_time_str)
            send_time = datetime.strptime("08:00", "%H:%M").time()

        if now.time() < send_time:
            logger.info("Current time (%s) is before scheduled send time (%s). Skipping.", now.time(), send_time)
            return

        # --- Check 3: Has a report already been sent today? ---
        cursor.execute("SELECT `value` FROM Settings WHERE `key` = 'last_report_sent_date'")
        last_sent_setting = cursor.fetchone()
        last_sent_date_str = last_sent_setting['value'] if last_sent_setting else None

        if last_sent_date_str:
            try:
                last_sent_date = datetime.strptime(last_sent_date_str, "%Y-%m-%d").date()
                if last_sent_date == today:
                    logger.info("Report already sent today (%s). Skipping.", today)
                    return
            except ValueError:
                logger.warning("Could not parse last_report_sent_date: '%s'. Proceeding.", last_sent_date_str)

        # --- All checks passed, send reports ---
        logger.info("All checks passed. Sending reports for %s...", today)
        cursor.execute("SELECT * FROM Teachers")
        teachers = cursor.fetchall()

        for teacher in teachers:
            teacher_email = teacher.get("email")
            teacher_class = teacher.get("class")

            if not teacher_email or not teacher_class:
                logger.warning("Teacher with ID %s is missing email or class. Skipping.", teacher.get('id'))
                continue

            cursor.execute("SELECT * FROM Users WHERE class = %s ORDER BY name", (teacher_class,))
            students = cursor.fetchall()

            for student in students:
                student["status"] = _get_student_attendance_status(cursor, student["id"], today)

            pdf_data = generate_class_attendance_pdf(teacher_class, students, today)

            subject = f"Daily Attendance Report for Class {teacher_class} - {today.strftime('%Y-%m-%d')}"
            body = f"Please find attached the daily attendance report for your class, {teacher_class}."
            attachment_filename = f"{teacher_class}_attendance_{today}.pdf"

            send_email(teacher_email, subject, body, pdf_data, attachment_filename)

        # --- Update last_report_sent_date ---
        today_str = today.strftime("%Y-%m-%d")
        cursor.execute("INSERT INTO Settings (`key`, `value`) VALUES ('last_report_sent_date', %s) ON DUPLICATE KEY UPDATE `value` = %s", (today_str, today_str))
        conn.commit()
        logger.info("Updated last_report_sent_date to %s.", today_str)

    except mysql.connector.Error as e:
        logger.exception(f"Database error during report generation: {e}")
    finally:
        if conn:
            conn.close()

    logger.info("Daily report generation finished.")

