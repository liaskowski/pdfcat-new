import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Category, FileType, FileHistory, Document
from ..schemas import (
    DocumentResponse, DocumentUpdate, FileHistoryResponse, 
    CategoryResponse, CategoryCreate, FileTypeResponse, FileTypeCreate
)
from ..dependencies import get_current_active_user, get_current_active_user_optional
from ..services.document_service import DocumentService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])

@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring server status."""
    from ..database import engine
    from sqlalchemy import text
    from ..config import settings
    
    status = {"status": "healthy", "services": {}}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status["services"]["database"] = "ok"
    except Exception as e:
        status["services"]["database"] = f"error: {str(e)}"
        status["status"] = "degraded"
    
    status["services"]["processing_queue"] = {
        "status": "ok",
        "mode": settings.TASK_MODE,
        "details": "managed_by_dramatiq" if settings.TASK_MODE == "SERVER" else "managed_by_threadpool"
    }
    return status

# --- Documents Endpoints ---

@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    category_id: Optional[int] = Form(None),
    file_type_id: Optional[int] = Form(None),
    folder_id: Optional[int] = Form(None),
    is_private: bool = Form(False),
    is_public: bool = Form(False),
    is_public_edit: bool = Form(False),
    is_read_only: bool = Form(False),
    encryption_key: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    use_ocr: bool = Form(True),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
    # Ensure filename in DB is pretty (based on title)
    db_filename = f"{title}.pdf" if not title.lower().endswith('.pdf') else title

    service = DocumentService(db)
    return service.upload_document(
        user=current_user,
        file=file,
        title=title,
        background_tasks=background_tasks,
        category_id=category_id,
        file_type_id=file_type_id,
        folder_id=folder_id,
        is_private=is_private,
        is_public=is_public,
        is_public_edit=is_public_edit,
        is_read_only=is_read_only,
        use_ocr=use_ocr,
        notes=notes or "",
        tags=tags,
        encryption_key=encryption_key,
        filename=db_filename
    )

@router.get("/documents/", response_model=List[DocumentResponse])
async def get_documents(
    skip: int = 0,
    limit: int = Query(100, le=500),
    folder_id: Optional[int] = Query(None),
    owner_id: Optional[int] = Query(None),
    view_mode: str = Query("my"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = DocumentService(db)
    return service.list_documents(
        user=current_user,
        skip=skip,
        limit=limit,
        folder_id=folder_id,
        owner_id=owner_id,
        view_mode=view_mode
    )

@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document_details(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = DocumentService(db)
    return service.get_document(document_id, current_user)

@router.put("/documents/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    doc_update: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = DocumentService(db)
    return service.update_document(document_id, current_user, doc_update)

@router.put("/documents/{document_id}/content", response_model=DocumentResponse)
async def update_document_content(
    document_id: int,
    file: UploadFile = File(...),
    use_ocr: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
    service = DocumentService(db)
    return service.update_document_content(document_id, current_user, file, use_ocr)

@router.get("/documents/{document_id}/history", response_model=List[FileHistoryResponse])
def get_document_history(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Direct DB access for read-only history (Simple enough to keep here for now)
    service = DocumentService(db)
    # Check access via service first
    service.get_document(document_id, current_user)
    
    history = db.query(FileHistory).filter(FileHistory.document_id == document_id).order_by(FileHistory.changed_at.desc()).all()
    return history

@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    token: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
):
    """
    Download document file (decrypted on-the-fly).
    Supports token via query param for iframe compatibility.
    """
    import fitz
    import io
    from urllib.parse import quote

    # Get user from token (Authorization header)
    # current_user is already validated by get_current_active_user

    service = DocumentService(db)
    doc = service.get_document(document_id, current_user)
    
    # URL Encode filename for header
    # Use only ASCII characters for standard 'filename' to avoid encoding errors
    safe_title = "".join([c for c in doc.title if (c.isalnum() and c.isascii()) or c in (" ", "-", "_")]).strip()
    if not safe_title:
         safe_title = f"document_{doc.id}"
         
    encoded_filename = quote(f"{doc.title}.pdf")
    
    # Open and decrypt PDF
    try:
        pdf_doc = fitz.open(doc.file_path)
        
        # Try multiple authentication methods
        if doc.encryption_key:
            try:
                pdf_doc.authenticate(doc.encryption_key)
            except:
                pass  # Try without key
        
        # Try to decrypt with empty password if still encrypted
        if pdf_doc.is_encrypted:
            passwords = ["", "admin", "password", "document", "file", "123456", "qwerty", "test", "pdf"]
            for pwd in passwords:
                try:
                    if pdf_doc.authenticate(pwd):
                        logger.info(f"Successfully decrypted with password: '{pwd}'")
                        break
                except:
                    continue
            else:
                # If no password works, return original file as-is
                logger.warning(f"Could not decrypt PDF {doc.file_path}, returning original file")
                pdf_doc.close()
                
                # Return original file
                with open(doc.file_path, 'rb') as f:
                    original_content = f.read()
                
                return Response(
                    content=original_content,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f"inline; filename=\"{safe_title}.pdf\"; filename*=UTF-8''{encoded_filename}",
                        "X-PDF-Status": "encrypted-raw"
                    }
                )
        
        # Save decrypted PDF to bytes buffer
        buffer = io.BytesIO()
        pdf_doc.save(buffer, garbage=4, deflate=True)
        pdf_doc.close()
        buffer.seek(0)
        
        return Response(
            content=buffer.read(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=\"{safe_title}.pdf\"; filename*=UTF-8''{encoded_filename}"
            }
        )
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

@router.get("/documents/{document_id}/preview")
async def preview_document(
    document_id: int,
    db: Session = Depends(get_db),
    token: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
):
    """
    Generate preview image for document.
    Supports token via query param for <img> tag compatibility.
    """
    # Get user from token (Authorization header)
    # current_user is already validated by get_current_active_user
    
    service = DocumentService(db)
    png_bytes = service.generate_preview(document_id, current_user)
    return Response(content=png_bytes, media_type="image/png")

@router.get("/search", response_model=List[DocumentResponse])
async def search_documents(
    q: str = Query(..., description="Search query"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = DocumentService(db)
    return service.search(current_user, q)

@router.get("/suggestions", response_model=List[str])
async def get_suggestions(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    service = DocumentService(db)
    return service.get_suggestions(current_user, q)

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = DocumentService(db)
    service.delete_document(document_id, current_user)
    return {"message": "Document deleted successfully"}

@router.post("/documents/{document_id}/duplicate", response_model=DocumentResponse)
async def duplicate_document(
    document_id: int,
    folder_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    service = DocumentService(db)
    return service.duplicate_document(document_id, current_user, folder_id)

# --- Categories & FileTypes (Kept simple in Router for now) ---

@router.post("/categories/", response_model=CategoryResponse)
def create_category(category: CategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    db_category = db.query(Category).filter(Category.name == category.name).first()
    if db_category:
        raise HTTPException(status_code=400, detail="Category already exists")
    db_category = Category(name=category.name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@router.get("/categories/", response_model=List[CategoryResponse])
def read_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Category).offset(skip).limit(limit).all()

@router.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    db_category = db.query(Category).filter(Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    if db.query(Document).filter(Document.category_id == category_id).count() > 0:
        raise HTTPException(status_code=400, detail="Category in use")
    db.delete(db_category)
    db.commit()
    return {"message": "Category deleted"}

@router.put("/categories/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, category: CategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    db_category = db.query(Category).filter(Category.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    if db.query(Category).filter(Category.name == category.name).first():
        raise HTTPException(status_code=400, detail="Category name exists")
    db_category.name = category.name
    db.commit()
    db.refresh(db_category)
    return db_category

@router.post("/file_types/", response_model=FileTypeResponse)
def create_file_type(file_type: FileTypeCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    db_ft = db.query(FileType).filter(FileType.name == file_type.name).first()
    if db_ft:
        raise HTTPException(status_code=400, detail="File type exists")
    db_ft = FileType(name=file_type.name)
    db.add(db_ft)
    db.commit()
    db.refresh(db_ft)
    return db_ft

@router.get("/file_types/", response_model=List[FileTypeResponse])
def read_file_types(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(FileType).offset(skip).limit(limit).all()

@router.delete("/file_types/{file_type_id}")
def delete_file_type(file_type_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    db_ft = db.query(FileType).filter(FileType.id == file_type_id).first()
    if not db_ft:
        raise HTTPException(status_code=404, detail="File type not found")
    if db.query(Document).filter(Document.file_type_id == file_type_id).count() > 0:
        raise HTTPException(status_code=400, detail="File type in use")
    db.delete(db_ft)
    db.commit()
    return {"message": "File type deleted"}

@router.put("/file_types/{file_type_id}", response_model=FileTypeResponse)
def update_file_type(file_type_id: int, file_type: FileTypeCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    db_ft = db.query(FileType).filter(FileType.id == file_type_id).first()
    if not db_ft:
        raise HTTPException(status_code=404, detail="File type not found")
    if db.query(FileType).filter(FileType.name == file_type.name).first():
        raise HTTPException(status_code=400, detail="File type name exists")
    db_ft.name = file_type.name
    db.commit()
    db.refresh(db_ft)
    return db_ft
