from typing import Optional, Any, List
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QThreadPool, QPoint, QStandardPaths, QByteArray, QBuffer
from PyQt6.QtGui import QIcon, QPainter, QColor, QBrush, QPixmap, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QMenu,
    QInputDialog,
    QGraphicsOpacityEffect,
    QStackedLayout
)
import qtawesome as qta
import json
import os

from ..api_manager import APIManager, APIDocument, APIFolder
from .thumbnail_runnable import ThumbnailRunnable
from ..utils.translator import Translator
from ..themes import ThemeManager
from ..widgets.shimmer_widget import ShimmerOverlay

class RestrictedListWidget(QListWidget):
    """
    A QListWidget that only allows dragging files owned by the current user.
    """
    def __init__(self, current_user_id_getter, parent=None):
        super().__init__(parent)
        self.current_user_id_getter = current_user_id_getter

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item:
            doc = item.data(Qt.ItemDataRole.UserRole)
            current_id = self.current_user_id_getter()
            if isinstance(doc, APIDocument) and current_id is not None:
                if doc.owner_id != current_id:
                    return
        super().startDrag(supportedActions)

class FileGrid(QFrame):
    """
    A widget that displays files in a grid/icon view with async thumbnail loading.
    """
    file_selected = pyqtSignal(object)  # APIDocument | None
    file_double_clicked = pyqtSignal(object) # APIDocument
    
    # Action signals
    open_requested = pyqtSignal(int)
    download_requested = pyqtSignal(object)
    copy_requested = pyqtSignal(object)
    cut_requested = pyqtSignal(object)
    paste_requested = pyqtSignal()
    delete_requested = pyqtSignal(object)
    edit_requested = pyqtSignal(object)
    rename_requested = pyqtSignal(object)

    def __init__(self, api: APIManager, parent=None):
        super().__init__(parent)
        self.api = api
        self.translator = Translator()
        self.setObjectName("card")
        self._current_user_id = None
        self._user_role = None
        self._clipboard_doc_id = None

        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(1)  # SINGLE thread - sequential loading
        self._thumbnail_cache: dict[int, QIcon] = {}
        
        # Lazy loading configuration
        self._all_files: List[APIDocument] = []
        self._loaded_count = 0
        self._lazy_load_batch_size = 50  # Load 50 files at a time
        self._is_loading_more = False
        
        # Track which thumbnails are being loaded
        self._loading_thumbnails = set()

        # Load persistent thumbnail cache
        self._load_thumbnail_cache()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        title = QLabel(self.translator.tr("main.my_documents"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # Grid with Shimmer Overlay
        self.container = QFrame()
        self.container.setFrameShape(QFrame.Shape.NoFrame)
        self.container_layout = QStackedLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self.files_list = RestrictedListWidget(lambda: self._current_user_id)
        self.files_list.setObjectName("filesGrid")
        self.files_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.files_list.setMovement(QListWidget.Movement.Static)
        self.files_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.files_list.setSpacing(20)
        self.files_list.setIconSize(QSize(64, 64))
        self.files_list.setGridSize(QSize(160, 140))
        self.files_list.setWordWrap(True)
        self.files_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.files_list.setAcceptDrops(False)
        self.files_list.setDragEnabled(True)
        self.files_list.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)

        self.files_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.files_list.customContextMenuRequested.connect(self._on_context_menu)
        
        # Connect scroll signal for lazy loading
        self.files_list.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.container_layout.addWidget(self.files_list)
        
        # Shimmer overlay for loading state
        self.shimmer_overlay = ShimmerOverlay(self.files_list)
        self.container_layout.addWidget(self.shimmer_overlay)

        layout.addWidget(self.container, 1)

        self.files_list.currentItemChanged.connect(self._on_selection_changed)
        self.files_list.itemDoubleClicked.connect(self._on_item_double_clicked)

    def set_loading(self, loading: bool):
        """Show/hide shimmer loading overlay."""
        if loading:
            self.shimmer_overlay.show_overlay()
            self.files_list.setEnabled(False)
        else:
            self.shimmer_overlay.hide_overlay()
            self.files_list.setEnabled(True)
    
    def _on_scroll(self, value):
        """Handle scroll event for lazy loading."""
        if self._is_loading_more:
            return

        scrollbar = self.files_list.verticalScrollBar()
        max_value = scrollbar.maximum()
        
        # Calculate current scroll position as percentage
        scroll_percent = value / max_value if max_value > 0 else 0
        
        # Load more when user scrolls just a bit (aggressive loading)
        items_from_end = len(self._all_files) - self._loaded_count
        
        # Trigger when:
        # 1. Scrolled past 10% (very aggressive)
        # 2. OR within 1500px from bottom (very early)
        # 3. OR less than 100 items remaining (bulk preload)
        pixels_from_bottom = max_value - value if max_value > 0 else 0
        
        if (scroll_percent > 0.1 or pixels_from_bottom < 1500 or items_from_end < 100) and self._loaded_count < len(self._all_files):
            self._load_more_files()
    
    def _load_more_files(self):
        """Load thumbnails for VISIBLE files only (true lazy loading)."""
        if self._loaded_count >= len(self._all_files):
            return
        
        if self._is_loading_more:
            return  # Already loading
        
        self._is_loading_more = True
        
        # Calculate how many items are visible in viewport
        viewport_height = self.files_list.viewport().height()
        item_height = self.files_list.gridSize().height() + self.files_list.spacing()
        visible_items = max(100, (viewport_height // item_height) + 20)  # At least 100 items
        
        # Load thumbnails for next batch
        start_idx = self._loaded_count
        end_idx = min(start_idx + visible_items, len(self._all_files))
        
        workers_started = 0
        for i in range(start_idx, end_idx):
            f = self._all_files[i]
            if f.id not in self._thumbnail_cache and f.id not in self._loading_thumbnails:
                worker = ThumbnailRunnable(self.api, f.id, self.files_list.iconSize())
                worker.signals.finished.connect(self._on_thumbnail_ready)
                
                # Mark as loading
                self._loading_thumbnails.add(f.id)
                
                # Start worker
                self.thread_pool.start(worker)
                workers_started += 1
        
        self._loaded_count = end_idx
        self._is_loading_more = False

    def set_context(self, user_id: int | None, role: str | None):
        self._current_user_id = user_id
        self._user_role = role

    def set_clipboard_state(self, doc_id: int | None):
        self._clipboard_doc_id = doc_id

    def _on_item_double_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, APIDocument):
            self.file_double_clicked.emit(data)

    def _on_context_menu(self, point):
        item = self.files_list.itemAt(point)
        doc = item.data(Qt.ItemDataRole.UserRole) if item else None
        
        menu = QMenu()
        if doc:
            is_owner = self._current_user_id is not None and doc.owner_id == self._current_user_id
            is_admin = self._user_role == "admin"
            can_edit = is_owner or is_admin or doc.is_public_edit
            can_delete = is_owner or is_admin
            can_download = is_owner or is_admin or not doc.is_read_only

            menu.addAction(self.translator.tr("context_menu.open")).triggered.connect(lambda: self.open_requested.emit(doc.id))
            
            download_action = menu.addAction(self.translator.tr("context_menu.download"))
            download_action.triggered.connect(lambda: self.download_requested.emit(doc))
            if not can_download:
                download_action.setEnabled(False)
                
            menu.addSeparator()
            menu.addAction(self.translator.tr("context_menu.copy")).triggered.connect(lambda: self.copy_requested.emit(doc))
            if is_owner or is_admin:
                menu.addAction(self.translator.tr("context_menu.cut")).triggered.connect(lambda: self.cut_requested.emit(doc))
            
            if can_edit:
                menu.addSeparator()
                menu.addAction(self.translator.tr("context_menu.rename")).triggered.connect(lambda: self.rename_requested.emit(doc))
                menu.addAction(self.translator.tr("context_menu.edit_metadata")).triggered.connect(lambda: self.edit_requested.emit(doc))
            
            if can_delete:
                if not can_edit: menu.addSeparator()
                menu.addAction(self.translator.tr("context_menu.delete")).triggered.connect(lambda: self.delete_requested.emit(doc))
        
        if self._clipboard_doc_id:
            if doc: menu.addSeparator()
            menu.addAction(self.translator.tr("context_menu.paste")).triggered.connect(lambda: self.paste_requested.emit())

        menu.exec(self.files_list.mapToGlobal(point))

    def _on_selection_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None):
        if current is None:
            self.file_selected.emit(None)
            return
        
        data = current.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, APIDocument):
            self.file_selected.emit(data)
        else:
            self.file_selected.emit(None)

    def rebuild_with_files(self, files: list[APIDocument], placeholder_icon: QIcon, owner_id: Optional[int] = None):
        """
        Rebuild grid with files using TRUE lazy loading.
        Shows all files immediately, loads thumbnails only for visible items.
        """
        # Cancel all pending thumbnail workers
        self.thread_pool.clear()
        
        self.set_loading(False)
        self.files_list.clear()
        self._thumbnail_cache.clear()
        self._loading_thumbnails.clear()
        
        # Store ALL files - grid will show them all
        self._all_files = files
        self._loaded_count = 0
        
        # Add ALL items to grid immediately (with placeholder icons)
        for f in files:
            icon = placeholder_icon
            if f.is_public:
                icon = self._add_public_indicator(placeholder_icon.pixmap(self.files_list.iconSize()))

            item = QListWidgetItem(icon, f.title)
            item.setData(Qt.ItemDataRole.UserRole, f)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setSizeHint(self.files_list.gridSize())
            self.files_list.addItem(item)

        # Force layout update so viewport height is correct
        self.files_list.updateGeometry()
        self.files_list.viewport().update()
        
        # Load thumbnails for visible items IMMEDIATELY (no delay)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._load_more_files)
        
        # Also trigger after short delay to catch any layout changes
        QTimer.singleShot(200, self._load_more_files)

        if self.files_list.count() > 0:
            self.files_list.setCurrentRow(0)
        else:
            self.file_selected.emit(None)

    def _on_thumbnail_ready(self, doc_id: int, image):
        """Handle thumbnail ready signal with proper error handling."""
        # Remove from loading set
        self._loading_thumbnails.discard(doc_id)
        
        # Check if grid was cleared while loading
        if self.files_list.count() == 0:
            return

        # image is QImage (received from thread safely)
        # Convert to QPixmap on main thread
        pixmap = QPixmap.fromImage(image)

        is_public = False
        target_item = None

        # Find the item in the grid and verify it's the right document
        for i in range(self.files_list.count()):
            item = self.files_list.item(i)
            if not item:  # Item was removed during iteration
                continue

            data = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, APIDocument) and data.id == doc_id:
                is_public = data.is_public
                target_item = item
                break

        # Item may have been removed while thumbnail was loading
        if target_item is None:
            return

        final_pixmap = pixmap
        if is_public:
            final_pixmap = self._add_public_indicator(pixmap).pixmap(self.files_list.iconSize())

        icon = QIcon(final_pixmap)
        self._thumbnail_cache[doc_id] = icon
        target_item.setIcon(icon)
    
    def _add_public_indicator(self, pixmap: QPixmap) -> QIcon:
        # Create a larger canvas if needed or draw directly
        copy = QPixmap(pixmap)
        painter = QPainter(copy)
        try:
            painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
            
            # Draw dot relative to icon size
            size = int(copy.width() * 0.25) # 25% of icon width
            margin = int(copy.width() * 0.05)
            
            x = copy.width() - size - margin
            y = margin
            
            theme_manager = ThemeManager()
            # White border for contrast against the icon image
            painter.setBrush(QBrush(QColor(theme_manager.get_color("success")))) # Theme Success
            painter.setPen(QPen(QColor(theme_manager.get_color("white")), 2)) # 2px white border
            painter.drawEllipse(x, y, size, size)
        finally:
            painter.end()
        return QIcon(copy)

    def find_and_select_document(self, doc_id: int):
        for i in range(self.files_list.count()):
            item = self.files_list.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, APIDocument) and data.id == doc_id:
                self.files_list.setCurrentItem(item)
                break

    def update_single_document(self, updated_doc: APIDocument):
        """Update a single document in grid without rebuilding everything."""
        from PyQt6.QtCore import Qt
        print(f"DEBUG: update_single_document called with doc_id={updated_doc.id}, title='{updated_doc.title}'")
        print(f"DEBUG: Updated doc object: {updated_doc}")
        print(f"DEBUG: Updated doc type: {type(updated_doc)}")
        
        for i in range(self.files_list.count()):
            item = self.files_list.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            print(f"DEBUG: Item {i} data: {data}, type: {type(data)}")
            
            if isinstance(data, APIDocument) and data.id == updated_doc.id:
                print(f"DEBUG: Found document at position {i}, updating...")
                print(f"DEBUG: Before update - Item title: '{item.text()}', Data title: '{data.title}'")
                print(f"DEBUG: Before update - Item doc_id: {data.id if hasattr(data, 'id') else 'NO ID'}")
                
                # Update document data
                item.setData(Qt.ItemDataRole.UserRole, updated_doc)
                item.setText(updated_doc.title)
                
                print(f"DEBUG: After update - Item title: '{item.text()}'")
                
                # Clear thumbnail cache for this document to force refresh
                if updated_doc.id in self._thumbnail_cache:
                    del self._thumbnail_cache[updated_doc.id]
                    print(f"DEBUG: Cleared thumbnail cache for doc {updated_doc.id}")
                
                # Remove from loading thumbnails to allow re-generation
                if updated_doc.id in self._loading_thumbnails:
                    self._loading_thumbnails.remove(updated_doc.id)
                    print(f"DEBUG: Removed doc {updated_doc.id} from loading thumbnails")
                
                # Trigger thumbnail regeneration for this item only
                # Get placeholder icon from main window
                placeholder_icon = QIcon()
                if hasattr(self, '_main_window_ref'):
                    placeholder_icon = self._main_window_ref._make_pdf_icon(64)
                else:
                    # Create simple placeholder if no main window reference
                    from PyQt6.QtGui import QPixmap, QPainter
                    pix = QPixmap(64, 64)
                    pix.fill(Qt.GlobalColor.lightGray)
                    placeholder_icon = QIcon(pix)
                
                icon = placeholder_icon
                if updated_doc.is_public:
                    icon = self._add_public_indicator(icon.pixmap(self.files_list.iconSize()))
                
                item.setIcon(icon)
                
                # Start thumbnail generation for this specific document
                from .thumbnail_runnable import ThumbnailRunnable
                worker = ThumbnailRunnable(self.api, updated_doc.id, self.files_list.iconSize())
                worker.signals.finished.connect(self._on_thumbnail_ready)
                self._loading_thumbnails.add(updated_doc.id)
                self.thread_pool.start(worker)
                
                print(f"DEBUG: Updated single document {updated_doc.id} in grid successfully")
                return True
        
        # Document not found in current grid
        print(f"DEBUG: Document {updated_doc.id} not found in current grid (total items: {self.files_list.count()})")
        print(f"DEBUG: All items in grid:")
        for i in range(self.files_list.count()):
            item = self.files_list.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, APIDocument):
                print(f"  Item {i}: id={data.id}, title='{data.title}'")
            else:
                print(f"  Item {i}: data type={type(data)}, value={data}")
        
        return False

        def get_sort_key(item_data):
            doc = item_data['doc']
            if mode == 'name_asc':
                return doc.title.lower()
            return doc.upload_date or ""

        reverse = (mode == 'date_desc')
        items_data.sort(key=get_sort_key, reverse=reverse)

        # Clear and rebuild in batches
        self.files_list.clear()
        self._sorted_items_data = items_data
        self._sort_batch_index = 0
        
        from PyQt6.QtCore import QTimer
        self._sort_timer = QTimer()
        self._sort_timer.timeout.connect(self._add_sort_batch)
        self._sort_timer.start(0)  # Immediate execution
    
    def _add_sort_batch(self):
        """Add sorted items in batches to avoid UI blocking."""
        batch_size = 50
        start_idx = self._sort_batch_index
        end_idx = min(start_idx + batch_size, len(self._sorted_items_data))
        
        for i in range(start_idx, end_idx):
            item_data = self._sorted_items_data[i]
            item = QListWidgetItem(item_data['icon'], item_data['text'])
            item.setData(Qt.ItemDataRole.UserRole, item_data['doc'])
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setSizeHint(self.files_list.gridSize())
            self.files_list.addItem(item)
        
        self._sort_batch_index = end_idx
        
        # Check if done
        if self._sort_batch_index >= len(self._sorted_items_data):
            self._sort_timer.stop()
            self._sorted_items_data = []
            
            # Restore selection
            if self.files_list.count() > 0:
                self.files_list.setCurrentRow(0)

    def _load_thumbnail_cache(self):
        """Load thumbnail cache from disk on startup"""
        cache_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
        cache_file = os.path.join(cache_dir, "pdflib", "thumbnail_cache.json")
        
        if not os.path.exists(cache_file):
            return
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            
            # Convert base64 strings back to QIcon
            for doc_id_str, icon_base64 in cache.items():
                try:
                    doc_id = int(doc_id_str)
                    # Decode base64 to QPixmap
                    data = QByteArray.fromBase64(icon_base64.encode())
                    pixmap = QPixmap()
                    pixmap.loadFromData(data, "PNG")
                    
                    if not pixmap.isNull():
                        icon = QIcon(pixmap)
                        self._thumbnail_cache[doc_id] = icon
                except Exception as e:
                    print(f"Failed to load thumbnail for doc {doc_id_str}: {e}")
            
            print(f"[INFO] Loaded {len(self._thumbnail_cache)} thumbnails from cache")
        except Exception as e:
            print(f"[WARNING] Failed to load thumbnail cache: {e}")
    
    def _save_thumbnail_cache(self):
        """Save thumbnail cache to disk"""
        try:
            cache_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
            cache_path = os.path.join(cache_dir, "pdflib")
            
            # Create directory if it doesn't exist
            if not os.path.exists(cache_path):
                os.makedirs(cache_path, exist_ok=True)
            
            cache_file = os.path.join(cache_path, "thumbnail_cache.json")
            
            # Serialize QIcon to base64
            cache = {}
            for doc_id, icon in self._thumbnail_cache.items():
                try:
                    # Convert QIcon to base64 PNG
                    pixmap = icon.pixmap(64, 64)
                    if not pixmap.isNull():
                        data = QByteArray()
                        buffer = QBuffer(data)
                        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
                        pixmap.save(buffer, "PNG", 80)  # 80% quality
                        cache[str(doc_id)] = bytes(data.toBase64()).decode('ascii')
                except Exception as e:
                    print(f"Failed to serialize thumbnail for doc {doc_id}: {e}")
            
            # Save to file
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2)
            
            print(f"[INFO] Saved {len(cache)} thumbnails to cache")
        except Exception as e:
            print(f"[WARNING] Failed to save thumbnail cache: {e}")
    
    def closeEvent(self, event):
        """Handle widget close - cleanup workers."""
        # Stop all pending thumbnail workers
        self.thread_pool.clear()
        self.thread_pool.waitForDone(1000)  # Wait up to 1s
        super().closeEvent(event) if hasattr(super(), 'closeEvent') else None
