import os
import logging
from flask import Flask
from flask_wtf.csrf import CSRFProtect

from .config import Config
from .database import get_db
from .blueprints.main import main_bp
from .blueprints.admin import admin_bp
from .blueprints.teacher import teacher_bp
from .blueprints.fingerprint_api import fingerprint_api_bp

csrf = CSRFProtect()


def create_app(config_class=Config):
    # Calculate path to root folder (Fingerprint-System-SNS)
    # this file is in src/main
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # src
    root_dir = os.path.dirname(base_dir)  # Fingerprint-System-SNS

    app = Flask(
        __name__,
        template_folder=os.path.join(root_dir, "templates"),
        static_folder=os.path.join(root_dir, "static"),
    )
    app.config.from_object(config_class)

    # Initialize extensions
    csrf.init_app(app)

    from .blueprints.parent import parent_bp
    from .blueprints.student import student_bp

    # Register blueprints
    # Main app runs on /sns prefix when deployed behind reverse proxy
    app.register_blueprint(main_bp, url_prefix="/sns")
    app.register_blueprint(admin_bp, url_prefix="/sns/admin")
    app.register_blueprint(teacher_bp, url_prefix="/sns/teacher")
    app.register_blueprint(parent_bp, url_prefix="/sns/parent")
    app.register_blueprint(student_bp, url_prefix="/sns/student")

    # Fingerprint API (for local agent communication) - CSRF exempt
    app.register_blueprint(fingerprint_api_bp, url_prefix="/sns")

    # Disable CSRF for API blueprint
    csrf.exempt(fingerprint_api_bp)

    # Configure logging
    log_level = getattr(logging, app.config["LOG_LEVEL"], logging.INFO)

    # Create logs directory if it doesn't exist (skip on Vercel due to read-only filesystem)
    if not app.debug and not os.getenv("VERCEL"):
        if not os.path.exists("logs"):
            os.mkdir("logs")
        from logging.handlers import RotatingFileHandler

        file_handler = RotatingFileHandler(
            "logs/fingerprint.log", maxBytes=102400, backupCount=10
        )
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
            )
        )
        file_handler.setLevel(logging.INFO)

        # Add to root logger to capture all
        logging.getLogger().addHandler(file_handler)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        force=True,
    )

    # Start the fingerprint listener (skip on Vercel/serverless environments)
    if not os.getenv("VERCEL"):
        try:
            from .hardware.fingerprint_listener import FingerprintListener
            import queue

            scan_queue = queue.Queue()
            fingerprint_thread = FingerprintListener(app, scan_queue)
            fingerprint_thread.start()
        except Exception as e:
            # Log error but don't crash the app if fingerprint listener fails
            logging.getLogger(__name__).error(
                f"Failed to start fingerprint listener: {e}"
            )

    return app
