import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import io

from server.main import app
from server.database import Base, get_db
from server.models import User, Folder, Document
from server.security import get_password_hash

# Test Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_folders.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestFoldersAdvanced(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        
        # Create test users
        db = TestingSessionLocal()
        cls.admin_pass = "adminpass"
        cls.admin = User(
            username="folderadmin",
            email="folderadmin@test.com",
            hashed_password=get_password_hash(cls.admin_pass),
            role="admin",
            is_active=True
        )
        cls.user_pass = "userpass"
        cls.user = User(
            username="folderuser",
            email="folderuser@test.com",
            hashed_password=get_password_hash(cls.user_pass),
            role="user",
            is_active=True
        )
        db.add(cls.admin)
        db.add(cls.user)
        db.commit()
        db.refresh(cls.admin)
        db.refresh(cls.user)
        db.close()

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=engine)
        if os.path.exists("test_folders.db"):
            try: os.remove("test_folders.db")
            except: pass

    def get_token(self, username, password):
        response = self.client.post(
            "/auth/token",
            data={"username": username, "password": password}
        )
        return response.json()["access_token"]

    def test_recursive_visibility(self):
        """Test if making a folder public recursively updates children"""
        token = self.get_token("folderuser", self.user_pass)
        headers = {"Authorization": f"Bearer {token}"}
        
        # 1. Create parent folder (private)
        resp = self.client.post("/folders/", json={"name": "Parent", "is_public": False}, headers=headers)
        parent_id = resp.json()["id"]
        
        # 2. Create subfolder (private)
        resp = self.client.post("/folders/", json={"name": "Child", "parent_id": parent_id, "is_public": False}, headers=headers)
        child_id = resp.json()["id"]
        
        # 3. Upload doc to subfolder (private)
        pdf_content = b"%PDF-1.4\n%%EOF"
        resp = self.client.post(
            "/documents/upload",
            data={"title": "Doc In Child", "folder_id": child_id, "is_public": "false", "use_ocr": "false"},
            files={"file": ("doc.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=headers
        )
        doc_id = resp.json()["id"]
        
        # 4. Patch parent to be public
        resp = self.client.patch(f"/folders/{parent_id}", json={"is_public": True}, headers=headers)
        self.assertEqual(resp.status_code, 200)
        
        # 5. Check child folder visibility
        resp = self.client.get(f"/folders/?parent_id={parent_id}&owner_id={self.user.id}&public_only=true", headers=headers)
        self.assertEqual(len(resp.json()), 1)
        self.assertTrue(resp.json()[0]["is_public"])
        
        # 6. Check doc visibility (should be public now)
        admin_token = self.get_token("folderadmin", self.admin_pass)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        # Another user search
        resp = self.client.get("/search?q=Doc", headers=admin_headers)
        self.assertEqual(len(resp.json()), 1)
        self.assertTrue(resp.json()[0]["is_public"])

    def test_folder_deletion_integrity(self):
        """Check what happens to documents and subfolders when a folder is deleted"""
        token = self.get_token("folderuser", self.user_pass)
        headers = {"Authorization": f"Bearer {token}"}
        
        # 1. Create folder
        resp = self.client.post("/folders/", json={"name": "To Delete"}, headers=headers)
        folder_id = resp.json()["id"]
        
        # 2. Upload doc to it
        pdf_content = b"%PDF-1.4\n%%EOF"
        resp = self.client.post(
            "/documents/upload",
            data={"title": "Orphan Test", "folder_id": folder_id, "use_ocr": "false"},
            files={"file": ("orphan.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=headers
        )
        doc_id = resp.json()["id"]
        
        # 3. Delete folder
        resp = self.client.delete(f"/folders/{folder_id}", headers=headers)
        self.assertEqual(resp.status_code, 200)
        
        # 4. Check doc
        resp = self.client.get(f"/documents/{doc_id}", headers=headers)
        if resp.status_code == 200:
            doc = resp.json()
            # If it still exists, folder_id should be None
            self.assertIsNone(doc["folder_id"])
        else:
             # Or it was deleted (cascade)
             pass

if __name__ == "__main__":
    unittest.main()
