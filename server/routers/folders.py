from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models import User, Folder, Document, DocumentIndex
from ..schemas import FolderCreate, FolderResponse, FolderUpdate
from ..dependencies import get_current_active_user

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
            if os.path.exists(doc.file_path):
                try:
                    os.remove(doc.file_path)
                except Exception as e:
                    logger.error(f"Failed to delete file {doc.file_path} during folder deletion: {e}")
            
            # Delete index and document
            db.query(DocumentIndex).filter(DocumentIndex.document_id == doc.id).delete()
            db.delete(doc)

        # 2. Recursively delete subfolders
        subfolders = db.query(Folder).filter(Folder.parent_id == fid).all()
        for sub in subfolders:
            recursive_delete(sub.id)
            db.delete(sub)

    # Note: Ensure os and logger are imported in folders.py
    import os
    import logging
    logger = logging.getLogger(__name__)

    recursive_delete(folder_id)
    db.delete(db_folder)
    db.commit()
    return {"message": "Folder and all its contents deleted successfully"}

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
    
    # Check if visibility changed
    is_public_new = update_data.get("is_public")
    if is_public_new is not None and is_public_new != db_folder.is_public:
        # Recursive update helper
        def update_children(fid: int, state: bool):
            # Update docs in this folder
            db.query(Document).filter(Document.folder_id == fid).update(
                {Document.is_public: state}, 
                synchronize_session=False
            )
            # Find and update subfolders
            subs = db.query(Folder).filter(Folder.parent_id == fid).all()
            for sub in subs:
                sub.is_public = state
                # Recurse
                update_children(sub.id, state)
        
        update_children(db_folder.id, is_public_new)

    for key, value in update_data.items():
        setattr(db_folder, key, value)
    
    db.commit()
    db.refresh(db_folder)
    return db_folder
