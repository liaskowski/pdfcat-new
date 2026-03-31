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
        # Check if email column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "email" not in columns:
            print("Adding 'email' column to 'users' table...")
            cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
            cursor.execute("CREATE UNIQUE INDEX ix_users_email ON users (email)")
            print("Column 'email' added.")
        else:
            print("'email' column already exists.")

        # Ensure at least one admin exists or make the first user admin
        cursor.execute("SELECT id, username, role FROM users ORDER BY id ASC LIMIT 1")
        first_user = cursor.fetchone()
        
        if first_user:
            uid, uname, role = first_user
            if role != 'admin':
                print(f"Promoting first user '{uname}' (ID: {uid}) to admin.")
                cursor.execute("UPDATE users SET role = 'admin' WHERE id = ?", (uid,))
            else:
                print(f"First user '{uname}' is already admin.")
        else:
            print("No users found in database.")

        conn.commit()
        print("Migration complete.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_db()
