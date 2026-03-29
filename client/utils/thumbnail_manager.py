import os
import hashlib
import logging
from typing import Optional, Dict
from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, QSize, Qt, QStandardPaths
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

class ThumbnailRunnable(QRunnable):
    """
    Background task to generate a thumbnail from a PDF file.
    """
    class Signals(QObject):
        finished = pyqtSignal(str, QPixmap)  # cache_key, pixmap
        error = pyqtSignal(str, str)         # cache_key, error_message

    def __init__(self, file_path: str, cache_key: str, size: QSize):
        super().__init__()
        self.file_path = file_path
        self.cache_key = cache_key
        self.size = size
        self.signals = self.Signals()

    def run(self):
        try:
            # Check if file exists
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(f"File not found: {self.file_path}")

            doc = fitz.open(self.file_path)
            if doc.page_count < 1:
                raise ValueError("Document has no pages")

            page = doc.load_page(0)
            
            # Calculate zoom to fit requested size (roughly)
            # We want high quality, so we render a bit larger and scale down if needed
            pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5)) 
            
            # Convert to QImage
            fmt = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
            qt_img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
            
            # Create QPixmap
            pixmap = QPixmap.fromImage(qt_img)
            
            # Scale to requested icon size (maintaining aspect ratio, usually)
            # Or return the raw pixmap and let UI scale. 
            # For list view icons, we usually want to scale here to save memory.
            scaled = pixmap.scaled(
                self.size, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            doc.close()
            self.signals.finished.emit(self.cache_key, scaled)

        except Exception as e:
            self.signals.error.emit(self.cache_key, str(e))

class ThumbnailManager(QObject):
    """
    Manages thumbnail generation and caching.
    """
    thumbnail_ready = pyqtSignal(str, QPixmap) # file_path (or id), pixmap

    def __init__(self, cache_dir_name: str = "pdflib_thumbnails"):
        super().__init__()
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(4)  # Limit concurrent generations
        
        self._mem_cache: Dict[str, QPixmap] = {}
        self._pending: set[str] = set()
        
        # Setup disk cache
        cache_root = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)
        self._disk_cache_dir = Path(cache_root) / cache_dir_name
        self._disk_cache_dir.mkdir(parents=True, exist_ok=True)

    def get_thumbnail(self, file_path: str, size: QSize = QSize(140, 140)) -> Optional[QPixmap]:
        """
        Returns thumbnail if cached. If not, returns None and starts generation in background.
        """
        # Generate a unique key for this file (path + mod_time) to invalidate on change
        try:
            mod_time = os.path.getmtime(file_path)
        except OSError:
            return None # File inaccessible
            
        key_raw = f"{file_path}_{mod_time}_{size.width()}x{size.height()}"
        cache_key = hashlib.md5(key_raw.encode('utf-8')).hexdigest()

        # 1. Check Memory Cache
        if cache_key in self._mem_cache:
            return self._mem_cache[cache_key]

        # 2. Check Disk Cache
        disk_path = self._disk_cache_dir / f"{cache_key}.png"
        if disk_path.exists():
            pix = QPixmap(str(disk_path))
            if not pix.isNull():
                self._mem_cache[cache_key] = pix
                return pix

        # 3. Schedule Generation
        if cache_key not in self._pending:
            self._pending.add(cache_key)
            task = ThumbnailRunnable(file_path, cache_key, size)
            
            # We need to pass the file_path back so the UI knows which item to update
            # But the Runnable uses cache_key. We'll map it back in the signal handler?
            # Simpler: The signal includes cache_key. But UI needs file_path.
            # Solution: We emit a signal that the UI listens to.
            # But wait, the UI usually associates items with file paths.
            # Let's verify how we'll match it back.
            # If we pass file_path as a "user data" to the signal.
            
            task.signals.finished.connect(
                lambda k, p: self._on_thumbnail_finished(k, p, file_path, disk_path)
            )
            task.signals.error.connect(
                lambda k, e: self._on_thumbnail_error(k, e)
            )
            self._pool.start(task)

        return None

    def _on_thumbnail_finished(self, cache_key: str, pixmap: QPixmap, file_path: str, disk_path: Path):
        self._pending.discard(cache_key)
        self._mem_cache[cache_key] = pixmap
        
        # Save to disk
        try:
            pixmap.save(str(disk_path), "PNG")
        except Exception as e:
            logger.warning(f"Failed to save thumbnail cache: {e}")

        self.thumbnail_ready.emit(file_path, pixmap)

    def _on_thumbnail_error(self, cache_key: str, error_msg: str):
        self._pending.discard(cache_key)
        logger.error(f"Thumbnail generation error: {error_msg}")
        # Optionally emit a specific 'failed' signal or just do nothing (keep default icon)
