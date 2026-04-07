from typing import Dict, Any
import os
from PyQt6.QtGui import QFontDatabase

class ThemeManager:
    _instance = None
    
    PALETTE_DARK = {
        "background": "#121212",
        "surface": "#1E1E1E",
        "border": "#333333",
        "text": "#FFFFFF",
        "text_secondary": "#AAAAAA",
        "primary": "#0A84FF",
        "accent": "#0A84FF",
        "danger": "#FF453A",
        "success": "#32D74B",
        "hover": "#2C2C2E",
        "white": "#FFFFFF"
    }
    
    PALETTE_LIGHT = {
        "background": "#F5F5F7",
        "surface": "#FFFFFF",
        "border": "#D1D1D6",
        "text": "#1C1C1E",
        "text_secondary": "#636366",
        "primary": "#007AFF",
        "accent": "#007AFF",
        "danger": "#FF3B30",
        "success": "#34C759",
        "hover": "#E5E5EA",
        "white": "#FFFFFF"
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThemeManager, cls).__new__(cls)
            cls._instance.current_theme = "Dark"
            cls._instance.load_fonts()
        return cls._instance
        
    def load_fonts(self):
        base_path = os.path.dirname(os.path.abspath(__file__))
        fonts_dir = os.path.join(base_path, "assets", "fonts")
        font_files = ["Inter-Regular.ttf", "Inter-Medium.ttf", "Inter-Regular.otf", "Inter-Medium.otf"]
        for f in font_files:
            p = os.path.join(fonts_dir, f)
            if os.path.exists(p): QFontDatabase.addApplicationFont(p)
    
    def set_theme(self, theme_name: str):
        from PyQt6.QtCore import QSettings
        self.current_theme = theme_name
        s = QSettings("pdflib", "client")
        s.setValue("theme", theme_name)
        s.sync()
        
    def get_color(self, color_name: str) -> str:
        p = self.PALETTE_DARK if self.current_theme == "Dark" else self.PALETTE_LIGHT
        return p.get(color_name, "#FF00FF")

    def get_icon_color(self) -> str:
        return "#343a40" if self.current_theme == "Light" else "#F8F9FA"

# ==============================================================================
# BASE COMPONENT STYLES
# ==============================================================================
BASE_QSS = """
* { font-family: "Inter", "Segoe UI", sans-serif; font-size: 12px; outline: none; }
QGroupBox { font-weight: bold; border: 1px solid palette(border); border-radius: 8px; margin-top: 15px; padding-top: 15px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
QTableWidget { gridline-color: transparent; border: 1px solid palette(border); border-radius: 6px; }
QHeaderView::section { padding: 8px; border: none; font-weight: bold; }
QPushButton { border-radius: 6px; padding: 8px 16px; font-weight: 500; }
QPushButton[iconOnly="true"] { padding: 4px; border: none; background: transparent; }
QComboBox { border-radius: 6px; padding: 5px 10px; border: 1px solid palette(border); }
QComboBox::drop-down { border: none; }

QTabWidget::pane { border: 1px solid palette(border); border-radius: 8px; top: -1px; background-color: palette(surface); }
QTabBar::tab { padding: 10px 20px; border: 1px solid palette(border); border-bottom: none; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 4px; background-color: palette(background); color: palette(text_secondary); }
QTabBar::tab:selected { background-color: palette(surface); color: palette(primary); font-weight: bold; border-bottom: 1px solid palette(surface); }
QTabBar::tab:hover:!selected { background-color: palette(hover); }

QScrollBar:vertical { background: transparent; width: 10px; margin: 0px; }
QScrollBar::handle:vertical { background: palette(scrollbar_handle); border-radius: 5px; min-height: 20px; margin: 2px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

QScrollBar:horizontal { background: transparent; height: 10px; margin: 0px; }
QScrollBar::handle:horizontal { background: palette(scrollbar_handle); border-radius: 5px; min-width: 20px; margin: 2px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }

QSplitter::handle { background-color: palette(border); }
QSplitter::handle:hover { background-color: palette(primary); }
"""

# ==============================================================================
# LIGHT THEME
# ==============================================================================
LIGHT_THEME_QSS = (BASE_QSS + "").replace("palette(border)", "#D1D1D6").replace("palette(primary)", "#007AFF").replace("palette(scrollbar_handle)", "#C1C1C1").replace("palette(background)", "#F5F5F7").replace("palette(surface)", "#FFFFFF").replace("palette(text_secondary)", "#636366").replace("palette(hover)", "#E5E5EA") + """
QMainWindow, QDialog, QMessageBox, QScrollArea, QStackedWidget, #root, QScrollArea > QWidget > QWidget { 
    background-color: #F5F5F7; 
    color: #1C1C1E; 
}
QScrollArea { border: none; }
QAbstractScrollArea::viewport { background-color: #F5F5F7; }

QWidget { color: #1C1C1E; }
QLabel, QCheckBox, QRadioButton, QGroupBox { color: #1C1C1E; background: transparent; }

#sidebarPanel { background-color: #EBEBEB; border-right: 1px solid #D1D1D6; }
#centerPanel, #card, #inspectorPanel { background-color: #FFFFFF; border: 1px solid #D1D1D6; border-radius: 8px; }
#sidebarPanel #card, #sidebarPanel QTreeWidget { background-color: transparent; border: none; }

QLineEdit, QTextEdit, QPlainTextEdit { background-color: #FFFFFF; border: 1px solid #D1D1D6; color: #000000; border-radius: 6px; }
QLineEdit:focus { border: 1px solid #007AFF; }

QHeaderView::section { background-color: #E5E5EA; color: #1C1C1E; border-bottom: 1px solid #D1D1D6; }
QTableWidget, QListWidget, QTreeWidget { background-color: #FFFFFF; alternate-background-color: #FAFAFA; color: #1C1C1E; }
QTableWidget::item:selected, QListWidget::item:selected, QTreeWidget::item:selected { background-color: #007AFF; color: #FFFFFF; }

QPushButton { background-color: #FFFFFF; border: 1px solid #D1D1D6; color: #1C1C1E; }
QPushButton:hover { background-color: #F2F2F7; }
QPushButton#primaryButton { background-color: #007AFF; color: #FFFFFF; border: none; }
QPushButton#dangerButton { background-color: #FF3B30; color: #FFFFFF; border: none; }
QPushButton#warningButton { background-color: #FF9500; color: #FFFFFF; border: none; }

QComboBox { background-color: #FFFFFF; color: #1C1C1E; }
QComboBox QAbstractItemView { background-color: #FFFFFF; border: 1px solid #D1D1D6; selection-background-color: #007AFF; color: #1C1C1E; }

QMenu { background-color: #FFFFFF; border: 1px solid #D1D1D6; color: #1C1C1E; }
QMenu::item { padding: 6px 20px; background-color: transparent; }
QMenu::item:selected { background-color: #007AFF; color: #FFFFFF; }
QMenu::separator { height: 1px; background: #E5E5EA; margin: 4px 0px; }
"""

# ==============================================================================
# DARK THEME
# ==============================================================================
DARK_THEME_QSS = (BASE_QSS + "").replace("palette(border)", "#333333").replace("palette(primary)", "#0A84FF").replace("palette(scrollbar_handle)", "#3D3D3D").replace("palette(background)", "#121212").replace("palette(surface)", "#1E1E1E").replace("palette(text_secondary)", "#AAAAAA").replace("palette(hover)", "#2C2C2E") + """
QMainWindow, QDialog, QMessageBox, QScrollArea, QStackedWidget, #root, QScrollArea > QWidget > QWidget { 
    background-color: #121212; 
    color: #EBEBF5; 
}
QScrollArea { border: none; }
QAbstractScrollArea::viewport { background-color: #121212; }

QWidget { color: #EBEBF5; }
QLabel, QCheckBox, QRadioButton, QGroupBox { color: #EBEBF5; background: transparent; }

#sidebarPanel { background-color: #1A1A1A; border-right: 1px solid #333333; }
#centerPanel, #card, #inspectorPanel { background-color: #1E1E1E; border: 1px solid #333333; border-radius: 8px; }
#sidebarPanel #card, #sidebarPanel QTreeWidget { background-color: transparent; border: none; }

QLineEdit, QTextEdit, QPlainTextEdit { background-color: #2C2C2E; border: 1px solid #3D3D3D; color: #FFFFFF; border-radius: 6px; }
QLineEdit:focus { border: 1px solid #0A84FF; }

QHeaderView::section { background-color: #2C2C2E; color: #FFFFFF; border-bottom: 1px solid #3D3D3D; }
QTableWidget, QListWidget, QTreeWidget { background-color: #1E1E1E; alternate-background-color: #252525; color: #EBEBF5; border: 1px solid #333333; }
QTableWidget::item:selected, QListWidget::item:selected, QTreeWidget::item:selected { background-color: #0A84FF; color: #FFFFFF; }

QPushButton { background-color: #2C2C2E; border: 1px solid #3D3D3D; color: #FFFFFF; }
QPushButton:hover { background-color: #3A3A3C; }
QPushButton#primaryButton { background-color: #0A84FF; color: #FFFFFF; border: none; }
QPushButton#dangerButton { background-color: #FF453A; color: #FFFFFF; border: none; }
QPushButton#warningButton { background-color: #FF9F0A; color: #FFFFFF; border: none; }

QComboBox { background-color: #2C2C2E; color: #FFFFFF; border: 1px solid #3D3D3D; }
QComboBox QAbstractItemView { background-color: #1E1E1E; border: 1px solid #3D3D3D; selection-background-color: #0A84FF; color: #FFFFFF; }

QMenu { background-color: #1E1E1E; border: 1px solid #333333; color: #EBEBF5; }
QMenu::item { padding: 6px 20px; background-color: transparent; }
QMenu::item:selected { background-color: #0A84FF; color: #FFFFFF; }
QMenu::separator { height: 1px; background: #333333; margin: 4px 0px; }
"""