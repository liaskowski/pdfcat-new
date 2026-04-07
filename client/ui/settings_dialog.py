from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QSlider, QPushButton, QGroupBox, QFormLayout, QApplication,
    QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QSettings
from ..utils.config_manager import ConfigManager
from ..utils.translator import Translator
from ..themes import LIGHT_THEME_QSS, DARK_THEME_QSS
from .manage_dialog import ManageDialog

class SettingsDialog(QDialog):
    def __init__(self, api, is_admin, parent=None):
        super().__init__(parent)
        self.api = api
        self.is_admin = is_admin
        self.config = ConfigManager()
        self.translator = Translator()
        self.setWindowTitle(self.translator.tr("settings.title"))
        self.setModal(True)
        
        self.settings = QSettings("pdflib", "client")
        geometry = self.settings.value(f"Geometry/{self.__class__.__name__}")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(600, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Appearance Group
        app_group = QGroupBox(self.translator.tr("settings.appearance"))
        app_layout = QFormLayout(app_group)
        app_layout.setSpacing(12)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("English", "en")
        self.lang_combo.addItem("Русский", "ru")
        self.lang_combo.addItem("Polski", "pl")
        
        current_lang = self.config.get("language", "en")
        index = self.lang_combo.findData(current_lang)
        if index >= 0:
            self.lang_combo.setCurrentIndex(index)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        self.theme_combo.setCurrentText(self.config.get("theme"))
        
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["100%", "125%", "150%"])
        current_scale = f"{self.config.get('scale')}%"
        self.scale_combo.setCurrentText(current_scale)

        self.font_combo = QComboBox()
        self.font_combo.addItems(["10", "11", "12", "14", "16"])
        self.font_combo.setCurrentText(str(self.config.get("font_size")))

        app_layout.addRow(self.translator.tr("settings.language"), self.lang_combo)
        app_layout.addRow(self.translator.tr("settings.theme"), self.theme_combo)
        app_layout.addRow(self.translator.tr("settings.scale"), self.scale_combo)
        app_layout.addRow(self.translator.tr("settings.font_size"), self.font_combo)
        
        layout.addWidget(app_group)

        # Data Management Group
        data_group = QGroupBox(self.translator.tr("settings.data_management"))
        data_layout = QVBoxLayout(data_group)
        data_layout.setSpacing(10)

        self.manage_btn = QPushButton(self.translator.tr("settings.btn_manage"))
        self.manage_btn.clicked.connect(self._on_manage_clicked)
        data_layout.addWidget(self.manage_btn)

        self.clear_cache_btn = QPushButton(self.translator.tr("settings.btn_clear_cache"))
        self.clear_cache_btn.setObjectName("warningButton")
        self.clear_cache_btn.clicked.connect(self._on_clear_cache_clicked)
        data_layout.addWidget(self.clear_cache_btn)

        layout.addWidget(data_group)
        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        self.cancel_btn = QPushButton(self.translator.tr("common.cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        
        self.apply_btn = QPushButton(self.translator.tr("common.save"))
        self.apply_btn.clicked.connect(self._apply_settings)
        self.apply_btn.setObjectName("primaryButton")
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.apply_btn)
        
        layout.addLayout(btn_layout)

    def closeEvent(self, event):
        self.settings.setValue(f"Geometry/{self.__class__.__name__}", self.saveGeometry())
        super().closeEvent(event)

    def _on_manage_clicked(self):
        dlg = ManageDialog(self.api, self.is_admin, self)
        dlg.exec()

    def _on_clear_cache_clicked(self):
        """Clear the thumbnail cache and show confirmation message."""
        reply = QMessageBox.question(
            self,
            self.translator.tr("settings.clear_cache_confirm_title"),
            self.translator.tr("settings.clear_cache_confirm_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Access the parent window (main_window) to get the file_grid reference
            # Structure: main_window.ui.file_grid
            parent_window = self.parent()
            if parent_window and hasattr(parent_window, 'ui') and hasattr(parent_window.ui, 'file_grid'):
                success = parent_window.ui.file_grid.clear_thumbnail_cache()
                if success:
                    QMessageBox.information(
                        self,
                        self.translator.tr("settings.clear_cache_success_title"),
                        self.translator.tr("settings.clear_cache_success_msg")
                    )
                else:
                    QMessageBox.warning(
                        self,
                        self.translator.tr("settings.clear_cache_error_title"),
                        self.translator.tr("settings.clear_cache_error_msg")
                    )
            else:
                QMessageBox.warning(
                    self,
                    self.translator.tr("settings.clear_cache_error_title"),
                    self.translator.tr("settings.clear_cache_error_not_found")
                )

    def _apply_settings(self):
        theme = self.theme_combo.currentText()
        scale_str = self.scale_combo.currentText().replace("%", "")
        font_str = self.font_combo.currentText()
        lang_code = str(self.lang_combo.currentData())
        
        try:
            scale = int(scale_str)
            font_size = int(font_str)
            
            old_lang = str(self.config.get("language", "en"))
            
            self.config.set("theme", theme)
            self.config.set("scale", scale)
            self.config.set("font_size", font_size)
            self.config.set("language", lang_code)
            
            # Force physical write
            self.config.save()
            
            if old_lang != lang_code:
                self.translator.reload()
                QMessageBox.information(self, self.translator.tr("settings.restart_required_title"), self.translator.tr("settings.restart_required_msg"))
                # We return a specific result to indicate a restart is needed
                self.done(2) # Using a custom code (Accepted is usually 1)
                return

            self._apply_to_app(theme, scale, font_size)
            self.accept()
        except ValueError:
            pass

    def _apply_to_app(self, theme, scale, font_size):
        app = QApplication.instance()
        if not app: return
        
        # Apply Theme
        if theme == "Dark":
            base_qss = DARK_THEME_QSS
        else:
            base_qss = LIGHT_THEME_QSS
            
        # Apply Font Size and some basic scaling simulation via QSS
        # Calculate effective font size based on scale percentage
        effective_font_size = int(font_size * (scale / 100.0))
        font_qss = f"\nQWidget {{ font-size: {effective_font_size}pt; }}\n"
        app.setStyleSheet(base_qss + font_qss)