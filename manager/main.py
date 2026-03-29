import sys
import os
import json
import subprocess
import time
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QPushButton, QDialog, QLineEdit, QLabel, QMessageBox,
    QStackedWidget, QInputDialog, QFrame, QFormLayout, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from .api_client.client import ManagerAPIClient
from .logic.health_check import ServerHealthCheckService
from .ui.dashboard import DashboardWidget
from .ui.user_management import UserManagementWidget
from .ui.dict_editor import DictEditorWidget
from .ui.history_log import HistoryLogWidget
from .ui.auto_tag import AutoTagWidget

class LoginWorker(QThread):
    finished = pyqtSignal(bool)
    def __init__(self, api, u, p):
        super().__init__()
        self.api, self.u, self.p = api, u, p
    def run(self):
        result = self.api.login(self.u, self.p)
        self.finished.emit(result)

class ProfileEditDialog(QDialog):
    def __init__(self, parent=None, profile=None):
        super().__init__(parent)
        self.setWindowTitle("Server Profile Settings")
        self.setFixedWidth(380)
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit(profile['name'] if profile else "")
        self.url_input = QLineEdit(profile['url'] if profile else "http://127.0.0.1:8000")
        
        self.use_email_cb = QCheckBox("Enable Email field in Login")
        if profile: self.use_email_cb.setChecked(profile.get('use_email', False))
        
        self.local_cb = QCheckBox("Local Instance (Run/Stop from Manager)")
        if profile: self.local_cb.setChecked(profile.get('local', False))
        
        layout.addRow("Profile Name:", self.name_input)
        layout.addRow("Server URL:", self.url_input)
        layout.addRow("", self.use_email_cb)
        layout.addRow("", self.local_cb)
        
        btns = QHBoxLayout()
        save_btn = QPushButton("Save Profile")
        save_btn.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white; height: 30px;")
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btns.addStretch()
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addRow(btns)

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "url": self.url_input.text().strip(),
            "use_email": self.use_email_cb.isChecked(),
            "local": self.local_cb.isChecked()
        }

class ProfileSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowSystemMenuHint)
        self.setWindowTitle("PDFLibrary Manager - Select Profile")
        self.setMinimumSize(450, 400)
        self._center_on_screen()
        self.selected_profile = None
        
        layout = QVBoxLayout(self)
        self.profile_list = QListWidget()
        layout.addWidget(QLabel("<b>1. Choose a server profile:</b>"))
        layout.addWidget(self.profile_list)
        
        self.profiles = []
        self.load_profiles()
        
        mgmt_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add New Profile")
        self.edit_btn = QPushButton("Edit Selected")
        self.del_btn = QPushButton("Delete")
        
        self.add_btn.clicked.connect(self.on_add_profile)
        self.edit_btn.clicked.connect(self.on_edit_profile)
        self.del_btn.clicked.connect(self.on_delete_profile)
        
        mgmt_layout.addWidget(self.add_btn)
        mgmt_layout.addWidget(self.edit_btn)
        mgmt_layout.addWidget(self.del_btn)
        layout.addLayout(mgmt_layout)
        
        self.select_btn = QPushButton("Next: Login to Selected Server")
        self.select_btn.setStyleSheet("font-weight: bold; height: 45px; background-color: #2196F3; color: white;")
        self.select_btn.clicked.connect(self.on_select)
        layout.addWidget(self.select_btn)

    def load_profiles(self):
        self.profile_list.clear()
        if os.path.exists("profiles.json"):
            try:
                with open("profiles.json", "r") as f:
                    self.profiles = json.load(f)
                    for p in self.profiles:
                        type_tag = "[LOCAL]" if p.get("local") else "[REMOTE]"
                        mail_tag = "+MAIL" if p.get("use_email") else ""
                        self.profile_list.addItem(f"{type_tag} {p['name']} - {p['url']} {mail_tag}")
            except: self.profiles = []
        else: self.profiles = []

    def save_profiles(self):
        with open("profiles.json", "w") as f: json.dump(self.profiles, f, indent=4)

    def on_add_profile(self):
        dlg = ProfileEditDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if data["name"] and data["url"]:
                self.profiles.append(data)
                self.save_profiles()
                self.load_profiles()

    def on_edit_profile(self):
        idx = self.profile_list.currentRow()
        if idx < 0: return
        dlg = ProfileEditDialog(self, self.profiles[idx])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.profiles[idx] = dlg.get_data()
            self.save_profiles()
            self.load_profiles()

    def on_delete_profile(self):
        idx = self.profile_list.currentRow()
        if idx >= 0:
            if QMessageBox.question(self, "Confirm", "Delete this profile?") == QMessageBox.StandardButton.Yes:
                self.profiles.pop(idx)
                self.save_profiles()
                self.load_profiles()

    def on_select(self):
        idx = self.profile_list.currentRow()
        if idx >= 0:
            self.selected_profile = self.profiles[idx]
            self.accept()

    def _center_on_screen(self):
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().availableGeometry()
        size = self.sizeHint()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(x, y)

class LoginDialog(QDialog):
    def __init__(self, api: ManagerAPIClient, use_email: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowSystemMenuHint)
        self.api = api
        self.setWindowTitle("Admin Login")
        self.setFixedWidth(320)
        self._center_on_screen()
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.username = QLineEdit("admin")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        
        form.addRow("Username:", self.username)
        form.addRow("Password:", self.password)
        
        self.email = None
        if use_email:
            self.email = QLineEdit()
            self.email.setPlaceholderText("Optional Admin Email")
            form.addRow("Email:", self.email)
            
        layout.addLayout(form)
        
        self.login_btn = QPushButton("Connect to Manager")
        self.login_btn.setFixedHeight(40)
        self.login_btn.setStyleSheet("font-weight: bold;")
        self.login_btn.clicked.connect(self.on_login)
        layout.addWidget(self.login_btn)

    def on_login(self):
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Authenticating...")
        self.worker = LoginWorker(self.api, self.username.text(), self.password.text())
        self.worker.finished.connect(self.on_auth_finished)
        self.worker.start()

    def on_auth_finished(self, success):
        if success: self.accept()
        else:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Connect to Manager")
            QMessageBox.critical(self, "Error", "Login failed. Check credentials or server.")

    def _center_on_screen(self):
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().availableGeometry()
        size = self.sizeHint()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(x, y)

class ManagerMainWindow(QMainWindow):
    def __init__(self, profile: dict, api: ManagerAPIClient):
        super().__init__()
        self.profile, self.api = profile, api
        self.setWindowTitle(f"PDFLibrary Manager - {profile['name']}")
        self.resize(1100, 800)
        self.server_process = None
        self.init_ui()
        self.health_check = ServerHealthCheckService(profile['url'])
        self.health_check.status_changed.connect(self.update_health_status)
        self.health_check.start()
        if self.profile.get("local"): self.toggle_server(True)

    def toggle_server(self, start=True):
        if start:
            if self.server_process and self.server_process.poll() is None: return
            try:
                env = os.environ.copy()
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                site_packages = os.path.join(base_dir, "vendor", "python", "Lib", "site-packages")
                env["PYTHONPATH"] = f"{base_dir};{site_packages};{env.get('PYTHONPATH', '')}"
                server_script = os.path.join(base_dir, "server", "main.py")
                self.server_process = subprocess.Popen([sys.executable, server_script], env=env, cwd=base_dir, creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
                self.update_server_btn(True)
            except Exception as e: QMessageBox.critical(self, "Error", f"Failed: {e}")
        else:
            if self.server_process: self.server_process.terminate(); self.server_process = None; self.update_server_btn(False)

    def update_server_btn(self, is_running):
        self.start_stop_btn.setText("Stop Local Server" if is_running else "Start Local Server")
        self.start_stop_btn.setStyleSheet("background-color: #f44336; color: white;" if is_running else "background-color: #4CAF50; color: white;")

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        sidebar = QWidget(); sidebar.setFixedWidth(220); side_layout = QVBoxLayout(sidebar)
        side_layout.addWidget(QLabel("<b>MANAGEMENT</b>"))
        self.nav_list = QListWidget(); self.nav_list.addItems(["Dashboard", "User Management", "Dictionary Editor", "Auto-Tagging", "History Log"])
        self.nav_list.currentRowChanged.connect(self.on_nav_changed); side_layout.addWidget(self.nav_list); side_layout.addStretch()
        if self.profile.get("local"):
            self.start_stop_btn = QPushButton("Start Local Server")
            self.start_stop_btn.clicked.connect(lambda: self.toggle_server(self.server_process is None or self.server_process.poll() is not None))
            side_layout.addWidget(self.start_stop_btn); self.update_server_btn(False)
        self.health_label = QLabel("Status: Checking..."); side_layout.addWidget(self.health_label); main_layout.addWidget(sidebar)
        self.stack = QStackedWidget()
        self.stack.addWidget(DashboardWidget(self.api))
        self.stack.addWidget(UserManagementWidget(self.api))
        self.stack.addWidget(DictEditorWidget(self.api))
        self.stack.addWidget(AutoTagWidget(self.api))
        self.stack.addWidget(HistoryLogWidget(self.api))
        main_layout.addWidget(self.stack, 1)

    def on_nav_changed(self, index):
        self.stack.setCurrentIndex(index)
        widget = self.stack.currentWidget()
        if hasattr(widget, "refresh"): widget.refresh()
        elif hasattr(widget, "refresh_all"): widget.refresh_all()

    def update_health_status(self, is_online, message):
        color = "green" if is_online else "red"
        self.health_label.setText(f"Status: <span style='color:{color}'>{message}</span>")

    def closeEvent(self, event):
        if self.server_process: self.server_process.terminate()
        self.health_check.stop(); super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    prof_dlg = ProfileSelectionDialog()
    if prof_dlg.exec() != QDialog.DialogCode.Accepted: return
    profile = prof_dlg.selected_profile
    api = ManagerAPIClient(profile['url'])
    login_dlg = LoginDialog(api, use_email=profile.get("use_email", False))
    if login_dlg.exec() != QDialog.DialogCode.Accepted: return
    window = ManagerMainWindow(profile, api)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
