from fastapi import Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import logging
from typing import Optional

from .config import settings
from .database import get_db
from .models import User
from .schemas import TokenData
from .security import oauth2_scheme

logger = logging.getLogger(__name__)

async def get_current_user(
    token_header: Optional[str] = Depends(oauth2_scheme),
    token_query: Optional[str] = Query(None, alias="token"),
    db: Session = Depends(get_db)
):
    """Получение текущего пользователя из JWT токена (заголовок или query-параметр)"""
    token = token_header or token_query
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        logger.warning("No token provided in header or query")
        raise credentials_exception

    try:
        logger.debug(f"Decoding token: {token[:20]}...")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("Token has no 'sub' claim")
            raise credentials_exception
        logger.debug(f"Token decoded successfully, user_id: {user_id}")
        token_data = TokenData(user_id=user_id)
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Token error: {e}")
        raise credentials_exception

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        logger.warning(f"User {token_data.user_id} not found in database")
        raise credentials_exception
    return user

async def get_current_user_optional(
    db: Session = Depends(get_db),
    token: Optional[str] = Query(None),
) -> Optional[User]:
    """Получение текущего пользователя из токена (может вернуть None)"""
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        user = db.query(User).filter(User.id == user_id).first()
        return user
    except Exception:
        return None

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """Получение активного пользователя"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_active_user_optional(
    db: Session = Depends(get_db),
    token: Optional[str] = Query(None),
) -> Optional[User]:
    """Получение активного пользователя (может вернуть None)"""
    user = await get_current_user_optional(db, token)
    if user and not user.is_active:
        return None
    return user

async def get_current_admin(current_user: User = Depends(get_current_active_user)):
    """Проверка прав администратора"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
