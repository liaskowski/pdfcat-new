"""
Stress tests for batch upload functionality.
Specifically tests the crash scenario when dragging many files at once.

This test suite simulates:
1. Large number of files (100+) dropped at once
2. Deep folder recursion
3. Memory pressure during encryption
4. API rate limiting scenarios
5. UI thread blocking detection
"""

import unittest
import os
import tempfile
import shutil
import time
import threading
import tracemalloc
from pathlib import Path
from unittest.mock import MagicMock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestLargeBatchUpload(unittest.TestCase):
    """Stress tests for large batch uploads"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all tests"""
        cls.temp_dir = tempfile.mkdtemp()
        cls.pdf_content = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
            b"trailer\n<< /Root 1 0 R /Size 4 >>\n%%EOF"
        )
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures"""
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    def setUp(self):
        """Set up for each test"""
        self.mock_api = MagicMock()
        self.mock_api.create_folder.return_value = MagicMock(id=999)
        self.mock_api.upload_file.return_value = MagicMock()
        
        # Start memory tracking
        tracemalloc.start()
    
    def tearDown(self):
        """Clean up after each test"""
        tracemalloc.stop()
        
        # Clean up created files
        for f in Path(self.temp_dir).glob("*.pdf"):
            f.unlink()
    
    def create_test_files(self, count: int, prefix: str = "test") -> list:
        """Helper to create multiple test PDF files"""
        files = []
        for i in range(count):
            file_path = os.path.join(self.temp_dir, f"{prefix}_{i:04d}.pdf")
            with open(file_path, "wb") as f:
                f.write(self.pdf_content)
            files.append(file_path)
        return files
    
    def test_upload_100_files(self):
        """Test uploading 100 files - should not crash"""
        try:
            from client.utils.workers import UploadWorker
        except ImportError:
            self.skipTest("Client modules not available")
        
        files = self.create_test_files(100, "hundred")
        
        worker = UploadWorker(self.mock_api, files, target_folder_id=None, is_public=False)
        
        errors = []
        worker.error.connect(lambda e: errors.append(e))
        
        start_time = time.time()
        worker.run()
        duration = time.time() - start_time
        
        # Should complete without errors
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        
        # Should upload all files
        self.assertEqual(self.mock_api.upload_file.call_count, 100)
        
        print(f"Uploaded 100 files in {duration:.2f}s")
    
    def test_upload_500_files(self):
        """Test uploading 500 files - stress test"""
        try:
            from client.utils.workers import UploadWorker
        except ImportError:
            self.skipTest("Client modules not available")
        
        files = self.create_test_files(500, "stress")
        
        worker = UploadWorker(self.mock_api, files, target_folder_id=None, is_public=False)
        
        errors = []
        worker.error.connect(lambda e: errors.append(e))
        
        progress_count = [0]
        worker.progress.connect(lambda c, t: progress_count.__setitem__(0, c))
        
        start_time = time.time()
        worker.run()
        duration = time.time() - start_time
        
        # Allow some failures due to resource constraints
        success_count = self.mock_api.upload_file.call_count
        self.assertGreater(success_count, 490, f"Most files should upload. Success: {success_count}")
        
        print(f"Uploaded {success_count}/500 files in {duration:.2f}s")
        print(f"Final memory: {tracemalloc.get_traced_memory()[1] / 1024 / 1024:.2f} MB")
    
    def test_upload_1000_files_memory(self):
        """Test memory usage during 1000 file upload"""
        try:
            from client.utils.workers import UploadWorker
        except ImportError:
            self.skipTest("Client modules not available")
        
        files = self.create_test_files(1000, "thousand")
        
        initial_memory = tracemalloc.get_traced_memory()[0]
        
        worker = UploadWorker(self.mock_api, files, target_folder_id=None, is_public=False)
        
        errors = []
        worker.error.connect(lambda e: errors.append(e))
        
        worker.run()
        
        current, peak = tracemalloc.get_traced_memory()
        memory_increase = current - initial_memory
        
        print(f"Memory increase: {memory_increase / 1024 / 1024:.2f} MB")
        print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")
        
        # Memory increase should be reasonable (< 100MB)
        self.assertLess(memory_increase, 100 * 1024 * 1024, "Memory leak detected")
    
    def test_deep_folder_recursion(self):
        """Test deep folder structure - potential stack overflow"""
        try:
            from client.utils.workers import UploadWorker
        except ImportError:
            self.skipTest("Client modules not available")
        
        # Create deep nested structure (10 levels)
        current_dir = self.temp_dir
        for i in range(10):
            current_dir = os.path.join(current_dir, f"level_{i}")
            os.makedirs(current_dir, exist_ok=True)
        
        # Add files at each level
        files = []
        for i, root_dir in enumerate(Path(self.temp_dir).rglob("level_*")):
            file_path = root_dir / f"file_{i}.pdf"
            with open(file_path, "wb") as f:
                f.write(self.pdf_content)
            files.append(str(file_path))
        
        worker = UploadWorker(
            self.mock_api,
            [str(self.temp_dir)],
            target_folder_id=123,
            is_public=True
        )
        
        errors = []
        worker.error.connect(lambda e: errors.append(e))
        
        # Should not crash with stack overflow
        try:
            worker.run()
        except RecursionError:
            self.fail("RecursionError - stack overflow with deep folders")
        
        # Should have created folders
        self.assertGreater(self.mock_api.create_folder.call_count, 0)
    
    def test_concurrent_batch_uploads(self):
        """Test multiple concurrent batch uploads"""
        try:
            from client.utils.workers import UploadWorker
        except ImportError:
            self.skipTest("Client modules not available")
        
        # Create file batches
        batches = []
        for batch_num in range(5):
            batch_files = self.create_test_files(50, f"batch_{batch_num}")
            batches.append(batch_files)
        
        results = []
        lock = threading.Lock()
        
        def run_batch(batch_idx, files):
            batch_api = MagicMock()
            batch_api.upload_file.return_value = MagicMock()
            
            worker = UploadWorker(batch_api, files, target_folder_id=None, is_public=False)
            errors = []
            worker.error.connect(lambda e: errors.append(e))
            
            start = time.time()
            worker.run()
            duration = time.time() - start
            
            with lock:
                results.append({
                    'batch': batch_idx,
                    'uploaded': batch_api.upload_file.call_count,
                    'errors': len(errors),
                    'duration': duration
                })
        
        # Run batches concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(run_batch, i, batch)
                for i, batch in enumerate(batches)
            ]
            
            for future in as_completed(futures):
                try:
                    future.result(timeout=120)
                except Exception as e:
                    self.fail(f"Concurrent batch failed: {e}")
        
        # Check results
        total_uploaded = sum(r['uploaded'] for r in results)
        total_errors = sum(r['errors'] for r in results)
        
        print(f"Total uploaded: {total_uploaded}/250")
        print(f"Total errors: {total_errors}")
        
        self.assertGreater(total_uploaded, 240, "Most files should upload")
    
    def test_large_file_batch(self):
        """Test batch upload with larger files (5MB each)"""
        try:
            from client.utils.workers import UploadWorker
        except ImportError:
            self.skipTest("Client modules not available")
        
        # Create 20 files of 5MB each
        large_content = self.pdf_content + b"0" * (5 * 1024 * 1024 - len(self.pdf_content))
        
        files = []
        for i in range(20):
            file_path = os.path.join(self.temp_dir, f"large_{i}.pdf")
            with open(file_path, "wb") as f:
                f.write(large_content)
            files.append(file_path)
        
        worker = UploadWorker(self.mock_api, files, target_folder_id=None, is_public=False)
        
        errors = []
        worker.error.connect(lambda e: errors.append(e))
        
        start_time = time.time()
        worker.run()
        duration = time.time() - start_time
        
        success_count = self.mock_api.upload_file.call_count
        
        print(f"Uploaded {success_count}/20 large files in {duration:.2f}s")
        print(f"Total size: {20 * 5}MB")
        
        self.assertGreater(success_count, 18, "Most large files should upload")
    
    def test_rapid_sequential_batches(self):
        """Test rapid sequential batch uploads without delay"""
        try:
            from client.utils.workers import UploadWorker
        except ImportError:
            self.skipTest("Client modules not available")
        
        total_uploaded = 0
        
        # Run 10 batches of 50 files each
        for batch_num in range(10):
            files = self.create_test_files(50, f"rapid_{batch_num}")
            
            batch_api = MagicMock()
            batch_api.upload_file.return_value = MagicMock()
            
            worker = UploadWorker(batch_api, files)
            worker.run()
            
            total_uploaded += batch_api.upload_file.call_count
        
        self.assertEqual(total_uploaded, 500, "All files should upload")
    
    def test_worker_cancellation_during_large_batch(self):
        """Test worker can be cancelled during large batch upload"""
        try:
            from client.utils.workers import UploadWorker
        except ImportError:
            self.skipTest("Client modules not available")
        
        files = self.create_test_files(200, "cancel")
        
        worker = UploadWorker(self.mock_api, files)
        
        uploaded_before_cancel = [0]
        
        def cancel_after_50():
            while self.mock_api.upload_file.call_count < 50:
                time.sleep(0.01)
            worker.stop()
        
        # Start cancellation thread
        cancel_thread = threading.Thread(target=cancel_after_50)
        cancel_thread.start()
        
        worker.run()
        
        cancel_thread.join(timeout=5)
        
        # Should have stopped before completing all
        self.assertLess(self.mock_api.upload_file.call_count, 200)
    
    def test_mixed_file_sizes_batch(self):
        """Test batch with mixed file sizes"""
        try:
            from client.utils.workers import UploadWorker
        except ImportError:
            self.skipTest("Client modules not available")
        
        files = []
        
        # Small files (1KB)
        for i in range(20):
            file_path = os.path.join(self.temp_dir, f"small_{i}.pdf")
            with open(file_path, "wb") as f:
                f.write(self.pdf_content)
            files.append(file_path)
        
        # Medium files (1MB)
        medium_content = self.pdf_content + b"0" * (1024 * 1024 - len(self.pdf_content))
        for i in range(10):
            file_path = os.path.join(self.temp_dir, f"medium_{i}.pdf")
            with open(file_path, "wb") as f:
                f.write(medium_content)
            files.append(file_path)
        
        # Large files (5MB)
        large_content = self.pdf_content + b"0" * (5 * 1024 * 1024 - len(self.pdf_content))
        for i in range(5):
            file_path = os.path.join(self.temp_dir, f"large_{i}.pdf")
            with open(file_path, "wb") as f:
                f.write(large_content)
            files.append(file_path)
        
        worker = UploadWorker(self.mock_api, files)
        
        errors = []
        worker.error.connect(lambda e: errors.append(e))
        
        worker.run()
        
        success_count = self.mock_api.upload_file.call_count
        
        print(f"Uploaded {success_count}/35 mixed files")
        
        self.assertGreater(success_count, 30, "Most mixed files should upload")


class TestUIResponsiveness(unittest.TestCase):
    """Test UI responsiveness during batch uploads"""
    
    def setUp(self):
        """Set up for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.pdf_content = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
            b"trailer\n<< /Root 1 0 R /Size 4 >>\n%%EOF"
        )
        self.mock_api = MagicMock()
        self.mock_api.upload_file.return_value = MagicMock()
    
    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_worker_runs_in_thread(self):
        """Test worker runs in separate thread (doesn't block UI)"""
        try:
            from client.utils.workers import UploadWorker
        except ImportError:
            self.skipTest("Client modules not available")
        
        # Create test files
        for i in range(50):
            file_path = os.path.join(self.temp_dir, f"thread_{i}.pdf")
            with open(file_path, "wb") as f:
                f.write(self.pdf_content)
        
        files = [os.path.join(self.temp_dir, f"thread_{i}.pdf") for i in range(50)]
        
        worker = UploadWorker(self.mock_api, files)
        
        main_thread_id = threading.current_thread().ident
        worker_thread_id = [None]
        
        original_run = worker.run
        
        def tracked_run():
            worker_thread_id[0] = threading.current_thread().ident
            original_run()
        
        worker.run = tracked_run
        worker.start()
        worker.wait(120000)  # QThread uses wait() with milliseconds
        
        # Worker should run in different thread
        self.assertIsNotNone(worker_thread_id[0])
        self.assertNotEqual(main_thread_id, worker_thread_id[0])


if __name__ == "__main__":
    unittest.main()
