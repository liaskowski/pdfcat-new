import pytesseract
from PyQt6.QtCore import QThread, pyqtSignal, QRectF, Qt
from PIL import Image
import io
import logging

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
            from server.utils.tesseract_config import setup_tesseract, get_tesseract_config
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
            if logging.getLogger().getEffectiveLevel() <= logging.DEBUG:
                print(f"DEBUG: OCR Full Output: {raw_data}")
            
            highlights = []
            img_w, img_h = img.size # Current size (after possible rotation)
            orig_w, orig_h = img_raw.size # Original pixels
            
            # K factors: PDF points / OCR image pixels
            # We use img_w/img_h because Tesseract data refers to the possibly rotated 'img'
            kx = self.page_width / img_w
            ky = self.page_height / img_h
            
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
                        # Recalculate K for rotated state if needed, 
                        # but simple ratio relative to current img size is safer
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
