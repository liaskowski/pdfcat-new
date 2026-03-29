"""
Centralized authentication utilities for consistent API security.
This prevents authorization mismatches between endpoints.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from .database import get_db
from .models import User
from .auth import get_current_active_user, get_current_active_user_optional


def require_auth(
    allow_query_param: bool = False,
    require_admin: bool = False
):
    """
    Centralized authentication dependency factory.
    
    Args:
        allow_query_param: If True, allows token via query param (for iframe compatibility)
        require_admin: If True, requires admin role
    
    Returns:
        Dependency function that validates authentication
    """
    def auth_dependency(
        db: Session = Depends(get_db),
        token: Optional[str] = None,
        current_user: Optional[User] = None
    ):
        if allow_query_param and token and not current_user:
            # Query param fallback for iframe compatibility
            current_user = get_current_active_user_optional(db, token)
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )
        elif not current_user:
            # Standard Authorization header validation
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        if require_admin and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return current_user
    
    return auth_dependency


# Standard authentication dependencies
AuthUser = Depends(require_auth())
AuthAdmin = Depends(require_auth(require_admin=True))
AuthUserOptional = Depends(require_auth(allow_query_param=True))
