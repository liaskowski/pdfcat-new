from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QGroupBox, QWidget, QHeaderView
)
from PyQt6.QtCore import Qt
import qtawesome as qta
from ..api_manager import APIManager
from ..utils.translator import Translator
from ..themes import ThemeManager

class AdminPanelDialog(QDialog):
    def __init__(self, api: APIManager, parent=None):
        super().__init__(parent)
        self.api = api
        self.translator = Translator()
        self.theme_manager = ThemeManager()
        self.setWindowTitle(self.translator.tr("admin.title"))
        self.resize(900, 700)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Users Section
        user_group = QGroupBox(self.translator.tr("admin.registered_users"))
        user_layout = QVBoxLayout(user_group)
        
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(5)
        self.user_table.setHorizontalHeaderLabels([
            self.translator.tr("admin.table_id"), 
            self.translator.tr("admin.username"), 
            self.translator.tr("admin.email"), 
            self.translator.tr("admin.role"), 
            self.translator.tr("admin.table_active")
        ])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.user_table.verticalHeader().setVisible(False)
        self.user_table.setAlternatingRowColors(True)
        self.user_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.user_table.setShowGrid(False)
        user_layout.addWidget(self.user_table)
        
        user_btns = QHBoxLayout()
        self.refresh_btn = QPushButton(self.translator.tr("admin.refresh"))
        self.refresh_btn.setIcon(qta.icon("fa5s.sync", color=self.theme_manager.get_color("text")))
        
        self.delete_btn = QPushButton(self.translator.tr("admin.delete_user"))
        self.delete_btn.setObjectName("dangerButton")
        self.delete_btn.setIcon(qta.icon("fa5s.user-minus", color="white"))
        
        user_btns.addWidget(self.refresh_btn)
        user_btns.addStretch()
        user_btns.addWidget(self.delete_btn)
        user_layout.addLayout(user_btns)
        
        layout.addWidget(user_group, 3)

        # Tags Section
        tag_group = QGroupBox(self.translator.tr("admin.tag_dictionary"))
        tag_layout = QVBoxLayout(tag_group)
        
        self.tag_table = QTableWidget()
        self.tag_table.setColumnCount(5)
        self.tag_table.setHorizontalHeaderLabels(["ID", "RU", "EN", "PL", "Markers"])
        self.tag_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tag_table.verticalHeader().setVisible(False)
        self.tag_table.setAlternatingRowColors(True)
        self.tag_table.setShowGrid(False)
        tag_layout.addWidget(self.tag_table)
        
        tag_btns = QHBoxLayout()
        self.add_tag_btn = QPushButton("+")
        self.add_tag_btn.setFixedSize(30, 30)
        self.save_tags_btn = QPushButton(self.translator.tr("common.save"))
        self.save_tags_btn.setObjectName("primaryButton")
        self.save_tags_btn.setFixedHeight(30)
        
        tag_btns.addWidget(self.add_tag_btn)
        tag_btns.addStretch()
        tag_btns.addWidget(self.save_tags_btn)
        tag_layout.addLayout(tag_btns)
        
        layout.addWidget(tag_group, 2)

        self.refresh_btn.clicked.connect(self._load_users)
        self.delete_btn.clicked.connect(self._delete_user)
        self.add_tag_btn.clicked.connect(self._add_tag_row)
        self.save_tags_btn.clicked.connect(self._save_tags)
        
        self._load_users()
        self._load_tags()

    def _load_tags(self):
        import os, json
        from pathlib import Path
        p = Path(__file__).parent.parent / "assets" / "configs" / "tag_dictionary.json"
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                tags = data.get("tags", [])
                self.tag_table.setRowCount(len(tags))
                for i, t in enumerate(tags):
                    self.tag_table.setItem(i, 0, QTableWidgetItem(t.get("id", "")))
                    self.tag_table.setItem(i, 1, QTableWidgetItem(t.get("ru", "")))
                    self.tag_table.setItem(i, 2, QTableWidgetItem(t.get("en", "")))
                    self.tag_table.setItem(i, 3, QTableWidgetItem(t.get("pl", "")))
                    self.tag_table.setItem(i, 4, QTableWidgetItem(", ".join(t.get("markers", []))))

    def _add_tag_row(self):
        r = self.tag_table.rowCount()
        self.tag_table.insertRow(r)
        for c in range(5): self.tag_table.setItem(r, c, QTableWidgetItem(""))

    def _save_tags(self):
        import os, json
        from pathlib import Path
        tags = []
        for r in range(self.tag_table.rowCount()):
            tid = self.tag_table.item(r, 0).text().strip()
            if not tid: continue
            tags.append({
                "id": tid, "ru": self.tag_table.item(r, 1).text(),
                "en": self.tag_table.item(r, 2).text(), "pl": self.tag_table.item(r, 3).text(),
                "markers": [m.strip() for m in self.tag_table.item(r, 4).text().split(",") if m.strip()]
            })
        p = Path(__file__).parent.parent / "assets" / "configs" / "tag_dictionary.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"tags": tags}, f, indent=2, ensure_ascii=False)
        QMessageBox.information(self, "Success", "Tags saved")

    def _load_users(self):
        try:
            users = self.api.get_all_users()
            self.user_table.setRowCount(len(users))
            for i, u in enumerate(users):
                self.user_table.setItem(i, 0, QTableWidgetItem(str(u.id)))
                self.user_table.setItem(i, 1, QTableWidgetItem(u.username))
                self.user_table.setItem(i, 2, QTableWidgetItem(str(u.email or "")))
                self.user_table.setItem(i, 3, QTableWidgetItem(u.role))
                self.user_table.setItem(i, 4, QTableWidgetItem("Yes" if u.is_active else "No"))
        except Exception as e: print(f"Admin Load Error: {e}")

    def _delete_user(self):
        row = self.user_table.currentRow()
        if row < 0: return
        uid = int(self.user_table.item(row, 0).text())
        if QMessageBox.question(self, "Confirm", f"Delete user {uid}?") == QMessageBox.StandardButton.Yes:
            try:
                self.api.delete_user(uid)
                self._load_users()
            except Exception as e: QMessageBox.critical(self, "Error", str(e))
