from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from pathlib import Path
from ..widgets.modern_pdf_viewer import ModernPDFViewer
from ..themes import LIGHT_THEME_QSS, DARK_THEME_QSS

class FileViewerWindow(QMainWindow):
    def __init__(self, file_path: str, is_dark_theme: bool = False, title: str = "Document Viewer", password: str = None):
        super().__init__()
        
        # Use provided title (original filename from database)
        self.setWindowTitle(f"{title}")
        self.resize(1000, 800)

        # Central widget container
        central_widget = QWidget()
        central_widget.setObjectName("root") # For theme styling
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # PDF Viewer Widget
        self.viewer = ModernPDFViewer()
        layout.addWidget(self.viewer)

        # Apply theme
        self.apply_theme("Dark" if is_dark_theme else "Light")

        # Load the file
        self.viewer.load_document(file_path, password=password)

    def apply_theme(self, theme_name: str):
        style = DARK_THEME_QSS if theme_name == "Dark" else LIGHT_THEME_QSS
        self.setStyleSheet(style)
        self.viewer.update_theme(theme_name)
