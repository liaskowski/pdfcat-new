from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
    QPushButton, QLabel, QInputDialog, QMessageBox, QTabWidget
)
from PyQt6.QtCore import QThread, pyqtSignal

class DictWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, api, action, data=None):
        super().__init__()
        self.api = api
        self.action = action
        self.data = data

    def run(self):
        try:
            res = {}
            if self.action == "list_all":
                res["categories"] = self.api.get_categories()
                res["file_types"] = self.api.get_file_types()
            elif self.action == "create_category":
                self.api.create_category(self.data)
            elif self.action == "create_file_type":
                self.api.create_file_type(self.data)
            elif self.action == "merge_tags":
                res["message"] = self.api.merge_tags(self.data["old"], self.data["new"])
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))

class DictEditorWidget(QWidget):
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.init_ui()
        self.refresh_all()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        
        # Categories Tab
        self.cat_tab = QWidget()
        cat_layout = QVBoxLayout(self.cat_tab)
        self.cat_list = QListWidget()
        cat_layout.addWidget(self.cat_list)
        cat_btns = QHBoxLayout()
        add_cat = QPushButton("Add Category")
        add_cat.clicked.connect(self.on_add_category)
        cat_btns.addWidget(add_cat)
        cat_layout.addLayout(cat_btns)
        self.tabs.addTab(self.cat_tab, "Categories")
        
        # File Types Tab
        self.type_tab = QWidget()
        type_layout = QVBoxLayout(self.type_tab)
        self.type_list = QListWidget()
        type_layout.addWidget(self.type_list)
        type_btns = QHBoxLayout()
        add_type = QPushButton("Add File Type")
        add_type.clicked.connect(self.on_add_file_type)
        type_btns.addWidget(add_type)
        type_layout.addLayout(type_btns)
        self.tabs.addTab(self.type_tab, "File Types")
        
        # Tags Tab (Merge Tags)
        self.tags_tab = QWidget()
        tags_layout = QVBoxLayout(self.tags_tab)
        tags_layout.addWidget(QLabel("Tag Merging Tool"))
        self.merge_btn = QPushButton("Merge Tags...")
        self.merge_btn.clicked.connect(self.on_merge_tags)
        tags_layout.addWidget(self.merge_btn)
        tags_layout.addStretch()
        self.tabs.addTab(self.tags_tab, "Tags Management")
        
        layout.addWidget(self.tabs)

    def refresh_all(self):
        self.worker = DictWorker(self.api, "list_all")
        self.worker.finished.connect(self.on_data_received)
        self.worker.start()

    def on_data_received(self, res):
        if "categories" in res:
            self.cat_list.clear()
            for c in res["categories"]: self.cat_list.addItem(c["name"])
        if "file_types" in res:
            self.type_list.clear()
            for t in res["file_types"]: self.type_list.addItem(t["name"])
        if "message" in res:
            QMessageBox.information(self, "Success", res["message"])

    def on_add_category(self):
        name, ok = QInputDialog.getText(self, "Add", "Category name:")
        if ok and name:
            self.worker = DictWorker(self.api, "create_category", name)
            self.worker.finished.connect(self.refresh_all)
            self.worker.start()

    def on_add_file_type(self):
        name, ok = QInputDialog.getText(self, "Add", "File type name:")
        if ok and name:
            self.worker = DictWorker(self.api, "create_file_type", name)
            self.worker.finished.connect(self.refresh_all)
            self.worker.start()

    def on_merge_tags(self):
        old_tag, ok1 = QInputDialog.getText(self, "Merge", "Old tag name:")
        if not ok1 or not old_tag: return
        new_tag, ok2 = QInputDialog.getText(self, "Merge", f"Merge '{old_tag}' into:")
        if not ok2 or not new_tag: return
        
        self.worker = DictWorker(self.api, "merge_tags", {"old": old_tag, "new": new_tag})
        self.worker.finished.connect(self.on_data_received)
        self.worker.error.connect(lambda e: QMessageBox.critical(self, "Error", e))
        self.worker.start()
