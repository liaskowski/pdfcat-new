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
        
        if "avatar_url" not in columns:
            print("Adding 'avatar_url' column to 'users' table...")
            cursor.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
            print("Column 'avatar_url' added.")
        else:
            print("'avatar_url' column already exists.")

        conn.commit()
        print("Migration complete.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
