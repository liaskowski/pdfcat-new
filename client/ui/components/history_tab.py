from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QHeaderView, QLabel, QTableWidgetItem
)
from ...utils.translator import Translator
from ...api_manager import APIManager

class HistoryTab(QWidget):
    def __init__(self, api: APIManager, doc_id: int, parent=None):
        super().__init__(parent)
        self.api = api
        self.doc_id = doc_id
        self.translator = Translator()
        self._init_ui()
        self._load_history()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels([
            self.translator.tr("upload.history_date"), 
            self.translator.tr("upload.history_user"), 
            self.translator.tr("upload.history_action"), 
            self.translator.tr("upload.history_details")
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSortingEnabled(True) # Enabled sorting
        
        layout.addWidget(self.history_table)

    def _load_history(self):
        try:
            history = self.api.get_document_history(self.doc_id)
            self.history_table.setRowCount(len(history))
            for i, entry in enumerate(history):
                # Date format
                date_str = entry.changed_at.replace("T", " ").split(".")[0]
                
                self.history_table.setItem(i, 0, QTableWidgetItem(date_str))
                
                user_text = entry.changed_by_username if entry.changed_by_username else f"User {entry.changed_by_id}"
                self.history_table.setItem(i, 1, QTableWidgetItem(user_text))
                
                self.history_table.setItem(i, 2, QTableWidgetItem(entry.change_type))
                
                details = ""
                if entry.field_changed:
                    details = f"Changed {entry.field_changed}"
                    if entry.old_value and len(entry.old_value) < 20:
                         details += f" from '{entry.old_value}'"
                    if entry.new_value and len(entry.new_value) < 20:
                         details += f" to '{entry.new_value}'"
                elif entry.new_value:
                    details = entry.new_value
                
                self.history_table.setItem(i, 3, QTableWidgetItem(details))
        except Exception as e:
            # We can't easily add a widget here without breaking layout, 
            # but we can print or maybe add a row
            print(f"History load failed: {e}")