import sqlite3
import os

DB_FILE = "app.db"

def migrate_db():
    if not os.path.exists(DB_FILE):
        print(f"Database {DB_FILE} not found. Skipping migration.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "reset_code" not in columns:
            print("Adding 'reset_code' column to 'users' table...")
            cursor.execute("ALTER TABLE users ADD COLUMN reset_code TEXT")
            print("Column 'reset_code' added.")
        else:
            print("'reset_code' column already exists.")

        # Ensure all existing users have an email for testing (cleanup task)
        cursor.execute("SELECT id, username, email FROM users")
        users = cursor.fetchall()
        for uid, uname, email in users:
            if not email:
                test_email = f"{uname}@example.com"
                print(f"Updating user {uname} with test email: {test_email}")
                cursor.execute("UPDATE users SET email = ? WHERE id = ?", (test_email, uid))

        conn.commit()
        print("Migration and data cleanup complete.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
