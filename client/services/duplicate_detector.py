"""
Duplicate detection service for file uploads.
Compares new files with existing documents by name and content.
"""

import re
from typing import List, Tuple, Optional
from pathlib import Path

from ..api_manager import APIDocument, APIManager


class DuplicateDetector:
    """
    Detects potential duplicate files by comparing:
    1. Filename similarity (fuzzy matching)
    2. Content similarity (text comparison)
    """
    
    # Thresholds
    NAME_SIMILARITY_THRESHOLD = 0.7  # 70% similar names
    CONTENT_SIMILARITY_THRESHOLD = 0.8  # 80% similar content
    
    def __init__(self, api: APIManager):
        self.api = api
    
    def check_duplicates(self, file_path: str, 
                         existing_docs: List[APIDocument]) -> List[Tuple[APIDocument, float]]:
        """
        Check for potential duplicates.
        Returns list of (document, combined_similarity_score) tuples.
        """
        new_filename = Path(file_path).stem.lower()
        similar_files = []
        
        for doc in existing_docs:
            # Check name similarity
            name_score = self._compare_filenames(new_filename, doc.title.lower())
            
            # Check content similarity (if we can extract text)
            content_score = 0.0
            try:
                content_score = self._compare_content(file_path, doc)
            except Exception:
                pass  # Content comparison failed, use name score only
            
            # Combined score (weighted average)
            combined_score = (name_score * 0.4) + (content_score * 0.6)
            
            # Include if either score exceeds threshold
            if name_score >= self.NAME_SIMILARITY_THRESHOLD or \
               content_score >= self.CONTENT_SIMILARITY_THRESHOLD:
                similar_files.append((doc, combined_score))
        
        # Sort by similarity score (highest first)
        similar_files.sort(key=lambda x: x[1], reverse=True)
        
        return similar_files
    
    def _compare_filenames(self, name1: str, name2: str) -> float:
        """
        Compare two filenames using multiple strategies.
        Returns similarity score 0.0 - 1.0.
        """
        # Strategy 1: Exact match
        if name1 == name2:
            return 1.0
        
        # Strategy 2: Contains check
        if name1 in name2 or name2 in name1:
            return 0.8
        
        # Strategy 3: Token-based similarity
        tokens1 = self._tokenize(name1)
        tokens2 = self._tokenize(name2)
        
        if not tokens1 or not tokens2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        jaccard = intersection / union if union > 0 else 0.0
        
        # Strategy 4: Levenshtein-like ratio (simplified)
        len_diff = abs(len(name1) - len(name2))
        max_len = max(len(name1), len(name2))
        length_ratio = 1.0 - (len_diff / max_len) if max_len > 0 else 0.0
        
        # Combine strategies
        return max(jaccard, length_ratio * 0.8)
    
    def _tokenize(self, text: str) -> set:
        """Extract meaningful tokens from text."""
        # Remove common words and special characters
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'of', 'in', 'on', 'for',
            'the', 'le', 'la', 'les', 'un', 'une', 'des', 'et', 'ou', 'de', 'dans', 'pour',  # French
            'der', 'die', 'das', 'und', 'oder', 'von', 'in', 'auf', 'für',  # German
            'the', 'a', 'an', 'and', 'or', 'of', 'in', 'on', 'for',  # English
            'the', 'a', 'an', 'and', 'or', 'of', 'in', 'on', 'for',  # Repeat for emphasis
        }
        
        # Extract words (alphanumeric, min 3 chars)
        words = re.findall(r'\b[a-zA-Zа-яА-ЯęĘąĄśŚłŁóÓńŃźŹżŹčČďĎěĚňŇřŘšťŤůÚžŽ0-9]{3,}\b', text.lower())
        
        # Filter stop words
        return set(w for w in words if w not in stop_words)
    
    def _compare_content(self, file_path: str, existing_doc: APIDocument) -> float:
        """
        Compare file content with existing document.
        Returns similarity score 0.0 - 1.0.
        """
        try:
            # Extract text from new file
            new_text = self._extract_text_from_file(file_path)
            if not new_text:
                return 0.0
            
            # Get existing document text (from index)
            existing_text = getattr(existing_doc, 'content_text', '')
            if not existing_text:
                return 0.0
            
            # Compare using token overlap
            tokens1 = self._tokenize(new_text[:5000])  # Limit to first 5000 chars
            tokens2 = self._tokenize(existing_text[:5000])
            
            if not tokens1 or not tokens2:
                return 0.0
            
            intersection = len(tokens1 & tokens2)
            union = len(tokens1 | tokens2)
            
            return intersection / union if union > 0 else 0.0
            
        except Exception:
            return 0.0
    
    def _extract_text_from_file(self, file_path: str) -> str:
        """Extract text from PDF file."""
        import fitz  # PyMuPDF
        
        doc = fitz.open(file_path)
        text = ""
        
        # Extract text from first 3 pages
        for page_num in range(min(3, len(doc))):
            page = doc[page_num]
            text += page.get_text()
        
        doc.close()
        return text
    
    def should_show_dialog(self, similar_files: List[Tuple[APIDocument, float]]) -> bool:
        """Check if we should show duplicate dialog."""
        if not similar_files:
            return False
        
        # Show dialog if any file has high similarity
        for doc, score in similar_files:
            if score >= self.NAME_SIMILARITY_THRESHOLD:
                return True
        
        return False
