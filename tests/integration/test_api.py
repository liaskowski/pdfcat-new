import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from server.main import app
from server.database import Base, get_db
from server.models import User
from server.security import get_password_hash

# Test Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_app.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        
        # Create test users
        db = TestingSessionLocal()
        cls.admin_pass = "adminpass"
        admin = User(
            username="testadmin",
            email="admin@test.com",
            hashed_password=get_password_hash(cls.admin_pass),
            role="admin",
            is_active=True
        )
        cls.user_pass = "userpass"
        user = User(
            username="testuser",
            email="user@test.com",
            hashed_password=get_password_hash(cls.user_pass),
            role="user",
            is_active=True
        )
        db.add(admin)
        db.add(user)
        db.commit()
        db.close()

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=engine)
        try:
            if os.path.exists("test_app.db"):
                os.remove("test_app.db")
        except PermissionError:
            pass # Common on Windows if file is still locked

    def test_login(self):
        response = self.client.post(
            "/auth/token",
            data={"username": "testadmin", "password": self.admin_pass}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json())
        return response.json()["access_token"]

    def test_create_user_by_admin(self):
        token = self.test_login()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.client.post(
            "/users",
            data={"username": "newuser", "email": "new@test.com", "role": "user"},
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "newuser")
        self.assertEqual(response.json()["role"], "user")

    def test_get_all_users_admin(self):
        token = self.test_login()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.client.get("/users/", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 2)

    def test_search_security(self):
        # 1. Login as User A
        response = self.client.post(
            "/auth/token",
            data={"username": "testadmin", "password": self.admin_pass}
        )
        token_a = response.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # 2. Upload a private document
        import io
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Title (Private Doc) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        response = self.client.post(
            "/documents/upload",
            data={
                "title": "Secret Document Alpha",
                "is_private": "true",
                "use_ocr": "false"
            },
            files={"file": ("secret.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=headers_a
        )
        self.assertEqual(response.status_code, 200)
        doc_id = response.json()["id"]

        # 3. Login as User B
        response = self.client.post(
            "/auth/token",
            data={"username": "testuser", "email": "user@test.com", "password": self.user_pass}
        )
        self.assertEqual(response.status_code, 200, f"Login failed for testuser: {response.text}")
        token_b = response.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 4. User B searches for "Secret"
        response = self.client.get("/search?q=Secret", headers=headers_b)
        self.assertEqual(response.status_code, 200)
        results = response.json()
        
        # 5. Assert document is NOT found for User B
        doc_ids = [d["id"] for d in results]
        self.assertNotIn(doc_id, doc_ids)

        # 6. Verify User A CAN find it
        response = self.client.get("/search?q=Secret", headers=headers_a)
        self.assertEqual(response.status_code, 200)
        results_a = response.json()
        doc_ids_a = [d["id"] for d in results_a]
        self.assertIn(doc_id, doc_ids_a)

    def test_search_security_contradiction(self):
        # Test case: document marked as both public and private
        # Should be hidden from others (private takes precedence)
        
        # 1. Login as User A
        response = self.client.post(
            "/auth/token",
            data={"username": "testadmin", "password": self.admin_pass}
        )
        token_a = response.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # 2. Upload a document with contradictory flags
        import io
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Title (Contradiction) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        response = self.client.post(
            "/documents/upload",
            data={
                "title": "Contradictory Privacy",
                "is_private": "true",
                "is_public": "true",
                "use_ocr": "false"
            },
            files={"file": ("contradict.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=headers_a
        )
        self.assertEqual(response.status_code, 200)
        doc_id = response.json()["id"]

        # 3. Login as User B
        response = self.client.post(
            "/auth/token",
            data={"username": "testuser", "email": "user@test.com", "password": self.user_pass}
        )
        token_b = response.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 4. User B searches
        response = self.client.get("/search?q=Contradictory", headers=headers_b)
        self.assertEqual(response.status_code, 200)
        results = response.json()
        
        # 5. Assert NOT found
        doc_ids = [d["id"] for d in results]
        self.assertNotIn(doc_id, doc_ids)

if __name__ == "__main__":
    unittest.main()
