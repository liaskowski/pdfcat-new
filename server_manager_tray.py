import sys
import os
import subprocess
import time
import logging
from pathlib import Path

# --- Early Logging Setup (before heavy imports) ---
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "manager_tray.log",
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)

logging.info("--- Tray Manager Starting ---")
logging.info(f"Python: {sys.executable}")
logging.info(f"CWD: {os.getcwd()}")

# --- Fix for Portable PyQt6 Plugins ---
QT_PLUGIN_PATH = BASE_DIR / "vendor" / "python" / "Lib" / "site-packages" / "PyQt6" / "Qt6" / "plugins"
if QT_PLUGIN_PATH.exists():
    os.environ["QT_PLUGIN_PATH"] = str(QT_PLUGIN_PATH)
    logging.info(f"Set QT_PLUGIN_PATH to {QT_PLUGIN_PATH}")
else:
    logging.warning(f"QT_PLUGIN_PATH not found at {QT_PLUGIN_PATH}")

try:
    from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
    from PyQt6.QtGui import QIcon, QAction
    from PyQt6.QtCore import QTimer, Qt
    logging.info("PyQt6 imports successful")
except ImportError as e:
    logging.critical(f"Failed to import PyQt6. Ensure it is installed in the vendor environment. Error: {e}")
    # We can't show a dialog because QApplication failed, but we logged it.
    sys.exit(1)
except Exception as e:
    logging.critical(f"Unexpected error during import: {e}", exc_info=True)
    sys.exit(1)

# --- Configuration ---
PYTHON_EXE = BASE_DIR / "vendor" / "python" / "python.exe"
GO_EXE = "go"

# Log files for services
LOG_FILE_SERVER = LOG_DIR / "server_fastapi.log"
LOG_FILE_SEARCH = LOG_DIR / "service_search.log"
LOG_FILE_PDF = LOG_DIR / "service_pdf.log"

class ServerManagerTray(QSystemTrayIcon):
    def __init__(self, parent=None):
        self.app = parent
        icon_path = str(BASE_DIR / "assets" / "icons" / "pdfCat.ico")
        
        if not os.path.exists(icon_path):
            logging.error(f"Icon not found at {icon_path}")
            # Fallback to standard icon if project icon is missing
            super().__init__(QIcon.fromTheme("network-server"), parent)
        else:
            super().__init__(QIcon(icon_path), parent)
        
        self.processes = {}
        self.setToolTip("pdfCAT Server Manager")
        
        # Setup Menu
        self.menu = QMenu()
        
        self.status_action = QAction("Status: Initializing...")
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)
        
        self.menu.addSeparator()
        
        self.view_logs_action = QAction("Open Logs Folder")
        self.view_logs_action.triggered.connect(self.open_logs)
        self.menu.addAction(self.view_logs_action)
        
        self.restart_action = QAction("Restart All Services")
        self.restart_action.triggered.connect(self.restart_all)
        self.menu.addAction(self.restart_action)
        
        self.menu.addSeparator()
        
        self.exit_action = QAction("Stop Server and Exit")
        self.exit_action.triggered.connect(self.stop_and_exit)
        self.menu.addAction(self.exit_action)
        
        self.setContextMenu(self.menu)
        
        # Start services
        QTimer.singleShot(500, self.start_all)
        
        # Timer to check health
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_health)
        self.timer.start(5000)

    def start_all(self):
        logging.info("Starting all services...")
        self.status_action.setText("Status: Starting services...")
        
        # Ensure ports are free (basic attempt)
        # 1. Start Go Search Service
        self._start_process(
            "search", 
            [GO_EXE, "run", "main.go"], 
            cwd=str(BASE_DIR / "services" / "search-service"),
            log_file=LOG_FILE_SEARCH
        )
        
        # 2. Start Go PDF Service
        self._start_process(
            "pdf_svc", 
            [GO_EXE, "run", "main.go"], 
            cwd=str(BASE_DIR / "services" / "pdf-service"),
            log_file=LOG_FILE_PDF
        )
        
        # 3. Start FastAPI Server
        # We must ensure the vendor python sees our project modules
        env = os.environ.copy()
        env["PYTHONPATH"] = str(BASE_DIR)
        
        self._start_process(
            "fastapi", 
            [str(PYTHON_EXE), "server/main.py"], 
            cwd=str(BASE_DIR),
            log_file=LOG_FILE_SERVER,
            env=env
        )
        
        self.showMessage("pdfCAT Server", "Server services are starting...", QSystemTrayIcon.MessageIcon.Information, 2000)

    def _start_process(self, name, args, cwd, log_file, env=None):
        try:
            f = open(log_file, "a", encoding="utf-8")
            f.write(f"\n--- Starting {name} at {time.ctime()} ---\n")
            f.flush()
            
            logging.info(f"Launching {name}: {args}")
            
            proc = subprocess.Popen(
                args,
                cwd=cwd,
                stdout=f,
                stderr=f,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            self.processes[name] = {"proc": proc, "log": f}
        except Exception as e:
            logging.error(f"CRITICAL: Failed to start {name}: {e}")

    def check_health(self):
        active = 0
        failed = []
        for name, data in self.processes.items():
            if data["proc"].poll() is None:
                active += 1
            else:
                failed.append(name)
        
        if failed:
            self.status_action.setText(f"Status: {', '.join(failed)} FAILED")
            logging.warning(f"Services failed: {failed}")
        elif active == len(self.processes):
            self.status_action.setText("Status: All services RUNNING")
        else:
            self.status_action.setText("Status: Checking...")

    def open_logs(self):
        os.startfile(str(LOG_DIR))

    def restart_all(self):
        logging.info("Manual restart triggered")
        self.stop_all()
        time.sleep(1)
        self.start_all()

    def stop_all(self):
        logging.info("Stopping all services")
        for name, data in self.processes.items():
            try:
                proc = data["proc"]
                logging.info(f"Terminating {name} (PID: {proc.pid})")
                
                # In Windows, we might need taskkill to be sure
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], 
                             creationflags=subprocess.CREATE_NO_WINDOW)
                
                data["log"].close()
            except Exception as e:
                logging.error(f"Error stopping {name}: {e}")
        self.processes = {}

    def stop_and_exit(self):
        self.stop_all()
        logging.info("Tray manager exiting")
        self.app.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    if not QSystemTrayIcon.isSystemTrayAvailable():
        logging.error("System tray is not available")
        sys.exit(1)
        
    app.setQuitOnLastWindowClosed(False)
    
    manager = ServerManagerTray(app)
    manager.show()
    
    logging.info("Manager Tray started successfully")
    sys.exit(app.exec())
