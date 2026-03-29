
from typing import Optional, List, Union

from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QListWidget,
    QPushButton,
    QInputDialog,
    QMessageBox,
    QListWidgetItem,
    QAbstractItemView,
    QLabel,
    QFrame
)
from PyQt6.QtCore import Qt, QSize
from ..utils.translator import Translator
from ..api_manager import APIManager
from ..api.schemas import APICategory, APIFileType

class ManagementTab(QWidget):
    def __init__(
        self,
        lang_key: str,
        api: APIManager,
        get_all_func,
        create_func,
        delete_func,
        update_func,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.lang_key = lang_key
        self.api = api
        self.get_all_func = get_all_func
        self.create_func = create_func
        self.delete_func = delete_func
        self.update_func = update_func
        self.translator = Translator()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        # Убрали инлайн стили, полагаемся на themes.py
        self.list_widget.setAlternatingRowColors(True)
        layout.addWidget(self.list_widget)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        self.btn_add = QPushButton(self.translator.tr("common.add"))
        self.btn_add.setObjectName("primaryButton")
        self.btn_add.setFixedHeight(32)
        
        self.btn_edit = QPushButton(self.translator.tr("common.edit"))
        self.btn_edit.setFixedHeight(32)
        
        self.btn_delete = QPushButton(self.translator.tr("common.delete"))
        self.btn_delete.setObjectName("dangerButton")
        self.btn_delete.setFixedHeight(32)

        buttons_layout.addWidget(self.btn_add)
        buttons_layout.addWidget(self.btn_edit)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_delete)
        layout.addLayout(buttons_layout)
        
        self.btn_add.clicked.connect(self._on_add)
        self.btn_edit.clicked.connect(self._on_edit_click)
        self.btn_delete.clicked.connect(self._on_delete)
        
        self.load_items()

    def load_items(self):
        try:
            items = self.get_all_func()
            self.list_widget.clear()
            for item in items:
                list_item = QListWidgetItem(item.name)
                list_item.setData(Qt.ItemDataRole.UserRole, item)
                self.list_widget.addItem(list_item)
        except Exception as e:
            print(f"Load Error: {e}")

    def _on_add(self):
        label = self.translator.tr(self.lang_key)
        text, ok = QInputDialog.getText(self, self.translator.tr("manage.new_item").format(item=label), label)
        if ok and text.strip():
            try:
                self.create_func(text.strip())
                self.load_items()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _on_edit_click(self):
        item = self.list_widget.currentItem()
        if not item: return
        data = item.data(Qt.ItemDataRole.UserRole)
        label = self.translator.tr(self.lang_key)
        text, ok = QInputDialog.getText(self, self.translator.tr("manage.edit_item").format(item=label), label, text=data.name)
        if ok and text.strip():
            try:
                self.update_func(data.id, text.strip())
                self.load_items()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _on_delete(self):
        item = self.list_widget.currentItem()
        if not item: return
        data = item.data(Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self, "Confirm", f"Delete {data.name}?") == QMessageBox.StandardButton.Yes:
            try:
                self.delete_func(data.id)
                self.load_items()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

class ManageDialog(QDialog):
    def __init__(self, api: APIManager, is_admin: bool, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.api = api
        self.translator = Translator()
        self.setWindowTitle(self.translator.tr("manage.title"))
        self.resize(500, 450)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        self.tab_widget.addTab(
            ManagementTab("manage.item_category", self.api, self.api.get_categories, self.api.create_category, self.api.delete_category, self.api.update_category),
            self.translator.tr("manage.categories")
        )
        self.tab_widget.addTab(
            ManagementTab("manage.item_file_type", self.api, self.api.get_file_types, self.api.create_file_type, self.api.delete_file_type, self.api.update_file_type),
            self.translator.tr("manage.file_types")
        )
