import sqlite3
import sys
import os

DB_FILE = "app.db"

def check_admin():
    if not os.path.exists(DB_FILE):
        print("Database not found.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT username, role FROM users ORDER BY id ASC LIMIT 1")
    first_user = cursor.fetchone()
    
    if first_user:
        username, role = first_user
        if role == 'admin':
            print(f"Initial Admin login: {username}")
        else:
            print(f"First user '{username}' is NOT admin. Run migration.")
    else:
        print("No users in database.")
        
    conn.close()

if __name__ == "__main__":
    check_admin()
