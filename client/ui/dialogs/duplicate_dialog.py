"""
Duplicate detection dialog for file uploads.
Shows potential duplicates and allows user to choose action.
"""

from typing import List, Optional, Tuple
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QButtonGroup, QRadioButton
)
from PyQt6.QtGui import QPixmap, QPainter, QColor, QBrush

from ..api_manager import APIDocument
from ..themes import ThemeManager
from ..utils.translator import Translator
from ..widgets.shimmer_widget import ShimmerWidget


class DuplicateDialog(QDialog):
    """
    Dialog shown when potential duplicate files are detected.
    Allows user to choose: Save as Copy, Replace, Keep Both, or Cancel.
    """
    
    # Result codes
    SAVE_COPY = 1
    REPLACE = 2
    KEEP_BOTH = 3
    CANCEL = 4
    
    def __init__(self, similar_files: List[Tuple[APIDocument, float]], 
                 new_filename: str, parent=None):
        super().__init__(parent)
        self.similar_files = similar_files  # List of (document, similarity_score)
        self.new_filename = new_filename
        self.translator = Translator()
        self.theme_manager = ThemeManager()
        
        self.setWindowTitle(self.translator.tr("duplicate.title"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.resize(600, 500)
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_label = QLabel(self.translator.tr("duplicate.title"))
        header_label.setObjectName("sectionTitle")
        layout.addWidget(header_label)
        
        info_label = QLabel(
            self.translator.tr("duplicate.similar_name").format(name=self.new_filename)
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Scrollable list of duplicates
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.duplicates_widget = QWidget()
        self.duplicates_layout = QVBoxLayout(self.duplicates_widget)
        self.duplicates_layout.setSpacing(10)
        
        # Radio button group for selecting action
        self.button_group = QButtonGroup(self)
        
        # Add each similar file
        for doc, score in self.similar_files:
            item_widget = self._create_duplicate_item(doc, score)
            self.duplicates_layout.addWidget(item_widget)
        
        scroll.setWidget(self.duplicates_widget)
        layout.addWidget(scroll, 1)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.save_copy_btn = QPushButton(self.translator.tr("duplicate.action_save_copy"))
        self.save_copy_btn.setObjectName("secondaryButton")
        self.save_copy_btn.clicked.connect(lambda: self._on_action(DuplicateDialog.SAVE_COPY))
        
        self.replace_btn = QPushButton(self.translator.tr("duplicate.action_replace"))
        self.replace_btn.setObjectName("warningButton")
        self.replace_btn.clicked.connect(lambda: self._on_action(DuplicateDialog.REPLACE))
        
        self.keep_both_btn = QPushButton(self.translator.tr("duplicate.action_keep_both"))
        self.keep_both_btn.setObjectName("primaryButton")
        self.keep_both_btn.clicked.connect(lambda: self._on_action(DuplicateDialog.KEEP_BOTH))
        
        self.cancel_btn = QPushButton(self.translator.tr("duplicate.action_cancel"))
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.clicked.connect(lambda: self._on_action(DuplicateDialog.CANCEL))
        
        btn_layout.addWidget(self.save_copy_btn)
        btn_layout.addWidget(self.replace_btn)
        btn_layout.addWidget(self.keep_both_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _create_duplicate_item(self, doc: APIDocument, score: float) -> QFrame:
        """Create a widget showing duplicate file info."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # File icon
        icon_label = QLabel()
        icon_pixmap = self._create_pdf_icon()
        icon_label.setPixmap(icon_pixmap)
        icon_label.setFixedSize(32, 32)
        layout.addWidget(icon_label)
        
        # File info
        info_layout = QVBoxLayout()
        
        filename_label = QLabel(f"<b>{doc.title}</b>")
        filename_label.setWordWrap(True)
        info_layout.addWidget(filename_label)
        
        # Similarity score with color coding
        score_color = self._get_score_color(score)
        score_text = self.translator.tr("duplicate.similarity_score").format(score=int(score * 100))
        score_label = QLabel(f"<span style='color: {score_color}'>{score_text}</span>")
        info_layout.addWidget(score_label)
        
        # Upload date
        date_label = QLabel(f"Uploaded: {doc.upload_date}")
        date_label.setStyleSheet(f"color: {self.theme_manager.get_color('text_secondary')}")
        info_layout.addWidget(date_label)
        
        layout.addLayout(info_layout, 1)
        
        # Radio button for selection
        radio = QRadioButton()
        self.button_group.addButton(radio)
        layout.addWidget(radio)
        
        return frame
    
    def _create_pdf_icon(self) -> QPixmap:
        """Create a PDF icon pixmap."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw red PDF icon
        painter.setBrush(QBrush(QColor("#e53e3e")))  # Red
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(4, 4, 24, 24, 4, 4)
        
        # White "PDF" text
        painter.setPen(QColor("white"))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "PDF")
        
        painter.end()
        return pixmap
    
    def _get_score_color(self, score: float) -> str:
        """Get color based on similarity score."""
        if score >= 0.8:
            return "#e53e3e"  # Red - high similarity
        elif score >= 0.5:
            return "#dd6b20"  # Orange - medium similarity
        else:
            return "#d69e2e"  # Yellow - low similarity
    
    def _on_action(self, action: int):
        """Handle action button click."""
        self.done(action)
    
    def get_selected_document(self) -> Optional[APIDocument]:
        """Get the document selected by user."""
        for radio in self.button_group.buttons():
            if radio.isChecked():
                index = self.button_group.id(radio)
                if 0 <= index < len(self.similar_files):
                    return self.similar_files[index][0]
        return None
