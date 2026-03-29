from dataclasses import dataclass
from typing import Any, Optional

@dataclass(frozen=True)
class APICategory:
    id: int
    name: str

    @staticmethod
    def from_json(data: dict[str, Any]) -> "APICategory":
        return APICategory(id=int(data["id"]), name=str(data["name"]))


@dataclass(frozen=True)
class APIFileType:
    id: int
    name: str

    @staticmethod
    def from_json(data: dict[str, Any]) -> "APIFileType":
        return APIFileType(id=int(data["id"]), name=str(data["name"]))


@dataclass(frozen=True)
class APIFolder:
    id: int
    name: str
    owner_id: int
    parent_id: Optional[int] = None
    is_public: bool = False
    created_at: Optional[str] = None

    @staticmethod
    def from_json(data: dict[str, Any]) -> "APIFolder":
        return APIFolder(
            id=int(data["id"]),
            name=str(data["name"]),
            owner_id=int(data["owner_id"]),
            parent_id=data.get("parent_id"),
            is_public=bool(data.get("is_public", False)),
            created_at=data.get("created_at")
        )

@dataclass(frozen=True)
class APIFileHistory:
    id: int
    document_id: int
    changed_by_id: int
    change_type: str
    changed_at: str
    field_changed: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by_username: Optional[str] = None
    
    @staticmethod
    def from_json(data: dict[str, Any]) -> "APIFileHistory":
        return APIFileHistory(
            id=int(data["id"]),
            document_id=int(data["document_id"]),
            changed_by_id=int(data["changed_by_id"]),
            change_type=str(data["change_type"]),
            changed_at=str(data["changed_at"]),
            field_changed=data.get("field_changed"),
            old_value=data.get("old_value"),
            new_value=data.get("new_value"),
            changed_by_username=data.get("changed_by_username"),
        )

@dataclass(frozen=True)
class APIUser:
    id: int
    username: str
    email: Optional[str] = None
    role: str = "user"
    is_active: bool = True
    avatar_url: Optional[str] = None
    is_public_profile: bool = False

    @staticmethod
    def from_json(data: dict[str, Any]) -> "APIUser":
        return APIUser(
            id=int(data["id"]),
            username=str(data["username"]),
            email=data.get("email"),
            role=str(data.get("role", "user")),
            is_active=bool(data.get("is_active", True)),
            avatar_url=data.get("avatar_url"),
            is_public_profile=bool(data.get("is_public_profile", False))
        )


@dataclass(frozen=True)
class APIDocument:
    id: int
    title: str
    filename: str
    upload_date: str
    owner_id: int
    category: Optional[APICategory]
    file_type: Optional[APIFileType]
    is_private: bool
    is_public: bool
    is_public_edit: bool
    is_read_only: bool
    encryption_key: Optional[str] = None
    folder_id: Optional[int] = None
    notes: Optional[str] = None
    tags: Optional[str] = None
    owner_username: Optional[str] = None
    owner_email: Optional[str] = None
    owner_avatar_url: Optional[str] = None
    file_size: Optional[int] = None
    content: Optional[str] = None

    @staticmethod
    def from_json(data: dict[str, Any]) -> "APIDocument":
        raw_private = data.get("is_private")
        is_private = False
        if isinstance(raw_private, bool):
            is_private = raw_private
        elif isinstance(raw_private, (int, float)):
            is_private = bool(raw_private)
        elif isinstance(raw_private, str):
            is_private = raw_private.strip().lower() in {"1", "true", "yes", "y"}
            
        raw_public = data.get("is_public_edit")
        is_public_edit = False
        if isinstance(raw_public, bool):
            is_public_edit = raw_public
        elif isinstance(raw_public, (int, float)):
            is_public_edit = bool(raw_public)
        elif isinstance(raw_public, str):
            is_public_edit = raw_public.strip().lower() in {"1", "true", "yes", "y"}

        # is_public (View)
        raw_public_view = data.get("is_public")
        is_public = False
        if isinstance(raw_public_view, bool):
            is_public = raw_public_view
        elif isinstance(raw_public_view, (int, float)):
            is_public = bool(raw_public_view)
        elif isinstance(raw_public_view, str):
            is_public = raw_public_view.strip().lower() in {"1", "true", "yes", "y"}
        
        raw_read_only = data.get("is_read_only")
        is_read_only = False
        if isinstance(raw_read_only, bool):
            is_read_only = raw_read_only
        elif isinstance(raw_read_only, (int, float)):
            is_read_only = bool(raw_read_only)
        elif isinstance(raw_read_only, str):
            is_read_only = raw_read_only.strip().lower() in {"1", "true", "yes", "y"}

        category_data = data.get("category")
        category = APICategory.from_json(category_data) if category_data else None

        file_type_data = data.get("file_type")
        file_type = APIFileType.from_json(file_type_data) if file_type_data else None

        return APIDocument(
            id=int(data["id"]),
            title=str(data["title"]),
            filename=str(data["filename"]),
            upload_date=str(data["upload_date"]),
            owner_id=int(data["owner_id"]),
            category=category,
            file_type=file_type,
            is_private=is_private,
            is_public=is_public,
            is_public_edit=is_public_edit,
            is_read_only=is_read_only,
            encryption_key=data.get("encryption_key"),
            folder_id=data.get("folder_id"),
            notes=data.get("notes"),
            tags=data.get("tags"),
            owner_username=data.get("owner_username"),
            owner_email=data.get("owner_email"),
            owner_avatar_url=data.get("owner_avatar_url"),
            file_size=data.get("file_size"),
            content=data.get("content"),
        )
