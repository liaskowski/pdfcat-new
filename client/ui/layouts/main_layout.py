from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QProgressBar
)
from PyQt6.QtCore import Qt, QByteArray

from ..custom_title_bar import CustomTitleBar
from ..layout_factory import LayoutFactory
from ..search_bar import SearchBar
from ..file_grid import FileGrid
from ..preview_panel import PreviewPanel
from ..navigation_tree import NavigationTree
# from ..server_status import ServerStatusWidget  # Temporarily disabled
from ...utils.translator import Translator

class MainLayout:
    def __init__(self, main_window, api_manager):
        self.main_window = main_window
        self.api = api_manager
        self.translator = Translator()
        
        # Expose widgets
        self.title_bar = None
        self.splitter = None
        self.sidebar_panel = None
        self.preview_panel = None
        self.nav_tree = None
        self.add_pdf_btn = None
        self.search_bar = None
        self.breadcrumbs = None
        self.file_grid = None
        self.sort_combo = None
        # self.server_status = None  # Temporarily disabled
        
        self.setup_ui()

    def setup_ui(self):
        self.main_window.setWindowTitle(self.translator.tr("app_title"))
        self.main_window.resize(1200, 720)
        self.main_window.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.main_window.setMouseTracking(True)

        root = QWidget()
        root.setObjectName("root")
        self.main_window.setCentralWidget(root)

        # Root Layout: TitleBar (Top) + Content (Bottom)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Title Bar
        self.title_bar = CustomTitleBar(self.main_window)
        root_layout.addWidget(self.title_bar)

        # Server Status Bar (temporarily disabled)
        # self.server_status = ServerStatusWidget()
        # root_layout.addWidget(self.server_status)

        # Content Area via QSplitter
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(0)
        
        root_layout.addWidget(content_widget, 1)

        # Build UI from components using LayoutFactory
        self.layout_factory = LayoutFactory(self.api)
        self.sidebar_panel = self.layout_factory.create_sidebar_panel()
        center_panel, self.preview_panel = self.layout_factory.create_center_and_inspector_panels()

        # Splitter setup
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.sidebar_panel)
        self.splitter.addWidget(center_panel)
        self.splitter.addWidget(self.preview_panel)
        
        # Give center panel priority
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        
        content_layout.addWidget(self.splitter)

        # Expose widgets for signal connection
        self.nav_tree = self.layout_factory.nav_tree
        self.add_pdf_btn = self.layout_factory.add_pdf_btn
        self.search_bar = self.layout_factory.search_bar
        self.breadcrumbs = self.layout_factory.breadcrumbs
        self.file_grid = self.layout_factory.file_grid
        self.sort_combo = self.layout_factory.sort_combo
        
        # Search info label logic (hidden by default)
        self.search_info_label = QLabel()
        self.search_info_label.setObjectName("sectionTitle")
        self.search_info_label.setStyleSheet("margin-left: 12px; font-weight: bold;")
        self.search_info_label.setVisible(False)
        
        # Progress Bar (Stage 3 Preparation)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        root_layout.addWidget(self.progress_bar)
        
        self.main_window.setAcceptDrops(True)

    def restore_splitter_state(self, state_hex: str):
        if state_hex and isinstance(state_hex, str):
            try:
                self.splitter.restoreState(QByteArray.fromHex(state_hex.encode()))
            except Exception as e:
                print(f"Failed to restore splitter state: {e}")

    def save_splitter_state(self) -> str:
        return self.splitter.saveState().toHex().data().decode()
