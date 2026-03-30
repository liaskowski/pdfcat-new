from typing import Optional, List, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel, QPushButton, 
    QFrame, QGraphicsDropShadowEffect, QApplication, QLineEdit, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize, QThreadPool, QTimer, QEvent, QRect, QRectF, QTime
from PyQt6.QtGui import QPixmap, QWheelEvent, QPainter, QColor, QImage, QPen, QIntValidator
import fitz
import qtawesome as qta

from ..themes import ThemeManager
from ..utils.translator import Translator
from .pdf.render_worker import InitialRenderWorker, PageRenderWorker
from .pdf.viewport_mgr import ViewportManager
from ..utils.workers import OCRSearchWorker

class ModernPDFViewer(QWidget):
    """
    Ultimate Pro Viewer.
    Optimized for 60 FPS via Manual Clipping and Seamless Viewport Tiling.
    """
    first_page_rendered = pyqtSignal(QPixmap)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        # Hardware Acceleration
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        self.theme_manager = ThemeManager()
        self.translator = Translator()
        self._doc: Optional[fitz.Document] = None
        self._source: Optional[str | bytes] = None
        self._password: Optional[str] = None
        self._current_page = 0
        self._zoom = 1.0
        self._rotation = 0
        self._thread_pool = QThreadPool()
        self._thread_pool.setMaxThreadCount(2)  # Limit threads for smoother UI

        # Search and Highlighting
        self.current_highlights: List[QRectF] = []
        self._ocr_worker: Optional[OCRSearchWorker] = None
        self._is_ocr_searching = False

        # Rendering State
        self._preview_pixmap: Optional[QPixmap] = None
        self._viewport_pixmap: Optional[QPixmap] = None
        self._viewport_rect: QRect = QRect()
        self._is_moving = False
        self._is_minimal = False
        
        # Snap Mode (for technical drawings)
        self._snap_mode = False  # Disabled by default
        self._snap_threshold = 10  # pixels

        # Selection
        self._words = []
        self._selected_rects = []
        self._selection_start: Optional[QPoint] = None
        self._is_selecting = False

        self._is_zooming = False
        self._zoom_timer = None
        
        # Performance optimization for large documents
        self._is_large_document = False  # Enable for files with complex drawings
        
        # Smooth zoom handling - queue zoom requests instead of blocking
        self._pending_zoom_factor = 1.0
        self._zoom_queue_timer = None
        
        # Prevent render pile-up
        self._render_pending = False

        self._init_ui()
        self.viewport_mgr = ViewportManager(self.scroll_area, self.image_label)
        
        self._render_timer = QTimer()
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(50)  # 50ms debounce for scroll
        self._render_timer.timeout.connect(self._update_visible_area)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # Connect scroll with debouncing
        self.scroll_area.horizontalScrollBar().valueChanged.connect(self._on_scroll)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll)

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.viewport().setAttribute(Qt.WidgetAttribute.WA_StaticContents)
        
        self.page_container = QWidget()
        self.page_layout = QVBoxLayout(self.page_container)
        self.page_layout.setContentsMargins(40, 40, 40, 40)
        self.page_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        class ViewportLabel(QLabel):
            def paintEvent(self, event):
                viewer = self.parent_viewer
                if not viewer._preview_pixmap: return

                painter = QPainter(self)
                dirty_rect = event.rect()
                painter.setClipRect(dirty_rect)

                # 1. Background Layer
                # OPTIMIZATION: Disable smoothing during zoom for better performance
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, not viewer._is_moving and not viewer._is_zooming)
                source_rect = self._map_to_pixmap(dirty_rect, viewer._preview_pixmap.size())
                painter.drawPixmap(dirty_rect, viewer._preview_pixmap, source_rect)

                # 2. High-Res Layer
                if viewer._viewport_pixmap:
                    vp_rect = viewer._viewport_rect
                    if dirty_rect.intersects(vp_rect):
                        target = dirty_rect.intersected(vp_rect)
                        source = target.translated(-vp_rect.topLeft())
                        painter.drawPixmap(target.topLeft(), viewer._viewport_pixmap, source)
                
                # 3. Search Highlights Overlay
                if hasattr(viewer, 'current_highlights') and viewer.current_highlights:
                    painter.save()
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                    highlight_color = QColor(255, 255, 0, 120)
                    painter.setBrush(highlight_color)
                    painter.setPen(Qt.PenStyle.NoPen)
                    
                    z = viewer._zoom
                    for r in viewer.current_highlights:
                        scaled_rect = QRectF(r.x() * z, r.y() * z, r.width() * z, r.height() * z)
                        if dirty_rect.intersects(scaled_rect.toRect()):
                            painter.drawRoundedRect(scaled_rect, 2, 2)
                    painter.restore()

                # 4. Selection Overlay
                if hasattr(viewer, '_selected_rects') and viewer._selected_rects:
                    painter.save()
                    painter.setBrush(QColor(0, 120, 215, 80))
                    painter.setPen(Qt.PenStyle.NoPen)
                    for r in viewer._selected_rects:
                        sr = QRect(int(r.x0), int(r.y0), int(r.width), int(r.height))
                        if dirty_rect.intersects(sr): painter.drawRect(sr)
                    painter.restore()

                # 5. Visual Debug: OCR analysis area
                if hasattr(viewer, '_ocr_debug_rect') and viewer._is_ocr_searching:
                    painter.setPen(QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.DashLine))
                    painter.drawRect(viewer._ocr_debug_rect)

                # 6. OCR Status Indicator
                if viewer._is_ocr_searching:
                    painter.save()
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setBrush(QColor(0, 0, 0, 180))
                    painter.setPen(Qt.PenStyle.NoPen)
                    status_rect = QRect(10, 10, 160, 30)
                    painter.drawRoundedRect(status_rect, 15, 15)
                    painter.setPen(Qt.GlobalColor.white)
                    painter.drawText(status_rect, Qt.AlignmentFlag.AlignCenter, "OCR Searching...")
                    painter.restore()

                painter.end()

            def _map_to_pixmap(self, rect: QRect, pix_size: QSize) -> QRect:
                rx = rect.x() / self.width() * pix_size.width()
                ry = rect.y() / self.height() * pix_size.height()
                rw = rect.width() / self.width() * pix_size.width()
                rh = rect.height() / self.height() * pix_size.height()
                return QRect(int(rx), int(ry), int(rw), int(rh))

        self.image_label = ViewportLabel()
        self.image_label.parent_viewer = self
        self.image_label.setMouseTracking(True)
        self.image_label.installEventFilter(self)
        
        self.page_layout.addWidget(self.image_label)
        self.scroll_area.setWidget(self.page_container)
        self.main_layout.addWidget(self.scroll_area)

        # Floating UI
        self.floating_panel = QFrame(self)
        self.floating_panel.setObjectName("floatingControls")
        self.floating_panel.setStyleSheet("""
            QFrame#floatingControls {
                background: rgba(35, 35, 35, 220);
                border-radius: 24px;
                border: 1px solid rgba(255, 255, 255, 30);
            }
            QPushButton { background: transparent; border: none; color: white; padding: 10px; border-radius: 18px; }
            QPushButton:hover { background: rgba(255, 255, 255, 40); }
            QLabel { color: white; font-weight: bold; }
            QLineEdit { background: rgba(255, 255, 255, 20); border: none; border-radius: 6px; color: white; padding: 2px 5px; }
        """)
        
        fp_layout = QHBoxLayout(self.floating_panel)
        fp_layout.setContentsMargins(15, 5, 15, 5)
        fp_layout.setSpacing(10)
        
        self.btn_prev = self._create_btn("fa5s.chevron-left", self.prev_page)
        self.page_input = QLineEdit(); self.page_input.setFixedWidth(40); self.page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_input.setValidator(QIntValidator(1, 9999)); self.page_input.returnPressed.connect(self._on_page_jump)
        self.lbl_total = QLabel("/ 0"); self.btn_next = self._create_btn("fa5s.chevron-right", self.next_page)
        fp_layout.addWidget(self.btn_prev); fp_layout.addWidget(self.page_input); fp_layout.addWidget(self.lbl_total); fp_layout.addWidget(self.btn_next)
        line = QFrame(); line.setFixedWidth(1); line.setStyleSheet("background: rgba(255,255,255,40); margin: 8px 0;"); fp_layout.addWidget(line)
        self.btn_zoom_out = self._create_btn("fa5s.minus", self.zoom_out); self.lbl_zoom = QLabel("100%"); self.btn_zoom_in = self._create_btn("fa5s.plus", self.zoom_in)
        fp_layout.addWidget(self.btn_zoom_out); fp_layout.addWidget(self.lbl_zoom); fp_layout.addWidget(self.btn_zoom_in)
        line2 = QFrame(); line2.setFixedWidth(1); line2.setStyleSheet("background: rgba(255,255,255,40); margin: 8px 0;"); fp_layout.addWidget(line2)
        self.btn_fit_width = self._create_btn("fa5s.arrows-alt-h", self.fit_width); self.btn_fit_page = self._create_btn("fa5s.expand", self.fit_page)
        fp_layout.addWidget(self.btn_fit_width); fp_layout.addWidget(self.btn_fit_page)

        self.btn_rotate_ccw = self._create_btn("fa5s.undo", self.rotate_ccw)
        self.btn_rotate_cw = self._create_btn("fa5s.redo", self.rotate_cw)
        fp_layout.addWidget(self.btn_rotate_ccw); fp_layout.addWidget(self.btn_rotate_cw)
        
        # Snap Mode Toggle (for panning - replaces middle mouse button)
        line3 = QFrame(); line3.setFixedWidth(1); line3.setStyleSheet("background: rgba(255,255,255,40); margin: 8px 0;"); fp_layout.addWidget(line3)
        self.btn_snap = self._create_btn("fa5s.hand-paper", self._toggle_snap_mode)
        self.btn_snap.setCheckable(True)
        self.btn_snap.setChecked(False)
        self.btn_snap.setToolTip("Pan Mode (drag to move view)")
        fp_layout.addWidget(self.btn_snap)

        self.floating_panel.adjustSize()
        # Don't connect scroll signals here - already connected in __init__
        self.update_theme()

    def rotate_cw(self):
        self._rotation = (self._rotation + 90) % 360
        if self._doc:
            page = self._doc.load_page(self._current_page)
            page.set_rotation(self._rotation)
        self._viewport_pixmap = None
        self._render_current_page()
        self._update_ui_state()

    def rotate_ccw(self):
        self._rotation = (self._rotation - 90) % 360
        if self._doc:
            page = self._doc.load_page(self._current_page)
            page.set_rotation(self._rotation)
        self._viewport_pixmap = None
        self._render_current_page()
        self._update_ui_state()
    
    def _toggle_snap_mode(self):
        """Toggle pan mode (same as middle mouse button)."""
        self._snap_mode = not self._snap_mode
        self.btn_snap.setChecked(self._snap_mode)
        self.btn_snap.setToolTip(f"Pan Mode: {'ON' if self._snap_mode else 'OFF'} (drag to move view)")
        
        # Update cursor if pan mode is enabled
        if self._snap_mode:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def highlight_search_result(self, query: str):
        """
        Searches for query on the current page and highlights results.
        """
        self.clear_highlights()
        if not self._doc or not query:
            return

        page = self._doc.load_page(self._current_page)
        page.set_rotation(self._rotation)
        
        # 1. Native Search
        areas = page.search_for(query)
        if areas:
            self.current_highlights = [QRectF(r.x0, r.y0, r.width, r.height) for r in areas]
            self.image_label.update()
            self._scroll_to_first_highlight()
            return

        # 2. OCR Fallback
        self._run_ocr_search(query)

    def set_ocr_highlights(self, rects: List[QRectF]):
        """Callback for OCR results."""
        page = self._doc.load_page(self._current_page)
        page.set_rotation(self._rotation)
        mat = page.rotation_matrix
        
        transformed = []
        for r in rects:
            fr = fitz.Rect(r.x(), r.y(), r.x() + r.width(), r.y() + r.height())
            tr = fr * mat
            transformed.append(QRectF(tr.x0, tr.y0, tr.width, tr.height))
            
        self.current_highlights = transformed
        self.image_label.update()
        if rects:
            self._scroll_to_first_highlight()

    def _run_ocr_search(self, query: str):
        if self._is_ocr_searching:
            return

        page = self._doc.load_page(self._current_page)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        
        self._is_ocr_searching = True
        z = self._zoom
        self._ocr_debug_rect = QRect(0, 0, int(page.rect.width * z), int(page.rect.height * z))
        self.image_label.update()
        
        self._ocr_worker = OCRSearchWorker(
            pix.tobytes("png"), 
            query, 
            (page.rect.width, page.rect.height)
        )
        self._ocr_worker.results_found.connect(self.set_ocr_highlights)
        self._ocr_worker.error.connect(lambda e: print(f"OCR Error: {e}"))
        self._ocr_worker.finished.connect(self._on_ocr_finished)
        self._ocr_worker.start()

    def clear_highlights(self):
        self.current_highlights = []
        if self._ocr_worker and self._ocr_worker.isRunning():
            self._ocr_worker.terminate()
        self._is_ocr_searching = False
        self.image_label.update()

    def _on_ocr_finished(self):
        self._is_ocr_searching = False
        if hasattr(self, '_ocr_debug_rect'):
            delattr(self, '_ocr_debug_rect')
        self.image_label.update()

    def _scroll_to_first_highlight(self):
        if not self.current_highlights:
            return
        first = self.current_highlights[0]
        z = self._zoom
        target_y = int(first.top() * z)
        self.scroll_area.verticalScrollBar().setValue(target_y - 100)

    def _create_btn(self, icon, callback):
        btn = QPushButton()
        btn.setIcon(qta.icon(icon, color="white"))
        btn.clicked.connect(callback)
        btn.setProperty("iconOnly", True)
        return btn

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.floating_panel.move((self.width() - self.floating_panel.width()) // 2, self.height() - self.floating_panel.height() - 30)

    def hideEvent(self, event):
        self._thread_pool.clear(); super().hideEvent(event)

    def setMinimalMode(self, mode: bool):
        self._is_minimal = mode
        self.floating_panel.setVisible(not mode)
        m = 0 if mode else 40; self.page_layout.setContentsMargins(m, m, m, m)
        self._toggle_shadow(not (mode or self._zoom > 1.5))

    def _toggle_shadow(self, enabled: bool):
        if enabled:
            # Re-create the effect because Qt takes ownership and may delete it when removed
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(30)
            shadow.setColor(QColor(0, 0, 0, 150))
            self.image_label.setGraphicsEffect(shadow)
        else:
            self.image_label.setGraphicsEffect(None)

    def show_static_preview(self, data):
        if isinstance(data, QPixmap): self._preview_pixmap = data
        else:
            if not data: return
            pix = QPixmap(); pix.loadFromData(data); self._preview_pixmap = pix
        if self._preview_pixmap:
            self.image_label.setFixedSize(self._preview_pixmap.size()); self.image_label.update()

    def load_document(self, source: str | bytes, password: str = None):
        self.current_highlights = []
        self.image_label.update()
        self._thread_pool.clear()

        # Close existing document first
        if self._doc:
            try:
                self._doc.close()
            except Exception:
                pass
            self._doc = None
        
        self._source = source
        self._password = password
        
        try:
            if isinstance(source, bytes):
                self._doc = fitz.open(stream=source, filetype="pdf")
            else:
                self._doc = fitz.open(source)

            if password:
                self._doc.authenticate(password)

            if self._doc.is_encrypted and self._doc.needs_pass:
                # Can't render encrypted document without password
                self.image_label.setText("Document is encrypted\nPassword required")
                self._doc.close()
                self._doc = None
                return

            if self._doc.page_count == 0:
                self.image_label.setText("Document has no pages")
                self._doc.close()
                self._doc = None
                return
            
            # DETECT LARGE DOCUMENTS (technical drawings, etc.)
            # Check first page size to determine if optimization is needed
            first_page = self._doc.load_page(0)
            page_area = first_page.rect.width * first_page.rect.height
            A4_area = 595 * 842  # Standard A4 at 72 DPI
            
            # If page is > 4x larger than A4, it's a large document (drawing, blueprint, etc.)
            self._is_large_document = page_area > (A4_area * 4)
            
            if self._is_large_document:
                print(f"[PERF] Large document detected: {first_page.rect.width}x{first_page.rect.height}")
                print(f"[PERF] Enabling optimizations for technical drawing")
            
            first_page = None  # Release page reference

            self._current_page = 0
            self._update_ui_state()
            self.fit_width()  # Start with fit-to-width view
            
        except Exception as e:
            self._doc = None
            error_msg = f"Failed to load document:\n{str(e)}"
            print(f"Load failed: {e}")
            self.image_label.setText(error_msg)

    def _on_scroll(self):
        self._is_moving = True
        # NOTE: We no longer clear _viewport_pixmap here to keep the view "Clear"
        self.image_label.update()
        self._render_timer.start()

    def _update_visible_area(self):
        self._is_moving = False
        
        # SKIP render during zoom for maximum performance
        if self._is_zooming:
            return

        if not self._doc or self._doc.is_closed or not self.isVisible(): return
        if self._doc.is_encrypted and self._doc.needs_pass: return

        try:
            page = self._doc.load_page(self._current_page)
            page.set_rotation(self._rotation)

            # Pass 0 as extra rotation because we already set it on the page object
            matrix, clip, target_rect = self.viewport_mgr.get_render_params(page, self._zoom, 0)

            # OPTIMIZATION for large documents: use smaller tiles (but still render!)
            if self._is_large_document:
                self.viewport_mgr.tile_size = 256  # Smaller tiles for large docs
            else:
                self.viewport_mgr.tile_size = 512

            worker = PageRenderWorker(self._source, self._current_page, matrix, clip, target_rect, self._password, self._rotation)
            worker.signals.viewport_ready.connect(self._on_viewport_ready)
            self._thread_pool.start(worker, priority=10)
        except Exception as e:
            print(f"Failed to load page for viewport: {e}")

    def _on_viewport_ready(self, pixmap, rect, page_num):
        if not self._doc or self._doc.is_closed: return
        if page_num != self._current_page: return
        self._viewport_pixmap = pixmap; self._viewport_rect = rect
        self.image_label.update(rect)

    def _render_current_page(self):
        if not self._doc or self._doc.is_closed: return
        if self._doc.is_encrypted and self._doc.needs_pass: return

        try:
            page = self._doc.load_page(self._current_page)
            page.set_rotation(self._rotation)

            w, h = page.rect.width, page.rect.height
            self.image_label.setFixedSize(int(w * self._zoom), int(h * self._zoom))

            # ADAPTIVE QUALITY based on zoom level:
            if self._is_large_document:
                # Large documents (technical drawings): aggressive optimization
                if self._is_zooming:
                    max_dim = 512   # During zoom: ultra low for speed
                elif self._zoom < 0.5:
                    max_dim = 512   # Very far: low quality
                elif self._zoom < 1.0:
                    max_dim = 768   # Far: medium-low quality
                elif self._zoom < 1.5:
                    max_dim = 1024  # Medium: good quality
                elif self._zoom < 3.0:
                    max_dim = 1536  # Close: high quality
                else:
                    max_dim = 2048  # Very close: maximum quality
            else:
                # Normal documents: standard quality
                if self._is_zooming:
                    max_dim = 768   # During zoom: lower quality
                elif self._zoom < 1.0:
                    max_dim = 1024  # Far: medium quality
                elif self._zoom < 2.0:
                    max_dim = 2048  # Medium: good quality
                else:
                    max_dim = 4000  # Close: maximum quality
            
            worker = InitialRenderWorker(self._source, self._current_page, self._zoom, self._password, rotation=self._rotation, max_dimension=max_dim, extract_words=not self._is_minimal)
            worker.signals.finished.connect(self._on_initial_ready)
            
            # Prevent render pile-up
            if self._render_pending:
                return  # Skip if render already pending
            
            self._render_pending = True
            self._thread_pool.start(worker)
        except Exception as e:
            print(f"Failed to load page for initial render: {e}")

    def _on_initial_ready(self, page_num, pixmap, words):
        if page_num == self._current_page:
            # Set Device Pixel Ratio for High DPI displays
            pixmap.setDevicePixelRatio(self.devicePixelRatio())
            self._preview_pixmap = pixmap; self._words = words; self._selected_rects = []

            # Reset viewport cache on page/zoom change
            self._viewport_pixmap = None
            self._viewport_rect = QRect()

            self._toggle_shadow(not (self._is_minimal or self._zoom > 1.5))
            self.image_label.update()

            # Reset render pending flag
            self._render_pending = False

            # Delay high-res render to ensure layout is ready
            QTimer.singleShot(20, self._update_visible_area)

    def _apply_zoom(self, factor: float, center_pos: Optional[QPoint] = None):
        if not self._doc: return
        
        # SMOOTH ZOOM: Accumulate zoom factors instead of blocking
        self._pending_zoom_factor *= factor
        
        # Cancel pending zoom render if exists
        if self._zoom_queue_timer and self._zoom_queue_timer.isActive():
            self._zoom_queue_timer.stop()
        
        # Execute zoom immediately for responsiveness
        self._execute_zoom(center_pos)
        
        # Schedule final high-quality render after zoom sequence
        if self._zoom_timer is None:
            self._zoom_timer = QTimer()
            self._zoom_timer.setSingleShot(True)
            self._zoom_timer.timeout.connect(self._on_zoom_stop)
        self._zoom_timer.start(200)  # 200ms after last zoom
    
    def _execute_zoom(self, center_pos: Optional[QPoint] = None):
        """Execute accumulated zoom with SMART quality scaling."""
        if not self._doc or self._pending_zoom_factor == 1.0:
            return
        
        self._is_zooming = True
        
        anchor = self.scroll_area.viewport().rect().center() if center_pos is None else self.image_label.mapTo(self.scroll_area.viewport(), center_pos)
        content_anchor = self.scroll_area.widget().mapFrom(self.scroll_area.viewport(), anchor)
        relative_anchor = content_anchor - self.image_label.pos()
        old_zoom = self._zoom
        
        # Apply accumulated zoom
        self._zoom = max(0.05, min(20.0, self._zoom * self._pending_zoom_factor))
        actual_factor = self._zoom / old_zoom
        
        # SMART ZOOM QUALITY:
        # At low zoom (<150%): Use pixmap scaling (fast, acceptable quality)
        # At high zoom (>150%): Trigger re-render for sharpness
        if self._zoom < 1.5:
            # LOW ZOOM: Scale existing pixmap (instant, good enough)
            if self._preview_pixmap and not self._preview_pixmap.isNull():
                new_size = QSize(int(self._preview_pixmap.width() * actual_factor),
                               int(self._preview_pixmap.height() * actual_factor))
                scaled = self._preview_pixmap.scaled(new_size, Qt.AspectRatioMode.KeepAspectRatio, 
                                                      Qt.TransformationMode.SmoothTransformation)
                self._preview_pixmap = scaled
                self.image_label.setFixedSize(new_size)
                self.image_label.update()
            else:
                self._render_current_page()
        else:
            # HIGH ZOOM: Re-render at appropriate quality (sharp!)
            self._viewport_pixmap = None
            self._render_current_page()
        
        self.scroll_area.widget().adjustSize()
        
        new_content_anchor = self.image_label.pos() + (relative_anchor * actual_factor)
        self.scroll_area.horizontalScrollBar().setValue(int(new_content_anchor.x() - anchor.x()))
        self.scroll_area.verticalScrollBar().setValue(int(new_content_anchor.y() - anchor.y()))
        self._update_ui_state()
        
        # Reset pending zoom
        self._pending_zoom_factor = 1.0
    
    def _on_zoom_stop(self):
        """Called when zoom stops to trigger high-quality render."""
        self._is_zooming = False
        
        # Final high-quality render after zoom sequence
        # Use QTimer to avoid blocking UI
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, self._render_current_page)

    def zoom_in(self): self._apply_zoom(1.25)
    def zoom_out(self): self._apply_zoom(0.8)
    def fit_width(self):
        if self._doc: self._zoom = (self.scroll_area.viewport().width() - 80) / self._doc.load_page(self._current_page).rect.width; self._viewport_pixmap = None; self._render_current_page(); self._update_ui_state()
    def fit_page(self):
        if self._doc: r = self._doc.load_page(self._current_page).rect; self._zoom = min((self.scroll_area.viewport().width()-80)/r.width, (self.scroll_area.viewport().height()-80)/r.height); self._viewport_pixmap = None; self._render_current_page(); self._update_ui_state()
    def prev_page(self): 
        self.current_highlights = []
        self.image_label.update()
        if self._current_page > 0: 
            self._current_page -= 1
            self._viewport_pixmap = None
            self._render_current_page()
            self._update_ui_state()

    def next_page(self):
        self.current_highlights = []
        self.image_label.update()
        if self._doc and self._current_page < self._doc.page_count - 1: 
            self._current_page += 1
            self._viewport_pixmap = None
            self._render_current_page()
            self._update_ui_state()
    def _on_page_jump(self):
        try:
            p = int(self.page_input.text()) - 1
            if 0 <= p < self._doc.page_count: self._current_page = p; self._viewport_pixmap = None; self._render_current_page(); self._update_ui_state()
        except: self._update_ui_state()
    def _update_ui_state(self):
        if not self._doc: return
        self.lbl_total.setText(f"/ {self._doc.page_count}"); self.page_input.setText(str(self._current_page + 1)); self.lbl_zoom.setText(f"{int(self._zoom * 100)}%")
    def update_theme(self, theme_name: str = None):
        t = theme_name or self.theme_manager.current_theme
        
        # Main Backgrounds (Matches Themes)
        if t == "Dark":
            bg_main = "#1C1C1E" 
            bg_panel = "rgba(44, 44, 46, 230)" # Elevated surface, semi-transparent
            text_color = "white"
            border_color = "rgba(255, 255, 255, 30)"
            icon_color = "white"
            input_bg = "rgba(255, 255, 255, 20)"
            btn_hover = "rgba(255, 255, 255, 40)"
        else:
            bg_main = "#E5E5EA" # Slightly darker than main window for contrast (PDF background)
            bg_panel = "rgba(255, 255, 255, 230)"
            text_color = "#1C1C1E"
            border_color = "rgba(0, 0, 0, 30)"
            icon_color = "#1C1C1E"
            input_bg = "rgba(0, 0, 0, 10)"
            btn_hover = "rgba(0, 0, 0, 15)"

        self.scroll_area.setStyleSheet(f"background: {bg_main}; border: none;")
        self.page_container.setStyleSheet(f"background: {bg_main};")
        
        # Floating Panel Styling
        self.floating_panel.setStyleSheet(f"""
            QFrame#floatingControls {{
                background: {bg_panel};
                border-radius: 12px;
                border: 1px solid {border_color};
            }}
            QPushButton {{ background: transparent; border: none; color: {text_color}; padding: 8px; border-radius: 8px; }}
            QPushButton:hover {{ background: {btn_hover}; }}
            QLabel {{ color: {text_color}; font-weight: 600; font-family: "Inter"; }}
            QLineEdit {{ background: {input_bg}; border: none; border-radius: 6px; color: {text_color}; padding: 4px; font-weight: 600; }}
        """)
        
        # Update Icons
        for btn, icon_name in [
            (self.btn_prev, "fa5s.chevron-left"),
            (self.btn_next, "fa5s.chevron-right"),
            (self.btn_zoom_out, "fa5s.minus"),
            (self.btn_zoom_in, "fa5s.plus"),
            (self.btn_fit_width, "fa5s.arrows-alt-h"),
            (self.btn_fit_page, "fa5s.expand"),
            (self.btn_rotate_ccw, "fa5s.undo"),
            (self.btn_rotate_cw, "fa5s.redo"),
            (self.btn_snap, "fa5s.hand-paper")  # Hand icon for pan mode
        ]:
            btn.setIcon(qta.icon(icon_name, color=icon_color))
    def _show_context_menu(self, pos):
        if not self._selected_rects: return
        m = QMenu(self); m.addAction("Copy").triggered.connect(self.copy_selection); m.exec(self.mapToGlobal(pos))
    def copy_selection(self):
        if not self._selected_rects: return
        res = []; sorted_w = sorted(self._words, key=lambda x: (x[1], x[0]))
        for w in sorted_w:
            wr = fitz.Rect(w[0], w[1], w[2], w[3])
            for r in self._selected_rects:
                if r.intersects(wr): res.append(w[4]); break
        if res: QApplication.clipboard().setText(" ".join(res))
    def eventFilter(self, obj, event):
        if obj == self.image_label:
            if event.type() == QEvent.Type.Wheel:
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    mp = event.position().toPoint()
                    if event.angleDelta().y() > 0: self._apply_zoom(1.25, mp)
                    else: self._apply_zoom(0.8, mp)
                    return True
                return False
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.MiddleButton or (event.button() == Qt.MouseButton.LeftButton and self._snap_mode):
                    # Enable panning (middle mouse OR left mouse with snap mode enabled)
                    self._is_panning = True
                    self._last_pos = event.globalPosition().toPoint()
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
                    return True
                elif event.button() == Qt.MouseButton.LeftButton and not self._snap_mode:
                    # Enable selection (left mouse when snap mode is OFF)
                    self._is_selecting = True
                    self._selection_start = event.pos()
                    self._selected_rects = []
                    return True
            elif event.type() == QEvent.Type.MouseMove:
                if getattr(self, '_is_panning', False):
                    d = event.globalPosition().toPoint() - self._last_pos; self._last_pos = event.globalPosition().toPoint()
                    self.scroll_area.horizontalScrollBar().setValue(self.scroll_area.horizontalScrollBar().value() - d.x())
                    self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().value() - d.y()); return True
                elif self._is_selecting:
                    self._update_selection(event.pos()); return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self._is_panning = False; self._is_selecting = False; self.setCursor(Qt.CursorShape.ArrowCursor); return True
        return super().eventFilter(obj, event)
    def _update_selection(self, pos):
        if not self._selection_start: return
        sr = fitz.Rect(min(self._selection_start.x(), pos.x()), min(self._selection_start.y(), pos.y()), max(self._selection_start.x(), pos.x()), max(self._selection_start.y(), pos.y()))
        lines = {}
        for w in self._words:
            if sr.intersects(fitz.Rect(w[0], w[1], w[2], w[3])):
                k = (w[5], w[6])
                if k not in lines: lines[k] = fitz.Rect(w[0], w[1], w[2], w[3])
                else: lines[k].include_rect(fitz.Rect(w[0], w[1], w[2], w[3]))
        self._selected_rects = list(lines.values()); self.image_label.update()
