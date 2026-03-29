import os
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
from ..utils.tesseract_config import get_tesseract_config

def extract_text(file_path: str, lang: str = 'rus+eng') -> str:
    """
    Extracts text from an image or PDF file using Tesseract OCR.
    """
    config = get_tesseract_config()
    text = ""
    
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == '.pdf':
            # Open PDF
            doc = fitz.open(file_path)
            for page in doc:
                # Render page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Zoom for better OCR
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Perform OCR on the page image
                page_text = pytesseract.image_to_string(img, lang=lang, config=config)
                text += page_text + "\n"
            doc.close()
        else:
            # Assume it's an image
            text = pytesseract.image_to_string(Image.open(file_path), lang=lang, config=config)
            
    except Exception as e:
        raise RuntimeError(f"OCR failed: {str(e)}")
        
    return text
