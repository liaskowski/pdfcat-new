from typing import List, Optional, Tuple, BinaryIO
import logging
import fitz
from datetime import datetime
from fastapi import HTTPException, UploadFile, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from ..models import Document, User, Folder, FileHistory, DocumentIndex
from ..schemas import DocumentCreate, DocumentUpdate
from ..config import settings
from ..services.pdf_processor import process_pdf
from ..services.storage import storage
from ..services.search_service import SearchService

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.search_service = SearchService(db)

    def get_document(self, document_id: int, user: User) -> Document:
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Access Check
        if doc.owner_id != user.id and not user.role == "admin":
            if not (doc.is_public or doc.is_public_edit):
                if doc.is_private:
                     raise HTTPException(status_code=403, detail="Access denied")
        
        return doc

    def list_documents(
        self, 
        user: User, 
        skip: int = 0, 
        limit: int = 100, 
        folder_id: Optional[int] = None, 
        owner_id: Optional[int] = None,
        view_mode: str = "my"
    ) -> List[Document]:
        query = self.db.query(Document)

        if view_mode == "my":
            query = query.filter(Document.owner_id == user.id)
            if folder_id is not None:
                query = query.filter(Document.folder_id == folder_id)

        elif view_mode == "community":
             query = query.filter(or_(Document.is_public == True, Document.is_public_edit == True))

        if owner_id:
             query = query.filter(Document.owner_id == owner_id)
             
        if folder_id is not None and view_mode != "my":
             query = query.filter(Document.folder_id == folder_id)

        return query.offset(skip).limit(limit).all()

    def search(self, user: User, query_str: str, limit: int = 100) -> List[Document]:
        return self.search_service.search_documents(user, query_str, limit)

    def get_suggestions(self, user: User, query_str: str) -> List[str]:
        return self.search_service.get_suggestions(user, query_str)

    def generate_preview(self, document_id: int, user: User) -> bytes:
        doc_db = self.get_document(document_id, user)
        
        if not doc_db.file_path or not storage.exists(doc_db.file_path):
             raise HTTPException(status_code=404, detail="File not found on storage")

        try:
            # We can't easily stream to fitz.open from storage abstraction without a file path
            # fitz.open(stream=...) works but requires reading the whole file into memory
            # For local storage, we can use the path.
            # Ideally, StorageService should expose a way to get a readable path or stream.
            # LocalStorageProvider returns a path from save(), so doc_db.file_path is a path.
            
            doc = fitz.open(doc_db.file_path)
            if doc_db.encryption_key:
                doc.authenticate(doc_db.encryption_key)

            if doc.page_count < 1:
                doc.close()
                raise HTTPException(status_code=400, detail="Document has no pages")

            page = doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
            doc.close()
            return pix.tobytes("png")
        except Exception as e:
            logger.error(f"Preview generation error: {e}")
            raise HTTPException(status_code=500, detail="Preview generation failed")

    def upload_document(
        self,
        user: User,
        file: UploadFile,
        title: str,
        background_tasks: BackgroundTasks,
        category_id: Optional[int] = None,
        file_type_id: Optional[int] = None,
        folder_id: Optional[int] = None,
        is_private: bool = False,
        is_public: bool = False,
        is_public_edit: bool = False,
        is_read_only: bool = False,
        use_ocr: bool = False,
        notes: str = "",
        tags: Optional[str] = None,
        encryption_key: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Document:

        if folder_id:
            folder = self.db.query(Folder).filter(Folder.id == folder_id).first()
            if not folder:
                raise HTTPException(status_code=404, detail="Folder not found")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        
        try:
            stored_path = storage.save(file.file, safe_filename)
        except Exception as e:
            logger.error(f"Storage save error: {e}")
            raise HTTPException(status_code=500, detail="Could not save file to storage")

        db_doc = Document(
            title=title,
            filename=filename or file.filename,
            file_path=stored_path,
            owner_id=user.id,
            folder_id=folder_id,
            category_id=category_id,
            file_type_id=file_type_id,
            is_private=is_private,
            is_public=is_public,
            is_public_edit=is_public_edit,
            is_read_only=is_read_only,
            encryption_key=encryption_key,
            notes=notes,
            tags=tags
        )
        self.db.add(db_doc)
        self.db.commit()
        self.db.refresh(db_doc)

        db_index = DocumentIndex(
            document_id=db_doc.id,
            content_text=""
        )
        self.db.add(db_index)

        self.save_history(
            doc=db_doc,
            user_id=user.id,
            change_type="create",
            new_value=f"File uploaded: {file.filename}"
        )

        process_pdf(stored_path, db_doc.id, use_ocr)

        return db_doc

    def update_document(
        self,
        document_id: int,
        user: User,
        update_data: DocumentUpdate
    ) -> Document:
        doc = self.get_document(document_id, user)
        
        if doc.owner_id != user.id and not user.role == "admin":
             if not doc.is_public_edit:
                  raise HTTPException(status_code=403, detail="Write access denied")

        # Track history
        for key, value in update_data.model_dump(exclude_unset=True).items():
            # Skip if value is None for required fields (title and booleans)
            if value is None and key in ["title", "is_private", "is_public", "is_public_edit", "is_read_only"]:
                 continue

            old_val = getattr(doc, key)
            if old_val != value:
                 self.save_history(doc, user.id, "update", str(value), str(old_val), key)
            setattr(doc, key, value)
            
            # If title is updated, also update filename to keep it pretty
            if key == "title" and value:
                 doc.filename = f"{value}.pdf" if not value.lower().endswith('.pdf') else value
        
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def update_document_content(
        self,
        document_id: int,
        user: User,
        file: UploadFile,
        use_ocr: bool
    ) -> Document:
        doc = self.get_document(document_id, user)
        
        if doc.owner_id != user.id and not user.role == "admin":
             if not doc.is_public_edit:
                  raise HTTPException(status_code=403, detail="Write access denied")
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        
        old_path = doc.file_path
        old_filename = doc.filename
        
        try:
             new_path = storage.save(file.file, safe_filename)
        except Exception as e:
             raise HTTPException(status_code=500, detail="Failed to save new file")
             
        doc.filename = file.filename
        doc.file_path = new_path
        
        self.save_history(doc, user.id, "content_update", file.filename, old_filename, "file_content")
        self.db.commit()
        
        if old_path:
             storage.delete(old_path)
             
        process_pdf(new_path, doc.id, use_ocr)
        self.db.refresh(doc)
        return doc

    def duplicate_document(self, document_id: int, user: User, folder_id: Optional[int] = None) -> Document:
        source_doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not source_doc:
            raise HTTPException(status_code=404, detail="Source document not found")
            
        if source_doc.is_private and source_doc.owner_id != user.id and user.role != "admin":
             raise HTTPException(status_code=403, detail="No access to source document")
             
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        new_filename = f"copy_{timestamp}_{source_doc.filename}"
        
        try:
             new_path = storage.copy(source_doc.file_path, new_filename)
        except Exception as e:
             logger.error(f"Copy failed: {e}")
             raise HTTPException(status_code=500, detail="File copy failed")
             
        new_doc = Document(
            title=f"Copy of {source_doc.title}",
            filename=source_doc.filename,
            owner_id=user.id,
            is_private=source_doc.is_private,
            is_public=source_doc.is_public,
            is_public_edit=False,
            notes=source_doc.notes,
            tags=source_doc.tags,
            file_path=new_path,
            category_id=source_doc.category_id,
            file_type_id=source_doc.file_type_id,
            folder_id=folder_id
        )
        self.db.add(new_doc)
        self.db.commit()
        self.db.refresh(new_doc)
        
        # Copy index
        source_index = self.db.query(DocumentIndex).filter(DocumentIndex.document_id == document_id).first()
        if source_index:
             new_index = DocumentIndex(
                 document_id=new_doc.id,
                 content_text=source_index.content_text
             )
             self.db.add(new_index)
             self.db.commit()
             
        return new_doc

    def delete_document(self, document_id: int, user: User):
        doc = self.get_document(document_id, user)
        
        if doc.owner_id != user.id and not user.role == "admin":
             raise HTTPException(status_code=403, detail="Only owner can delete document")

        # Use Storage Service for deletion
        if doc.file_path:
            storage.delete(doc.file_path)
            
        # Delete index
        self.db.query(DocumentIndex).filter(DocumentIndex.document_id == document_id).delete()

        self.db.delete(doc)
        self.db.commit()

    def save_history(self, doc: Document, user_id: int, change_type: str, new_value: str = "", old_value: str = "", field_changed: str = None):
        history = FileHistory(
            document_id=doc.id,
            changed_by_id=user_id,
            change_type=change_type,
            new_value=new_value,
            old_value=old_value,
            field_changed=field_changed
        )
        self.db.add(history)
        self.db.commit()