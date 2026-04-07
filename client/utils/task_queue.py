"""
Thread pool and queue management utilities for handling concurrent operations.
Provides rate limiting, progress tracking, and cancellation support.
"""

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from .logger import log_debug, log_error


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    task_id: int
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    progress: int = 0


class RateLimiter:
    """Token bucket rate limiter for controlling request rate."""

    def __init__(self, max_concurrent: int = 5, min_delay_ms: int = 0):
        self.max_concurrent = max_concurrent
        self.min_delay = min_delay_ms / 1000.0  # Convert to seconds
        self._semaphore = threading.Semaphore(max_concurrent)
        self._last_call_time = 0
        self._lock = threading.Lock()

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire a slot, respecting rate limit."""
        # First enforce minimum delay BEFORE acquiring semaphore
        if self.min_delay > 0:
            with self._lock:
                elapsed = time.time() - self._last_call_time
                if elapsed < self.min_delay:
                    wait_time = self.min_delay - elapsed
                    # Release lock while sleeping to avoid blocking other threads
                    pass
                else:
                    wait_time = 0
            
            if wait_time > 0:
                time.sleep(wait_time)
        
        # Now acquire the semaphore
        acquired = self._semaphore.acquire(timeout=timeout)
        if acquired:
            with self._lock:
                self._last_call_time = time.time()
        return acquired

    def release(self):
        """Release a slot."""
        self._semaphore.release()
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False


class TaskQueue:
    """
    Thread-safe task queue with progress tracking and cancellation support.
    Designed for batch file uploads and other bulk operations.
    """
    
    def __init__(self, max_workers: int = 5, rate_limit: int = 5):
        self.max_workers = max_workers
        self.rate_limiter = RateLimiter(max_concurrent=rate_limit)
        self._executor: Optional[ThreadPoolExecutor] = None
        self._futures = {}
        self._lock = threading.Lock()
        self._cancelled = False
        self._task_counter = 0
        self._results: List[TaskResult] = []
        
        # Progress tracking
        self._total_tasks = 0
        self._completed_tasks = 0
        self._failed_tasks = 0
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None
        self._log_callback: Optional[Callable[[str], None]] = None
    
    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        """Set callback for progress updates: (current, total, message)"""
        self._progress_callback = callback
    
    def set_log_callback(self, callback: Callable[[str], None]):
        """Set callback for log messages."""
        self._log_callback = callback
    
    def _log(self, message: str):
        if self._log_callback:
            self._log_callback(message)
        else:
            print(f"[TaskQueue] {message}")
    
    def _update_progress(self, current: int, total: int, message: str = ""):
        if self._progress_callback:
            self._progress_callback(current, total, message)
    
    def add_task(self, func: Callable, *args, **kwargs) -> int:
        """Add a task to the queue. Returns task_id."""
        with self._lock:
            self._task_counter += 1
            task_id = self._task_counter
            self._total_tasks += 1
        
        self._log(f"Task {task_id} added to queue")
        return task_id
    
    def _execute_task(self, task_id: int, func: Callable, *args, **kwargs) -> TaskResult:
        """Execute a single task with rate limiting and error handling."""
        log_debug("task_queue", f"_execute_task STARTED for task {task_id}")
        
        if self._cancelled:
            log_debug("task_queue", f"Task {task_id} cancelled before start")
            return TaskResult(task_id, TaskStatus.CANCELLED)
        
        try:
            log_debug("task_queue", f"Task {task_id} acquiring rate limiter slot")
            with self.rate_limiter:
                log_debug("task_queue", f"Task {task_id} acquired slot, checking cancellation")
                if self._cancelled:
                    log_debug("task_queue", f"Task {task_id} cancelled after acquiring slot")
                    return TaskResult(task_id, TaskStatus.CANCELLED)
                
                log_debug("task_queue", f"Task {task_id} STARTED executing")
                result = func(*args, **kwargs)
                log_debug("task_queue", f"Task {task_id} COMPLETED successfully")
                
                return TaskResult(task_id, TaskStatus.COMPLETED, result=result)
                
        except Exception as e:
            log_error("task_queue", f"Task {task_id} FAILED: {e}", exc_info=True)
            return TaskResult(task_id, TaskStatus.FAILED, error=str(e))
    
    def submit(self, func: Callable, *args, **kwargs) -> int:
        """Submit a task for execution."""
        task_id = self.add_task(func, *args, **kwargs)
        
        log_debug("task_queue", f"submit() called for task {task_id}, executor exists: {self._executor is not None}")

        if self._executor is None:
            log_debug("task_queue", "Creating ThreadPoolExecutor")
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
            log_debug("task_queue", f"ThreadPoolExecutor created with {self.max_workers} workers")

        log_debug("task_queue", f"Submitting task {task_id} to executor")
        future = self._executor.submit(self._execute_task, task_id, func, *args, **kwargs)
        log_debug("task_queue", f"Task {task_id} submitted, future done: {future.done()}")

        with self._lock:
            self._futures[task_id] = future

        return task_id
    
    def cancel(self, wait: bool = True):
        """Cancel all pending tasks."""
        self._cancelled = True
        self._log("Cancelling all tasks...")
        
        with self._lock:
            for task_id, future in self._futures.items():
                if not future.done():
                    future.cancel()
        
        if wait and self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
    
    def wait(self, timeout: Optional[float] = None) -> List[TaskResult]:
        """Wait for all tasks to complete."""
        results = []
        
        with self._lock:
            futures_copy = dict(self._futures)
        
        for task_id, future in futures_copy.items():
            try:
                result = future.result(timeout=timeout)
                results.append(result)
                
                with self._lock:
                    if result.status == TaskStatus.COMPLETED:
                        self._completed_tasks += 1
                    elif result.status in (TaskStatus.FAILED, TaskStatus.CANCELLED):
                        self._failed_tasks += 1
                
                self._update_progress(
                    self._completed_tasks + self._failed_tasks,
                    self._total_tasks,
                    f"Task {task_id}: {result.status.value}"
                )
                
            except Exception as e:
                results.append(TaskResult(task_id, TaskStatus.FAILED, error=str(e)))
                self._failed_tasks += 1
        
        return results
    
    def shutdown(self, wait: bool = True):
        """Shutdown the executor and cleanup resources."""
        self.cancel(wait=wait)
        self._log("TaskQueue shutdown complete")
    
    def get_stats(self) -> dict:
        """Get current queue statistics."""
        with self._lock:
            pending = sum(1 for f in self._futures.values() if not f.done())
            return {
                "total": self._total_tasks,
                "completed": self._completed_tasks,
                "failed": self._failed_tasks,
                "pending": pending,
                "cancelled": self._cancelled
            }


class BatchUploadQueue(TaskQueue):
    """
    Specialized task queue for batch file uploads.
    Includes encryption, tagging, and retry logic.
    All heavy operations (encryption, tagging) happen in worker threads.
    """

    def __init__(self, api, max_workers: int = 3, rate_limit: int = 3, do_encryption: bool = True):
        # Disable min_delay for better concurrency
        super().__init__(max_workers=max_workers, rate_limit=rate_limit)
        # Override rate limiter with no delay
        self.rate_limiter = RateLimiter(max_concurrent=rate_limit, min_delay_ms=0)
        
        self.api = api
        self._retry_count = 0
        self._max_retries = 2
        self._successful_uploads = []
        self._failed_uploads = []
        self.do_encryption = do_encryption

    def submit_upload(self, file_path: str, metadata: dict) -> int:
        """Submit a file upload task. Encryption and tagging happen in worker thread."""
        def upload_task():
            return self._upload_with_retry(file_path, metadata)

        return self.submit(upload_task)

    def _upload_with_retry(self, file_path: str, metadata: dict):
        """Execute upload with retry logic. Handles encryption in worker thread."""
        from pathlib import Path
        import secrets
        import fitz
        import tempfile
        
        self._log(f"_upload_with_retry STARTED for {Path(file_path).name}")
        
        # Auto-tagging in worker thread
        tags = []
        if not metadata.get('tags'):
            try:
                from ..logic.tags_engine import TagAnalyzer
                tag_analyzer = TagAnalyzer()
                self._log(f"Starting tag analysis for {Path(file_path).name}")
                tags = tag_analyzer.analyze_file(file_path, locale="en")
                if tags:
                    self._log(f"Auto-tags for {Path(file_path).name}: {', '.join(tags)}")
            except Exception as tag_error:
                self._log(f"Tag analysis failed for {file_path}: {tag_error}")

        # Merge with manually entered tags
        if metadata.get('tags'):
            manual_tags = [t.strip() for t in metadata['tags'].split(',') if t.strip()]
            tags = list(set(tags + manual_tags))

        tags_str = ",".join(tags) if tags else ""

        # Encryption in worker thread
        encryption_key = None
        upload_path = file_path
        temp_path = None

        if self.do_encryption:
            self._log(f"Starting encryption for {Path(file_path).name}")
            try:
                encryption_key = secrets.token_urlsafe(16)
                self._log(f"Opening PDF for encryption: {Path(file_path).name}")
                doc = fitz.open(file_path)
                fd, temp_path = tempfile.mkstemp(suffix=".pdf")
                os.close(fd)

                self._log(f"Saving encrypted PDF: {Path(file_path).name}")
                doc.save(
                    temp_path,
                    encryption=fitz.PDF_ENCRYPT_AES_256,
                    owner_pw=encryption_key,
                    user_pw=encryption_key
                )
                doc.close()
                upload_path = temp_path
                self._log(f"Encrypted {Path(file_path).name} -> {temp_path}")
            except Exception as e:
                self._log(f"Encryption failed for {file_path}, uploading unencrypted: {e}")
                encryption_key = None
                upload_path = file_path

        self._log(f"Starting API upload for {Path(file_path).name}")
        try:
            last_error = None
            for attempt in range(self._max_retries + 1):
                try:
                    self._log(f"Uploading {Path(file_path).name} (attempt {attempt + 1})")

                    # Use the API's upload method
                    result = self.api.upload_file(
                        file_path=upload_path,
                        title=metadata.get('title', Path(file_path).stem),
                        category_id=metadata.get('category_id'),
                        file_type_id=metadata.get('file_type_id'),
                        use_ocr=metadata.get('use_ocr', True),
                        is_private=metadata.get('is_private', True),
                        is_public=metadata.get('is_public', False),
                        is_public_edit=metadata.get('is_public_edit', False),
                        is_read_only=metadata.get('is_read_only', False),
                        encryption_key=encryption_key,
                        notes=metadata.get('notes', ''),
                        tags=tags_str,
                        folder_id=metadata.get('folder_id'),
                    )

                    # Track successful upload
                    self._successful_uploads.append({
                        'file': file_path,
                        'result': result
                    })

                    return result

                except Exception as e:
                    last_error = e
                    self._log(f"Upload attempt {attempt + 1} failed: {str(e)}")
                    if attempt < self._max_retries:
                        time.sleep(1.0 * (attempt + 1))  # Exponential backoff

            # All retries failed
            self._failed_uploads.append({
                'file': file_path,
                'error': str(last_error)
            })
            raise last_error

        except Exception as e:
            # Track failed upload
            self._failed_uploads.append({
                'file': file_path,
                'error': str(e)
            })
            raise e

        finally:
            # Cleanup temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as cleanup_error:
                    self._log(f"Failed to cleanup temp file {temp_path}: {cleanup_error}")

    def get_upload_summary(self) -> dict:
        """Get summary of upload results."""
        return {
            'successful': self._successful_uploads,
            'failed': self._failed_uploads,
            'total_attempted': len(self._successful_uploads) + len(self._failed_uploads)
        }
