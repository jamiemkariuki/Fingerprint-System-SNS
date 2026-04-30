"""
Initialize Test Database
Creates test database and sample data
"""

import mysql.connector
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
}

TEST_DB_NAME = "fpsnsdb_test"


def create_test_database():
    """Create test database"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {TEST_DB_NAME}")
    print(f"Created database: {TEST_DB_NAME}")

    conn.close()


def create_tables():
    """Create tables from schema"""
    conn = mysql.connector.connect(**DB_CONFIG, database=TEST_DB_NAME)
    cursor = conn.cursor()

    schema_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schema.sql"
    )

    with open(schema_file, "r") as f:
        schema = f.read()

    for statement in schema.split(";"):
        statement = statement.strip()
        if statement:
            try:
                cursor.execute(statement)
            except Exception as e:
                print(f"Warning: {e}")

    conn.commit()
    print("Created tables")

    conn.close()


def insert_sample_data():
    """Insert sample test data"""
    conn = mysql.connector.connect(**DB_CONFIG, database=TEST_DB_NAME)
    cursor = conn.cursor()

    import bcrypt

    # Sample students
    for i in range(1, 6):
        name = f"Test Student {i}"
        username = f"student{i}"
        class_name = f"Class {i % 3 + 1}"
        password = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode("utf-8")

        cursor.execute(
            "INSERT IGNORE INTO Users (name, username, password_hash, class) VALUES (%s, %s, %s, %s)",
            (name, username, password, class_name),
        )

    # Sample teachers
    for i in range(1, 4):
        name = f"Test Teacher {i}"
        username = f"teacher{i}"
        email = f"teacher{i}@test.local"
        class_name = f"Class {i}"
        password = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode("utf-8")

        cursor.execute(
            "INSERT IGNORE INTO Teachers (name, username, email, class, password_hash) VALUES (%s, %s, %s, %s, %s)",
            (name, username, email, class_name, password),
        )

    conn.commit()
    print("Inserted sample data")

    conn.close()


def main():
    print("=== Initializing Test Database ===")

    create_test_database()
    create_tables()
    insert_sample_data()

    print("=== Test Database Ready ===")
    print(f"Database: {TEST_DB_NAME}")
    print("Users: student1-5 / password123")
    print("Teachers: teacher1-3 / password123")


if __name__ == "__main__":
    main()
