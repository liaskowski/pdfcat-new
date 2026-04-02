"""
Server status monitoring and automatic startup component.
"""

import subprocess
import threading
import time
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtGui import QColor, QPalette
import requests
from ..api.config import config


class ServerStatusWorker(QThread):
    """Background worker to check server status."""
    
    finished = pyqtSignal(bool)  # is_online
    error = pyqtSignal(str)  # error_message
    
    def __init__(self, api_manager):
        super().__init__()
        self.api = api_manager
        self.base_url = api_manager.base_url if hasattr(api_manager, 'base_url') else None
        # Store login credentials for later use
        self.username = None
        self.password = None
        self.email = None
    
    def run(self):
        """Check server status in background."""
        if not self.base_url:
            self.error.emit("No base URL provided for health check")
            return
            
        try:
            url = f"{self.base_url}/health"
            
            # Create a simple session for health check
            import requests
            session = requests.Session()
            resp = session.get(url, timeout=5)
            
            if resp.status_code == 200:
                self.finished.emit(True)
            else:
                self.error.emit(f"Server returned status {resp.status_code}")
        except requests.exceptions.ConnectionError:
            self.error.emit("Connection refused - server may be offline")
        except requests.exceptions.Timeout:
            self.error.emit("Connection timeout - server may be starting")
        except Exception as e:
            self.error.emit(f"Unexpected error: {str(e)}")


class ServerStatusMonitor(QObject):
    """Monitor server status and handle automatic startup."""
    
    status_changed = pyqtSignal(str, str)  # status, message
    server_started = pyqtSignal()
    server_stopped = pyqtSignal()
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000", parent=None):
        super().__init__(parent)
        self.base_url = base_url.rstrip('/')
        self.server_process: Optional[subprocess.Popen] = None
        self.is_server_running = False
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self._check_server_status)
        self.check_timer.start(5000)  # Check every 5 seconds
        
        # Start monitoring immediately
        QTimer.singleShot(1000, self._check_server_status)
    
    def _check_server_status(self):
        """Check if server is running."""
        try:
            url = f"{self.base_url}/health"
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                if not self.is_server_running:
                    self.is_server_running = True
                    self.status_changed.emit("online", "Server online")
                    self.server_started.emit()
            else:
                if self.is_server_running:
                    self.is_server_running = False
                    self.status_changed.emit("offline", "Server offline")
                    self.server_stopped.emit()
        except requests.exceptions.RequestException:
            if self.is_server_running:
                self.is_server_running = False
                self.status_changed.emit("offline", "Server offline")
                self.server_stopped.emit()
    
    def start_server(self):
        """Start the server automatically."""
        if self.is_server_running or self.server_process:
            return
        
        try:
            # Start server in background
            import os
            server_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            server_script = os.path.join(server_dir, "server", "main.py")
            
            # Try to find Python executable
            python_exe = None
            venv_python = os.path.join(server_dir, ".venv", "Scripts", "python.exe")
            if os.path.exists(venv_python):
                python_exe = venv_python
            else:
                python_exe = "python"
            
            self.server_process = subprocess.Popen(
                [python_exe, server_script],
                cwd=server_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.status_changed.emit("starting", "Starting server...")
            
            # Start a thread to monitor the server process
            threading.Thread(target=self._monitor_server_process, daemon=True).start()
            
        except Exception as e:
            self.status_changed.emit("error", f"Failed to start server: {e}")
    
    def _monitor_server_process(self):
        """Monitor the server process in background."""
        if not self.server_process:
            return
        
        # Wait for server to start or fail
        try:
            stdout, stderr = self.server_process.communicate(timeout=10)
            
            if self.server_process.returncode == 0:
                self.status_changed.emit("error", "Server process exited")
            else:
                error_msg = stderr.strip() if stderr else "Server failed to start"
                self.status_changed.emit("error", f"Server error: {error_msg}")
        except subprocess.TimeoutExpired:
            # Process is still running (good!)
            # Continue monitoring with the timer
            pass
        finally:
            self.server_process = None
    
    def stop_server(self):
        """Stop the server process."""
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.server_process = None


class ServerStatusWidget(QFrame):
    """Widget to display server status with controls."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        
        self.monitor = ServerStatusMonitor()
        self.monitor.status_changed.connect(self._update_status)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Status indicator
        self.status_indicator = QLabel("●")
        self.status_indicator.setFixedWidth(16)
        self.status_indicator.setStyleSheet("color: #ff4444; font-size: 14px;")
        
        # Status text
        self.status_text = QLabel("Checking...")
        self.status_text.setStyleSheet("color: #ccc;")
        
        # Start/Stop button
        self.control_button = QPushButton("Start Server")
        self.control_button.clicked.connect(self._toggle_server)
        
        layout.addWidget(self.status_indicator)
        layout.addWidget(self.status_text, 1)
        layout.addWidget(self.control_button)
    
    def _update_status(self, status: str, message: str):
        """Update the status display."""
        self.status_text.setText(message)
        
        if status == "online":
            self.status_indicator.setStyleSheet("color: #44ff44; font-size: 14px;")
            self.control_button.setText("Stop Server")
            self.control_button.setEnabled(True)
        elif status == "offline":
            self.status_indicator.setStyleSheet("color: #ff4444; font-size: 14px;")
            self.control_button.setText("Start Server")
            self.control_button.setEnabled(True)
        elif status == "starting":
            self.status_indicator.setStyleSheet("color: #ffaa44; font-size: 14px;")
            self.control_button.setText("Starting...")
            self.control_button.setEnabled(False)
        elif status == "error":
            self.status_indicator.setStyleSheet("color: #ff4444; font-size: 14px;")
            self.control_button.setText("Start Server")
            self.control_button.setEnabled(True)
    
    def _toggle_server(self):
        """Toggle server start/stop."""
        if self.monitor.is_server_running:
            self.monitor.stop_server()
        else:
            self.monitor.start_server()
