"""
High-performance thread pool for background operations
Optimized for file I/O, thumbnail generation, and network operations
"""

import threading
import time
import queue
from typing import Callable, Any, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication
import traceback

class TaskPriority:
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class Task:
    """Background task with priority and metadata"""
    
    def __init__(self, func: Callable, *args, priority: int = TaskPriority.NORMAL, 
                 callback: Optional[Callable] = None, error_callback: Optional[Callable] = None,
                 task_id: Optional[str] = None, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.priority = priority
        self.callback = callback
        self.error_callback = error_callback
        self.task_id = task_id or f"task_{id(self)}"
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
    
    def execute(self):
        """Execute the task and return result"""
        try:
            self.started_at = time.time()
            result = self.func(*self.args, **self.kwargs)
            self.completed_at = time.time()
            return result
        except Exception as e:
            self.completed_at = time.time()
            raise e

class BackgroundTaskManager(QObject):
    """
    Advanced thread pool manager with priority queue and monitoring
    """
    
    task_completed = pyqtSignal(str, object)  # task_id, result
    task_failed = pyqtSignal(str, str)  # task_id, error
    task_started = pyqtSignal(str)  # task_id
    queue_status = pyqtSignal(int, int)  # pending, running
    performance_warning = pyqtSignal(str)  # warning message
    
    def __init__(self, max_workers: int = None):
        super().__init__()
        
        # Auto-detect optimal worker count
        if max_workers is None:
            import os
            cpu_count = os.cpu_count() or 4
            max_workers = min(cpu_count * 2, 8)  # Cap at 8 workers
        
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Priority queue for pending tasks
        self._pending_queue = queue.PriorityQueue()
        self._running_tasks: Dict[str, Future] = {}
        self._completed_tasks: Dict[str, Any] = {}
        
        # Performance monitoring
        self._task_stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'avg_execution_time': 0.0,
            'total_execution_time': 0.0
        }
        
        # Queue processor
        self._queue_processor = threading.Thread(target=self._process_queue, daemon=True)
        self._queue_processor.start()
        
        # Status updater
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(1000)  # Update every second
        
        print(f"🧵 BackgroundTaskManager initialized: {max_workers} workers")
    
    def submit_task(self, func: Callable, *args, priority: int = TaskPriority.NORMAL,
                    callback: Optional[Callable] = None, error_callback: Optional[Callable] = None,
                    task_id: Optional[str] = None, **kwargs) -> str:
        """Submit a task to the background queue"""
        
        task = Task(
            func=func,
            *args,
            priority=priority,
            callback=callback,
            error_callback=error_callback,
            task_id=task_id,
            **kwargs
        )
        
        # Add to priority queue (negative priority for max-heap behavior)
        self._pending_queue.put((-priority, task))
        self._task_stats['total_tasks'] += 1
        
        print(f"📝 Task submitted: {task.task_id} (priority: {priority})")
        return task.task_id
    
    def _process_queue(self):
        """Process tasks from priority queue"""
        while True:
            try:
                # Get task from queue (blocks if empty)
                _, task = self._pending_queue.get(timeout=1.0)
                
                # Submit to thread pool
                future = self.executor.submit(task.execute)
                self._running_tasks[task.task_id] = future
                
                # Set up completion callback
                future.add_done_callback(lambda f, t=task: self._task_completed(f, t))
                
                self.task_started.emit(task.task_id)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Error processing queue: {e}")
                traceback.print_exc()
    
    def _task_completed(self, future: Future, task: Task):
        """Handle task completion"""
        try:
            # Remove from running tasks
            self._running_tasks.pop(task.task_id, None)
            
            # Get result
            try:
                result = future.result()
                self._completed_tasks[task.task_id] = result
                
                # Update statistics
                execution_time = task.completed_at - task.started_at
                self._task_stats['completed_tasks'] += 1
                self._task_stats['total_execution_time'] += execution_time
                self._task_stats['avg_execution_time'] = (
                    self._task_stats['total_execution_time'] / self._task_stats['completed_tasks']
                )
                
                # Check for performance warnings
                if execution_time > 5.0:  # 5 seconds
                    self.performance_warning.emit(
                        f"Task {task.task_id} took {execution_time:.2f}s"
                    )
                
                # Call callback if provided
                if task.callback:
                    try:
                        task.callback(result)
                    except Exception as e:
                        print(f"❌ Error in task callback: {e}")
                
                self.task_completed.emit(task.task_id, result)
                print(f"✅ Task completed: {task.task_id} ({execution_time:.2f}s)")
                
            except Exception as e:
                # Handle task failure
                self._task_stats['failed_tasks'] += 1
                
                # Call error callback if provided
                if task.error_callback:
                    try:
                        task.error_callback(str(e))
                    except Exception as cb_error:
                        print(f"❌ Error in error callback: {cb_error}")
                
                self.task_failed.emit(task.task_id, str(e))
                print(f"❌ Task failed: {task.task_id} - {e}")
                
        except Exception as e:
            print(f"❌ Error in task completion handler: {e}")
            traceback.print_exc()
    
    def _update_status(self):
        """Update queue status"""
        pending_count = self._pending_queue.qsize()
        running_count = len(self._running_tasks)
        self.queue_status.emit(pending_count, running_count)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a specific task"""
        if task_id in self._running_tasks:
            future = self._running_tasks[task_id]
            cancelled = future.cancel()
            if cancelled:
                self._running_tasks.pop(task_id, None)
                print(f"🚫 Task cancelled: {task_id}")
            return cancelled
        return False
    
    def get_task_result(self, task_id: str) -> Optional[Any]:
        """Get result of a completed task"""
        return self._completed_tasks.get(task_id)
    
    def get_stats(self) -> Dict:
        """Get task manager statistics"""
        return {
            'pending_tasks': self._pending_queue.qsize(),
            'running_tasks': len(self._running_tasks),
            'completed_tasks': len(self._completed_tasks),
            'max_workers': self.max_workers,
            'task_stats': self._task_stats.copy()
        }
    
    def shutdown(self, wait: bool = True):
        """Shutdown the task manager"""
        print("🛑 Shutting down BackgroundTaskManager...")
        
        if wait:
            # Wait for all running tasks to complete
            for future in self._running_tasks.values():
                future.result()
        
        self.executor.shutdown(wait=wait)
        print("✅ BackgroundTaskManager shutdown complete")

# Global task manager instance
_task_manager: Optional[BackgroundTaskManager] = None

def get_task_manager() -> BackgroundTaskManager:
    """Get global task manager instance"""
    global _task_manager
    if _task_manager is None:
        _task_manager = BackgroundTaskManager()
    return _task_manager

def shutdown_task_manager():
    """Shutdown global task manager"""
    global _task_manager
    if _task_manager:
        _task_manager.shutdown()
        _task_manager = None

# Convenience functions for common operations
def run_in_background(func: Callable, *args, priority: int = TaskPriority.NORMAL,
                      callback: Optional[Callable] = None, **kwargs) -> str:
    """Run function in background thread"""
    manager = get_task_manager()
    return manager.submit_task(func, *args, priority=priority, callback=callback, **kwargs)

def run_thumbnail_task(document_id: int, thumbnail_func: Callable, 
                      callback: Callable, error_callback: Callable = None) -> str:
    """Convenience function for thumbnail generation"""
    return run_in_background(
        thumbnail_func,
        document_id,
        priority=TaskPriority.HIGH,
        callback=callback,
        error_callback=error_callback,
        task_id=f"thumbnail_{document_id}"
    )

# Usage example:
# def generate_thumbnail(doc_id):
#     # Expensive thumbnail generation
#     return thumbnail
#
# def on_thumbnail_ready(thumbnail):
#     # Update UI with thumbnail
#     pass
#
# task_id = run_thumbnail_task(123, generate_thumbnail, on_thumbnail_ready)
