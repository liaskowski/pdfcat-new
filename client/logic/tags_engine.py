import json
import os
import re
import fitz
import pytesseract
from PIL import Image
import io
from pathlib import Path
from ..utils.tesseract_config import setup_tesseract, get_tesseract_config

class TagAnalyzer:
    def __init__(self, dictionary_path: str = None):
        setup_tesseract()
        if dictionary_path is None:
            # Try to find it relative to this file
            base_path = Path(__file__).parent.parent
            dictionary_path = os.path.join(base_path, "assets", "configs", "tag_dictionary.json")
        
        self.dictionary_path = dictionary_path
        self.tags_data = []
        self.load_dictionary()

    def load_dictionary(self):
        try:
            if os.path.exists(self.dictionary_path):
                with open(self.dictionary_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.tags_data = data.get("tags", [])
        except Exception as e:
            print(f"Error loading tag dictionary: {e}")

    def analyze_file(self, file_source: str | bytes, locale: str = "en", password: str = None) -> list[str]:
        """
        Analyzes the first 2 pages of the PDF and returns a list of localized tags.
        """
        combined_text = ""
        # Analyze first 2 pages for better accuracy
        for page_num in range(2):
            text = self._extract_text_from_page(file_source, page_num, password=password)
            
            # If text is too short, it's likely a scan or poor quality PDF layer
            if len(text.strip()) < 50:
                text = self._ocr_page(file_source, page_num, password=password)
            
            combined_text += "\n" + text
        
        found_tags = []
        for tag_info in self.tags_data:
            markers = tag_info.get("markers", [])
            for marker in markers:
                # Use word boundary \b and IGNORECASE for precision
                # Handle cases where markers might have regex special chars
                try:
                    if re.search(marker, combined_text, re.IGNORECASE | re.UNICODE):
                        tag_name = tag_info.get(locale, tag_info.get("en", tag_info.get("id")))
                        if tag_name not in found_tags:
                            found_tags.append(tag_name)
                        break
                except re.error:
                    # Fallback for simple string match if regex is invalid
                    if marker.lower() in combined_text.lower():
                        tag_name = tag_info.get(locale, tag_info.get("en", tag_info.get("id")))
                        if tag_name not in found_tags:
                            found_tags.append(tag_name)
                        break
        
        return found_tags

    def analyze_file_from_text(self, text: str, locale: str = "en") -> list[str]:
        """
        Analyze text content directly (without reading from file) and return localized tags.
        Useful for re-tagging existing documents where text is already indexed.
        """
        found_tags = []
        for tag_info in self.tags_data:
            markers = tag_info.get("markers", [])
            for marker in markers:
                # Use word boundary \b and IGNORECASE for precision
                try:
                    if re.search(marker, text, re.IGNORECASE | re.UNICODE):
                        tag_name = tag_info.get(locale, tag_info.get("en", tag_info.get("id")))
                        if tag_name not in found_tags:
                            found_tags.append(tag_name)
                        break
                except re.error:
                    # Fallback for simple string match if regex is invalid
                    if marker.lower() in text.lower():
                        tag_name = tag_info.get(locale, tag_info.get("en", tag_info.get("id")))
                        if tag_name not in found_tags:
                            found_tags.append(tag_name)
                        break

        return found_tags

    def _extract_text_from_page(self, file_source: str | bytes, page_num: int, password: str = None) -> str:
        try:
            if isinstance(file_source, bytes):
                doc = fitz.open(stream=file_source, filetype="pdf")
            else:
                doc = fitz.open(file_source)
            
            if password:
                doc.authenticate(password)
                
            text = ""
            if page_num < doc.page_count:
                page = doc.load_page(page_num)
                text = page.get_text()
            
            doc.close()
            return text
        except Exception as e:
            print(f"Error extracting text from page {page_num}: {e}")
        return ""

    def _ocr_page(self, file_source: str | bytes, page_num: int, password: str = None) -> str:
        try:
            if isinstance(file_source, bytes):
                doc = fitz.open(stream=file_source, filetype="pdf")
            else:
                doc = fitz.open(file_source)
            
            if password:
                doc.authenticate(password)
                
            if page_num >= doc.page_count:
                doc.close()
                return ""
                
            page = doc.load_page(page_num)
            # Higher DPI (300ish) for much better OCR quality
            pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5)) 
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data)).convert("L") # Grayscale improves Tesseract accuracy
            
            # Set languages
            lang = 'rus+eng+pol'
            
            # 1. Try to detect orientation and rotate if needed
            try:
                osd = pytesseract.image_to_osd(img, output_type=pytesseract.Output.DICT, config=get_tesseract_config())
                rotate = osd.get("rotate", 0)
                if rotate != 0:
                    img = img.rotate(-rotate, expand=True)
            except Exception:
                pass # OSD might fail if not enough text/features
            
            # 2. Actual OCR
            text = pytesseract.image_to_string(img, lang=lang, config=get_tesseract_config())
            doc.close()
            return text
        except Exception as e:
            print(f"Error during OCR on page {page_num}: {e}")
            if 'doc' in locals(): doc.close()
        return ""

    def suggest_tags_by_similarity(self, new_doc_title: str, existing_docs: list, threshold: float = 0.8) -> list[str]:
        """
        Simple similarity check based on title. 
        In a real app, this could be more complex (comparing content, size, etc.)
        """
        # This is a placeholder for the "80% similarity" requirement
        # We'll use a simple token-based similarity if needed, 
        # but for now we'll just check if one title contains most words of another
        
        new_words = set(re.findall(r'\w+', new_doc_title.lower()))
        if not new_words:
            return []

        for doc in existing_docs:
            if not doc.tags:
                continue
            
            existing_words = set(re.findall(r'\w+', doc.title.lower()))
            if not existing_words:
                continue
                
            intersection = new_words.intersection(existing_words)
            similarity = len(intersection) / max(len(new_words), len(existing_words))
            
            if similarity >= threshold:
                return doc.tags.split(",") if isinstance(doc.tags, str) else []
                
        return []
