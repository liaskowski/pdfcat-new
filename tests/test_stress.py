import unittest
import time
import io
import os
import threading
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.main import app
from server.database import Base, get_db
from server.models import User
from server.security import get_password_hash

# Test Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_stress.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class TestStress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        
        # Create test users
        db = TestingSessionLocal()
        cls.admin_pass = "adminpass"
        admin = User(
            username="stressadmin",
            email="stressadmin@test.com",
            hashed_password=get_password_hash(cls.admin_pass),
            role="admin",
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.close()

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=engine)
        if os.path.exists("test_stress.db"):
            try: os.remove("test_stress.db")
            except: pass

    def get_token(self):
        response = self.client.post(
            "/auth/token",
            data={"username": "stressadmin", "password": self.admin_pass}
        )
        return response.json()["access_token"]

    def test_large_file_upload(self):
        """Test uploading a 'large' file (mocked as 10MB for speed in test, but could be larger)"""
        token = self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a 10MB dummy PDF
        size_mb = 10
        content = b"%PDF-1.4\n" + b"0" * (size_mb * 1024 * 1024) + b"\n%%EOF"
        
        start_time = time.time()
        response = self.client.post(
            "/documents/upload",
            data={
                "title": f"Large {size_mb}MB Doc",
                "use_ocr": "false"
            },
            files={"file": ("large.pdf", io.BytesIO(content), "application/pdf")},
            headers=headers
        )
        duration = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        print(f"Uploaded {size_mb}MB in {duration:.2f}s")

    def test_concurrent_searches(self):
        """Test multiple concurrent search requests"""
        token = self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        results = []
        def make_search():
            resp = self.client.get("/search?q=test", headers=headers)
            results.append(resp.status_code)

        threads = []
        for _ in range(20):
            t = threading.Thread(target=make_search)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        for status in results:
            self.assertEqual(status, 200)

    def test_rapid_metadata_updates(self):
        """Test rapid sequential updates to a single document"""
        token = self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # 1. Create doc
        pdf_content = b"%PDF-1.4\n%%EOF"
        response = self.client.post(
            "/documents/upload",
            data={"title": "Update Test", "use_ocr": "false"},
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=headers
        )
        doc_id = response.json()["id"]

        # 2. Rapid updates
        for i in range(50):
            response = self.client.put(
                f"/documents/{doc_id}",
                json={"title": f"Title {i}"},
                headers=headers
            )
            self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
    unittest.main()
