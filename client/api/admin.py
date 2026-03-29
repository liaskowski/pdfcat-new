from typing import Any, Optional, List
import requests
from .base import APIBase, APIError
from .schemas import APIUser

from .config import config

class AdminAPI(APIBase):
    def create_user(self, username: str, password: Optional[str] = None, email: Optional[str] = None, role: str = "user") -> dict[str, Any]:
        """Создание нового пользователя (Admin only)."""
        if not self._token:
            raise RuntimeError("JWT token is not set")

        url = config.get_url("/users")
        data = {"username": username, "role": role}
        if password:
            data["password"] = password
        if email:
            data["email"] = email

        resp = self._session.post(
            url,
            data=data,
            timeout=self._timeout,
        )
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Create user failed", resp.text)
        return resp.json()

    def get_public_users(self) -> List[APIUser]:
        if not self._token:
            raise RuntimeError("JWT token is not set")
        
        url = config.get_url("/users/public")
        resp = self._session.get(url, timeout=self._timeout)
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Failed to get public users", resp.text)
        return [APIUser.from_json(item) for item in resp.json()]

    def get_all_users(self) -> List[APIUser]:
        if not self._token:
            raise RuntimeError("JWT token is not set")
        
        url = config.get_url("/users/")
        resp = self._session.get(url, timeout=self._timeout)
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Failed to get users", resp.text)
        return [APIUser.from_json(item) for item in resp.json()]

    def delete_user(self, user_id: int) -> None:
        if not self._token:
            raise RuntimeError("JWT token is not set")
        
        url = config.get_url(f"/admin/users/{user_id}")
        resp = self._session.delete(url, timeout=self._timeout)
        if resp.status_code not in [200, 204]:
             raise APIError(resp.status_code, "Failed to delete user", resp.text)
