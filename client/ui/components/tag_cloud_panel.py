from typing import Dict, List, Optional
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QCheckBox, QWidget, QLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect, QPoint
from ...themes import ThemeManager

class TagButton(QPushButton):
    def __init__(self, tag: str, count: int, parent=None):
        super().__init__(parent)
        self.tag_text = tag
        self.count = count
        self.setText(f"{tag} ({count})")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(24)
        
        tm = ThemeManager()
        is_dark = tm.current_theme == "Dark"
        
        # High contrast colors for Neon/Minimalist look
        if is_dark:
            bg_col = "rgba(10, 132, 255, 0.12)"
            border_col = "rgba(10, 132, 255, 0.4)"
            text_col = "#FFFFFF" # Pure white for better visibility
            hover_bg = "rgba(10, 132, 255, 0.25)"
        else:
            bg_col = "rgba(0, 122, 255, 0.08)"
            border_col = "rgba(0, 122, 255, 0.25)"
            text_col = "#1C1C1E"
            hover_bg = "rgba(0, 122, 255, 0.15)"
        
        self.setStyleSheet(f"""
            QPushButton {{
                padding: 4px 12px;
                background: {bg_col};
                border: 1px solid {border_col};
                border-radius: 12px;
                color: {text_col};
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {hover_bg};
                border: 1px solid palette(primary);
            }}
            QPushButton:checked {{
                background: palette(primary);
                color: white;
                border: none;
            }}
        """)

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if parent is not None: self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.items = []

    def __del__(self): del self.items
    def addItem(self, item): self.items.append(item)
    def count(self): return len(self.items)
    def itemAt(self, index):
        if 0 <= index < len(self.items): return self.items[index]
        return None
    def takeAt(self, index):
        if 0 <= index < len(self.items): return self.items.pop(index)
        return None
    def expandingDirections(self): return Qt.Orientation(0)
    def hasHeightForWidth(self): return True
    def heightForWidth(self, width): return self._do_layout(QRect(0, 0, width, 0), True)
    def setGeometry(self, rect): super().setGeometry(rect); self._do_layout(rect, False)
    def sizeHint(self): return self.minimumSize()
    def minimumSize(self):
        size = QSize()
        for item in self.items: size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect, test_only):
        x, y, line_height = rect.x(), rect.y(), 0
        for item in self.items:
            wid = item.widget()
            if not wid: continue
            space_x, space_y = self.spacing(), self.spacing()
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x, y = rect.x(), y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            if not test_only: item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        return y + line_height - rect.y()

class TagCloudPanel(QFrame):
    tag_selected = pyqtSignal(str, bool) # tag_text, is_checked
    filter_mode_changed = pyqtSignal(bool) # only_current_view

    def __init__(self, parent=None):
        super().__init__(parent)
        from ...utils.translator import Translator
        self.translator = Translator()
        tm = ThemeManager()
        is_dark = tm.current_theme == "Dark"
        
        self.setObjectName("tagCloudPanel")
        self.setVisible(False)
        self.setMinimumHeight(120)
        self.setMaximumHeight(250)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)
        
        # Header
        header = QHBoxLayout()
        title = QLabel(self.translator.tr("tag_explorer.title"))
        title.setStyleSheet(f"font-weight: bold; color: {tm.get_color('primary')}; font-size: 13px;")
        
        self.current_view_check = QCheckBox(self.translator.tr("tag_explorer.filter_current"))
        self.current_view_check.setChecked(True)
        self.current_view_check.toggled.connect(self.filter_mode_changed.emit)
        self.current_view_check.setStyleSheet(f"color: {tm.get_color('text_secondary')};")
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.current_view_check)
        layout.addLayout(header)
        
        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.flow_layout = FlowLayout(self.container, spacing=8)
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll, 1)
        
        bg = "#1A1A1A" if is_dark else "#F9F9F9"
        border = "#333333" if is_dark else "#D1D1D6"
        
        self.setStyleSheet(f"""
            QFrame#tagCloudPanel {{
                background-color: {bg};
                border-top: 1px solid {border};
                border-bottom: 1px solid {border};
            }}
        """)

    def update_tags(self, tag_counts: Dict[str, int], active_tags: List[str]):
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
            btn = TagButton(tag, count)
            if tag in active_tags: btn.setChecked(True)
            btn.toggled.connect(lambda checked, t=tag: self.tag_selected.emit(t, checked))
            self.flow_layout.addWidget(btn)
