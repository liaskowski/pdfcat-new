from PyQt6.QtCore import Qt, QPoint, QRect, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QLayout, QSizePolicy, QStyle, QLineEdit, 
    QPushButton, QHBoxLayout, QVBoxLayout, QScrollArea,
    QCompleter, QComboBox, QFrame, QLabel
)
from PyQt6.QtGui import QIcon
import qtawesome as qta
from ..ui.layouts.flow_layout import FlowLayout
from ..themes import ThemeManager

class TagChip(QFrame):
    removed = pyqtSignal(str)

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text
        self.setObjectName("tagChip")
        self.theme_manager = ThemeManager()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        label = QLabel(f"#{text}")
        label.setObjectName("tagChipLabel")
        layout.addWidget(label)
        
        close_btn = QPushButton()
        # Use white for the X icon as chips are usually colored
        close_btn.setIcon(qta.icon('fa5s.times', color=self.theme_manager.get_color("white")))
        close_btn.setFixedSize(16, 16)
        close_btn.setFlat(True)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setObjectName("tagChipCloseBtn")
        close_btn.clicked.connect(self._on_remove)
        layout.addWidget(close_btn)
        
        # Base chip color logic
        self.setStyleSheet(f"""
            #tagChip {{
                background-color: {self.theme_manager.get_color("accent")};
                border-radius: 12px;
            }}
            #tagChipLabel {{
                color: {self.theme_manager.get_color("white")};
                font-weight: bold;
            }}
            #tagChipCloseBtn:hover {{
                background-color: rgba(255, 255, 255, 0.3);
                border-radius: 8px;
            }}
        """)

    def _on_remove(self):
        self.removed.emit(self.text)

class TagInputWidget(QWidget):
    def __init__(self, tag_analyzer, locale="en", parent=None):
        super().__init__(parent)
        self.tag_analyzer = tag_analyzer
        self.locale = locale
        self.tags = set()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)

        # Chip Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setMaximumHeight(100) # Limit height
        self.scroll_area.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)

        self.chip_container = QWidget()
        self.flow_layout = FlowLayout(self.chip_container, margin=0, spacing=6)
        self.chip_container.setLayout(self.flow_layout)
        self.scroll_area.setWidget(self.chip_container)

        self.layout.addWidget(self.scroll_area)

        # Input Area
        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(8)

        self.input = QLineEdit()
        self.input.setObjectName("input")
        self.input.setPlaceholderText("Add tag...")
        self.input.returnPressed.connect(self._add_from_input)

        # Dictionary Dropdown
        self.dict_combo = QComboBox()
        self.dict_combo.setObjectName("input")
        self.dict_combo.setPlaceholderText("Select from dictionary...")
        self.dict_combo.setMinimumWidth(150)
        self.dict_combo.activated.connect(self._add_from_combo)

        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.dict_combo)

        self.layout.addLayout(input_row)

        # Initial load - MUST load dictionary before using
        self.known_tags = []
        self._load_dictionary_tags()
        self._setup_completer()
    
    def set_locale(self, locale: str):
        """Update locale and reload dictionary tags."""
        if self.locale != locale:
            self.locale = locale
            self._load_dictionary_tags()
            self._setup_completer()

    def _load_dictionary_tags(self):
        # Flatten dictionary tags for current locale
        self.known_tags = []
        if self.tag_analyzer and self.tag_analyzer.tags_data:
            for t in self.tag_analyzer.tags_data:
                # Resolve name based on locale - priority: locale > en > id
                name = t.get(self.locale, t.get("en", t.get("id")))
                if name:
                    self.known_tags.append(name)

        self.known_tags.sort()

        self.dict_combo.clear()
        self.dict_combo.addItem("Select from dictionary...", None)
        for tag in self.known_tags:
            self.dict_combo.addItem(tag, tag)

    def _setup_completer(self):
        self.completer = QCompleter(self.known_tags)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.input.setCompleter(self.completer)

    def _add_from_input(self):
        text = self.input.text().strip()
        if text:
            # Handle comma separated
            parts = [t.strip() for t in text.split(',') if t.strip()]
            for p in parts:
                self.add_tag(p)
            self.input.clear()

    def _add_from_combo(self, index):
        if index > 0: # 0 is placeholder
            tag = self.dict_combo.itemText(index)
            self.add_tag(tag)
            self.dict_combo.setCurrentIndex(0)

    def add_tag(self, tag_text):
        tag_text = tag_text.strip()
        if not tag_text:
            return
            
        # Remove # if user typed it
        if tag_text.startswith("#"):
            tag_text = tag_text[1:]
            
        if tag_text in self.tags:
            return
            
        self.tags.add(tag_text)
        
        chip = TagChip(tag_text)
        chip.removed.connect(self.remove_tag)
        self.flow_layout.addWidget(chip)
        # Force layout update
        self.chip_container.adjustSize()

    def remove_tag(self, tag_text):
        if tag_text in self.tags:
            self.tags.remove(tag_text)
            
            # Find and remove widget
            for i in range(self.flow_layout.count()):
                item = self.flow_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if isinstance(widget, TagChip) and widget.text == tag_text:
                        self.flow_layout.takeAt(i)
                        widget.deleteLater()
                        break
            self.chip_container.adjustSize()

    def get_tags(self):
        return sorted(list(self.tags))

    def set_tags(self, tags):
        # Clear existing
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.tags.clear()
        
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',') if t.strip()]
            
        for t in tags:
            self.add_tag(t)
