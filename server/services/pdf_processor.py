import os
import logging
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
from typing import Optional, Any

from ..database import SessionLocal
from ..models import DocumentIndex, Document
from ..utils.tesseract_config import setup_tesseract, get_tesseract_config
from ..worker import task
from ..config import settings

logger = logging.getLogger(__name__)

# --- Legacy Initialization (Kept for compatibility if called elsewhere, but no-op now) ---
def init_pdf_processor(max_workers: int = 2):
    """No-op: Worker management is handled by server/worker.py"""
    pass

@task(queue_name="pdf_processing")
def process_pdf(file_path: str, document_id: int, use_ocr: bool = True):
    """
    Background Task: Process PDF file (Extract text + OCR).
    Decorated with @task to support both ThreadPool (Local) and Redis/Dramatiq (Server).
    """
    logger.info(f"Starting PDF processing for doc_id={document_id}")
    db = SessionLocal()
    try:
        # Get document for encryption key
        db_doc = db.query(Document).filter(Document.id == document_id).first()
        if not db_doc:
            logger.warning(f"Document {document_id} not found in DB")
            return

        encryption_key = db_doc.encryption_key

        # Open PDF via PyMuPDF
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            logger.error(f"Failed to open PDF file {file_path}: {e}")
            return

        if encryption_key:
            doc.authenticate(encryption_key)

        all_text = []
        lang = 'rus+eng+pol'
        tess_config = get_tesseract_config()

        # Process each page
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = ""
            ocr_text = ""

            # Step 1: Extract embedded text
            embedded_text = page.get_text().strip()
            if embedded_text:
                page_text = embedded_text
                logger.debug(f"Page {page_num + 1}: Extracted {len(embedded_text)} chars of embedded text")

            # Step 2: Run OCR to capture additional text (from images, scans, etc.)
            if use_ocr:
                try:
                    # Convert page to high-resolution image
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x resolution
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data)).convert("L")  # Grayscale
                    
                    # Try to detect orientation
                    rotations = [0]
                    try:
                        osd = pytesseract.image_to_osd(img, output_type=pytesseract.Output.DICT, config=tess_config)
                        rotate_hint = int(osd.get("rotate", 0))
                        if rotate_hint in [90, 180, 270]:
                            rotations = [rotate_hint]
                            img = img.rotate(-rotate_hint, expand=True)
                    except Exception:
                        pass

                    # Run OCR
                    ocr_text = pytesseract.image_to_string(img, lang=lang, config=tess_config).strip()
                    logger.debug(f"Page {page_num + 1}: OCR extracted {len(ocr_text)} chars")
                    
                except Exception as ocr_error:
                    logger.warning(f"OCR failed for page {page_num + 1}: {str(ocr_error)}")

            # Step 3: Combine embedded text and OCR text
            if page_text and ocr_text:
                combined = _combine_texts(page_text, ocr_text)
                all_text.append(combined)
            elif page_text:
                all_text.append(page_text)
            elif ocr_text:
                all_text.append(ocr_text)
            else:
                all_text.append("")

        doc.close()

        # Combine all text
        full_text = "\n\n".join(all_text)

        # Update DocumentIndex in DB
        db_index = db.query(DocumentIndex).filter(DocumentIndex.document_id == document_id).first()
        if db_index:
            db_index.content_text = full_text
            db.commit()
            logger.info(f"Updated DocumentIndex for document_id={document_id} with {len(full_text)} characters")
        else:
            # Create if missing (sanity check)
            db_index = DocumentIndex(document_id=document_id, content_text=full_text)
            db.add(db_index)
            db.commit()

        # Notify Go Search Service
        if settings.SEARCH_GO_URL:
            import requests
            try:
                resp = requests.post(
                    f"{settings.SEARCH_GO_URL}/index",
                    json={"id": document_id, "content": full_text},
                    timeout=5
                )
                if resp.status_code == 200:
                    logger.info(f"Successfully notified Go Search Service for doc_id={document_id}")
                else:
                    logger.error(f"Go Search Service index failed: {resp.text}")
            except Exception as e:
                logger.error(f"Failed to connect to Go Search Service: {e}")

    except Exception as e:
        logger.error(f"Error processing PDF {file_path}: {str(e)}", exc_info=True)
    finally:
        db.close()


def process_pdf_async(file_path: str, document_id: int, use_ocr: bool = True) -> bool:
    """
    Wrapper for sending the task.
    This replaces the old custom queue logic with our hybrid task dispatcher.
    """
    try:
        process_pdf.send(file_path, document_id, use_ocr)
        return True
    except Exception as e:
        logger.error(f"Failed to dispatch PDF task: {e}")
        return False

def _combine_texts(embedded: str, ocr: str) -> str:
    """
    Combine embedded text and OCR text, avoiding duplicates.
    """
    if not embedded:
        return ocr
    if not ocr:
        return embedded
    
    embedded_words = set(embedded.lower().split())
    ocr_words = set(ocr.lower().split())
    
    if len(embedded_words) == 0:
        return ocr
        
    overlap = len(embedded_words & ocr_words) / max(len(embedded_words), len(ocr_words))
    
    if overlap > 0.8:
        return ocr if len(ocr) > len(embedded) else embedded
    else:
        return f"{embedded}\n{ocr}"

# ... extract_keywords (unchanged) ...
def extract_keywords(text: str, max_keywords: int = 10) -> list:
    """
    Extract keywords from text for automatic tagging.
    """
    import re
    from collections import Counter
    
    STOP_WORDS = {
        'ru': {'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'вдруг', 'ли', 'если', 'уже', 'или', 'ни', 'быть', 'был', 'него', 'до', 'вас', 'нибудь', 'опять', 'уж', 'вам', 'ведь', 'там', 'потом', 'себя', 'ничего', 'ей', 'может', 'они', 'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'им', 'более', 'всегда', 'конечно', 'всю', 'между', 'собой', 'какой', 'этот', 'этого', 'этому', 'этим', 'этом', 'этой', 'эту', 'этою', 'эти', 'этих', 'этими', 'какие', 'какого', 'какойто', 'каких', 'какими', 'сам', 'сама', 'само', 'сами', 'себе', 'свое', 'свои', 'свой', 'своей', 'своего', 'своих', 'своему', 'своим', 'своими', 'своем', 'своём', 'себой', 'собою', 'зачем', 'почему', 'потому', 'того', 'той', 'тех', 'тем', 'теми', 'тот'},
        'en': {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought', 'used', 'right', 'just', 'also', 'into', 'that', 'this', 'these', 'those', 'such', 'who', 'whom', 'whose', 'which', 'what', 'where', 'when', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'any', 'no', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very'},
        'pl': {'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x', 'a', 'aby', 'ach', 'acz', 'aczkolwiek', 'aj', 'albo', 'ale', 'ani', 'aż', 'bardziej', 'bardzo', 'bo', 'bowiem', 'by', 'byli', 'bynajmniej', 'być', 'był', 'była', 'było', 'były', 'będzie', 'będą', 'cali', 'cała', 'cały', 'ci', 'cię', 'ciebie', 'co', 'cokolwiek', 'coś', 'czasami', 'czemu', 'czy', 'czyli'}
    }
    
    words = re.findall(r'\b[a-zA-Zа-яА-ЯęĘąĄśŚłŁóÓńŃźŹżŹčČďĎěĚňŇřŘšťŤůÚžŽ]{3,}\b', text.lower())
    
    filtered_words = [
        word for word in words
        if word not in STOP_WORDS['ru']
        and word not in STOP_WORDS['en']
        and word not in STOP_WORDS['pl']
        and not word.isdigit()
    ]
    
    word_counts = Counter(filtered_words)
    top_keywords = [word for word, count in word_counts.most_common(max_keywords * 2)]
    
    final_keywords = []
    for word in top_keywords:
        if len(final_keywords) >= max_keywords:
            break
        if len(word) > 3:
            final_keywords.append(word)
    
    return final_keywords
