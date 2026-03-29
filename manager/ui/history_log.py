from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt

class HistoryLogWidget(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.init_ui()
        self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("Refresh Logs")
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Time", "User", "Action", "Field", "Detail"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

    def refresh(self):
        if not self.api:
            return
        try:
            logs = self.api.get_history()
            self.table.setRowCount(0)
            self.table.setColumnCount(3)
            self.table.setHorizontalHeaderLabels(["Date/Time", "User", "Activity Description"])
            
            for log in logs:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # Format time
                dt = log["changed_at"].split(".")[0].replace("T", " ")
                user = log.get("changed_by_username", f"User #{log['changed_by_id']}")
                
                # Format description
                desc = self.format_log(log)
                
                self.table.setItem(row, 0, QTableWidgetItem(dt))
                self.table.setItem(row, 1, QTableWidgetItem(user))
                self.table.setItem(row, 2, QTableWidgetItem(desc))
        except Exception as e:
            print(f"Log error: {e}")

    def format_log(self, log):
        ctype = log["change_type"]
        field = log.get("field_changed", "")
        doc_id = log.get("document_id", "?")
        
        if ctype == "create":
            return f"Uploaded new document (ID: {doc_id})"
        elif ctype == "update":
            return f"Updated '{field}' of document #{doc_id}"
        elif ctype == "content_update":
            return f"Replaced file content for document #{doc_id}"
        elif ctype == "delete":
            return f"Deleted document #{doc_id}"
        
        return f"{ctype} on doc #{doc_id} (field: {field})"
