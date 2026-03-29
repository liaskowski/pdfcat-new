from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QComboBox
)
from .navigation_tree import NavigationTree
from .search_bar import SearchBar
from .file_grid import FileGrid
from .preview_panel import PreviewPanel
from ..api_manager import APIManager
from ..utils.translator import Translator

class LayoutFactory:
    def __init__(self, api: APIManager):
        self.api = api
        self.translator = Translator()
        self.nav_tree = None
        self.add_pdf_btn = None
        self.search_bar = None
        self.breadcrumbs = None
        self.file_grid = None
        self.preview_panel = None
        self.sort_combo = None

    def create_sidebar_panel(self) -> QWidget:
        # ... existing implementation ...
        sidebar = QFrame()
        sidebar.setObjectName("sidebarPanel")
        sidebar.setMinimumWidth(150)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Navigation
        folders_card = QFrame()
        folders_card.setObjectName("card")
        folders_layout = QVBoxLayout(folders_card)
        folders_layout.setContentsMargins(12, 12, 12, 12)
        folders_layout.setSpacing(8)

        folders_title = QLabel(self.translator.tr("main.navigation")) 
        folders_title.setObjectName("sectionTitle")

        self.nav_tree = NavigationTree(self.api)

        folders_layout.addWidget(folders_title)
        folders_layout.addWidget(self.nav_tree)

        layout.addWidget(folders_card, 1)

        # Buttons
        import qtawesome as qta
        from PyQt6.QtCore import QSize
        self.add_pdf_btn = QPushButton(self.translator.tr("main.sidebar_upload"))
        self.add_pdf_btn.setIcon(qta.icon('fa5s.plus-circle', color='white'))
        self.add_pdf_btn.setIconSize(QSize(20, 20))
        self.add_pdf_btn.setToolTip(self.translator.tr("main.tooltip_upload"))
        self.add_pdf_btn.setObjectName("primaryButton")
        self.add_pdf_btn.setMinimumHeight(48)
        layout.addWidget(self.add_pdf_btn)

        return sidebar

    def create_center_and_inspector_panels(self) -> tuple[QWidget, QWidget]:
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0,0,0,0)
        center_layout.setSpacing(12)
        
        self.search_bar = SearchBar(self.api)
        
        # Toolbar Row
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        
        self.breadcrumbs = QLabel(self.translator.tr("main.my_documents"))
        self.breadcrumbs.setObjectName("sectionTitle")
        self.breadcrumbs.setStyleSheet("margin-left: 12px; color: #666;")
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItem(self.translator.tr("sort.name_asc"), "name_asc")
        self.sort_combo.addItem(self.translator.tr("sort.date_newest"), "date_desc")
        self.sort_combo.addItem(self.translator.tr("sort.date_oldest"), "date_asc")
        self.sort_combo.setFixedWidth(150)
        
        toolbar_layout.addWidget(self.breadcrumbs)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(QLabel(self.translator.tr("sort.label")))
        toolbar_layout.addWidget(self.sort_combo)
        
        self.file_grid = FileGrid(self.api)
        
        center_layout.addWidget(self.search_bar)
        center_layout.addWidget(toolbar)
        center_layout.addWidget(self.file_grid, 1)
        
        self.preview_panel = PreviewPanel(self.api)
        
        return center_panel, self.preview_panel
