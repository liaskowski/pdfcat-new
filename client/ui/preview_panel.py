from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QHBoxLayout, QSizePolicy, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThreadPool
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath
from typing import Optional
import qtawesome as qta
from ..api_manager import APIManager, APIDocument
from ..widgets.modern_pdf_viewer import ModernPDFViewer
from ..themes import ThemeManager
from ..utils.translator import Translator
from ..utils.cache_manager import CacheManager
from ..api.config import config
from .layouts.flow_layout import FlowLayout

class PreviewPanel(QFrame):
    """
    A widget that displays document preview, metadata, and action buttons.
    """
    open_file = pyqtSignal(int)
    edit_file = pyqtSignal(APIDocument)
    download_file = pyqtSignal(APIDocument)
    delete_file = pyqtSignal(APIDocument)
    tag_clicked = pyqtSignal(str)

    def __init__(self, api: APIManager, parent=None):
        super().__init__(parent)
        self.api = api
        self.theme_manager = ThemeManager()
        self.translator = Translator()
        self.cache_manager = CacheManager()
        self.setObjectName("inspectorPanel")
        self.setMinimumWidth(200)
        
        self._document: APIDocument | None = None
        self._current_doc_id = None
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(3) # Preview, Avatar, maybe Metadata

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        text_color = self.theme_manager.get_color("text")

        # --- Preview Card ---
        preview_card = QFrame()
        preview_card.setObjectName("card")
        preview_layout = QVBoxLayout(preview_card)
        preview_title = QLabel(self.translator.tr("preview.title"))
        preview_title.setObjectName("sectionTitle")
        
        self.preview_widget = ModernPDFViewer()
        self.preview_widget.setMinimalMode(True)
        self.preview_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_widget.first_page_rendered.connect(self._on_preview_generated)
        
        preview_layout.addWidget(preview_title)
        preview_layout.addWidget(self.preview_widget)

        # --- Metadata Card ---
        meta_card = QFrame()
        meta_card.setObjectName("card")
        meta_layout = QVBoxLayout(meta_card)
        self.date_label = QLabel(self.translator.tr("preview.date").format(date="—"))
        self.size_label = QLabel(self.translator.tr("preview.size_kb").format(size="0"))
        
        # Owner Row with Avatar
        owner_row = QHBoxLayout()
        owner_row.setContentsMargins(0,0,0,0)
        self.avatar_lbl = QLabel()
        self.avatar_lbl.setFixedSize(24, 24)
        self.owner_label = QLabel(self.translator.tr("preview.owner").format(owner="—"))
        owner_row.addWidget(self.avatar_lbl)
        owner_row.addWidget(self.owner_label)
        owner_row.addStretch()
        
        self.category_label = QLabel(self.translator.tr("preview.category").format(category="—"))
        self.file_type_label = QLabel(self.translator.tr("preview.file_type").format(file_type="—"))
        
        meta_layout.addWidget(self.date_label)
        meta_layout.addWidget(self.size_label)
        meta_layout.addLayout(owner_row)
        meta_layout.addWidget(self.category_label)
        meta_layout.addWidget(self.file_type_label)

        # --- Tags Section ---
        tags_container = QWidget()
        tags_container_layout = QVBoxLayout(tags_container)
        tags_container_layout.setContentsMargins(0, 0, 0, 0)
        tags_container_layout.setSpacing(4)

        tags_header = QHBoxLayout()
        tags_title = QLabel(self.translator.tr("preview.tags"))
        tags_title.setObjectName("sectionTitle")
        self.edit_tags_btn = QPushButton()
        self.edit_tags_btn.setIcon(qta.icon('fa5s.pencil-alt', color=text_color))
        self.edit_tags_btn.setFixedSize(20, 20)
        self.edit_tags_btn.setFlat(True)
        self.edit_tags_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_tags_btn.clicked.connect(self._on_edit_tags_clicked)

        tags_header.addWidget(tags_title)
        tags_header.addWidget(self.edit_tags_btn)
        tags_header.addStretch()

        # Use FlowLayout for tags to allow wrapping
        self.tags_widget = QWidget()
        self.tags_layout = FlowLayout(self.tags_widget, margin=0, spacing=6)
        
        # Limit height and add scrolling if needed
        self.tags_widget.setMaximumHeight(120)
        tags_scroll = QScrollArea()
        tags_scroll.setWidget(self.tags_widget)
        tags_scroll.setWidgetResizable(True)
        tags_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tags_scroll.setFrameShape(QFrame.Shape.NoFrame)
        tags_scroll.setMaximumHeight(120)

        tags_container_layout.addLayout(tags_header)
        tags_container_layout.addWidget(tags_scroll)
        
        meta_layout.addWidget(tags_container)
        
        # --- Description Card ---
        desc_card = QFrame()
        desc_card.setObjectName("card")
        desc_layout = QVBoxLayout(desc_card)
        desc_title = QLabel(self.translator.tr("preview.notes"))
        desc_title.setObjectName("sectionTitle")
        self.description_text = QTextEdit()
        self.description_text.setObjectName("input")
        self.description_text.setReadOnly(True)
        self.description_text.setPlaceholderText(self.translator.tr("preview.notes") + "...")
        self.description_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.description_text.setMaximumHeight(200)
        self.description_text.setMinimumHeight(60)
        desc_layout.addWidget(desc_title)
        desc_layout.addWidget(self.description_text)

        # --- Buttons ---
        buttons_row = QFrame()
        buttons_layout = QHBoxLayout(buttons_row)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(8)
        
        text_color = self.theme_manager.get_color("text")
        white = self.theme_manager.get_color("white")

        from PyQt6.QtCore import QSize
        icon_size = QSize(20, 20)

        self.open_file_btn = QPushButton(self.translator.tr("context_menu.open"))
        self.open_file_btn.setIcon(qta.icon('fa5s.external-link-alt', color=text_color))
        self.open_file_btn.setIconSize(icon_size)
        
        self.edit_btn = QPushButton(self.translator.tr("common.edit"))
        self.edit_btn.setIcon(qta.icon('fa5s.edit', color=text_color))
        self.edit_btn.setIconSize(icon_size)
        
        self.download_btn = QPushButton(self.translator.tr("context_menu.download"))
        self.download_btn.setIcon(qta.icon('fa5s.download', color=white))
        self.download_btn.setIconSize(icon_size)
        
        self.delete_btn = QPushButton(self.translator.tr("common.delete"))
        self.delete_btn.setIcon(qta.icon('fa5s.trash-alt', color=white))
        self.delete_btn.setIconSize(icon_size)
        
        for btn in [self.open_file_btn, self.edit_btn, self.download_btn, self.delete_btn]:
            btn.setObjectName("secondaryButton" if btn != self.download_btn else "primaryButton")
            if btn == self.delete_btn: btn.setObjectName("dangerButton")
            btn.setMinimumHeight(40)
            btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            buttons_layout.addWidget(btn)

        # --- Layout ---
        layout.addWidget(preview_card, 1)
        layout.addWidget(meta_card, 0)
        layout.addWidget(desc_card, 0)
        layout.addWidget(buttons_row, 0)
        
        # --- Connections ---
        self.open_file_btn.clicked.connect(self._on_open_clicked)
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        self.download_btn.clicked.connect(self._on_download_clicked)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        
        self.set_document(None) # Initial state

    def set_document(self, doc: APIDocument | None, current_user_id: int | None = None, is_admin: bool = False):
        # 1. Update current document ID for tracking async tasks
        self._document = doc
        self._current_doc_id = doc.id if doc else None
        
        # 2. Safety: Disconnect old signals (let runnables finish in background pool)
        if hasattr(self, '_preview_signals') and self._preview_signals:
            try: self._preview_signals.finished.disconnect()
            except: pass
            self._preview_signals = None

        if hasattr(self, '_avatar_signals') and self._avatar_signals:
            try: self._avatar_signals.finished.disconnect()
            except: pass
            self._avatar_signals = None

        if doc is None:
            self.date_label.setText(self.translator.tr("preview.date").format(date="—"))
            self.size_label.setText(self.translator.tr("preview.size_kb").format(size="0"))
            self.owner_label.setText(self.translator.tr("preview.owner").format(owner="—"))
            self.avatar_lbl.clear()
            self.category_label.setText(self.translator.tr("preview.category").format(category="—"))
            self.file_type_label.setText(self.translator.tr("preview.file_type").format(file_type="—"))
            self._clear_tags()
            self.description_text.setPlainText("")

            self.open_file_btn.setEnabled(False)
            self.download_btn.setEnabled(False)
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return

        # Enable buttons
        self.open_file_btn.setEnabled(True)
        self.download_btn.setEnabled(True)

        # Populate metadata
        file_size = doc.file_size or 0
        if file_size > 1024 * 1024:  # > 1MB
            size_text = f"{file_size / (1024 * 1024):.2f} MB"
            self.size_label.setText(self.translator.tr("preview.size_mb").format(size=size_text))
        else:
            size_text = f"{file_size / 1024:.1f} KB"
            self.size_label.setText(self.translator.tr("preview.size_kb").format(size=size_text))
        
        self.date_label.setText(self.translator.tr("preview.date").format(date=doc.upload_date or 'N/A'))
        self.owner_label.setText(self.translator.tr("preview.owner").format(owner=doc.owner_username or 'N/A'))
        self.category_label.setText(self.translator.tr("preview.category").format(category=doc.category.name if doc.category else '—'))
        self.file_type_label.setText(self.translator.tr("preview.file_type").format(file_type=doc.file_type.name if doc.file_type else '—'))
        
        self._clear_tags()
        if doc.tags:
            for tag in doc.tags.split(","):
                tag = tag.strip()
                if tag:
                    display_text = tag if tag.startswith("#") else f"#{tag}"
                    btn = QPushButton(display_text)
                    btn.setObjectName("tagButton")
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    search_query = tag if tag.startswith("#") else f"#{tag}"
                    btn.clicked.connect(lambda checked, q=search_query: self.tag_clicked.emit(q))
                    self.tags_layout.addWidget(btn)

        self.description_text.setPlainText(doc.notes or self.translator.tr("preview.no_notes"))
        self._adjust_notes_height()
        
        # Load avatar ASYNCHRONOUSLY
        if doc.owner_avatar_url:
            self._load_avatar_async(doc.owner_avatar_url)
        else:
            self._set_default_avatar()

        # Set permissions
        is_owner = (current_user_id is not None and doc.owner_id == current_user_id)
        is_owner_or_admin = is_owner or is_admin
        can_edit = is_owner_or_admin or doc.is_public_edit
        can_delete = is_owner_or_admin
        can_download = is_owner_or_admin or not doc.is_read_only

        self.edit_btn.setVisible(is_owner_or_admin or doc.is_public_edit)
        self.delete_btn.setVisible(is_owner_or_admin)
        self.edit_btn.setEnabled(can_edit)
        self.delete_btn.setEnabled(can_delete)
        self.download_btn.setEnabled(can_download)

        # Check Cache FIRST
        cached_preview = self.cache_manager.get_large_preview(doc.id)
        if cached_preview:
            self.preview_widget.show_static_preview(cached_preview)
            self._load_preview_async(doc.id, doc.encryption_key)
        else:
            self._load_preview_async(doc.id, doc.encryption_key)

    def _load_preview_async(self, doc_id: int, password: Optional[str] = None):
        """Load preview asynchronously with debouncing using QThreadPool."""
        if not hasattr(self, 'preview_widget'): return
        self.preview_widget.image_label.setText(self.translator.tr("preview.loading"))

        # De-bounce increased to 250ms for faster navigation
        if not hasattr(self, '_preview_load_timer'):
            from PyQt6.QtCore import QTimer
            self._preview_load_timer = QTimer()
            self._preview_load_timer.setSingleShot(True)
            
        try: self._preview_load_timer.timeout.disconnect()
        except: pass
        
        self._preview_load_timer.setInterval(250)
        self._preview_load_timer.timeout.connect(
            lambda: self._start_preview_download(doc_id, password)
        )
        self._preview_load_timer.start()
    
    def _start_preview_download(self, doc_id: int, password: Optional[str] = None):
        """Actually start the download using QThreadPool."""
        from ..utils.workers import DownloadRunnable
        
        # Double check if we still want this document
        if doc_id != self._current_doc_id:
            return

        # Disconnect old signals
        if hasattr(self, '_preview_signals') and self._preview_signals:
            try: self._preview_signals.finished.disconnect()
            except: pass

        runnable = DownloadRunnable(self.api, doc_id)
        self._preview_signals = runnable.signals # Keep reference to signals
        self._preview_signals.finished.connect(
            lambda did, content: self._on_preview_loaded(did, content, password)
        )
        self._preview_signals.error.connect(self._on_preview_error)
        self._pool.start(runnable)
    
    def _on_preview_loaded(self, doc_id: int, content: bytes, password: Optional[str]):
        """Handle async preview load completion."""
        if doc_id != self._current_doc_id:
            return # Ignore stale results
            
        try:
            self.preview_widget.load_document(content, password=password)
        except Exception as e:
            print(f"Failed to display preview: {e}")
            self.preview_widget.image_label.setText(f"Error: {str(e)}")
    
    def _on_preview_error(self, error_msg: str):
        if "404" in error_msg: return
        print(f"Preview load error: {error_msg}")
        self.preview_widget.image_label.setText(f"Failed to load preview")

    def _load_avatar_async(self, url: str):
        """Load avatar asynchronously via QThreadPool."""
        from ..utils.workers import AvatarRunnable
        
        if not url or not url.strip():
            self._set_default_avatar()
            return
            
        full_url = url if url.startswith("http") else f"{self.api.base_url}/{url.lstrip('/')}"
        
        # Disconnect previous if any
        if hasattr(self, '_avatar_signals') and self._avatar_signals:
            try: self._avatar_signals.finished.disconnect()
            except: pass

        runnable = AvatarRunnable(self.api, full_url)
        self._avatar_signals = runnable.signals
        self._avatar_signals.finished.connect(self._on_avatar_loaded)
        self._pool.start(runnable)

    def _on_avatar_loaded(self, url: str, pixmap: QPixmap):
        """Handle async avatar load."""
        if not self._document or not self._document.owner_avatar_url:
            return
            
        # Verify this avatar still belongs to current doc
        current_avatar_url = self._document.owner_avatar_url
        if not current_avatar_url.startswith("http"):
            current_avatar_url = f"{self.api.base_url}/{current_avatar_url.lstrip('/')}"
            
        if url != current_avatar_url:
            return
            
        self._set_avatar_pixmap(pixmap)



    def _clear_tags(self):
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_edit_tags_clicked(self):
        if self._document:
            self.edit_file.emit(self._document)

    def _on_preview_generated(self, pixmap: QPixmap):
        if self._document:
            self.cache_manager.save_large_preview(self._document.id, pixmap)

    def _set_avatar_pixmap(self, pixmap: QPixmap):
        size = 24
        rounded = QPixmap(size, size)
        rounded.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        painter.end()
        self.avatar_lbl.setPixmap(rounded)

    def _set_default_avatar(self):
        pix = QPixmap(24, 24)
        pix.fill(Qt.GlobalColor.gray)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, 24, 24)
        painter.setClipPath(path) 
        painter.end()
        self.avatar_lbl.setPixmap(pix)

    def _on_open_clicked(self):
        if self._document:
            self.open_file.emit(self._document.id)

    def _on_edit_clicked(self):
        if self._document:
            self.edit_file.emit(self._document)
            
    def _on_download_clicked(self):
        if self._document:
            self.download_file.emit(self._document)
            
    def _on_delete_clicked(self):
        if self._document:
            self.delete_file.emit(self._document)

    def _adjust_notes_height(self):
        doc_height = self.description_text.document().size().height()
        margins = self.description_text.contentsMargins()
        frame_width = self.description_text.frameWidth() * 2
        new_height = int(doc_height + margins.top() + margins.bottom() + frame_width + 10)
        # 60 is min, 200 is max (set in UI)
        self.description_text.setFixedHeight(min(200, max(60, new_height)))
