import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "app.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def migrate_social():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        logger.info("Starting Social & Folder Migration...")

        # 1. Create 'folders' table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='folders';")
        if not cursor.fetchone():
            logger.info("Creating table 'folders'...")
            cursor.execute("""
                CREATE TABLE folders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR NOT NULL,
                    parent_id INTEGER REFERENCES folders(id) ON DELETE CASCADE,
                    owner_id INTEGER NOT NULL REFERENCES users(id),
                    is_public BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("CREATE INDEX ix_folders_parent_id ON folders (parent_id);")
            cursor.execute("CREATE INDEX ix_folders_owner_id ON folders (owner_id);")
        else:
            logger.info("Table 'folders' already exists.")

        # 2. Update 'documents' table
        cursor.execute("PRAGMA table_info(documents);")
        columns = [row['name'] for row in cursor.fetchall()]

        if 'folder_id' not in columns:
            logger.info("Adding column 'folder_id' to 'documents'...")
            cursor.execute("ALTER TABLE documents ADD COLUMN folder_id INTEGER REFERENCES folders(id) ON DELETE SET NULL;")
        
        if 'is_public' not in columns:
            logger.info("Adding column 'is_public' to 'documents'...")
            cursor.execute("ALTER TABLE documents ADD COLUMN is_public BOOLEAN DEFAULT 0;")

        # 3. Add 'is_public_profile' to 'users' if possible (Depends if users table has flexible schema or needs alter)
        # Checking users table
        cursor.execute("PRAGMA table_info(users);")
        user_columns = [row['name'] for row in cursor.fetchall()]
        
        if 'is_public_profile' not in user_columns:
            logger.info("Adding column 'is_public_profile' to 'users'...")
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN is_public_profile BOOLEAN DEFAULT 0;")
            except sqlite3.OperationalError as e:
                logger.warning(f"Could not add column to users table (might not exist yet or locked): {e}")

        conn.commit()
        logger.info("Social migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_social()
