import unittest
import requests
import time
import io
import os
import concurrent.futures

BASE_URL = "http://127.0.0.1:8000"

class TestDeepScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # We assume server is running
        try:
            resp = requests.post(f"{BASE_URL}/auth/token", data={"username": "admin", "password": "admin"}, timeout=5)
            cls.token = resp.json()["access_token"]
            cls.headers = {"Authorization": f"Bearer {cls.token}"}
        except Exception as e:
            print(f"FAILED: Connection to {BASE_URL}: {e}")
            raise unittest.SkipTest("Server not reachable")

    def test_concurrent_ocr_flood(self):
        """Scenario: Flood the server with OCR requests."""
        print("\n[SCENARIO] Concurrent OCR Flood...")
        pdf_content = b"%PDF-1.4\n%%EOF"
        
        def upload_and_ocr(i):
            try:
                resp = requests.post(
                    f"{BASE_URL}/documents/upload",
                    data={"title": f"Flood Doc {i}", "use_ocr": "true"},
                    files={"file": (f"flood_{i}.pdf", io.BytesIO(pdf_content), "application/pdf")},
                    headers=self.headers,
                    timeout=10
                )
                return resp.status_code
            except Exception as e:
                return str(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(upload_and_ocr, range(5)))
        
        for status in results:
            self.assertEqual(status, 200, f"Status was {status}")
        
        # Check DB health
        resp = requests.get(f"{BASE_URL}/users/", headers=self.headers)
        self.assertEqual(resp.status_code, 200, "Server DB pool might be exhausted!")

    def test_file_deletion_out_of_sync(self):
        """Scenario: Physical file deleted manually."""
        print("\n[SCENARIO] Manual file deletion sync check...")
        pdf_content = b"%PDF-1.4\n%%EOF"
        resp = requests.post(
            f"{BASE_URL}/documents/upload",
            data={"title": "Sync Test", "use_ocr": "false"},
            files={"file": ("sync.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=self.headers
        )
        doc = resp.json()
        doc_id = doc["id"]
        file_path = doc["file_path"]
        
        # Path might be relative to server root, ensure it works
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.getcwd(), file_path)

        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Manually deleted: {file_path}")
        else:
            print(f"WARNING: File not found at {file_path}")
        
        # Try to download - Server should ideally return 404
        resp = requests.get(f"{BASE_URL}/documents/{doc_id}/download", headers=self.headers)
        print(f"Download missing file status: {resp.status_code}")
        # FastAPI FileResponse might return 404 automatically if file is missing
        self.assertNotEqual(resp.status_code, 200)

    def test_large_notes_overflow(self):
        """Scenario: extremely large notes."""
        print("\n[SCENARIO] Huge metadata notes...")
        large_notes = "X" * (100 * 1024) # 100KB is enough for test
        
        pdf_content = b"%PDF-1.4\n%%EOF"
        resp = requests.post(
            f"{BASE_URL}/documents/upload",
            data={"title": "Huge Notes", "use_ocr": "false", "notes": large_notes},
            files={"file": ("notes.pdf", io.BytesIO(pdf_content), "application/pdf")},
            headers=self.headers
        )
        self.assertEqual(resp.status_code, 200)
        doc_id = resp.json()["id"]
        
        resp = requests.get(f"{BASE_URL}/documents/{doc_id}", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["notes"]), 100 * 1024)

if __name__ == "__main__":
    unittest.main()
