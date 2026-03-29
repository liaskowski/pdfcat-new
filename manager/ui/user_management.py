from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
    QPushButton, QHeaderView, QMessageBox, QInputDialog, QDialog,
    QLineEdit, QLabel, QComboBox, QFormLayout
)
from PyQt6.QtCore import QThread, pyqtSignal

class UserDialog(QDialog):
    def __init__(self, parent=None, edit_mode=False):
        super().__init__(parent)
        self.setWindowTitle("Edit User" if edit_mode else "Create User")
        self.setFixedWidth(350)
        
        layout = QFormLayout(self)
        
        self.username = QLineEdit()
        self.email = QLineEdit()
        self.password = QLineEdit()
        self.password.setPlaceholderText("Leave empty for auto-gen" if not edit_mode else "Enter new password")
        
        self.role = QComboBox()
        self.role.addItems(["user", "admin"])
        
        layout.addRow("Username:", self.username)
        layout.addRow("Email:", self.email)
        layout.addRow("Password:", self.password)
        layout.addRow("Role:", self.role)
        
        self.btns = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        self.btns.addWidget(self.cancel_btn)
        self.btns.addWidget(self.save_btn)
        layout.addRow(self.btns)

class UserWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api, action="list", data=None):
        super().__init__()
        self.api = api
        self.action = action
        self.data = data

    def run(self):
        try:
            if self.action == "list":
                users = self.api.get_users()
                self.finished.emit(users)
            elif self.action == "delete":
                self.api.delete_user(self.data)
                self.finished.emit([])
            elif self.action == "create":
                self.api.create_user(**self.data)
                self.finished.emit([])
            elif self.action == "change_password":
                self.api.admin_change_password(self.data["id"], self.data["password"])
                self.finished.emit([])
        except Exception as e:
            self.error.emit(str(e))

class UserManagementWidget(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.init_ui()
        self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("Add User")
        self.refresh_btn = QPushButton("Refresh")
        self.pass_btn = QPushButton("Change Password")
        self.delete_btn = QPushButton("Delete Selected")
        
        self.add_btn.clicked.connect(self.on_add_user)
        self.refresh_btn.clicked.connect(self.refresh)
        self.pass_btn.clicked.connect(self.on_change_password)
        self.delete_btn.clicked.connect(self.on_delete_user)
        
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.pass_btn)
        toolbar.addWidget(self.delete_btn)
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
        
        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Username", "Email", "Role"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

    def refresh(self):
        self.worker = UserWorker(self.api, "list")
        self.worker.finished.connect(self.populate_table)
        self.worker.error.connect(lambda e: QMessageBox.critical(self, "Error", e))
        self.worker.start()

    def populate_table(self, users):
        self.table.setRowCount(0)
        for user in users:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(user["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(user["username"]))
            self.table.setItem(row, 2, QTableWidgetItem(user.get("email", "")))
            self.table.setItem(row, 3, QTableWidgetItem(user["role"]))

    def on_add_user(self):
        dlg = UserDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = {
                "username": dlg.username.text(),
                "email": dlg.email.text() if dlg.email.text() else None,
                "password": dlg.password.text() if dlg.password.text() else None,
                "role": dlg.role.currentText()
            }
            self.worker = UserWorker(self.api, "create", data)
            self.worker.finished.connect(self.refresh)
            self.worker.error.connect(lambda e: QMessageBox.critical(self, "Error", e))
            self.worker.start()

    def on_change_password(self):
        row = self.table.currentRow()
        if row < 0: return
        
        user_id = int(self.table.item(row, 0).text())
        username = self.table.item(row, 1).text()
        
        new_pass, ok = QInputDialog.getText(self, "Password", f"New password for {username}:", QLineEdit.EchoMode.Password)
        if ok and new_pass:
            self.worker = UserWorker(self.api, "change_password", {"id": user_id, "password": new_pass})
            self.worker.finished.connect(lambda: QMessageBox.information(self, "Success", "Password updated"))
            self.worker.error.connect(lambda e: QMessageBox.critical(self, "Error", e))
            self.worker.start()

    def on_delete_user(self):
        row = self.table.currentRow()
        if row < 0: return
        
        user_id = int(self.table.item(row, 0).text())
        confirm = QMessageBox.question(self, "Confirm", f"Delete user {user_id}?")
        if confirm == QMessageBox.StandardButton.Yes:
            self.worker = UserWorker(self.api, "delete", user_id)
            self.worker.finished.connect(self.refresh)
            self.worker.error.connect(lambda e: QMessageBox.critical(self, "Error", e))
            self.worker.start()
