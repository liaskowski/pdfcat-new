"""
Login worker for background authentication.
"""

from PyQt6.QtCore import QThread, pyqtSignal


class LoginWorker(QThread):
    """Worker for handling login in background thread."""
    
    finished = pyqtSignal(str)  # token
    error = pyqtSignal(str)  # error message
    
    def __init__(self, api, username: str, password: str, email: str = None):
        super().__init__()
        self.api = api
        self.username = username
        self.password = password
        self.email = email
    
    def run(self):
        """Execute login in background thread."""
        try:
            token = self.api.login(self.username, self.password, self.email)
            self.finished.emit(token)
        except Exception as e:
            self.error.emit(str(e))
