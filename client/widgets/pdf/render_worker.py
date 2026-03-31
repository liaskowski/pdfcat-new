from typing import List, Tuple, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, QRect
from PyQt6.QtGui import QImage, QPixmap
import fitz  # PyMuPDF

class RenderSignals(QObject):
    finished = pyqtSignal(int, object, list) # page_num, low_res_pixmap, words
    viewport_ready = pyqtSignal(QPixmap, QRect, int) # pixmap, target_rect, page_num
    error = pyqtSignal(str)

class InitialRenderWorker(QRunnable):
    """ Generates LowRes preview and extracts text words quickly. """
    def __init__(self, source: str | bytes, page_num: int, scale: float, password: str = None, 
                 rotation: int = 0, max_dimension: int = 4000, extract_words: bool = True):
        super().__init__()
        self.source = source
        self.page_num = page_num
        self.scale = scale
        self.password = password
        self.rotation = rotation
        self.max_dimension = max_dimension
        self.extract_words = extract_words
        self.signals = RenderSignals()

    def run(self):
        doc = None
        try:
            if isinstance(self.source, bytes):
                doc = fitz.open(stream=self.source, filetype="pdf")
            else:
                doc = fitz.open(self.source)
            
            if self.password:
                doc.authenticate(self.password)

            page = doc.load_page(self.page_num)
            # Apply rotation before any measurements or rendering
            if self.rotation != 0:
                page.set_rotation(self.rotation)
            
            # Matrix only handles scaling now
            mat_full = fitz.Matrix(self.scale, self.scale)
            
            if not self.extract_words:
                self.max_dimension = min(self.max_dimension, 1024)

            low_scale = self.scale * 0.15
            w_preview = page.rect.width * low_scale
            h_preview = page.rect.height * low_scale
            
            if w_preview > self.max_dimension or h_preview > self.max_dimension:
                ratio = min(self.max_dimension / page.rect.width, self.max_dimension / page.rect.height)
                low_scale = ratio
            
            mat_low = fitz.Matrix(low_scale, low_scale)
            pix_low = page.get_pixmap(matrix=mat_low)
            
            fmt = QImage.Format.Format_RGB888
            # .copy() is CRITICAL here to own the memory
            qimg = QImage(pix_low.samples, pix_low.width, pix_low.height, pix_low.stride, fmt).copy()
            low_res_pix = QPixmap.fromImage(qimg)
            
            words = []
            if self.extract_words:
                raw_words = page.get_text("words")
                for w in raw_words:
                    rect = fitz.Rect(w[:4]) * mat_full
                    words.append((rect.x0, rect.y0, rect.x1, rect.y1, w[4], w[5], w[6], w[7]))
            
            self.signals.finished.emit(self.page_num, low_res_pix, words)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            if doc: doc.close()

class PageRenderWorker(QRunnable):
    """ Renders ONLY the visible area in High Quality. """
    def __init__(self, source: str | bytes, page_num: int, matrix: fitz.Matrix, 
                 clip_rect: fitz.Rect, target_rect: QRect, password: str = None, rotation: int = 0):
        super().__init__()
        self.source = source
        self.page_num = page_num
        self.matrix = matrix
        self.clip_rect = clip_rect
        self.target_rect = target_rect 
        self.password = password
        self.rotation = rotation
        self.signals = RenderSignals()

    def run(self):
        doc = None
        try:
            if isinstance(self.source, bytes):
                doc = fitz.open(stream=self.source, filetype="pdf")
            else:
                doc = fitz.open(self.source)
            
            if self.password:
                doc.authenticate(self.password)

            page = doc.load_page(self.page_num)
            if self.rotation != 0:
                page.set_rotation(self.rotation)
                
            pix = page.get_pixmap(matrix=self.matrix, clip=self.clip_rect)
            
            fmt = QImage.Format.Format_RGB888
            # .copy() ensures we own the pixel data after doc/page is closed
            qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt).copy()
            hq_pix = QPixmap.fromImage(qimg)
            
            self.signals.viewport_ready.emit(hq_pix, self.target_rect, self.page_num)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            if doc: doc.close()
