from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox, QStackedWidget, QWidget, QFormLayout
)
from PyQt6.QtCore import Qt
import re
from ..api_manager import APIManager
from ..utils.translator import Translator

class ForgotPasswordDialog(QDialog):
    def __init__(self, api: APIManager, parent=None):
        super().__init__(parent)
        self.api = api
        self.translator = Translator()
        self.setWindowTitle(self.translator.tr("forgot_pwd.title"))
        self.resize(450, 350)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel(self.translator.tr("forgot_pwd.title"))
        header.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(header)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Step 1
        self.step1 = QWidget()
        s1_layout = QVBoxLayout(self.step1)
        s1_layout.setContentsMargins(0, 0, 0, 0)
        s1_layout.setSpacing(15)
        
        s1_layout.addWidget(QLabel(self.translator.tr("forgot_pwd.info_email")))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText(self.translator.tr("forgot_pwd.email_placeholder"))
        self.email_input.setFixedHeight(36)
        s1_layout.addWidget(self.email_input)
        
        self.btn_send = QPushButton(self.translator.tr("forgot_pwd.send_code"))
        self.btn_send.setObjectName("primaryButton")
        self.btn_send.setFixedHeight(40)
        self.btn_send.clicked.connect(self._send_code)
        s1_layout.addWidget(self.btn_send)
        s1_layout.addStretch()
        
        self.stack.addWidget(self.step1)

        # Step 2
        self.step2 = QWidget()
        s2_layout = QVBoxLayout(self.step2)
        s2_layout.setContentsMargins(0, 0, 0, 0)
        s2_layout.setSpacing(15)
        
        s2_layout.addWidget(QLabel(self.translator.tr("forgot_pwd.info_code")))
        
        form = QFormLayout()
        self.code_input = QLineEdit()
        self.new_pwd = QLineEdit()
        self.new_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.conf_pwd = QLineEdit()
        self.conf_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        
        form.addRow("Code:", self.code_input)
        form.addRow("New Pwd:", self.new_pwd)
        form.addRow("Confirm:", self.conf_pwd)
        s2_layout.addLayout(form)
        
        self.btn_reset = QPushButton(self.translator.tr("forgot_pwd.reset_btn"))
        self.btn_reset.setObjectName("primaryButton")
        self.btn_reset.setFixedHeight(40)
        self.btn_reset.clicked.connect(self._reset_password)
        s2_layout.addWidget(self.btn_reset)
        s2_layout.addStretch()
        
        self.stack.addWidget(self.step2)

    def _send_code(self):
        email = self.email_input.text().strip()
        if "@" not in email: return
        try:
            self.api.forgot_password(email)
            self.email = email
            self.stack.setCurrentIndex(1)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _reset_password(self):
        code = self.code_input.text().strip()
        pwd = self.new_pwd.text()
        if pwd != self.conf_pwd.text(): return
        try:
            self.api.reset_password(self.email, code, pwd)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))