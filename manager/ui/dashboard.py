from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGridLayout, QFrame, QPushButton, 
    QMessageBox, QFileDialog, QTabWidget, QHBoxLayout
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import time
import os

class StatsWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api):
        super().__init__()
        self.api = api

    def run(self):
        try:
            stats = self.api.get_stats()
            self.finished.emit(stats)
        except Exception as e:
            self.error.emit(str(e))

class MaintenanceWorker(QThread):
    finished_msg = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api, action, data=None):
        super().__init__()
        self.api = api
        self.action = action
        self.data = data

    def run(self):
        try:
            if self.action == "reindex":
                msg = self.api.reindex()
                self.finished_msg.emit(msg)
            elif self.action == "backup":
                self.api.save_backup_to_file(self.data)
                self.finished_msg.emit("Backup saved successfully")
        except Exception as e:
            self.error.emit(str(e))

class DashboardWidget(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.init_ui()
        self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # --- Stats Tab ---
        self.stats_tab = QWidget()
        stats_layout = QVBoxLayout(self.stats_tab)
        
        header = QLabel("System Dashboard")
        header.setStyleSheet("font-size: 18pt; font-weight: bold;")
        stats_layout.addWidget(header)
        
        self.grid = QGridLayout()
        self.cards = {
            "users": self.create_card("Total Users", "0"),
            "docs": self.create_card("Documents", "0"),
            "storage": self.create_card("Storage Used", "0 MB"),
            "cpu": self.create_card("CPU Load", "0%"),
            "ram": self.create_card("RAM Usage", "0%")
        }
        self.grid.addWidget(self.cards["users"], 0, 0)
        self.grid.addWidget(self.cards["docs"], 0, 1)
        self.grid.addWidget(self.cards["storage"], 0, 2)
        self.grid.addWidget(self.cards["cpu"], 1, 0)
        self.grid.addWidget(self.cards["ram"], 1, 1)
        stats_layout.addLayout(self.grid)
        
        self.refresh_btn = QPushButton("Refresh Data")
        self.refresh_btn.clicked.connect(self.refresh)
        stats_layout.addWidget(self.refresh_btn)
        stats_layout.addStretch()
        
        self.tabs.addTab(self.stats_tab, "Statistics")
        
        # --- Maintenance Tab ---
        self.maint_tab = QWidget()
        maint_layout = QVBoxLayout(self.maint_tab)
        
        maint_layout.addWidget(QLabel("<b>Server Maintenance Tools</b>"))
        
        self.backup_btn = QPushButton("Create System Backup (ZIP)")
        self.backup_btn.setMinimumHeight(50)
        self.backup_btn.clicked.connect(self.on_backup)
        
        self.open_backups_btn = QPushButton("Open Backups Folder")
        self.open_backups_btn.setMinimumHeight(30)
        self.open_backups_btn.clicked.connect(self.on_open_backups)
        
        self.reindex_btn = QPushButton("Trigger Full PDF Re-indexing")
        self.reindex_btn.setMinimumHeight(50)
        self.reindex_btn.clicked.connect(self.on_reindex)
        
        maint_layout.addWidget(self.backup_btn)
        maint_layout.addWidget(self.open_backups_btn)
        maint_layout.addSpacing(20) # Spacer
        maint_layout.addWidget(self.reindex_btn)
        maint_layout.addStretch()
        
        self.tabs.addTab(self.maint_tab, "Maintenance")
        
        layout.addWidget(self.tabs)

    def on_open_backups(self):
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        # Backups are in project_root/backups
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backups"))
        if not os.path.exists(base_path):
            os.makedirs(base_path, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(base_path))

    def create_card(self, title, value):
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        layout = QVBoxLayout(frame)
        t_label = QLabel(title)
        t_label.setStyleSheet("color: gray;")
        v_label = QLabel(value)
        v_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(t_label)
        layout.addWidget(v_label)
        frame.v_label = v_label
        return frame

    def refresh(self):
        self.refresh_btn.setEnabled(False)
        self.worker = StatsWorker(self.api)
        self.worker.finished.connect(self.on_stats_received)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_stats_received(self, stats):
        self.refresh_btn.setEnabled(True)
        db = stats.get("database", {})
        sys = stats.get("system", {})
        storage = stats.get("storage", {})
        self.cards["users"].v_label.setText(str(db.get("users", "0")))
        self.cards["docs"].v_label.setText(str(db.get("documents", "0")))
        bytes_val = storage.get("upload_dir_bytes", 0)
        mb_val = bytes_val / (1024 * 1024)
        self.cards["storage"].v_label.setText(f"{mb_val:.2f} MB")
        self.cards["cpu"].v_label.setText(f"{sys.get('cpu_percent', 0)}%")
        self.cards["ram"].v_label.setText(f"{sys.get('ram_percent', 0)}%")

    def on_error(self, err):
        self.refresh_btn.setEnabled(True)
        for card in self.cards.values():
            card.v_label.setText("Error")
            card.v_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #f44336;")

    def on_reindex(self):
        confirm = QMessageBox.question(self, "Reindex", "This will re-process all documents. Continue?")
        if confirm == QMessageBox.StandardButton.Yes:
            self.reindex_btn.setEnabled(False)
            self.m_worker = MaintenanceWorker(self.api, "reindex")
            self.m_worker.finished_msg.connect(lambda msg: (QMessageBox.information(self, "Success", msg), self.reindex_btn.setEnabled(True)))
            self.m_worker.error.connect(lambda e: (QMessageBox.critical(self, "Error", e), self.reindex_btn.setEnabled(True)))
            self.m_worker.start()

    def on_backup(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Backup", "server_backup.zip", "Zip Files (*.zip)")
        if path:
            self.backup_btn.setEnabled(False)
            self.m_worker = MaintenanceWorker(self.api, "backup", path)
            self.m_worker.finished_msg.connect(lambda msg: (QMessageBox.information(self, "Success", msg), self.backup_btn.setEnabled(True)))
            self.m_worker.error.connect(lambda e: (QMessageBox.critical(self, "Error", e), self.backup_btn.setEnabled(True)))
            self.m_worker.start()
