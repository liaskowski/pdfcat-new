from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QHBoxLayout, 
    QComboBox, QPushButton, QTextEdit, QCheckBox, QFrame, QLabel,
    QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt
import qtawesome as qta

from ...widgets.tag_input import TagInputWidget
from ...utils.translator import Translator
from ...themes import ThemeManager
from ...logic.tags_engine import TagAnalyzer
from ...api_manager import APIManager, APIDocument, APICategory, APIFileType

class DocumentMetadataForm(QWidget):
    def __init__(
        self,
        api: APIManager,
        is_edit_mode: bool,
        is_public_default: bool,
        current_user_id: int | None,
        is_admin: bool,
        parent=None,
        batch_mode: bool = False
    ):
        super().__init__(parent)
        self.api = api
        self.is_edit_mode = is_edit_mode
        self.batch_mode = batch_mode
        self.translator = Translator()
        self.theme_manager = ThemeManager()
        self.tag_analyzer = TagAnalyzer()

        self._categories: List[APICategory] = []
        self._file_types: List[APIFileType] = []

        # Permissions context
        self.current_user_id = current_user_id
        self.is_admin = is_admin

        self._init_ui(is_public_default)
        self._load_combos()

    def _init_ui(self, is_public_default: bool):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(15)

        # Ownership Label
        self.owner_info_label = QLabel()
        self.owner_info_label.setObjectName("sectionTitle")
        self.owner_info_label.setWordWrap(True)
        layout.addWidget(self.owner_info_label)

        # Form Card
        form_card = QWidget()
        form_card.setObjectName("card")
        form_layout = QFormLayout(form_card)
        form_layout.setContentsMargins(12, 12, 12, 12)
        form_layout.setSpacing(10)
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self.display_name_input = QLineEdit()
        self.display_name_input.setObjectName("input")
        self.display_name_input.setPlaceholderText(self.translator.tr("upload.display_name"))
        form_layout.addRow(self.translator.tr("upload.display_name") + ":", self.display_name_input)

        # Category
        category_row = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.setObjectName("input")
        self.add_category_btn = QPushButton()
        self.add_category_btn.setIcon(qta.icon('fa5s.plus', color=self.theme_manager.get_color("text")))
        self.add_category_btn.setFixedSize(32, 32)
        self.add_category_btn.setObjectName("secondaryButton")
        self.add_category_btn.clicked.connect(self._on_add_category_clicked)
        category_row.addWidget(self.category_combo, 1)
        category_row.addWidget(self.add_category_btn)
        form_layout.addRow(self.translator.tr("upload.category") + ":", category_row)

        # File Type
        file_type_row = QHBoxLayout()
        self.file_type_combo = QComboBox()
        self.file_type_combo.setObjectName("input")
        self.add_file_type_btn = QPushButton()
        self.add_file_type_btn.setIcon(qta.icon('fa5s.plus', color=self.theme_manager.get_color("text")))
        self.add_file_type_btn.setFixedSize(32, 32)
        self.add_file_type_btn.setObjectName("secondaryButton")
        self.add_file_type_btn.clicked.connect(self._on_add_file_type_clicked)
        file_type_row.addWidget(self.file_type_combo, 1)
        file_type_row.addWidget(self.add_file_type_btn)
        form_layout.addRow(self.translator.tr("upload.file_type") + ":", file_type_row)
        
        # Tags
        self.tags_input = TagInputWidget(self.tag_analyzer, self.translator.get_locale())
        self.tags_input.setObjectName("tagInputWidget")
        form_layout.addRow(self.translator.tr("upload.tags") + ":", self.tags_input)

        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setObjectName("input")
        self.notes_input.setPlaceholderText(self.translator.tr("upload.notes_placeholder"))
        self.notes_input.setMinimumHeight(150)
        form_layout.addRow(self.translator.tr("upload.notes") + ":", self.notes_input)

        # Checkboxes
        self.is_private_checkbox = QCheckBox(self.translator.tr("upload.is_private"))
        form_layout.addRow(self.is_private_checkbox)

        self.is_public_checkbox = QCheckBox(self.translator.tr("upload.is_public"))
        self.is_public_checkbox.setChecked(is_public_default)
        form_layout.addRow(self.is_public_checkbox)

        # Make is_private and is_public mutually exclusive
        self.is_private_checkbox.toggled.connect(self._on_private_toggled)
        self.is_public_checkbox.toggled.connect(self._on_public_toggled)

        self.is_public_edit_checkbox = QCheckBox(self.translator.tr("upload.allow_edit"))
        form_layout.addRow(self.is_public_edit_checkbox)
        
        self.is_read_only_checkbox = QCheckBox(self.translator.tr("upload.read_only"))
        form_layout.addRow(self.is_read_only_checkbox)

        if not self.is_edit_mode:
            self.use_ocr_checkbox = QCheckBox(self.translator.tr("upload.use_ocr"))
            self.use_ocr_checkbox.setChecked(True)
            form_layout.addRow(self.use_ocr_checkbox)

        # Update Content Button (placeholder, connected in parent or here?)
        # Let's keep update content button in parent for now, or expose a signal?
        # Actually, simpler to keep it here if we want to isolate form UI.
        self.update_content_btn = QPushButton(self.translator.tr("upload.update_content"))
        self.update_content_btn.setObjectName("secondaryButton")
        self.update_content_btn.hide() # Hidden by default
        form_layout.addRow(self.update_content_btn)
        
        layout.addWidget(form_card)
        layout.addStretch(1)

    def _load_combos(self):
        try:
            self._categories = self.api.get_categories()
            self.category_combo.clear()
            self.category_combo.addItem("None", None)
            for cat in self._categories:
                self.category_combo.addItem(cat.name, cat.id)

            self._file_types = self.api.get_file_types()
            self.file_type_combo.clear()
            self.file_type_combo.addItem("None", None)
            for ft in self._file_types:
                self.file_type_combo.addItem(ft.name, ft.id)
        except Exception as e:
            print(f"Error loading categories/file types: {e}")

    def _on_add_category_clicked(self):
        name, ok = QInputDialog.getText(self, self.translator.tr("upload.add_category"), self.translator.tr("upload.category_name"))
        if ok and name.strip():
            try:
                cat = self.api.create_category(name.strip())
                self._load_combos()
                for i in range(self.category_combo.count()):
                    if self.category_combo.itemData(i) == cat.id:
                        self.category_combo.setCurrentIndex(i)
                        break
            except Exception as e:
                QMessageBox.critical(self, self.translator.tr("common.error"), str(e))

    def _on_add_file_type_clicked(self):
        name, ok = QInputDialog.getText(self, self.translator.tr("upload.add_file_type"), self.translator.tr("upload.file_type_name"))
        if ok and name.strip():
            try:
                ft = self.api.create_file_type(name.strip())
                self._load_combos()
                for i in range(self.file_type_combo.count()):
                    if self.file_type_combo.itemData(i) == ft.id:
                        self.file_type_combo.setCurrentIndex(i)
                        break
            except Exception as e:
                QMessageBox.critical(self, self.translator.tr("common.error"), str(e))

    def fill_from_document(self, doc: APIDocument):
        self.display_name_input.setText(doc.title)
        self.is_private_checkbox.setChecked(doc.is_private)
        self.is_public_checkbox.setChecked(doc.is_public)
        self.is_public_edit_checkbox.setChecked(doc.is_public_edit)
        self.is_read_only_checkbox.setChecked(doc.is_read_only)
        
        if doc.notes:
            self.notes_input.setText(doc.notes)
        if doc.tags:
            self.tags_input.set_tags(doc.tags)
        
        if doc.category:
            for i in range(self.category_combo.count()):
                if self.category_combo.itemData(i) == doc.category.id:
                    self.category_combo.setCurrentIndex(i)
                    break
        
        if doc.file_type:
            for i in range(self.file_type_combo.count()):
                if self.file_type_combo.itemData(i) == doc.file_type.id:
                    self.file_type_combo.setCurrentIndex(i)
                    break
        
        self._apply_permissions(doc)

    def _apply_permissions(self, doc: APIDocument):
        is_owner = doc.owner_id == self.current_user_id
        can_edit = is_owner or self.is_admin or doc.is_public_edit
        
        # If Read Only is set, block editing content for everyone (even owner?), 
        # or maybe allow owner to toggle it off?
        # Prompt says: "Если is_read_only == True, блокируй кнопку 'Заменить файл' и редактирование метаданных (сделай поля setEnabled(False))."
        # Assuming owner can UNCHECK it. But while checked, fields are disabled.
        
        is_read_only = doc.is_read_only
        
        success_color = self.theme_manager.get_color("success")
        warning_color = self.theme_manager.get_color("warning")

        if is_owner:
            self.owner_info_label.setText(self.translator.tr("preview.owner_is_you"))
            self.owner_info_label.setStyleSheet(f"color: {success_color}; font-weight: bold;")
        else:
            owner_name = doc.owner_username or f"User {doc.owner_id}"
            status_text = self.translator.tr("preview.owner_status").format(name=owner_name)
            if can_edit:
                status_text += self.translator.tr("preview.collaborative_editing")
            else:
                status_text += self.translator.tr("preview.read_only_access")
            self.owner_info_label.setText(status_text)
            self.owner_info_label.setStyleSheet(f"color: {warning_color}; font-weight: bold;")

        if not is_owner and not self.is_admin:
            self.is_private_checkbox.hide()
            self.is_public_checkbox.hide()
            self.is_public_edit_checkbox.hide()
            self.is_read_only_checkbox.hide()
            
            if not can_edit:
                self._disable_all_inputs()
                
        else:
            # Owner can see update button
            self.update_content_btn.show()

        # Read Only Logic override: It now means NO DOWNLOAD.
        # It does NOT block editing metadata/content if allowed by is_public_edit.
        # We just ensure the checkbox reflects the state.
        
        # However, for non-owners/admins, we already hid the checkbox above. 
        # For owners/admins, they can toggle it.
        # We DO NOT disable inputs here anymore.

    def _disable_all_inputs(self):
        self.display_name_input.setEnabled(False)
        self.category_combo.setEnabled(False)
        self.file_type_combo.setEnabled(False)
        self.notes_input.setEnabled(False)
        self.tags_input.setEnabled(False)
        self.is_private_checkbox.setEnabled(False)
        self.is_public_checkbox.setEnabled(False)
        self.is_public_edit_checkbox.setEnabled(False)
        self.is_read_only_checkbox.setEnabled(False)

    def _on_private_toggled(self, checked):
        """Handle is_private checkbox change - make mutually exclusive with is_public."""
        if checked:
            # If private is checked, uncheck public
            self.is_public_checkbox.blockSignals(True)
            self.is_public_checkbox.setChecked(False)
            self.is_public_checkbox.blockSignals(False)

    def _on_public_toggled(self, checked):
        """Handle is_public checkbox change - make mutually exclusive with is_private."""
        if checked:
            # If public is checked, uncheck private
            self.is_private_checkbox.blockSignals(True)
            self.is_private_checkbox.setChecked(False)
            self.is_private_checkbox.blockSignals(False)

    def get_data(self):
        """Get form data with validation."""
        title = self.display_name_input.text().strip()
        if not title and not self.batch_mode:
            raise ValueError(self.translator.tr("upload.validation_title_required"))

        return {
            "title": title if title else None,
            "category_id": self.category_combo.currentData(),
            "file_type_id": self.file_type_combo.currentData(),
            "is_private": self.is_private_checkbox.isChecked(),
            "is_public": self.is_public_checkbox.isChecked(),
            "is_public_edit": self.is_public_edit_checkbox.isChecked(),
            "is_read_only": self.is_read_only_checkbox.isChecked(),
            "notes": self.notes_input.toPlainText(),
            "tags": ",".join(self.tags_input.get_tags()),
            "use_ocr": self.use_ocr_checkbox.isChecked() if not self.is_edit_mode else False,
            "folder_id": None  # Default to None - folder selection handled elsewhere
        }
