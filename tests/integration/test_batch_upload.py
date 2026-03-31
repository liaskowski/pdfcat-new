"""
Comprehensive tests for batch upload functionality.
Tests cover the drag-and-drop batch upload bug where the client crashes
when dropping a large number of files.

Identified Issues:
1. Recursive scan_recursive() can cause stack overflow with deep folder structures
2. No batch size limiting or memory management
3. Synchronous encryption without proper error handling
4. No rate limiting for API calls
5. UI thread blocking during large batch operations
"""

import unittest
import io
import os
import tempfile
import shutil
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Check if server can be imported (requires PIL)
try:
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    from server.main import app
    from server.database import Base, get_db
    from server.models import User
    from server.security import get_password_hash
    
    SERVER_AVAILABLE = True
except ImportError as e:
    SERVER_AVAILABLE = False
    print(f"Server tests skipped: {e}")

# Test Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_batch_upload.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


if SERVER_AVAILABLE:
    app.dependency_overrides[get_db] = override_get_db


class TestBatchUpload(unittest.TestCase):
    """Test batch upload functionality and stress scenarios"""
    
    @classmethod
    def setUpClass(cls):
        if not SERVER_AVAILABLE:
            raise unittest.SkipTest("Server module not available (PIL import error)")
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        
        # Create test users
        db = TestingSessionLocal()
        cls.admin_pass = "adminpass"
        cls.admin_user = User(
            username="batchadmin",
            email="batchadmin@test.com",
            hashed_password=get_password_hash(cls.admin_pass),
            role="admin",
            is_active=True
        )
        cls.user_pass = "userpass"
        cls.normal_user = User(
            username="batchuser",
            email="batchuser@test.com",
            hashed_password=get_password_hash(cls.user_pass),
            role="user",
            is_active=True
        )
        db.add(cls.admin_user)
        db.add(cls.normal_user)
        db.commit()
        db.close()
        
        # Create temp directory for test PDFs
        cls.temp_dir = tempfile.mkdtemp()
        cls.test_pdfs = []
        
    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=engine)
        
        # Cleanup temp files
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir, ignore_errors=True)
        
        # Cleanup database
        try:
            if os.path.exists("test_batch_upload.db"):
                os.remove("test_batch_upload.db")
        except PermissionError:
            pass
    
    def get_token(self, username: str, password: str) -> str:
        """Helper to get auth token"""
        response = self.client.post(
            "/auth/token",
            data={"username": username, "password": password}
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["access_token"]
    
    def create_test_pdf(self, name: str, content: bytes = None) -> str:
        """Create a test PDF file"""
        if content is None:
            # Minimal valid PDF
            content = (
                b"%PDF-1.4\n"
                b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
                b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
                b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
                b"trailer\n<< /Root 1 0 R /Size 4 >>\n%%EOF"
            )
        
        file_path = os.path.join(self.temp_dir, name)
        with open(file_path, "wb") as f:
            f.write(content)
        return file_path
    
    def setUp(self):
        """Reset temp directory for each test"""
        self.admin_token = self.get_token("batchadmin", self.admin_pass)
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        self.user_token = self.get_token("batchuser", self.user_pass)
        self.user_headers = {"Authorization": f"Bearer {self.user_token}"}
    
    def test_single_file_upload(self):
        """Test basic single file upload works"""
        pdf_path = self.create_test_pdf("single.pdf")
        
        with open(pdf_path, "rb") as f:
            response = self.client.post(
                "/documents/upload",
                data={
                    "title": "Single Test Document",
                    "use_ocr": "false",
                    "is_private": "false",
                    "is_public": "true"
                },
                files={"file": ("single.pdf", f, "application/pdf")},
                headers=self.admin_headers
            )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "Single Test Document")
        self.assertIsNotNone(data["id"])
    
    def test_batch_upload_10_files(self):
        """Test uploading 10 files in sequence"""
        # Create 10 test PDFs
        for i in range(10):
            self.create_test_pdf(f"batch_{i:02d}.pdf")
        
        success_count = 0
        for i in range(10):
            pdf_path = os.path.join(self.temp_dir, f"batch_{i:02d}.pdf")
            with open(pdf_path, "rb") as f:
                response = self.client.post(
                    "/documents/upload",
                    data={
                        "title": f"Batch Document {i}",
                        "use_ocr": "false",
                        "is_private": "false",
                        "is_public": "true"
                    },
                    files={"file": (f"batch_{i:02d}.pdf", f, "application/pdf")},
                    headers=self.admin_headers
                )
                if response.status_code == 200:
                    success_count += 1
        
        self.assertEqual(success_count, 10, "All 10 files should upload successfully")
    
    def test_batch_upload_50_files(self):
        """Test uploading 50 files - stress test for batch operations"""
        # Create 50 test PDFs
        for i in range(50):
            self.create_test_pdf(f"stress_{i:03d}.pdf")
        
        success_count = 0
        errors = []
        
        for i in range(50):
            pdf_path = os.path.join(self.temp_dir, f"stress_{i:03d}.pdf")
            try:
                with open(pdf_path, "rb") as f:
                    response = self.client.post(
                        "/documents/upload",
                        data={
                            "title": f"Stress Document {i}",
                            "use_ocr": "false",
                            "is_private": "false",
                            "is_public": "true"
                        },
                        files={"file": (f"stress_{i:03d}.pdf", f, "application/pdf")},
                        headers=self.admin_headers,
                        timeout=30.0
                    )
                    if response.status_code == 200:
                        success_count += 1
                    else:
                        errors.append(f"File {i}: {response.status_code} - {response.text}")
            except Exception as e:
                errors.append(f"File {i}: {str(e)}")
        
        # Allow some failures due to resource constraints, but most should succeed
        self.assertGreater(success_count, 45, f"Most files should upload. Errors: {errors[:5]}")
    
    def test_concurrent_batch_upload(self):
        """Test concurrent uploads from multiple threads"""
        # Create test files
        for i in range(20):
            self.create_test_pdf(f"concurrent_{i:02d}.pdf")
        
        results = []
        lock = threading.Lock()
        
        def upload_file(file_num: int):
            pdf_path = os.path.join(self.temp_dir, f"concurrent_{file_num:02d}.pdf")
            try:
                with open(pdf_path, "rb") as f:
                    response = self.client.post(
                        "/documents/upload",
                        data={
                            "title": f"Concurrent Document {file_num}",
                            "use_ocr": "false",
                            "is_private": "false",
                            "is_public": "true"
                        },
                        files={"file": (f"concurrent_{file_num:02d}.pdf", f, "application/pdf")},
                        headers=self.admin_headers,
                        timeout=30.0
                    )
                    with lock:
                        results.append((file_num, response.status_code))
            except Exception as e:
                with lock:
                    results.append((file_num, f"Error: {str(e)}"))
        
        # Start 5 concurrent threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=upload_file, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=60)
        
        # Check results
        success_count = sum(1 for _, r in results if r == 200)
        self.assertGreater(success_count, 3, f"At least 4 concurrent uploads should succeed. Results: {results}")
    
    def test_large_file_batch_upload(self):
        """Test batch upload with larger files (1MB each)"""
        # Create 5 test PDFs of 1MB each
        large_content = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
            b"trailer\n<< /Root 1 0 R /Size 4 >>\n%%EOF"
        )
        # Pad to 1MB
        large_content = large_content + b"0" * (1024 * 1024 - len(large_content))
        
        for i in range(5):
            self.create_test_pdf(f"large_{i}.pdf", large_content)
        
        success_count = 0
        total_size = 0
        
        for i in range(5):
            pdf_path = os.path.join(self.temp_dir, f"large_{i}.pdf")
            file_size = os.path.getsize(pdf_path)
            total_size += file_size
            
            with open(pdf_path, "rb") as f:
                response = self.client.post(
                    "/documents/upload",
                    data={
                        "title": f"Large Document {i}",
                        "use_ocr": "false",
                        "is_private": "false",
                        "is_public": "true"
                    },
                    files={"file": (f"large_{i}.pdf", f, "application/pdf")},
                    headers=self.admin_headers,
                    timeout=60.0
                )
                if response.status_code == 200:
                    success_count += 1
        
        self.assertEqual(success_count, 5, "All large files should upload")
        self.assertGreater(total_size, 4 * 1024 * 1024, "Should upload more than 4MB total")
    
    def test_batch_upload_with_folders(self):
        """Test batch upload simulating folder structure"""
        # Create nested folder structure
        base_folder = os.path.join(self.temp_dir, "test_folder")
        os.makedirs(base_folder, exist_ok=True)
        
        sub_folder = os.path.join(base_folder, "subfolder")
        os.makedirs(sub_folder, exist_ok=True)
        
        # Create files in both folders
        for i in range(5):
            self.create_test_pdf(f"root_{i}.pdf")
        
        for i in range(5):
            self.create_test_pdf(f"sub_{i}.pdf")
        
        # Simulate folder upload by uploading all files
        all_files = list(Path(self.temp_dir).glob("*.pdf"))
        
        success_count = 0
        for pdf_path in all_files[:10]:  # Limit to 10 files
            with open(pdf_path, "rb") as f:
                response = self.client.post(
                    "/documents/upload",
                    data={
                        "title": f"Folder Test: {pdf_path.name}",
                        "use_ocr": "false",
                        "is_private": "false",
                        "is_public": "true"
                    },
                    files={"file": (pdf_path.name, f, "application/pdf")},
                    headers=self.admin_headers,
                    timeout=30.0
                )
                if response.status_code == 200:
                    success_count += 1
        
        self.assertEqual(success_count, 10, "All folder files should upload")
    
    def test_rapid_sequential_uploads(self):
        """Test rapid sequential uploads without delay"""
        success_count = 0
        
        for i in range(20):
            pdf_content = (
                b"%PDF-1.4\n"
                b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
                b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
                b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
                b"trailer\n<< /Root 1 0 R /Size 4 >>\n%%EOF"
            )
            
            response = self.client.post(
                "/documents/upload",
                data={
                    "title": f"Rapid Document {i}",
                    "use_ocr": "false",
                    "is_private": "false",
                    "is_public": "true"
                },
                files={"file": (f"rapid_{i}.pdf", io.BytesIO(pdf_content), "application/pdf")},
                headers=self.admin_headers,
                timeout=30.0
            )
            if response.status_code == 200:
                success_count += 1
        
        self.assertEqual(success_count, 20, "All rapid uploads should succeed")
    
    def test_batch_upload_permissions(self):
        """Test that normal user can batch upload but has limitations"""
        # Create test files
        for i in range(5):
            self.create_test_pdf(f"user_{i}.pdf")
        
        success_count = 0
        
        for i in range(5):
            pdf_path = os.path.join(self.temp_dir, f"user_{i}.pdf")
            with open(pdf_path, "rb") as f:
                response = self.client.post(
                    "/documents/upload",
                    data={
                        "title": f"User Document {i}",
                        "use_ocr": "false",
                        "is_private": "true",  # User uploads private by default
                        "is_public": "false"
                    },
                    files={"file": (f"user_{i}.pdf", f, "application/pdf")},
                    headers=self.user_headers,
                    timeout=30.0
                )
                if response.status_code == 200:
                    success_count += 1
        
        self.assertEqual(success_count, 5, "Normal user should be able to batch upload")
    
    def test_duplicate_filename_batch(self):
        """Test batch upload with duplicate filenames"""
        pdf_content = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
            b"trailer\n<< /Root 1 0 R /Size 4 >>\n%%EOF"
        )
        
        # Upload same filename multiple times with different titles
        success_count = 0
        
        for i in range(5):
            response = self.client.post(
                "/documents/upload",
                data={
                    "title": f"Duplicate Test {i}",
                    "use_ocr": "false",
                    "is_private": "false",
                    "is_public": "true"
                },
                files={"file": ("duplicate.pdf", io.BytesIO(pdf_content), "application/pdf")},
                headers=self.admin_headers,
                timeout=30.0
            )
            if response.status_code == 200:
                success_count += 1
        
        self.assertEqual(success_count, 5, "Server should handle duplicate filenames")


class TestClientBatchUploadWorker(unittest.TestCase):
    """Test client-side UploadWorker logic"""
    
    def test_upload_worker_initialization(self):
        """Test UploadWorker can be initialized with batch of files"""
        try:
            from client.utils.workers import UploadWorker
            from unittest.mock import MagicMock
            
            mock_api = MagicMock()
            paths = [f"/fake/path/file_{i}.pdf" for i in range(100)]
            
            worker = UploadWorker(mock_api, paths, target_folder_id=None, is_public=False)
            
            self.assertEqual(len(worker.paths), 100)
            self.assertFalse(worker._stop)
        except ImportError:
            self.skipTest("Client modules not available for testing")
    
    def test_upload_worker_stop_flag(self):
        """Test UploadWorker stop flag functionality"""
        try:
            from client.utils.workers import UploadWorker
            from unittest.mock import MagicMock
            
            mock_api = MagicMock()
            paths = [f"/fake/path/file_{i}.pdf" for i in range(10)]
            
            worker = UploadWorker(mock_api, paths)
            worker.stop()
            
            self.assertTrue(worker._stop)
        except ImportError:
            self.skipTest("Client modules not available for testing")


if __name__ == "__main__":
    unittest.main()
