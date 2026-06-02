from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import logging

from ..database import get_db
from ..models import User, Folder, Document, DocumentIndex
from ..schemas import FolderCreate, FolderResponse, FolderUpdate
from ..dependencies import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/folders", tags=["folders"])

@router.post("/", response_model=FolderResponse)
def create_folder(
    folder: FolderCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Check if parent exists and is accessible
    if folder.parent_id:
        parent = db.query(Folder).filter(Folder.id == folder.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent folder not found")
        if parent.owner_id != current_user.id and not parent.is_public:
             # Basic check, deeper permission logic might be needed for shared folders
             pass 

    db_folder = Folder(
        name=folder.name,
        parent_id=folder.parent_id,
        owner_id=current_user.id,
        is_public=folder.is_public
    )
    db.add(db_folder)
    db.commit()
    db.refresh(db_folder)
    return db_folder

@router.get("/", response_model=List[FolderResponse])
def read_folders(
    parent_id: Optional[int] = Query(None),
    owner_id: Optional[int] = Query(None),
    public_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Folder)
    
    if owner_id is not None:
        if public_only:
             query = query.filter(Folder.owner_id == owner_id, Folder.is_public == True)
        else:
             # If asking for private folders of someone else
             if owner_id != current_user.id and current_user.role != "admin":
                 # Fallback to public only if not allowed
                 query = query.filter(Folder.owner_id == owner_id, Folder.is_public == True)
             else:
                 query = query.filter(Folder.owner_id == owner_id)
    elif public_only:
        query = query.filter(Folder.is_public == True)
    else:
        # Default: show my folders
        query = query.filter(Folder.owner_id == current_user.id)

    if parent_id is not None:
        query = query.filter(Folder.parent_id == parent_id)
    
    return query.all()

@router.delete("/{folder_id}")
def delete_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    try:
        db_folder = db.query(Folder).filter(Folder.id == folder_id).first()
        if not db_folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        if db_folder.owner_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Not authorized")

        def recursive_delete(fid: int):
            # 1. Delete all documents in this folder
            docs = db.query(Document).filter(Document.folder_id == fid).all()
            for doc in docs:
                # Remove physical file
                if doc.file_path:
                    try:
                        if os.path.exists(doc.file_path):
                            os.remove(doc.file_path)
                            logger.info(f"Deleted file: {doc.file_path}")
                        else:
                            logger.warning(f"File not found during folder deletion: {doc.file_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete file {doc.file_path} during folder deletion: {e}")
                        # Continue with document deletion even if file deletion fails

                # Delete index and document
                try:
                    db.query(DocumentIndex).filter(DocumentIndex.document_id == doc.id).delete()
                    db.delete(doc)
                except Exception as e:
                    logger.error(f"Failed to delete document {doc.id} during folder deletion: {e}")
                    # Continue with other deletions

            # 2. Recursively delete subfolders
            subfolders = db.query(Folder).filter(Folder.parent_id == fid).all()
            for sub in subfolders:
                try:
                    recursive_delete(sub.id)
                    db.delete(sub)
                except Exception as e:
                    logger.error(f"Failed to delete subfolder {sub.id} during folder deletion: {e}")
                    # Continue with other deletions

        recursive_delete(folder_id)
        db.delete(db_folder)
        db.commit()
        logger.info(f"Folder {folder_id} and all its contents deleted successfully")
        return {"message": "Folder and all its contents deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting folder {folder_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete folder: {str(e)}")

@router.patch("/{folder_id}", response_model=FolderResponse)
def patch_folder(
    folder_id: int,
    folder_update: FolderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Обновление папки (имя, видимость, родитель)."""
    db_folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not db_folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if db_folder.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions to edit this folder")

    update_data = folder_update.model_dump(exclude_unset=True)
    
    # Check if any security settings changed
    is_pub = update_data.get("is_public")
    is_priv = update_data.get("is_private")
    is_pub_edit = update_data.get("is_public_edit")
    
    # Sync logic based on existing Folder.is_public field
    if is_pub is not None:
        def sync_security_inheritance(fid: int, pub_state: bool):
            # Calculate logic: If pub_state is False -> document is Private
            # If pub_state is True -> document is Public
            target_is_private = not pub_state
            
            # Sync Documents in this folder
            db.query(Document).filter(Document.folder_id == fid).update({
                Document.is_public: pub_state,
                Document.is_private: target_is_private,
                Document.is_public_edit: False if not pub_state else Document.is_public_edit
            }, synchronize_session=False)
            
            # Sync Subfolders recursively
            subs = db.query(Folder).filter(Folder.parent_id == fid).all()
            for sub in subs:
                sub.is_public = pub_state
                # (Folders don't have is_private field, only is_public)
                sync_security_inheritance(sub.id, pub_state)
        
        sync_security_inheritance(db_folder.id, is_pub)

    for key, value in update_data.items():
        setattr(db_folder, key, value)
    
    db.commit()
    db.refresh(db_folder)
    return db_folder
