from typing import Any, Optional, List
import requests
from pathlib import Path
from .base import APIBase, APIError
from .config import config
from .schemas import APIDocument, APIFolder, APICategory, APIFileType, APIFileHistory

class DocumentsAPI(APIBase):
    def upload_file(
        self,
        file_path: str,
        title: str,
        category_id: Optional[int],
        file_type_id: Optional[int] = None,
        use_ocr: bool = True,
        is_private: bool = False,
        is_public: bool = False,
        is_public_edit: bool = False,
        is_read_only: bool = False,
        encryption_key: Optional[str] = None,
        folder_id: Optional[int] = None,
        notes: str = "",
        tags: Optional[str] = None,
    ) -> APIDocument:
        if not self._token:
            raise RuntimeError("JWT token is not set")

        url = config.get_url("/documents/upload")
        data: dict[str, Any] = {
            "title": title,
            "is_private": "true" if is_private else "false",
            "is_public": "true" if is_public else "false",
            "is_public_edit": "true" if is_public_edit else "false",
            "is_read_only": "true" if is_read_only else "false",
            "use_ocr": "true" if use_ocr else "false",
            "notes": notes,
        }
        if tags is not None:
            data["tags"] = tags
        if category_id is not None:
            data["category_id"] = category_id
        if file_type_id is not None:
            data["file_type_id"] = file_type_id
        if folder_id is not None:
            data["folder_id"] = folder_id
        if encryption_key:
            data["encryption_key"] = encryption_key

        with open(file_path, "rb") as f:
            filename = Path(file_path).name
            resp = self._session.post(
                url,
                headers=self._headers(),
                files={"file": (filename, f, "application/pdf")},
                data=data,
                timeout=self._timeout,
            )

        if resp.status_code != 200:
            raise APIError(resp.status_code, "Upload failed", resp.text)

        return APIDocument.from_json(resp.json())

    def search_documents(
        self,
        query: str
    ) -> list[APIDocument]:
        if not self._token:
            raise RuntimeError("JWT token is not set")

        url = config.get_url("/search")
        params = {"q": query}

        # Use session for connection pooling (NOT direct requests)
        resp = self._session.get(
            url,
            headers=self._headers(),
            params=params,
            timeout=self._timeout,
        )
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Search failed", resp.text)

        return [APIDocument.from_json(item) for item in resp.json()]

    def get_suggestions(self, query: str) -> list[str]:
        """Получение подсказок для строки поиска."""
        if not self._token:
            raise RuntimeError("JWT token is not set")

        url = config.get_url("/suggestions")
        resp = self._session.get(
            url,
            params={"q": query},
            timeout=self._timeout,
        )
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Get suggestions failed", resp.text)

        return resp.json()

    def get_document(self, document_id: int) -> APIDocument:
        if not self._token:
            raise RuntimeError("JWT token is not set")

        url = config.get_url(f"/documents/{document_id}")
        resp = self._session.get(
            url,
            timeout=self._timeout,
        )
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Get document failed", resp.text)

        return APIDocument.from_json(resp.json())

    def update_document(
        self,
        document_id: int,
        title: str,
        category_id: Optional[int],
        file_type_id: Optional[int],
        is_private: bool,
        is_public: bool,
        is_public_edit: bool,
        notes: str,
        is_read_only: Optional[bool] = None,
        tags: Optional[str] = None,
        folder_id: Optional[int] = None,
    ) -> APIDocument:
        """Обновление метаданных документа."""
        if not self._token:
            raise RuntimeError("JWT token is not set")

        print(f"DEBUG API: Updating document {document_id} with title='{title}'")
        
        url = config.get_url(f"/documents/{document_id}")
        payload = {
            "title": title,
            "category_id": category_id,
            "file_type_id": file_type_id,
            "is_private": is_private,
            "is_public": is_public,
            "is_public_edit": is_public_edit,
            "notes": notes,
        }
        
        # Add optional fields only if provided
        if is_read_only is not None:
            payload["is_read_only"] = is_read_only
        if tags is not None:
            payload["tags"] = tags
        if folder_id is not None:
            payload["folder_id"] = folder_id

        resp = self._session.put(
            url,
            json=payload,
            timeout=self._timeout,
        )

        print(f"DEBUG API: Update response status: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"DEBUG API: Update response body: {resp.text}")
            raise APIError(resp.status_code, "Update document failed", resp.text)

        result = APIDocument.from_json(resp.json())
        print(f"DEBUG API: Updated document returned: id={result.id}, title='{result.title}'")
        return result

    def update_document_content(
        self,
        document_id: int,
        file_path: str,
        use_ocr: bool = True,
    ) -> APIDocument:
        """Обновление содержимого файла (замена файла)."""
        if not self._token:
            raise RuntimeError("JWT token is not set")

        url = config.get_url(f"/documents/{document_id}/content")
        data: dict[str, Any] = {
            "use_ocr": "true" if use_ocr else "false",
        }

        with open(file_path, "rb") as f:
            filename = Path(file_path).name
            resp = self._session.put(
                url,
                files={"file": (filename, f, "application/pdf")},
                data=data,
                timeout=self._timeout,
            )

        if resp.status_code != 200:
            raise APIError(resp.status_code, "Update content failed", resp.text)

        return APIDocument.from_json(resp.json())

    def get_document_history(self, document_id: int) -> List[APIFileHistory]:
        if not self._token:
            raise RuntimeError("JWT token is not set")

        url = config.get_url(f"/documents/{document_id}/history")
        resp = self._session.get(
            url,
            timeout=self._timeout,
        )
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Get history failed", resp.text)

        return [APIFileHistory.from_json(item) for item in resp.json()]

    def get_preview_png(self, document_id: int) -> bytes:
        if not self._token:
            raise RuntimeError("JWT token is not set")

        url = config.get_url(f"/documents/{document_id}/preview")
        resp = self._session.get(
            url,
            timeout=self._timeout,
        )
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Preview failed", resp.text)
        return resp.content

    def download_document(self, document_id: int) -> bytes:
        if not self._token:
            raise RuntimeError("JWT token is not set")

        # Start monitoring
        self._start_operation(f"Download document {document_id}")

        print(f"DEBUG API: Downloading document {document_id}")
        print(f"DEBUG API: Token present: {bool(self._token)}")
        print(f"DEBUG API: Token first 20 chars: {self._token[:20] if self._token else 'None'}")
        print(f"DEBUG API: Session headers: {dict(self._session.headers)}")

        try:
            url = config.get_url(f"/documents/{document_id}/download")
            resp = self._session.get(
                url,
                timeout=self._timeout,
            )
            
            print(f"DEBUG API: Download response status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"DEBUG API: Download response body: {resp.text}")
                raise APIError(resp.status_code, "Download failed", resp.text)
            
            return resp.content
        finally:
            self._end_operation()

    def list_documents(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        folder_id: Optional[int] = None,
        owner_id: Optional[int] = None,
        view_mode: str = "my" # my, shared, community
    ) -> list[APIDocument]:
        if not self._token:
            raise RuntimeError("JWT token is not set")

        url = config.get_url("/documents/")
        params: dict[str, Any] = {"skip": skip, "limit": limit, "view_mode": view_mode}
        if folder_id is not None:
            params["folder_id"] = folder_id
        if owner_id is not None:
            params["owner_id"] = owner_id

        resp = self._session.get(
            url,
            params=params,
            timeout=self._timeout,
        )
        if resp.status_code != 200:
            raise APIError(resp.status_code, "List documents failed", resp.text)

        return [APIDocument.from_json(item) for item in resp.json()]

    # Folder Management
    def create_folder(self, name: str, parent_id: Optional[int] = None, is_public: bool = False) -> APIFolder:
        if not self._token:
            raise RuntimeError("JWT token is not set")
        
        url = config.get_url("/folders/")
        payload = {"name": name, "is_public": is_public}
        if parent_id is not None:
            payload["parent_id"] = parent_id
            
        resp = self._session.post(url, json=payload, timeout=self._timeout)
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Failed to create folder", resp.text)
        return APIFolder.from_json(resp.json())

    def get_folders(
        self, 
        parent_id: Optional[int] = None, 
        owner_id: Optional[int] = None,
        public_only: bool = False
    ) -> List[APIFolder]:
        if not self._token:
            raise RuntimeError("JWT token is not set")

        url = config.get_url("/folders/")
        params = {}
        if parent_id is not None:
            params["parent_id"] = parent_id
        if owner_id is not None:
            params["owner_id"] = owner_id
        if public_only:
            params["public_only"] = "true"
            
        resp = self._session.get(url, params=params, timeout=self._timeout)
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Failed to get folders", resp.text)
        return [APIFolder.from_json(item) for item in resp.json()]

    def delete_folder(self, folder_id: int) -> None:
        if not self._token:
            raise RuntimeError("JWT token is not set")

        url = config.get_url(f"/folders/{folder_id}")
        resp = self._session.delete(url, timeout=self._timeout)
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Delete folder failed", resp.text)

    def update_folder(
        self, 
        folder_id: int, 
        name: Optional[str] = None, 
        parent_id: Optional[int] = None, 
        is_public: Optional[bool] = None
    ) -> APIFolder:
        if not self._token:
            raise RuntimeError("JWT token is not set")
        
        url = config.get_url(f"/folders/{folder_id}")
        payload = {}
        if name is not None:
            payload["name"] = name
        if parent_id is not None:
            payload["parent_id"] = parent_id
        if is_public is not None:
            payload["is_public"] = is_public
        
        resp = self._session.patch(url, json=payload, timeout=self._timeout)
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Failed to update folder", resp.text)
        return APIFolder.from_json(resp.json())

    def delete_document(self, document_id: int) -> None:
        """Удаление документа"""
        if not self._token:
            raise RuntimeError("JWT token is not set")

        url = config.get_url(f"/documents/{document_id}")
        resp = self._session.delete(
            url,
            timeout=self._timeout,
        )
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Delete document failed", resp.text)

    def duplicate_document(self, document_id: int, folder_id: Optional[int] = None) -> APIDocument:
        if not self._token:
            raise RuntimeError("JWT token is not set")

        url = config.get_url(f"/documents/{document_id}/duplicate")
        data = {}
        if folder_id is not None:
            data["folder_id"] = folder_id

        resp = self._session.post(
            url,
            data=data,
            timeout=self._timeout,
        )
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Duplicate failed", resp.text)

        return APIDocument.from_json(resp.json())

    # Category Management
    def get_categories(self) -> List[APICategory]:
        url = config.get_url("/categories/")
        resp = self._session.get(url, timeout=self._timeout)
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Failed to get categories", resp.text)
        return [APICategory.from_json(item) for item in resp.json()]

    def create_category(self, name: str) -> APICategory:
        url = config.get_url("/categories/")
        resp = self._session.post(url, json={"name": name}, timeout=self._timeout)
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Failed to create category", resp.text)
        return APICategory.from_json(resp.json())

    def delete_category(self, category_id: int) -> None:
        url = config.get_url(f"/categories/{category_id}")
        resp = self._session.delete(url, timeout=self._timeout)
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Failed to delete category", resp.text)

    def update_category(self, category_id: int, name: str) -> APICategory:
        url = config.get_url(f"/categories/{category_id}")
        resp = self._session.put(url, json={"name": name}, timeout=self._timeout)
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Failed to update category", resp.text)
        return APICategory.from_json(resp.json())

    # File Type Management
    def get_file_types(self) -> List[APIFileType]:
        url = config.get_url("/file_types/")
        resp = self._session.get(url, timeout=self._timeout)
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Failed to get file types", resp.text)
        return [APIFileType.from_json(item) for item in resp.json()]

    def create_file_type(self, name: str) -> APIFileType:
        url = config.get_url("/file_types/")
        resp = self._session.post(url, json={"name": name}, timeout=self._timeout)
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Failed to create file type", resp.text)
        return APIFileType.from_json(resp.json())

    def delete_file_type(self, file_type_id: int) -> None:
        url = config.get_url(f"/file_types/{file_type_id}")
        resp = self._session.delete(url, timeout=self._timeout)
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Failed to delete file type", resp.text)

    def update_file_type(self, file_type_id: int, name: str) -> APIFileType:
        url = config.get_url(f"/file_types/{file_type_id}")
        resp = self._session.put(url, json={"name": name}, timeout=self._timeout)
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Failed to update file type", resp.text)
        return APIFileType.from_json(resp.json())