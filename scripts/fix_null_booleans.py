import sys
import os

# Добавляем корень проекта в пути
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.database import SessionLocal
from server.models import Document, User, Folder

def fix_everything():
    db = SessionLocal()
    try:
        print("[INFO] Starting global data cleanup...")
        
        # 1. Fix Documents
        docs = db.query(Document).all()
        doc_count = 0
        for doc in docs:
            changed = False
            if doc.is_private is None: doc.is_private = False; changed = True
            if doc.is_public is None: doc.is_public = False; changed = True
            if doc.is_public_edit is None: doc.is_public_edit = False; changed = True
            if doc.is_read_only is None: doc.is_read_only = False; changed = True
            if changed: doc_count += 1
        
        # 2. Fix Users
        users = db.query(User).all()
        user_count = 0
        for user in users:
            changed = False
            if user.is_active is None: user.is_active = True; changed = True
            if user.is_public_profile is None: user.is_public_profile = False; changed = True
            if changed: user_count += 1
            
        # 3. Fix Folders
        folders = db.query(Folder).all()
        folder_count = 0
        for folder in folders:
            changed = False
            if folder.is_public is None: folder.is_public = False; changed = True
            if changed: folder_count += 1

        if doc_count > 0 or user_count > 0 or folder_count > 0:
            db.commit()
            print(f"[SUCCESS] Cleanup complete:")
            print(f"  - Documents fixed: {doc_count}")
            print(f"  - Users fixed: {user_count}")
            print(f"  - Folders fixed: {folder_count}")
        else:
            print("[INFO] All tables are clean.")
            
    except Exception as e:
        print(f"[ERROR] Global cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_everything()
