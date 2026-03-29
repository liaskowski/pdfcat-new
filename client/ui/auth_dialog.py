import json
from typing import Optional
from PyQt6.QtCore import QSettings, Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout, QWidget, QListWidget, QFrame, QFormLayout
)
import qtawesome as qta
from ..api_manager import APIManager
from .forgot_password_dialog import ForgotPasswordDialog
from ..workers.login_worker import LoginWorker
from .server_status import ServerStatusWorker
from ..utils.translator import Translator
from ..workers.discovery_worker import DiscoveryWorker
from ..utils.logger import get_logger, log_info, log_error, log_warning, log_debug

logger = get_logger("client.auth")

class ServerEditDialog(QDialog):
    def __init__(self, parent=None, profile=None):
        super().__init__(parent)
        self.setWindowTitle("Server Details")
        self.setFixedWidth(350)
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit(profile['name'] if profile else "")
        self.name_input.setPlaceholderText("e.g. Office Server")
        
        self.url_input = QLineEdit(profile['url'] if profile else "http://")
        
        self.use_email_cb = QCheckBox("Requires Email for Login")
        if profile: self.use_email_cb.setChecked(profile.get('use_email', False))
        
        layout.addRow("Name:", self.name_input)
        layout.addRow("URL:", self.url_input)
        layout.addRow("", self.use_email_cb)
        
        btns = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        btns.addWidget(save_btn)
        layout.addRow(btns)

    def get_data(self):
        return {
            "name": self.name_input.text().strip() or "Unnamed Server",
            "url": self.url_input.text().strip(),
            "use_email": self.use_email_cb.isChecked()
        }

class ServerSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowSystemMenuHint)
        self.setWindowTitle("Select Server")
        self.setMinimumSize(400, 450)
        self._center_on_screen()
        self.selected_profile = None
        self.profiles = []
        
        layout = QVBoxLayout(self)
        self.profile_list = QListWidget()
        layout.addWidget(QLabel("Available Servers:"))
        layout.addWidget(self.profile_list)
        
        self._load_profiles()
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.edit_btn = QPushButton("Edit")
        self.del_btn = QPushButton("Delete")
        
        self.add_btn.clicked.connect(self.on_add)
        self.edit_btn.clicked.connect(self.on_edit)
        self.del_btn.clicked.connect(self.on_delete)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.del_btn)
        layout.addLayout(btn_layout)
        
        # Scan Button
        self.scan_btn = QPushButton("Scan Network for Servers")
        self.scan_btn.setIcon(qta.icon('fa5s.search', color='black'))
        self.scan_btn.clicked.connect(self.start_scan)
        layout.addWidget(self.scan_btn)
        
        # Connect Button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("primaryButton")
        self.connect_btn.setFixedHeight(40)
        self.connect_btn.clicked.connect(self.on_connect)
        layout.addWidget(self.connect_btn)
        
        self.discovery_worker = DiscoveryWorker()
        self.discovery_worker.server_found.connect(self.on_server_found)

    def _load_profiles(self):
        s = QSettings("pdflib", "client")
        profiles_json = s.value("server_profiles", "[]")
        try:
            self.profiles = json.loads(profiles_json)
        except:
            self.profiles = []
            
        # Migration for legacy single-server config
        if not self.profiles:
            legacy_url = s.value("base_url")
            if legacy_url:
                self.profiles.append({"name": "Default Server", "url": legacy_url, "use_email": False})
                self._save_profiles()
        
        self.refresh_list()

    def _save_profiles(self):
        s = QSettings("pdflib", "client")
        s.setValue("server_profiles", json.dumps(self.profiles))
        s.sync()

    def refresh_list(self):
        self.profile_list.clear()
        for p in self.profiles:
            mail = "[Email]" if p.get("use_email") else ""
            self.profile_list.addItem(f"{p['name']} ({p['url']}) {mail}")

    def on_add(self):
        dlg = ServerEditDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.profiles.append(dlg.get_data())
            self._save_profiles()
            self.refresh_list()

    def on_edit(self):
        row = self.profile_list.currentRow()
        if row < 0: return
        dlg = ServerEditDialog(self, self.profiles[row])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.profiles[row] = dlg.get_data()
            self._save_profiles()
            self.refresh_list()

    def on_delete(self):
        row = self.profile_list.currentRow()
        if row >= 0:
            self.profiles.pop(row)
            self._save_profiles()
            self.refresh_list()

    def start_scan(self):
        self.scan_btn.setText("Scanning...")
        self.scan_btn.setEnabled(False)
        
        if not self.discovery_worker.isRunning():
            self.discovery_worker.start()
        else:
            self.discovery_worker.scan()
            
        # Reset UI after 5 seconds
        QTimer.singleShot(5000, self._reset_scan_btn)

    def _reset_scan_btn(self):
        self.scan_btn.setText("Scan Network for Servers")
        self.scan_btn.setEnabled(True)

    def on_server_found(self, ip, hostname, port):
        url = f"http://{ip}:{port}"
        # Check if already exists in profiles
        for p in self.profiles:
            if p['url'].rstrip('/') == url.rstrip('/'):
                return
            
        # Add to local temporary list and update UI
        new_profile = {"name": f"{hostname} (found)", "url": url, "use_email": False}
        self.profiles.append(new_profile)
        self._save_profiles()
        self.refresh_list()

    def on_connect(self):
        row = self.profile_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selection", "Please select a server.")
            return
        self.selected_profile = self.profiles[row]
        self.accept()

    def _center_on_screen(self):
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().availableGeometry()
        size = self.sizeHint()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(x, y)


class LoginDialog(QDialog):
    def __init__(self, api: APIManager, profile: dict, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowSystemMenuHint)
        self.api = api
        self.profile = profile
        self.translator = Translator()
        self.token = None
        
        self.setWindowTitle(f"Login - {profile['name']}")
        self.setFixedWidth(350)
        self._center_on_screen()
        
        layout = QVBoxLayout(self)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(self.translator.tr("auth.username"))
        layout.addWidget(QLabel(self.translator.tr("auth.username")))
        layout.addWidget(self.username_input)
        
        self.email_input = None
        if profile.get("use_email"):
            self.email_input = QLineEdit()
            self.email_input.setPlaceholderText(self.translator.tr("auth.email"))
            layout.addWidget(QLabel(self.translator.tr("auth.email")))
            layout.addWidget(self.email_input)
            
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText(self.translator.tr("auth.password"))
        layout.addWidget(QLabel(self.translator.tr("auth.password")))
        layout.addWidget(self.password_input)
        
        self.remember_cb = QCheckBox(self.translator.tr("auth.remember_me"))
        layout.addWidget(self.remember_cb)
        
        self.login_btn = QPushButton(self.translator.tr("auth.login_btn"))
        self.login_btn.setObjectName("primaryButton")
        self.login_btn.clicked.connect(self.on_login)
        layout.addWidget(self.login_btn)
        
        self.forgot_btn = QPushButton(self.translator.tr("auth.forgot_password"))
        self.forgot_btn.setFlat(True)
        self.forgot_btn.clicked.connect(self.on_forgot)
        layout.addWidget(self.forgot_btn)
        
        self._load_creds()

    def _get_stable_key(self, url: str) -> str:
        # Create a stable key from URL by removing special characters
        import re
        clean_url = re.sub(r'[^a-zA-Z0-9]', '_', url)
        return f"creds_{clean_url}"

    def _load_creds(self):
        s = QSettings("pdflib", "client")
        key_prefix = self._get_stable_key(self.profile['url'])
        
        remember = s.value(f"{key_prefix}/remember", "false")
        if str(remember).lower() == "true":
            self.remember_cb.setChecked(True)
            self.username_input.setText(s.value(f"{key_prefix}/username", ""))
            if self.email_input:
                self.email_input.setText(s.value(f"{key_prefix}/email", ""))

    def _save_creds(self, token):
        try:
            s = QSettings("pdflib", "client")
            key_prefix = self._get_stable_key(self.profile['url'])

            if self.remember_cb.isChecked():
                # Save credentials for future auto-login
                s.setValue(f"{key_prefix}/remember", "true")
                s.setValue(f"{key_prefix}/username", self.username_input.text())
                if self.email_input:
                    s.setValue(f"{key_prefix}/email", self.email_input.text())
                
                # Save session token for auto-login
                s.setValue("token", token)
                s.setValue("base_url", self.profile['url'])
                log_info("auth", f"Credentials saved for user: {self.username_input.text()}")
            else:
                # Don't save anything
                s.setValue(f"{key_prefix}/remember", "false")
                s.remove(f"{key_prefix}/username")
                s.remove(f"{key_prefix}/email")
                # Don't save token if "Remember Me" not checked
                s.remove("token")
                s.remove("base_url")
                log_info("auth", "Credentials not saved (Remember Me unchecked)")
            
            s.sync()
            log_debug("auth", "Settings synced")
        except Exception as e:
            log_error("auth", f"Failed to save credentials: {e}", exc_info=True)

    def on_login(self):
        u = self.username_input.text().strip()
        p = self.password_input.text()
        e = self.email_input.text().strip() if self.email_input else None
        
        if not u or not p:
            QMessageBox.warning(self, "Error", "Username and Password required")
            return
            
        if self.email_input and not e:
             QMessageBox.warning(self, "Error", "Email is required for this server")
             return

        # Check server status before attempting login
        self._check_server_and_login(u, p, e)

    def _check_server_and_login(self, username: str, password: str, email: str):
        """Check server status before attempting login."""
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Checking server...")
        
        # Create worker for server status check
        self.status_worker = ServerStatusWorker(self.api)
        self.status_worker.finished.connect(self._on_server_status_checked)
        self.status_worker.error.connect(self._on_server_status_error)
        self.status_worker.username = username
        self.status_worker.password = password
        self.status_worker.email = email
        self.status_worker.start()

    def _on_server_status_checked(self, is_online: bool):
        """Handle server status check result."""
        if not is_online:
            self._show_server_offline_dialog()
        else:
            # Server is online, proceed with login
            self._proceed_with_login()

    def _on_server_status_error(self, error_msg: str):
        """Handle server status check error."""
        self._show_server_error_dialog(error_msg)

    def _show_server_offline_dialog(self):
        """Show dialog when server is offline."""
        reply = QMessageBox.question(
            self,
            "Server Offline",
            "The server is not responding. Would you like to:\n\n"
            "1. Try again\n"
            "2. Start the server automatically\n"
            "3. Cancel login",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Try again
            self._check_server_and_login(
                self.status_worker.username,
                self.status_worker.password,
                self.status_worker.email
            )
        elif reply == QMessageBox.StandardButton.No:
            # Try to start server
            self._try_start_server()
        else:
            # Cancel login
            self._reset_login_button()

    def _show_server_error_dialog(self, error_msg: str):
        """Show dialog when server status check fails."""
        reply = QMessageBox.question(
            self,
            "Server Error",
            f"Failed to check server status: {error_msg}\n\n"
            "Would you like to:\n\n"
            "1. Try anyway\n"
            "2. Try again\n"
            "3. Cancel login",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Try login anyway
            self._proceed_with_login()
        elif reply == QMessageBox.StandardButton.No:
            # Try again
            self._check_server_and_login(
                self.status_worker.username,
                self.status_worker.password,
                self.status_worker.email
            )
        else:
            # Cancel login
            self._reset_login_button()

    def _try_start_server(self):
        """Try to start the server automatically."""
        self.login_btn.setText("Starting server...")
        
        # Use the server status monitor to start server
        from .server_status import ServerStatusMonitor
        self.server_monitor = ServerStatusMonitor()
        self.server_monitor.status_changed.connect(self._on_server_start_status)
        self.server_monitor.server_started.connect(self._on_server_started)
        self.server_monitor.start_server()

    def _on_server_start_status(self, status: str, message: str):
        """Handle server start status updates."""
        self.login_btn.setText(message)
        
        if status == "error":
            self._reset_login_button()
            QMessageBox.critical(self, "Server Error", f"Failed to start server: {message}")

    def _on_server_started(self):
        """Handle successful server start."""
        # Wait a moment for server to fully initialize
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self._check_server_and_login(
            self.status_worker.username,
            self.status_worker.password,
            self.status_worker.email
        ))

    def _proceed_with_login(self):
        """Proceed with login after server status check."""
        self.login_btn.setText("Logging in...")
        
        self.worker = LoginWorker(
            self.api,
            self.status_worker.username,
            self.status_worker.password,
            self.status_worker.email
        )
        self.worker.finished.connect(self.on_success)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def _reset_login_button(self):
        """Reset login button to original state."""
        self.login_btn.setEnabled(True)
        self.login_btn.setText(self.translator.tr("auth.login_btn"))

    def on_success(self, token):
        self.token = token
        self._save_creds(token)
        self.accept()

    def on_error(self, msg):
        self.login_btn.setEnabled(True)
        self.login_btn.setText(self.translator.tr("auth.login_btn"))
        QMessageBox.critical(self, "Login Failed", msg)

    def on_forgot(self):
        ForgotPasswordDialog(self.api, self).exec()

    def _center_on_screen(self):
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().availableGeometry()
        size = self.sizeHint()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(x, y)
