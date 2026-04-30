import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # !!! IMPORTANT !!!
    # In a production environment, SECRET_KEY should be a strong, randomly generated value
    # and loaded from an environment variable or a secure configuration management system.
    # Using os.urandom(32) as a default is for development convenience only.
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32))

    SESSION_COOKIE_HTTPONLY = True
    # !!! IMPORTANT !!!
    # In a production environment, SESSION_COOKIE_SECURE should be True if served over HTTPS.
    # This prevents the browser from sending the cookie over unencrypted HTTP connections.
    SESSION_COOKIE_SECURE = (
        os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    )
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")

    # Database configuration
    USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() in ("1", "true", "yes")
    DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL") or ""

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "fp_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "fp_pass")
    DB_NAME = os.getenv("DB_NAME", "fpsnsdb")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "80"))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    # Email Configuration
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.office365.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
