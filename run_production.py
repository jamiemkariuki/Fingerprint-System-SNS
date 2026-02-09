import os
import time
import threading
import logging
from waitress import serve
from wsgi import application

# Configure logging for the scheduler
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("scheduler")

def report_scheduler():
    """
    Background thread that checks every 1 minutes if reports should be sent.
    The actual send logic in email.py handles day/time/duplicate checks.
    """
    # Import here to avoid circular imports
    from src.main.utils.email import generate_and_send_reports
    
    logger.info("Report scheduler started. Will check every 1s minutes.")
    while True:
        try:
            logger.info("Running scheduled report check...")
            generate_and_send_reports()
        except Exception as e:
            logger.exception(f"Error in report scheduler: {e}")
        
        # Sleep for 15 minutes
        time.sleep(60)

if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "8080"))
    
    # Start the background report scheduler thread
    scheduler_thread = threading.Thread(target=report_scheduler, daemon=True)
    scheduler_thread.start()
    
    print(f"Starting Production Server on {host}:{port}...")
    print("Background report scheduler is running (checks every 15 minutes).")
    serve(application, host=host, port=port)

