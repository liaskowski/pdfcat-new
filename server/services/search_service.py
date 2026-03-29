from typing import List, Optional
import re
import logging
import requests
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from fastapi import Depends

from ..models import Document, DocumentIndex, Category, FileType, User
from ..config import settings

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self, db: Session):
        self.db = db

    def search_documents(self, user: User, query_str: str, limit: int = 100) -> List[Document]:
        """
        Поиск документов. Если доступен Go-сервис, используем его для полнотекстового поиска.
        В противном случае используем медленный SQL LIKE.
        """
        if settings.SEARCH_GO_URL:
            try:
                resp = requests.get(f"{settings.SEARCH_GO_URL}/search", params={"q": query_str}, timeout=5)
                if resp.status_code == 200:
                    results = resp.json()
                    ids = [r["id"] for r in results]
                    if not ids:
                        return []
                    
                    # Fetch documents with metadata from DB for the IDs returned by Go
                    # and ensure user has access.
                    if user.role == "admin":
                        return self.db.query(Document).filter(Document.id.in_(ids)).all()
                    else:
                        return self.db.query(Document).filter(
                            and_(
                                Document.id.in_(ids),
                                or_(
                                    Document.owner_id == user.id,
                                    and_(Document.is_public == True, Document.is_private == False)
                                )
                            )
                        ).all()
                else:
                    logger.error(f"Go Search Error: {resp.text}")
            except Exception as e:
                logger.error(f"Failed to connect to Go Search: {e}")

        # --- Fallback to SQL Search ---
        if user.role == "admin":
            base_query = self.db.query(Document)
        else:
            base_query = self.db.query(Document).filter(
                or_(
                    Document.owner_id == user.id,
                    and_(Document.is_public == True, Document.is_private == False)
                )
            )
        
        words = query_str.strip().split()
        if not words:
            return []

        # Сначала получаем кандидатов через простой LIKE (быстро)
        query = (
            base_query
            .outerjoin(DocumentIndex)
            .outerjoin(Category)
            .outerjoin(FileType)
            .outerjoin(User, Document.owner_id == User.id)
        )

        # Простой поиск для получения кандидатов
        for word in words:
            if word.startswith("#") and len(word) > 1:
                tag_pattern = f"%{word[1:]}%"
                query = query.filter(Document.tags.ilike(tag_pattern))
                continue

            word_lower = word.lower()
            # Ищем везде где слово МОЖЕТ быть (получаем кандидатов)
            query = query.filter(
                or_(
                    DocumentIndex.content_text.ilike(f'%{word_lower}%'),
                    Document.title.ilike(f'%{word}%'),
                    Document.filename.ilike(f'%{word}%'),
                    Document.notes.ilike(f'%{word}%'),
                    Document.tags.ilike(f'%{word}%'),
                    Category.name.ilike(f'%{word}%'),
                    FileType.name.ilike(f'%{word}%'),
                    User.username.ilike(f'%{word}%'),
                )
            )

        # Получаем результаты
        results = query.limit(limit).all()
        
        # Теперь ФИЛЬТРУЕМ на Python - оставляем только где слово начинается с границы
        filtered_results = []
        for doc in results:
            match_found = False
            
            for word in words:
                if word.startswith("#"):
                    # Tag search
                    if doc.tags and word[1:].lower() in doc.tags.lower():
                        match_found = True
                        continue
                
                word_lower = word.lower()
                
                # Проверяем title
                if doc.title and self._has_word_boundary(doc.title.lower(), word_lower):
                    match_found = True
                    continue
                
                # Проверяем filename
                if doc.filename and self._has_word_boundary(doc.filename.lower(), word_lower):
                    match_found = True
                    continue
                
                # Проверяем notes
                if doc.notes and self._has_word_boundary(doc.notes.lower(), word_lower):
                    match_found = True
                    continue
                
                # Проверяем tags
                if doc.tags and self._has_word_boundary(doc.tags.lower(), word_lower):
                    match_found = True
                    continue
                
                # Проверяем content (OCR) - самое важное!
                if doc.index and doc.index.content_text:
                    if self._has_word_boundary(doc.index.content_text.lower(), word_lower):
                        match_found = True
                        continue
                
                # Если ни одно поле не совпало с этим словом - документ не подходит
                if not match_found:
                    break
            
            if match_found:
                filtered_results.append(doc)

        return filtered_results

    def get_suggestions(self, user: User, query_str: str) -> List[str]:
        """Get search suggestions based on document content and titles."""
        if not query_str:
            return []

        search_pattern = f"%{query_str}%"
        
        # Search in content_text (OCR/indexed content)
        content_results = (
            self.db.query(DocumentIndex.content_text)
            .join(Document, DocumentIndex.document_id == Document.id)
            .filter(
                or_(
                    Document.owner_id == user.id,
                    and_(Document.is_public == True, Document.is_private == False)
                )
            )
            .filter(DocumentIndex.content_text.ilike(search_pattern))
            .limit(15)
        ).all()
        
        # Also search in titles
        title_results = (
            self.db.query(Document.title)
            .filter(
                or_(
                    Document.owner_id == user.id,
                    and_(Document.is_public == True, Document.is_private == False)
                )
            )
            .filter(Document.title.ilike(search_pattern))
            .limit(15)
        ).all()

        suggestions = set()
        query_lower = query_str.lower()
        pattern = re.compile(r'\b(' + re.escape(query_lower) + r'\w*((?:\s+\S+){0,2}))', re.IGNORECASE)

        # Process content results
        for row in content_results:
            if not row or not row[0]:
                continue
            text = row[0]
            matches = pattern.findall(text)
            for match in matches:
                full_phrase = match[0]
                clean_phrase = " ".join(full_phrase.split())
                if clean_phrase and len(clean_phrase) > len(query_str):
                    suggestions.add(clean_phrase)
                if len(suggestions) >= 15:
                    break
            if len(suggestions) >= 15:
                break
        
        # Process title results
        for row in title_results:
            if row and row[0]:
                title = row[0]
                if len(title) > len(query_str) and query_str.lower() in title.lower():
                    suggestions.add(title)
            if len(suggestions) >= 15:
                break

        return sorted(list(suggestions), key=lambda x: (len(x), x))[:10]

    def _has_word_boundary(self, text: str, word: str) -> bool:
        """
        Проверяет есть ли слово в тексте с СТРОГОЙ границей.
        """
        if not text or not word:
            return False
        
        idx = 0
        while True:
            pos = text.find(word, idx)
            if pos == -1:
                return False
            
            if pos == 0:
                return True
            
            char_before = text[pos - 1]
            if not char_before.isalpha():
                return True
            
            idx = pos + 1
        
        return False
