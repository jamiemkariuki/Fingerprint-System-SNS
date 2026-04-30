#!/usr/bin/env python3

import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_hnBPkldL2W9i@ep-raspy-base-akq29c7r.c-3.us-west-2.aws.neon.tech/neondb?sslmode=require",
)


def initialize_database():
    """Initialize the NeonDB database with the required schema"""
    try:
        # Connect to the database
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True  # Required for creating tables

        cursor = conn.cursor()

        print("Connected to NeonDB successfully!")
        print("Initializing database schema...")

        # Read and execute the schema file
        with open("schema.postgres.sql", "r") as schema_file:
            sql_commands = schema_file.read()

        # Execute the SQL commands
        try:
            # Split commands by semicolon and execute individually
            commands = sql_commands.split(";")
            for cmd in commands:
                cmd = cmd.strip()
                if cmd:
                    cursor.execute(cmd)
        except psycopg2.errors.DuplicateTable as e:
            print(f"Some tables or indexes already exist: {e}")
            print("Continuing with initialization...")
        except Exception as e:
            print(f"Error executing schema: {e}")
            raise

        print("Database schema initialized successfully!")

        # Create a default admin user
        print("Creating default admin user...")
        import bcrypt

        password_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()

        cursor.execute(
            """
            INSERT INTO "Admins" (username, password_hash) 
            VALUES (%s, %s) 
            ON CONFLICT (username) DO UPDATE 
            SET password_hash = EXCLUDED.password_hash
        """,
            ("admin", password_hash),
        )

        print("Default admin user created: admin/admin123")

        cursor.close()
        conn.close()

        print("Database initialization complete!")

    except Exception as e:
        print(f"Error initializing database: {e}")
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    initialize_database()
