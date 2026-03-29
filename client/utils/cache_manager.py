import os
import fitz
from pathlib import Path
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import QStandardPaths, QObject
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        # ~/.cache/pdflib/
        self.cache_dir = Path.home() / ".cache" / "pdflib"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_thumbnail(self, doc_id: int) -> QImage | None:
        """Returns cached thumbnail for doc_id or None."""
        path = self.cache_dir / f"{doc_id}.png"
        if path.exists():
            try:
                img = QImage(str(path))
                if not img.isNull():
                    return img
            except Exception as e:
                logger.warning(f"Failed to load cached thumbnail {doc_id}: {e}")
        return None

    def save_thumbnail(self, doc_id: int, image: QImage):
        """Saves thumbnail to cache."""
        try:
            path = self.cache_dir / f"{doc_id}.png"
            image.save(str(path), "PNG")
            self._cleanup_if_needed()
        except Exception as e:
            logger.warning(f"Failed to save thumbnail {doc_id}: {e}")

    def _cleanup_if_needed(self):
        """Clear ALL old thumbnails when quality settings change."""
        try:
            # For now, clear all cache to regenerate with new quality
            # This ensures all thumbnails use the new 0.4 matrix
            files = list(self.cache_dir.glob("*.png"))
            if files:
                logger.info(f"Clearing {len(files)} old cached thumbnails")
                for f in files:
                    f.unlink()
        except Exception:
            pass

    def generate_from_path(self, file_path: str, doc_id: int) -> QImage | None:
        """
        Generates thumbnail for file grid.
        Balanced quality/performance: 0.4 matrix for readable previews.
        """
        try:
            doc = fitz.open(file_path)
            if doc.page_count < 1:
                return None

            page = doc.load_page(0)
            # BALANCED: 0.4 = ~400x560 for A4 (good enough to see content)
            # This is 3x smaller than original 1.4, but much clearer than 0.2
            pix = page.get_pixmap(matrix=fitz.Matrix(0.4, 0.4))

            # Convert to QImage
            fmt = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
            qt_img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt).copy()

            # Save to cache
            self.save_thumbnail(doc_id, qt_img)

            doc.close()
            return qt_img
        except Exception as e:
            logger.error(f"Failed to generate thumbnail for {file_path}: {e}")
            return None
            return None

    def get_large_preview(self, doc_id: int) -> QPixmap | None:
        """Returns cached large preview for doc_id or None."""
        path = self.cache_dir / f"preview_large_{doc_id}.png"
        if path.exists():
            try:
                pix = QPixmap(str(path))
                if not pix.isNull():
                    return pix
            except Exception as e:
                logger.warning(f"Failed to load cached preview {doc_id}: {e}")
        return None

    def save_large_preview(self, doc_id: int, pixmap: QPixmap):
        """Saves large preview to cache."""
        try:
            path = self.cache_dir / f"preview_large_{doc_id}.png"
            pixmap.save(str(path), "PNG")
        except Exception as e:
            logger.warning(f"Failed to save preview {doc_id}: {e}")
