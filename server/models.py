from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import os
from typing import Optional

from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True) # Added email
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")  # admin или user
    avatar_url = Column(String, nullable=True)
    reset_code = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_public_profile = Column(Boolean, default=False, nullable=False)
    
    # Связи
    documents = relationship("Document", back_populates="owner")
    folders = relationship("Folder", back_populates="owner")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    
    documents = relationship("Document", back_populates="category")

class FileType(Base):
    __tablename__ = "file_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

    documents = relationship("Document", back_populates="file_type")

class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey("folders.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="folders")
    parent = relationship("Folder", remote_side=[id], back_populates="children")
    children = relationship("Folder", back_populates="parent", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="folder")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_private = Column(Boolean, default=False, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False) # Public View
    is_public_edit = Column(Boolean, default=False, nullable=False)
    is_read_only = Column(Boolean, default=False, nullable=False)
    encryption_key = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    file_path = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    file_type_id = Column(Integer, ForeignKey("file_types.id"), nullable=True)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)
    tags = Column(Text, nullable=True) # Comma-separated tags
    
    # Связи
    owner = relationship("User", back_populates="documents")
    category = relationship("Category", back_populates="documents")
    file_type = relationship("FileType", back_populates="documents")
    folder = relationship("Folder", back_populates="documents")
    index = relationship("DocumentIndex", back_populates="document", uselist=False)
    history = relationship("FileHistory", back_populates="document", cascade="all, delete-orphan")

    @property
    def owner_username(self) -> Optional[str]:
        return self.owner.username if self.owner else None

    @property
    def owner_email(self) -> Optional[str]:
        return self.owner.email if self.owner else None

    @property
    def owner_avatar_url(self) -> Optional[str]:
        return self.owner.avatar_url if self.owner else None

    @property
    def file_size(self) -> Optional[int]:
        try:
            return os.path.getsize(self.file_path)
        except Exception:
            return None

class FileHistory(Base):
    __tablename__ = "file_history"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    change_type = Column(String, nullable=False)  # 'create', 'update', 'content_update'
    field_changed = Column(String, nullable=True) # 'title', 'category', 'notes', etc.
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    document = relationship("Document", back_populates="history")
    changed_by = relationship("User")

    @property
    def changed_by_username(self) -> Optional[str]:
        return self.changed_by.username if self.changed_by else None

class DocumentIndex(Base):
    __tablename__ = "document_indexes"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, unique=True)
    content_text = Column(Text, nullable=True)  # Для поиска
    
    # Связи
    document = relationship("Document", back_populates="index")
