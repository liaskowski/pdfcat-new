from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QWheelEvent

from ..utils.workers import PdfRenderWorker

class PdfViewer(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        self._file_path: Optional[str] = None
        self._password: Optional[str] = None
        self._document_id: Optional[int] = None
        self._current_page = 0
        self._total_pages = 0
        self._zoom = 1.5  # Initial zoom
        self._worker: Optional[PdfRenderWorker] = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        self.toolbar = QWidget()
        self.toolbar.setFixedHeight(40)
        tb_layout = QHBoxLayout(self.toolbar)
        tb_layout.setContentsMargins(8, 0, 8, 0)
        
        self.prev_btn = QPushButton("<")
        self.prev_btn.setFixedSize(30, 30)
        self.prev_btn.clicked.connect(self._prev_page)
        
        self.page_label = QLabel("0 / 0")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setFixedWidth(60)
        
        self.next_btn = QPushButton(">")
        self.next_btn.setFixedSize(30, 30)
        self.next_btn.clicked.connect(self._next_page)
        
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.setFixedSize(30, 30)
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedSize(30, 30)
        self.zoom_in_btn.clicked.connect(self._zoom_in)

        self.rotate_btn = QPushButton("R")
        self.rotate_btn.setFixedSize(30, 30)
        self.rotate_btn.setToolTip(self.translator.tr("viewer.rotate_90"))
        self.rotate_btn.clicked.connect(self._rotate_right)

        tb_layout.addWidget(self.prev_btn)
        tb_layout.addWidget(self.page_label)
        tb_layout.addWidget(self.next_btn)
        tb_layout.addStretch()
        tb_layout.addWidget(self.rotate_btn)
        tb_layout.addWidget(self.zoom_out_btn)
        tb_layout.addWidget(self.zoom_in_btn)

        layout.addWidget(self.toolbar)

        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.image_label)
        
        layout.addWidget(self.scroll_area)

    def load_file(self, file_path: str, password: str = None, document_id: int = None):
        self._file_path = file_path
        self._password = password
        self._document_id = document_id
        self._current_page = 0
        self._zoom = 1.5
        self._rotation = 0
        
        # Get total pages (basic check, worker handles rendering)
        import fitz
        try:
            if document_id:
                # For server documents, we'll get page count from API or download
                self._total_pages = 0  # Will be set when document is loaded
            else:
                # Local file access (fallback)
                doc = fitz.open(file_path)
                if self._password:
                    doc.authenticate(self._password)
                self._total_pages = doc.page_count
                doc.close()
        except Exception:
            self._total_pages = 0
        
        self._update_controls()
        self._request_render()

    def _request_render(self):
        if not self._file_path and not self._document_id:
            return

        self.image_label.setText("Loading...")
        
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()

        # Get API manager from main window if available
        api_manager = None
        if self._document_id:
            try:
                from ..main_window import MainWindow
                main_window = self.parent()
                while main_window and not isinstance(main_window, MainWindow):
                    main_window = main_window.parent()
                if main_window:
                    api_manager = main_window.api_manager
            except Exception:
                pass

        self._worker = PdfRenderWorker(
            self._file_path, 
            self._zoom, 
            self._current_page, 
            self._rotation, 
            password=self._password,
            document_id=self._document_id,
            api_manager=api_manager
        )
        self._worker.finished.connect(self._on_render_finished)
        self._worker.error.connect(self._on_render_error)
        self._worker.page_count_loaded.connect(self._on_page_count_loaded)
        self._worker.start()

    def _on_render_finished(self, pixmap: QPixmap):
        self.image_label.setPixmap(pixmap)
        self.image_label.adjustSize()

    def _on_render_error(self, error: str):
        self.image_label.setText(f"Error: {error}")

    def _on_page_count_loaded(self, page_count: int):
        self._total_pages = page_count
        self._update_controls()

    def _update_controls(self):
        self.page_label.setText(f"{self._current_page + 1} / {self._total_pages}")
        self.prev_btn.setEnabled(self._current_page > 0)
        self.next_btn.setEnabled(self._current_page < self._total_pages - 1)

    def _prev_page(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._update_controls()
            self._request_render()

    def _next_page(self):
        if self._current_page < self._total_pages - 1:
            self._current_page += 1
            self._update_controls()
            self._request_render()

    def _zoom_in(self):
        self._zoom += 0.25
        self._request_render()

    def _zoom_out(self):
        if self._zoom > 0.5:
            self._zoom -= 0.25
            self._request_render()
    
    def _rotate_right(self):
        self._rotation = (self._rotation + 90) % 360
        self._request_render()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_R:
            self._rotate_right()
            event.accept()
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self._zoom_in()
            else:
                self._zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)
