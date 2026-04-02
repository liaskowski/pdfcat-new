# This is a new file, it requires the ThumbnailRunnable class.
# I'll create it here as it's a small helper for the UI components.
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, QSize, Qt
from PyQt6.QtGui import QImage

class ThumbnailRunnable(QRunnable):
    """
    Background task to fetch thumbnail from server for UI lists.
    """
    class Signals(QObject):
        # Emit QImage (thread-safe) instead of QPixmap
        finished = pyqtSignal(int, QImage)  # doc_id, image

    def __init__(self, api, doc_id: int, size: QSize):
        super().__init__()
        self.api = api
        self.doc_id = doc_id
        self.size = size
        self.signals = self.Signals()

    def run(self):
        import gc
        import time
        # Check if API has authentication token
        if not self.api.token:
            return
            
        from ..utils.cache_manager import CacheManager
        cache = CacheManager()

        # Fetch preview from server
        try:
            png_bytes = self.api.get_preview_png(self.doc_id)
            img = QImage()
            img.loadFromData(png_bytes, "PNG")

            if not img.isNull():
                # Scale for list view
                scaled = img.scaled(
                    self.size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # Save to cache
                cache.save_thumbnail(self.doc_id, scaled)
                
                self.signals.finished.emit(self.doc_id, scaled)
                
                # Be nice to memory and UI thread
                gc.collect()
                time.sleep(0.1) # Small gap between requests
        except Exception as e:
            # Suppress common network/not-found errors
            pass
