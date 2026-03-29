
import os
from pathlib import Path
from PyQt6.QtCore import Qt, QSettings, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMainWindow, QApplication, QProgressBar, QSizePolicy, QSizeGrip

from .api_manager import APIManager
from .api.config import config
from .ui.layouts.main_layout import MainLayout
from .ui.controllers.main_controller import MainController
from .utils.logger import get_logger, log_error, log_warning, log_info

logger = get_logger("client.main_window")

# Get paths to assets
CLIENT_DIR = Path(__file__).parent
ASSETS_DIR = CLIENT_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "pdfCat.jpg"
ICON_PATH = ASSETS_DIR / "pdfCat.ico"

class MainWindow(QMainWindow):
    # Signal to delegate drop events to controller
    drop_event_requested = pyqtSignal(object, object)  # event, tree_pos
    
    def __init__(self) -> None:
        super().__init__()
        
        # Set application icon
        if ICON_PATH.exists():
            app_icon = QIcon(str(ICON_PATH))
            self.setWindowIcon(app_icon)
            QApplication.setWindowIcon(app_icon)
            log_info("main_window", f"Application icon set: {ICON_PATH}")
        else:
            log_warning("main_window", f"Icon file not found: {ICON_PATH}")
        
        # Enable frameless window for custom title bar and resizing
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Initialize API
        self.settings = QSettings("pdflib", "client")
        base_url = str(self.settings.value("base_url", "http://127.0.0.1:8000"))
        config.set_base_url(base_url)
        
        token = self.settings.value("token")
        token_str = str(token) if token else None
        self.api = APIManager(base_url=config.base_url, token=token_str)

        # Initialize Layout
        self.ui = MainLayout(self, self.api)
             
        # Restore Window State
        geometry = self.settings.value("MainWindow/geometry")
        state = self.settings.value("MainWindow/windowState")
        
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1280, 800)
        
        self.setMinimumSize(1024, 768)
            
        if state:
            self.restoreState(state)

        # Status Bar Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setStyleSheet("QProgressBar { border: 0px; border-radius: 4px; text-align: center; } QProgressBar::chunk { background-color: #3b82f6; border-radius: 4px; }")
        self.statusBar().addPermanentWidget(self.progress_bar)
        
        # Add Size Grip
        self.statusBar().addPermanentWidget(QSizeGrip(self))
        
        # Initialize Controller
        self.controller = MainController(self, self.ui, self.api)
        
        # Ensure central widget and title bar track mouse for resizing
        if self.centralWidget():
            self.centralWidget().setMouseTracking(True)
            self.centralWidget().installEventFilter(self)
        
        # CRITICAL: Title bar must be filtered by MainWindow to prioritize resizing over dragging
        self.ui.title_bar.setMouseTracking(True)
        self.ui.title_bar.installEventFilter(self)
        # Also filter window control buttons to prevent them from eating resize events in corners
        for btn in [self.ui.title_bar.min_btn, self.ui.title_bar.max_btn, self.ui.title_bar.close_btn]:
            btn.installEventFilter(self)
        
        self.installEventFilter(self)

    def closeEvent(self, event):
        try:
            from .utils.logger import log_debug, log_info
            log_info("main_window", "Application closing, saving state...")

            # Save geometry and state
            self.settings.setValue("MainWindow/geometry", self.saveGeometry())
            self.settings.setValue("MainWindow/windowState", self.saveState())
            log_debug("main_window", "Window geometry and state saved")

            # Save caches
            self.ui.file_grid._save_thumbnail_cache()
            log_debug("main_window", "Thumbnail cache saved")

            self.controller.search_handler._save_cache()
            log_debug("main_window", "Document cache saved")

            # Save controller state
            self.controller.save_state()
            log_debug("main_window", "Controller state saved")

            log_info("main_window", "Application closed successfully")
        except Exception as e:
            from .utils.logger import log_error
            log_error("main_window", f"Error during close: {e}", exc_info=True)
        finally:
            super().closeEvent(event)

    def dragEnterEvent(self, event):
        from .utils.logger import log_debug
        log_debug("main_window", f"dragEnterEvent: hasUrls={event.mimeData().hasUrls()}, urlCount={len(event.mimeData().urls())}")
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            log_debug("main_window", "dragEnterEvent accepted")

    def dropEvent(self, event):
        from .utils.logger import log_debug, log_error
        try:
            log_debug("main_window", f"dropEvent: position={event.position()}, source={event.source()}")
            tree_pos = self.ui.nav_tree.viewport().mapFrom(self, event.position().toPoint())
            log_debug("main_window", f"tree_pos={tree_pos}, emitting signal")
            self.drop_event_requested.emit(event, tree_pos)
            log_debug("main_window", "dropEvent signal emitted")
        except Exception as e:
            log_error("main_window", f"dropEvent error: {e}", exc_info=True)

    def update_progress(self, value: int, message: str = ""):
        """Update progress bar in status bar for non-blocking progress display."""
        if value < 0 or value >= 100:
            self.progress_bar.setVisible(False)
            if message:
                self.statusBar().showMessage(message, 3000)
        else:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(value)
            if message:
                self.statusBar().showMessage(message)
    
    def set_upload_progress(self, value: int, total: int, message: str = ""):
        """Set upload progress in status bar (non-blocking)."""
        if total > 0:
            percent = int((value / total) * 100)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(percent)
            status_msg = f"Upload: {value}/{total} - {message}" if message else f"Upload: {value}/{total}"
            self.statusBar().showMessage(status_msg)
    
    def set_indexing_progress(self, value: int, total: int, message: str = ""):
        """Set indexing progress in status bar (non-blocking)."""
        if total > 0:
            percent = int((value / total) * 100)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(percent)
            status_msg = f"Indexing: {value}/{total} - {message}" if message else f"Indexing: {value}/{total}"
            self.statusBar().showMessage(status_msg)
    
    def clear_progress(self):
        """Clear progress bar and status message."""
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.statusBar().clearMessage()

    # --- Resizing Logic (Frameless Window) ---
    @property
    def _resize_margin(self):
        return 10

    def eventFilter(self, obj, event):
        if event.type() == event.Type.HoverMove or event.type() == event.Type.MouseMove:
            self._handle_resize_hover(event)
            if hasattr(self, "_resize_mode") and self._resize_mode:
                return True # Consume event if resizing
        elif event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self._handle_resize_press(event)
            if hasattr(self, "_resize_mode") and self._resize_mode:
                return True # Consume event if resizing
        elif event.type() == event.Type.MouseButtonRelease:
            if hasattr(self, "_resize_mode") and self._resize_mode:
                self._resize_mode = None
                self.setCursor(Qt.CursorShape.ArrowCursor)
                return True
            
        return super().eventFilter(obj, event)

    def _handle_resize_hover(self, event):
        # Only handle if not dragging window via titlebar (CustomTitleBar handles that)
        if hasattr(self, "_resize_mode") and self._resize_mode:
            self._handle_resize_move(event)
            return

        pos = event.globalPosition().toPoint() - self.pos()
        rect = self.rect()
        margin = self._resize_margin
        
        # Determine cursor shape
        cursor = Qt.CursorShape.ArrowCursor
        
        x, y = pos.x(), pos.y()
        w, h = rect.width(), rect.height()
        
        if x < margin and y < margin: cursor = Qt.CursorShape.SizeFDiagCursor
        elif x > w - margin and y > h - margin: cursor = Qt.CursorShape.SizeFDiagCursor
        elif x < margin and y > h - margin: cursor = Qt.CursorShape.SizeBDiagCursor
        elif x > w - margin and y < margin: cursor = Qt.CursorShape.SizeBDiagCursor
        elif x < margin or x > w - margin: cursor = Qt.CursorShape.SizeHorCursor
        elif y < margin or y > h - margin: cursor = Qt.CursorShape.SizeVerCursor
        
        # Only override cursor if we are at an edge
        if cursor != Qt.CursorShape.ArrowCursor:
            self.setCursor(cursor)
        else:
            # Check if we need to reset cursor (only if we previously set it)
            if self.cursor().shape() in (
                Qt.CursorShape.SizeFDiagCursor, Qt.CursorShape.SizeBDiagCursor, 
                Qt.CursorShape.SizeHorCursor, Qt.CursorShape.SizeVerCursor
            ):
                 self.setCursor(Qt.CursorShape.ArrowCursor)

    def _handle_resize_press(self, event):
        pos = event.globalPosition().toPoint() - self.pos()
        rect = self.rect()
        margin = self._resize_margin
        
        x, y = pos.x(), pos.y()
        w, h = rect.width(), rect.height()
        
        self._resize_mode = None
        if x < margin: self._resize_mode = "left"
        elif x > w - margin: self._resize_mode = "right"
        
        if y < margin: 
            self._resize_mode = "top" if not self._resize_mode else self._resize_mode + "_top"
        elif y > h - margin: 
            self._resize_mode = "bottom" if not self._resize_mode else self._resize_mode + "_bottom"

        if self._resize_mode:
            self._drag_pos = event.globalPosition().toPoint()

    def _handle_resize_move(self, event):
        if not self._resize_mode:
            return
            
        global_pos = event.globalPosition().toPoint()
        diff = global_pos - self._drag_pos
        
        # Don't do anything if no movement
        if diff.x() == 0 and diff.y() == 0:
            return

        geo = self.geometry()
        min_w = self.minimumWidth()
        min_h = self.minimumHeight()
        
        new_geo = self.geometry()
        
        if "left" in self._resize_mode:
            new_left = geo.left() + diff.x()
            new_width = geo.width() - diff.x()
            if new_width >= min_w:
                new_geo.setLeft(new_left)
        elif "right" in self._resize_mode:
            new_width = geo.width() + diff.x()
            if new_width >= min_w:
                new_geo.setRight(geo.right() + diff.x())
        
        if "top" in self._resize_mode:
            new_top = geo.top() + diff.y()
            new_height = geo.height() - diff.y()
            if new_height >= min_h:
                new_geo.setTop(new_top)
        elif "bottom" in self._resize_mode:
            new_height = geo.height() + diff.y()
            if new_height >= min_h:
                new_geo.setBottom(geo.bottom() + diff.y())
            
        if new_geo != geo:
            self.setGeometry(new_geo)
            self._drag_pos = global_pos

    def _make_pdf_icon(self, size: int) -> QIcon:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.white)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor("black"))
        p.setBrush(QColor("white"))
        p.drawRoundedRect(1, 1, size - 2, size - 2, 10, 10)
        font = QFont()
        font.setBold(True)
        font.setPointSize(max(8, int(size / 4)))
        p.setFont(font)
        p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "PDF")
        p.end()
        return QIcon(pix)

    def _make_circle_avatar_pixmap(self, size: int) -> QPixmap:
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor("black"))
        p.setBrush(QColor("white"))
        p.drawEllipse(1, 1, size - 2, size - 2)
        font = QFont()
        font.setBold(True)
        font.setPointSize(max(10, int(size / 3)))
        p.setFont(font)
        p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "U")
        p.end()
        return pix
