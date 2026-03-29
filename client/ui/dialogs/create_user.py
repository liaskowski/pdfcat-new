from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QComboBox, QPushButton, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from ...api_manager import APIManager
from ...utils.translator import Translator

class CreateUserWidget(QGroupBox):
    user_created = pyqtSignal()

    def __init__(self, api: APIManager, parent=None):
        self.translator = Translator()
        super().__init__(self.translator.tr("admin.create_user_title"), parent)
        self.api = api
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 15)
        layout.setSpacing(10)

        # Form
        form_layout = QHBoxLayout()
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(self.translator.tr("admin.username"))
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText(self.translator.tr("admin.email"))
        
        self.role_combo = QComboBox()
        self.role_combo.addItems(["user", "admin"])
        
        form_layout.addWidget(self.username_input)
        form_layout.addWidget(self.email_input)
        form_layout.addWidget(self.role_combo)
        
        layout.addLayout(form_layout)
        
        create_btn = QPushButton(self.translator.tr("admin.create_btn"))
        create_btn.setObjectName("primaryButton")
        create_btn.clicked.connect(self._create_user)
        layout.addWidget(create_btn, 0, Qt.AlignmentFlag.AlignRight)

    def _create_user(self):
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        role = self.role_combo.currentText()

        if not username:
            QMessageBox.warning(self, self.translator.tr("common.warning"), self.translator.tr("admin.validation_username"))
            return

        try:
            self.api.create_user(
                username=username,
                email=email if email else None,
                role=role
            )
            QMessageBox.information(self, self.translator.tr("common.success"), self.translator.tr("admin.user_created"))
            self.username_input.clear()
            self.email_input.clear()
            self.user_created.emit()
        except Exception as e:
            QMessageBox.critical(self, self.translator.tr("common.error"), f"Failed: {e}")

