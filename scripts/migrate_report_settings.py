import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def migrate():
    print("Migrating database... Updating Settings for Email Schedule.")
    conn = None
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "fpsnsdb"),
            port=int(os.getenv("DB_PORT", 3306))
        )
        cursor = conn.cursor()

        # Insert default send_time if not exists
        cursor.execute("SELECT `value` FROM Settings WHERE `key` = 'send_time'")
        if not cursor.fetchone():
            print("Adding 'send_time' setting (default 08:00)...")
            cursor.execute("INSERT INTO Settings (`key`, `value`) VALUES ('send_time', '08:00')")
        else:
            print("'send_time' already exists.")

        # Insert last_report_sent_date if not exists
        cursor.execute("SELECT `value` FROM Settings WHERE `key` = 'last_report_sent_date'")
        if not cursor.fetchone():
            print("Adding 'last_report_sent_date' setting (default NULL)...")
            cursor.execute("INSERT INTO Settings (`key`, `value`) VALUES ('last_report_sent_date', NULL)")
        else:
            print("'last_report_sent_date' already exists.")

        conn.commit()
        print("Settings migration complete.")
        
    except mysql.connector.Error as e:
        print(f"Error migrating: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate()
