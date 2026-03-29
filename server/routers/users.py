from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List
import os
import shutil

from ..database import get_db
from ..models import User
from ..schemas import UserResponse
from ..dependencies import get_current_active_user, get_current_admin

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Загрузка аватара пользователя"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Ensure directory exists
    avatar_dir = "server/static/avatars"
    os.makedirs(avatar_dir, exist_ok=True)
    
    # Save file
    # Use user ID in filename to avoid conflicts/junk
    ext = file.filename.split(".")[-1]
    filename = f"user_{current_user.id}.{ext}"
    file_path = os.path.join(avatar_dir, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Update user
    # URL relative to static mount: static/avatars/filename
    # Frontend will prepend base_url
    relative_url = f"static/avatars/{filename}"
    current_user.avatar_url = relative_url
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.get("/", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Получение списка всех пользователей (только для админов)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.get("/public", response_model=List[UserResponse])
async def read_public_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получение списка пользователей с публичными профилями"""
    users = db.query(User).filter(User.is_public_profile == True, User.id != current_user.id).all()
    return users
