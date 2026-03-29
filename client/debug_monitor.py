"""
Debug monitor to track application hangs and performance issues.
"""

import sys
import time
import threading
import traceback
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication


class HangMonitor(QObject):
    """Monitor for detecting GUI hangs and blocking operations."""
    
    hang_detected = pyqtSignal(str, float)  # operation, duration
    
    def __init__(self):
        super().__init__()
        self.last_check_time = time.time()
        self.current_operation = "Idle"
        self.is_monitoring = True
        
        # Start monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._check_for_hangs)
        self.monitor_timer.start(1000)  # Check every second
        
        # Track long operations
        self.operation_start_time = None
        self.operation_name = None
    
    def start_operation(self, operation_name: str):
        """Track start of potentially long operation."""
        self.operation_name = operation_name
        self.operation_start_time = time.time()
        self.current_operation = operation_name
        print(f"DEBUG: Starting operation: {operation_name}")
    
    def end_operation(self):
        """Track end of operation."""
        if self.operation_start_time:
            duration = time.time() - self.operation_start_time
            if duration > 2.0:  # Log operations longer than 2 seconds
                print(f"DEBUG: Operation '{self.operation_name}' took {duration:.2f}s")
            
            if duration > 5.0:  # Warn about very long operations
                print(f"WARNING: Long operation detected: '{self.operation_name}' took {duration:.2f}s")
        
        self.operation_start_time = None
        self.operation_name = None
        self.current_operation = "Idle"
    
    def _check_for_hangs(self):
        """Check if GUI is hanging."""
        current_time = time.time()
        time_since_last_check = current_time - self.last_check_time
        
        # If more than 3 seconds since last check, GUI might be hanging
        if time_since_last_check > 3.0:
            print(f"WARNING: Possible GUI hang detected! {time_since_last_check:.2f}s since last check")
            print(f"Current operation: {self.current_operation}")
            
            # Print thread info
            print("Active threads:")
            for thread in threading.enumerate():
                print(f"  - {thread.name}: {thread.is_alive()}")
        
        self.last_check_time = current_time
    
    def log_thread_stack(self):
        """Log stack traces of all threads for debugging."""
        print("DEBUG: Thread stack traces:")
        for thread_id, frame in sys._current_frames().items():
            thread = threading.Thread(target=lambda: None)
            thread.ident = thread_id
            thread_name = thread.name if hasattr(thread, 'name') else f"Thread-{thread_id}"
            print(f"\n--- Thread {thread_name} (ID: {thread_id}) ---")
            traceback.print_stack(frame)


# Global monitor instance
_monitor = None

def get_monitor():
    """Get or create the hang monitor."""
    global _monitor
    if _monitor is None and QApplication.instance():
        _monitor = HangMonitor()
    return _monitor

def start_operation(operation_name: str):
    """Start tracking an operation."""
    monitor = get_monitor()
    if monitor:
        monitor.start_operation(operation_name)

def end_operation():
    """End tracking current operation."""
    monitor = get_monitor()
    if monitor:
        monitor.end_operation()

def log_thread_stacks():
    """Log all thread stacks."""
    monitor = get_monitor()
    if monitor:
        monitor.log_thread_stack()


# Context manager for operations
class OperationTracker:
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
    
    def __enter__(self):
        start_operation(self.operation_name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_operation()
