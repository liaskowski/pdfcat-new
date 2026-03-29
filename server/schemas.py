from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    role: str = "user"
    avatar_url: Optional[str] = None
    is_active: bool = True
    is_public_profile: bool = False

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    current_password: Optional[str] = None
    is_public_profile: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    
    class Config:
        from_attributes = True

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int

    class Config:
        from_attributes = True

class FileTypeBase(BaseModel):
    name: str

class FileTypeCreate(FileTypeBase):
    pass

class FileTypeResponse(FileTypeBase):
    id: int

    class Config:
        from_attributes = True

class FolderBase(BaseModel):
    name: str
    parent_id: Optional[int] = None
    is_public: bool = False

class FolderCreate(FolderBase):
    pass

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None
    is_public: Optional[bool] = None

class FolderResponse(FolderBase):
    id: int
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentBase(BaseModel):
    title: str
    is_private: bool = False
    is_public: bool = False
    is_public_edit: bool = False
    is_read_only: bool = False
    encryption_key: Optional[str] = None
    notes: Optional[str] = None
    category_id: Optional[int] = None
    file_type_id: Optional[int] = None
    folder_id: Optional[int] = None
    tags: Optional[str] = None


class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    is_private: Optional[bool] = None
    is_public: Optional[bool] = None
    is_public_edit: Optional[bool] = None
    is_read_only: Optional[bool] = None
    notes: Optional[str] = None
    category_id: Optional[int] = None
    file_type_id: Optional[int] = None
    folder_id: Optional[int] = None
    tags: Optional[str] = None

class DocumentResponse(BaseModel):
    id: int
    title: str
    is_private: bool = False
    is_public: bool = False
    is_public_edit: bool = False
    is_read_only: bool = False
    encryption_key: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None
    filename: str
    upload_date: datetime
    owner_id: int
    owner_username: Optional[str] = None
    owner_email: Optional[str] = None
    owner_avatar_url: Optional[str] = None
    file_size: Optional[int] = None
    category: Optional[CategoryResponse] = None
    file_type: Optional[FileTypeResponse] = None
    folder_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class FileHistoryResponse(BaseModel):
    id: int
    document_id: int
    changed_by_id: int
    changed_by_username: Optional[str] = None
    change_type: str
    field_changed: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_at: datetime
    
    class Config:
        from_attributes = True
