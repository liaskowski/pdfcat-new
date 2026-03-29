import os
import shutil
import zipfile
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Response, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import User, Document, DocumentIndex, FileHistory, Category, FileType, Folder
from ..schemas import FileHistoryResponse
from ..dependencies import get_current_admin
from ..security import get_password_hash

# ... (rest of imports)
from ..config import settings
from ..services.pdf_processor import process_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# --- System Stats ---

@router.get("/stats")
async def get_system_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get system statistics: CPU/RAM (basic), Storage, Document counts.
    """
    # Database Stats
    total_users = db.query(func.count(User.id)).scalar()
    total_docs = db.query(func.count(Document.id)).scalar()
    
    # Calculate storage usage directory
    upload_dir_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(settings.UPLOAD_DIR):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    upload_dir_size += os.path.getsize(fp)
    except Exception as e:
        logger.error(f"Error calculating storage size: {e}")

    # System Resources (Using standard library where possible)
    # Note: psutil would be better but trying to avoid extra deps if possible.
    # If psutil is allowed/available, I'd import it. For now, returning placeholders or basic os info.
    import platform
    
    stats = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "database": {
            "users": total_users,
            "documents": total_docs
        },
        "storage": {
            "upload_dir_bytes": upload_dir_size,
            "upload_dir_path": settings.UPLOAD_DIR
        },
        "timestamp": datetime.utcnow()
    }
    
    # Try adding PSUTIL if available
    try:
        import psutil
        stats["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "ram_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage(settings.UPLOAD_DIR).percent
        }
    except ImportError:
        stats["system"] = {"error": "psutil not installed"}

    return stats

# --- Backup ---

@router.post("/backup")
async def create_backup(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin)
):
    """
    Export Database (SQLite) and Uploads folder into a ZIP archive.
    """
    import secrets
    import gc
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_token = secrets.token_hex(4)
    backup_filename = f"backup_{timestamp}_{random_token}.zip"
    backup_path = os.path.join(os.path.dirname(settings.UPLOAD_DIR), "backups", backup_filename)
    
    # Ensure backup dir exists
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    
    try:
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 1. Backup DB
            db_path = "app.db" 
            if os.path.exists(db_path):
                zipf.write(db_path, arcname="app.db")
            
            # 2. Backup Uploads
            for root, dirs, files in os.walk(settings.UPLOAD_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(settings.UPLOAD_DIR))
                    zipf.write(file_path, arcname=arcname)
        
        # Explicitly trigger GC after heavy operation
        gc.collect()
                    
        return FileResponse(path=backup_path, filename=backup_filename, media_type='application/zip')
        
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Reindexing ---

@router.post("/reindex")
async def reindex_documents(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Trigger background re-indexing (OCR/Text Extraction) for ALL documents.
    """
    documents = db.query(Document).all()
    count = 0
    for doc in documents:
        if doc.file_path and os.path.exists(doc.file_path):
            # We call the existing process_pdf function
            # Note: This might be heavy!
            background_tasks.add_task(process_pdf, doc.file_path, doc.id, use_ocr=True)
            count += 1
            
    return {"message": f"Reindexing started for {count} documents."}

# --- Tag Management ---

@router.post("/merge-tags")
async def merge_tags(
    old_tag: str,
    new_tag: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Merge 'old_tag' into 'new_tag' across all documents.
    """
    # Simple text replacement logic for CSV tags
    # In a real relation table, this would be different.
    # Current model: tags = Column(Text) # Comma-separated
    
    docs = db.query(Document).filter(Document.tags.contains(old_tag)).all()
    updated_count = 0
    
    for doc in docs:
        if not doc.tags:
            continue
            
        tag_list = [t.strip() for t in doc.tags.split(',')]
        if old_tag in tag_list:
            # Remove old
            tag_list = [t for t in tag_list if t != old_tag]
            # Add new if not exists
            if new_tag not in tag_list:
                tag_list.append(new_tag)
            
            doc.tags = ",".join(tag_list)
            updated_count += 1
            
    db.commit()
    return {"message": f"Merged tag '{old_tag}' into '{new_tag}' in {updated_count} documents."}


@router.post("/auto-tag")
async def auto_tag_documents(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Automatically generate tags for all existing documents based on their content.
    Uses the same TagAnalyzer engine as the client (tag_dictionary.json).
    """
    import sys
    import os
    from pathlib import Path
    
    # Import TagAnalyzer from client
    base_dir = Path(__file__).parent.parent.parent
    client_dir = base_dir / "client"
    sys.path.insert(0, str(client_dir))
    
    from logic.tags_engine import TagAnalyzer
    
    tag_analyzer = TagAnalyzer()
    docs = db.query(Document).all()
    count = len(docs)

    # Process in background to avoid timeout
    async def process_auto_tag():
        for doc in docs:
            try:
                # Extract text from document index
                index = db.query(DocumentIndex).filter(
                    DocumentIndex.document_id == doc.id
                ).first()

                if not index or not index.content_text:
                    logger.warning(f"No content for document {doc.id}")
                    continue

                # Use TagAnalyzer to analyze existing content
                tags = tag_analyzer.analyze_file_from_text(index.content_text, locale="en")

                # Get existing tags
                existing_tags = set()
                if doc.tags:
                    existing_tags = set(t.strip().lower() for t in doc.tags.split(',') if t.strip())

                # Add new tags (merge with existing)
                for tag in tags:
                    if tag.lower() not in existing_tags:
                        if doc.tags:
                            doc.tags += f",{tag}"
                        else:
                            doc.tags = tag
                        existing_tags.add(tag.lower())

                logger.info(f"Auto-tagged document {doc.id}: {tags}")

            except Exception as e:
                logger.error(f"Auto-tag error for document {doc.id}: {e}")
                continue

        db.commit()
        logger.info(f"Auto-tagging completed for {count} documents")

    # Start background task
    background_tasks.add_task(process_auto_tag)

    return {"message": f"Auto-tagging started for {count} documents using tag dictionary."}


# --- Password Management ---

@router.post("/users/{user_id}/password")
def admin_change_password(
    user_id: int,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Force change user password by administrator.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    return {"message": f"Password changed for user {user.username}"}

# --- History Log ---

@router.get("/history", response_model=List[FileHistoryResponse])
def get_global_history(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Get global activity logs.
    """
    return db.query(FileHistory).order_by(FileHistory.changed_at.desc()).limit(limit).all()

# --- User Management (Legacy Wrapper) ---

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Delete a user and all their data.
    """
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete self")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Cleanup docs
    user_docs = db.query(Document).filter(Document.owner_id == user_id).all()
    for doc in user_docs:
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except:
                pass
        db.delete(doc) # Cascade should handle history/index but explicit delete is safer
        
    db.delete(user)
    db.commit()
    return None