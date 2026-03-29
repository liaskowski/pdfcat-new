from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QGroupBox, QFormLayout,
    QCheckBox, QFileDialog
)
from PyQt6.QtCore import Qt, QSettings
from ..api_manager import APIManager
from ..utils.translator import Translator

class ProfileDialog(QDialog):
    def __init__(self, api: APIManager, current_user: dict, parent=None):
        super().__init__(parent)
        self.api = api
        self.current_user = current_user
        self.translator = Translator()
        self.setWindowTitle(self.translator.tr("profile.title"))
        self.setModal(True)
        
        self.settings = QSettings("pdflib", "client")
        geometry = self.settings.value(f"Geometry/{self.__class__.__name__}")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(500, 600) # Default size, but resizeable

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Info Group
        info_group = QGroupBox(self.translator.tr("profile.title")) 
        info_layout = QFormLayout(info_group)
        info_layout.setSpacing(12)
        
        self.username_edit = QLineEdit(current_user.get("username", ""))
        self.email_edit = QLineEdit(current_user.get("email") or "")
        
        info_layout.addRow(self.translator.tr("auth.username"), self.username_edit)
        info_layout.addRow(self.translator.tr("auth.email"), self.email_edit)
        
        self.public_cb = QCheckBox(self.translator.tr("profile.public_profile"))
        self.public_cb.setChecked(current_user.get("is_public_profile", False))
        info_layout.addRow("", self.public_cb)
        
        layout.addWidget(info_group)

        # Avatar Group
        avatar_group = QGroupBox(self.translator.tr("profile.avatar_label"))
        avatar_layout = QHBoxLayout(avatar_group)
        
        self.avatar_label = QLabel(self.translator.tr("preview.no_avatar"))
        if current_user.get("avatar_url"):
             self.avatar_label.setText(self.translator.tr("profile.avatar_updated")) 
        
        self.change_avatar_btn = QPushButton(self.translator.tr("profile.change_avatar"))
        self.change_avatar_btn.clicked.connect(self._change_avatar)
        
        avatar_layout.addWidget(self.avatar_label)
        avatar_layout.addWidget(self.change_avatar_btn)
        
        layout.addWidget(avatar_group)

        # Password Group
        pwd_group = QGroupBox(self.translator.tr("profile.current_password"))
        pwd_layout = QFormLayout(pwd_group)
        pwd_layout.setSpacing(12)
        
        self.current_pwd_edit = QLineEdit()
        self.current_pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_pwd_edit.setPlaceholderText(self.translator.tr("profile.pwd_placeholder"))
        
        self.new_pwd_edit = QLineEdit()
        self.new_pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        pwd_layout.addRow(self.translator.tr("profile.current_password"), self.current_pwd_edit)
        pwd_layout.addRow(self.translator.tr("profile.new_password"), self.new_pwd_edit)
        
        layout.addWidget(pwd_group)
        
        # Logout
        self.logout_btn = QPushButton(self.translator.tr("profile.logout"))
        self.logout_btn.setObjectName("dangerButton")
        self.logout_btn.clicked.connect(self._on_logout_clicked)
        layout.addWidget(self.logout_btn)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.cancel_btn = QPushButton(self.translator.tr("common.close"))
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton(self.translator.tr("profile.save_changes"))
        self.save_btn.clicked.connect(self._save_changes)
        self.save_btn.setObjectName("primaryButton")
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)

        self.logout_requested = False

    def closeEvent(self, event):
        self.settings.setValue(f"Geometry/{self.__class__.__name__}", self.saveGeometry())
        super().closeEvent(event)

    def _on_logout_clicked(self):
        reply = QMessageBox.question(self, self.translator.tr("profile.logout"), self.translator.tr("profile.logout_confirm"), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.logout_requested = True
            self.reject() # Close dialog

    def _change_avatar(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Avatar", "", "Images (*.png *.jpg *.jpeg)")
        if not file_path:
            return

        try:
            user = self.api.upload_avatar(file_path)
            # Update current user dict
            self.current_user["avatar_url"] = user.get("avatar_url")
            self.avatar_label.setText(self.translator.tr("profile.avatar_updated"))
            QMessageBox.information(self, self.translator.tr("common.success"), self.translator.tr("profile.avatar_success"))
        except Exception as e:
            QMessageBox.critical(self, self.translator.tr("common.error"), f"Failed: {e}")

    def _save_changes(self):
        username = self.username_edit.text().strip()
        email = self.email_edit.text().strip()
        current_pwd = self.current_pwd_edit.text()
        new_pwd = self.new_pwd_edit.text()
        
        updates = {}
        
        if username != self.current_user.get("username"):
            updates["username"] = username
        
        if email != (self.current_user.get("email") or ""):
            updates["email"] = email
            
        is_public = self.public_cb.isChecked()
        if is_public != self.current_user.get("is_public_profile", False):
            updates["is_public_profile"] = is_public

        if new_pwd:
            if not current_pwd:
                QMessageBox.warning(self, self.translator.tr("common.warning"), self.translator.tr("profile.pwd_required"))
                return
            updates["password"] = new_pwd
            updates["current_password"] = current_pwd
            
        if not updates:
            self.accept()
            return

        try:
            self.api.update_me(**updates)
            QMessageBox.information(self, self.translator.tr("common.success"), self.translator.tr("profile.profile_success"))
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, self.translator.tr("common.error"), f"Failed: {e}")

