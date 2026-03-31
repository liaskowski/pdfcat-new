from typing import List, Tuple, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QRect
from PyQt6.QtGui import QImage, QPixmap
import fitz  # PyMuPDF

class RenderSignals(QObject):
    finished = pyqtSignal(int, object, list) # page_num, low_res_pixmap, words
    viewport_ready = pyqtSignal(QPixmap, QRect) # pixmap, target_rect_in_widget_coords
    error = pyqtSignal(str)

class InitialRenderWorker(QRunnable):
    """ Generates LowRes preview and extracts text words quickly. """
    def __init__(self, doc: fitz.Document, page_num: int, scale: float, rotation: int = 0, max_dimension: int = 4000):
        super().__init__()
        self.doc = doc
        self.page_num = page_num
        self.scale = scale
        self.rotation = rotation
        self.max_dimension = max_dimension # Safety limit (approx 2x 1080p or 1440p)
        self.signals = RenderSignals()

    def run(self):
        try:
            page = self.doc.load_page(self.page_num)
            
            # Calculate target size at full scale
            mat_full = fitz.Matrix(self.scale, self.scale).prerotate(self.rotation)
            rect_full = page.rect * mat_full
            
            # Determine Low Res Scale
            # Goal: Create a preview that is not too huge.
            # Current logic: 0.25 of full scale.
            low_scale = self.scale * 0.25
            
            # Check limits
            w_preview = page.rect.width * low_scale
            h_preview = page.rect.height * low_scale
            
            if w_preview > self.max_dimension or h_preview > self.max_dimension:
                # Cap scaling
                ratio = min(self.max_dimension / page.rect.width, self.max_dimension / page.rect.height)
                low_scale = ratio
            
            mat_low = fitz.Matrix(low_scale, low_scale).prerotate(self.rotation)
            pix_low = page.get_pixmap(matrix=mat_low)
            
            fmt = QImage.Format.Format_RGB888
            qimg = QImage(pix_low.samples, pix_low.width, pix_low.height, pix_low.stride, fmt)
            low_res_pix = QPixmap.fromImage(qimg)
            
            # 2. Words (Full coordinates)
            raw_words = page.get_text("words")
            words = []
            for w in raw_words:
                # Map word rect to FULL scale for selection logic
                rect = fitz.Rect(w[:4]) * mat_full
                words.append((rect.x0, rect.y0, rect.x1, rect.y1, w[4], w[5], w[6], w[7]))
            
            self.signals.finished.emit(self.page_num, low_res_pix, words)
        except Exception as e:
            self.signals.error.emit(str(e))

class ViewportRenderWorker(QRunnable):
    """ Renders ONLY the visible area in High Quality. """
    def __init__(self, doc: fitz.Document, page_num: int, scale: float, rotation: int, visible_rect: QRect):
        super().__init__()
        self.doc = doc
        self.page_num = page_num
        self.scale = scale
        self.rotation = rotation
        self.visible_rect = visible_rect # In PageLabel (Widget) coordinates
        self.signals = RenderSignals()

    def run(self):
        try:
            page = self.doc.load_page(self.page_num)
            
            # Map Widget Coords -> PDF Coords
            x = self.visible_rect.x() / self.scale
            y = self.visible_rect.y() / self.scale
            w = self.visible_rect.width() / self.scale
            h = self.visible_rect.height() / self.scale
            
            clip_rect = fitz.Rect(x, y, x + w, y + h)
            
            # Apply full scale matrix
            mat = fitz.Matrix(self.scale, self.scale).prerotate(self.rotation)
            
            # Render clipped area
            pix = page.get_pixmap(matrix=mat, clip=clip_rect)
            
            fmt = QImage.Format.Format_RGB888
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
            hq_pix = QPixmap.fromImage(qimg)
            
            self.signals.viewport_ready.emit(hq_pix, self.visible_rect)
            
        except Exception as e:
            # self.signals.error.emit(str(e))
            pass
