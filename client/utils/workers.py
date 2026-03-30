from PyQt6.QtCore import QThread, pyqtSignal, Qt, QRectF
from PyQt6.QtGui import QPixmap
import fitz
import tempfile
import os
import time
import io
import logging
from pathlib import Path
from PIL import Image
import pytesseract

class PdfRenderWorker(QThread):
    finished = pyqtSignal(QPixmap)
    error = pyqtSignal(str)
    page_count_loaded = pyqtSignal(int)  # New signal to report page count

    def __init__(self, file_path: str = None, zoom: float = 2.0, page_num: int = 0, rotation: int = 0, password: str = None, document_id: int = None, api_manager=None):
        super().__init__()
        self.file_path = file_path
        self.document_id = document_id
        self.api_manager = api_manager
        self.zoom = zoom
        self.page_num = page_num
        self.rotation = rotation
        self.password = password

    def run(self):
        try:
            # Handle API-based document loading
            if self.document_id and self.api_manager:
                # Download PDF from API
                pdf_bytes = self.api_manager.documents.download_document(self.document_id)
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            else:
                # Local file access (fallback)
                if not self.file_path:
                    self.error.emit("No file path or document ID provided")
                    return
                doc = fitz.open(self.file_path)
            
            if self.password:
                doc.authenticate(self.password)
                
            if doc.page_count < 1:
                self.error.emit("No pages in document")
                doc.close()
                return

            # Emit page count for API-based documents
            if self.document_id:
                self.page_count_loaded.emit(doc.page_count)

            if self.page_num >= doc.page_count:
                self.error.emit("Page number out of range")
                doc.close()
                return

            page = doc.load_page(self.page_num)
            
            # Apply rotation
            page.set_rotation(self.rotation)
            
            mat = fitz.Matrix(self.zoom, self.zoom)
            
            pix = page.get_pixmap(matrix=mat, annots=True)
            doc.close()

            # Save to temp file to load into QPixmap (safest way across threads/contexts)
            # Alternatively, we could load from bytes, but temp file is robust.
            fd, tmp_path = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            pix.save(tmp_path)
            
            qpix = QPixmap(tmp_path)
            
            # Clean up temp file immediately after loading
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            
            if qpix.isNull():
                self.error.emit("Failed to load pixmap")
            else:
                # Scale if necessary (though usually better to scale in UI)
                # We return the high-res pixmap.
                self.finished.emit(qpix)

        except Exception as e:
            self.error.emit(str(e))


class ApiPreviewWorker(QThread):
    finished = pyqtSignal(QPixmap)
    error = pyqtSignal(str)

    def __init__(self, api, document_id: int):
        super().__init__()
        self.api = api
        self.document_id = document_id

    def run(self):
        try:
            png_bytes = self.api.get_preview_png(self.document_id)
            pix = QPixmap()
            pix.loadFromData(png_bytes, "PNG")
            if pix.isNull():
                self.error.emit("Empty or invalid image data")
            else:
                self.finished.emit(pix)
        except Exception as e:
            self.error.emit(str(e))


class SearchSuggestionWorker(QThread):
    suggestions_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api, query: str, limit: int = 10):
        super().__init__()
        self.api = api
        self.query = query
        self.limit = limit

    def run(self):
        try:
            if not self.query:
                self.suggestions_ready.emit([])
                return
            
            # Use the new lightweight suggestions endpoint
            suggestions = self.api.get_suggestions(self.query)
            
            # Limit is now handled by the server, but we can double-check
            self.suggestions_ready.emit(suggestions[:self.limit])
        except Exception as e:
            # Silently fail for suggestions, or emit error if needed
            self.error.emit(str(e))

import secrets

# ... existing imports ...

from ..logic.tags_engine import TagAnalyzer

class UploadWorker(QThread):
    progress = pyqtSignal(int, int) # current, total
    finished = pyqtSignal()
    error = pyqtSignal(str)
    log = pyqtSignal(str) # For status updates

    def __init__(self, api, paths: list[str], target_folder_id: int = None, is_public: bool = False):
        super().__init__()
        self.api = api
        self.paths = paths
        self.target_folder_id = target_folder_id
        self.is_public = is_public
        self._stop = False
        self.tag_analyzer = TagAnalyzer()

    def stop(self):
        self._stop = True

    def run(self):
        try:
            # 1. Scan files
            tasks = [] # (file_path, parent_folder_id)

            def scan_recursive(path: str, parent_id: int):
                if self._stop: return

                if os.path.isfile(path):
                    ext = os.path.splitext(path)[1].lower()
                    if ext in ['.pdf', '.dxf']:
                        tasks.append((path, parent_id))
                elif os.path.isdir(path):
                    # Create folder on server
                    folder_name = os.path.basename(path)
                    self.log.emit(f"Creating folder: {folder_name}")
                    try:
                        new_folder = self.api.create_folder(folder_name, parent_id, self.is_public)
                        new_parent_id = new_folder.id
                    except Exception as e:
                        self.error.emit(f"Failed to create folder {folder_name}: {e}")
                        return

                    for entry in os.scandir(path):
                        scan_recursive(entry.path, new_parent_id)

            self.log.emit("Scanning files...")
            for p in self.paths:
                scan_recursive(p, self.target_folder_id)

            total = len(tasks)
            self.log.emit(f"Found {total} files to upload.")

            for i, (fpath, pid) in enumerate(tasks):
                if self._stop: break

                fname = os.path.basename(fpath)
                self.log.emit(f"Uploading {i+1}/{total}: {fname}")

                try:
                    # Auto-tagging: Analyze file for tags
                    tags = []
                    try:
                        tags = self.tag_analyzer.analyze_file(fpath, locale="en")
                        if tags:
                            self.log.emit(f"Auto-tags: {', '.join(tags)}")
                    except Exception as tag_error:
                        print(f"Tag analysis failed for {fpath}: {tag_error}")
                        tags = []

                    tags_str = ",".join(tags) if tags else ""

                    # Encrypt file
                    encryption_key = secrets.token_urlsafe(16)
                    doc = fitz.open(fpath)
                    fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
                    os.close(fd)

                    doc.save(
                        tmp_path,
                        encryption=fitz.PDF_ENCRYPT_AES_256,
                        owner_pw=encryption_key,
                        user_pw=encryption_key
                    )
                    doc.close()

                    self.api.upload_file(
                        file_path=tmp_path,
                        title=os.path.splitext(fname)[0],
                        category_id=None,
                        file_type_id=None,
                        use_ocr=True, # Default to True
                        is_private=not self.is_public,
                        is_public=self.is_public,
                        folder_id=pid,
                        encryption_key=encryption_key,
                        tags=tags_str,  # Add auto-generated tags
                    )

                    os.remove(tmp_path)

                except Exception as e:
                    self.error.emit(f"Error uploading {fname}: {e}")
                    # Try uploading unencrypted if encryption fails?
                    try:
                        if os.path.exists(tmp_path): os.remove(tmp_path)
                    except: pass

                self.progress.emit(i + 1, total)

            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))

class DeleteWorker(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, api, document_id: int):
        super().__init__()
        self.api = api
        self.document_id = document_id

    def run(self):
        try:
            self.api.delete_document(self.document_id)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class MetadataWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, api, document_id: int):
        super().__init__()
        self.api = api
        self.document_id = document_id

    def run(self):
        try:
            doc = self.api.get_document(self.document_id)
            self.finished.emit(doc)
        except Exception as e:
            self.error.emit(str(e))

class DownloadWorker(QThread):
    finished = pyqtSignal(bytes)
    error = pyqtSignal(str)

    def __init__(self, api, document_id: int):
        super().__init__()
        self.api = api
        self.document_id = document_id

    def run(self):
        try:
            content = self.api.download_document(self.document_id)
            self.finished.emit(content)
        except Exception as e:
            self.error.emit(str(e))

class SearchWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api, query: str = None, view_mode: str = None, folder_id: int = None, owner_id: int = None, load_all: bool = False):
        super().__init__()
        self.api = api
        self.query = query
        self.view_mode = view_mode
        self.folder_id = folder_id
        self.owner_id = owner_id
        self.load_all = load_all  # If True, load all files with pagination

    def run(self):
        try:
            if self.query:
                docs = self.api.search_documents(query=self.query)
                self.finished.emit(docs)
            elif self.load_all:
                # Load ALL files with pagination (infinite scroll support)
                all_docs = []
                skip = 0
                limit = 100  # Load in batches of 100
                
                while True:
                    batch = self.api.list_documents(
                        view_mode=self.view_mode,
                        folder_id=self.folder_id,
                        owner_id=self.owner_id,
                        skip=skip,
                        limit=limit
                    )
                    all_docs.extend(batch)
                    
                    # If we got less than limit, we've loaded all
                    if len(batch) < limit:
                        break
                    
                    skip += limit
                    
                    # Safety limit to prevent infinite loop (10000 files max)
                    if skip >= 10000:
                        break
                
                self.finished.emit(all_docs)
            else:
                # Load only first batch (for infinite scroll)
                docs = self.api.list_documents(
                    view_mode=self.view_mode,
                    folder_id=self.folder_id,
                    owner_id=self.owner_id,
                    skip=0,
                    limit=100  # First batch only
                )
                self.finished.emit(docs)
        except Exception as e:
            self.error.emit(str(e))

class OCRWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api, file_path: str, lang: str = 'rus+eng'):
        super().__init__()
        self.api = api
        self.file_path = file_path
        self.lang = lang

    def run(self):
        try:
            text = self.api.recognize_document(self.file_path, self.lang)
            self.finished.emit(text)
        except Exception as e:
            self.error.emit(str(e))

class AvatarWorker(QThread):
    finished = pyqtSignal(QPixmap)
    error = pyqtSignal(str)

    def __init__(self, api, url: str):
        super().__init__()
        self.api = api
        self.url = url

    def run(self):
        try:
            # Use api_manager to fetch resource
            content = self.api.get_resource(self.url)
            pix = QPixmap()
            if pix.loadFromData(content):
                self.finished.emit(pix)
            else:
                error_msg = f"Failed to load image data from {self.url}"
                print(error_msg)
                self.error.emit(error_msg)
        except Exception as e:
            print(f"AvatarWorker Error: {e}")
            self.error.emit(str(e))

class IndexingWorker(QThread):
    finished = pyqtSignal()
    document_indexed = pyqtSignal(int, str)

    def __init__(self, api, search_handler, documents: list):
        super().__init__()
        self.api = api
        self.search_handler = search_handler
        self.documents = documents
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        for doc in self.documents:
            if self._stop: break
            
            # Skip if already in cache and has content
            cached = self.search_handler._cache.get(doc.id)
            if cached and cached.get("content"):
                continue

            try:
                # Download doc
                content = self.api.download_document(doc.id)
                fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
                os.close(fd)
                Path(tmp_path).write_bytes(content)

                # Index doc
                text = self.search_handler.index_document_content(doc.id, tmp_path, password=doc.encryption_key)
                self.document_indexed.emit(doc.id, text)

                # Clean up
                try: os.remove(tmp_path)
                except: pass
                
                # Be nice to the CPU/Network
                time.sleep(0.5)
            except Exception as e:
                print(f"IndexingWorker Error for doc {doc.id}: {e}")

        self.finished.emit()

class OCRSearchWorker(QThread):
    """
    Worker that performs OCR on a page image to find specific text coordinates.
    """
    results_found = pyqtSignal(list)  # list of QRectF
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, pixmap_data: bytes, query: str, page_size: tuple):
        super().__init__()
        # Initialize Tesseract path
        try:
            from .tesseract_config import setup_tesseract, get_tesseract_config
            # setup_tesseract() will set pytesseract.pytesseract.tesseract_cmd
            setup_tesseract()
            self.tesseract_config = get_tesseract_config()
        except Exception as e:
            logging.error(f"OCR Init Error (config): {e}")
            self.tesseract_config = ""
            
        self.pixmap_data = pixmap_data
        # Ensure query is clean and lowercased
        self.query = " ".join(query.lower().strip().split())
        self.page_width, self.page_height = page_size

    def run(self):
        try:
            logging.debug(f"OCR Start on page size {self.page_width}x{self.page_height} with query '{self.query}'")
            img_raw = Image.open(io.BytesIO(self.pixmap_data))
            logging.debug(f"DEBUG: Image size sent to OCR: {img_raw.width}x{img_raw.height}")
            
            img = img_raw.convert("L")
            
            # Detect orientation
            angle = 0
            try:
                osd = pytesseract.image_to_osd(img, output_type=pytesseract.Output.DICT, config=self.tesseract_config)
                angle = osd.get("rotate", 0)
                if angle != 0:
                    logging.debug(f"OCR: Auto-rotating image by {angle} degrees")
                    img = img.rotate(-angle, expand=True)
            except Exception:
                pass

            # Get verbose data including coordinates
            raw_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang='rus+eng+pol', config=self.tesseract_config)
            
            highlights = []
            img_w, img_h = img.size # Current size (after possible rotation)
            orig_w, orig_h = img_raw.size # Original pixels
            
            # Multi-word query normalization
            query_words = self.query.split()
            raw_count = len(raw_data['text'])

            for i in range(raw_count):
                text = str(raw_data['text'][i]).lower().strip()
                if not text: continue
                
                if self.query in text or (query_words and query_words[0] in text):
                    x, y, w, h = raw_data['left'][i], raw_data['top'][i], raw_data['width'][i], raw_data['height'][i]
                    
                    # Map coordinates back if we rotated the image for OCR
                    if angle == 90:
                        real_x, real_y = y, orig_h - x - w
                        real_w, real_h = h, w
                    elif angle == 180:
                        real_x, real_y = orig_w - x - w, orig_h - y - h
                        real_w, real_h = w, h
                    elif angle == 270:
                        real_x, real_y = orig_w - y - h, x
                        real_w, real_h = h, w
                    else:
                        real_x, real_y, real_w, real_h = x, y, w, h

                    # Scale to PDF coordinates using ratios
                    final_x = (real_x / orig_w) * self.page_width
                    final_y = (real_y / orig_h) * self.page_height
                    final_w = (real_w / orig_w) * self.page_width
                    final_h = (real_h / orig_h) * self.page_height
                    
                    highlights.append(QRectF(final_x, final_y, final_w, final_h))

            logging.debug(f"OCR: Found {len(highlights)} potential matches")
            self.results_found.emit(highlights)
        except Exception as e:
            logging.error(f"OCR Error: {str(e)}")
            self.error.emit(str(e))
        finally:
            self.finished.emit()
