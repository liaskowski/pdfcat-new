import secrets
import string
from typing import Optional
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Form, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import Token, UserResponse, UserUpdate
from ..security import authenticate_user, create_access_token, get_password_hash, verify_password
from ..config import settings
from ..dependencies import get_current_active_user, get_current_admin
from ..services.email_service import send_welcome_email, send_reset_email

router = APIRouter(tags=["auth"])

@router.post("/auth/forgot-password")
async def forgot_password(
    background_tasks: BackgroundTasks,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """Запрос кода восстановления пароля"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Don't reveal if user exists for security
        return {"message": "If this email is registered, a code has been sent."}
    
    # Generate 6-digit code
    code = ''.join(secrets.choice(string.digits) for i in range(6))
    user.reset_code = code
    db.commit()
    
    background_tasks.add_task(send_reset_email, email, code)
    return {"message": "If this email is registered, a code has been sent."}

@router.post("/auth/reset-password")
async def reset_password(
    email: str = Form(...),
    code: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Сброс пароля по коду из письма"""
    user = db.query(User).filter(User.email == email, User.reset_code == code).first()
    if not user or not code:
        raise HTTPException(status_code=400, detail="Invalid email or code")
    
    user.hashed_password = get_password_hash(new_password)
    user.reset_code = None # Clear code
    db.commit()
    return {"message": "Password reset successful"}

@router.post("/auth/token", response_model=Token)
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Логин и получение JWT токена (Username + Password)"""
    user = authenticate_user(db, username, password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
            
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/users", response_model=UserResponse)
async def create_user(
    background_tasks: BackgroundTasks,
    username: str = Form(...),
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    role: str = Form("user"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Создание нового пользователя (только админ)"""
    # Проверка существования пользователя
    db_user = db.query(User).filter(User.username == username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    if email:
        db_email = db.query(User).filter(User.email == email).first()
        if db_email:
             raise HTTPException(status_code=400, detail="Email already registered")

    # Handle Password
    temp_password = password
    if not temp_password:
        alphabet = string.ascii_letters + string.digits
        temp_password = ''.join(secrets.choice(alphabet) for i in range(10))

    # Создание нового пользователя
    hashed_password = get_password_hash(temp_password)
    db_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        role=role if role in ["admin", "user"] else "user",
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Send Welcome Email in background
    if email:
        background_tasks.add_task(send_welcome_email, email, username, temp_password)

    return db_user

@router.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Получение информации о текущем пользователе"""
    return current_user

@router.patch("/users/me", response_model=UserResponse)
async def update_users_me(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Обновление профиля текущего пользователя"""
    if user_update.username is not None and user_update.username != current_user.username:
        existing_user = db.query(User).filter(User.username == user_update.username, User.id != current_user.id).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = user_update.username
        
    if user_update.email is not None and user_update.email != current_user.email:
        existing_email = db.query(User).filter(User.email == user_update.email).first()
        if existing_email:
             raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = user_update.email

    if user_update.password is not None:
        if not user_update.current_password:
            raise HTTPException(status_code=400, detail="Current password required to change password")
        if not verify_password(user_update.current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect current password")
        current_user.hashed_password = get_password_hash(user_update.password)

    if user_update.is_public_profile is not None:
        current_user.is_public_profile = user_update.is_public_profile
    
    db.commit()
    db.refresh(current_user)
    return current_user
