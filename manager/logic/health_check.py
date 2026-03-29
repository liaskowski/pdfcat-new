import time
import requests
from PyQt6.QtCore import QThread, pyqtSignal

class ServerHealthCheckService(QThread):
    status_changed = pyqtSignal(bool, str) # is_online, message

    def __init__(self, base_url: str, interval: int = 30):
        super().__init__()
        self.base_url = base_url.rstrip('/')
        self.interval = interval
        self.running = True

    def run(self):
        while self.running:
            try:
                response = requests.get(f"{self.base_url}/", timeout=3)
                if response.status_code < 500:
                    self.status_changed.emit(True, "Online")
                else:
                    self.status_changed.emit(False, f"Server Error: {response.status_code}")
            except Exception:
                self.status_changed.emit(False, "Offline")
            
            # Responsive sleep
            for _ in range(self.interval):
                if not self.running: break
                time.sleep(1)

    def stop(self):
        self.running = False
