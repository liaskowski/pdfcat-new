from typing import Any, Optional
import requests
from pathlib import Path
from .base import APIBase, APIError

class AuthAPI(APIBase):
    def login(self, username: str, password: str, email: Optional[str] = None) -> str:
        url = f"{self.base_url}/auth/token"
        data = {"username": username, "password": password}
        if email:
            data["email"] = email
            
        resp = self._session.post(
            url,
            data=data,
            timeout=self._timeout,
        )
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Login failed", resp.text)

        payload = resp.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError("Login response missing access_token")

        self._token = str(token)
        return self._token

    def forgot_password(self, email: str) -> dict[str, Any]:
        url = f"{self.base_url}/auth/forgot-password"
        resp = self._session.post(url, data={"email": email}, timeout=self._timeout)
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Failed to request reset code", resp.text)
        return resp.json()

    def reset_password(self, email: str, code: str, new_password: str) -> dict[str, Any]:
        url = f"{self.base_url}/auth/reset-password"
        data = {"email": email, "code": code, "new_password": new_password}
        resp = self._session.post(url, data=data, timeout=self._timeout)
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Password reset failed", resp.text)
        return resp.json()

    def get_me(self) -> dict[str, Any]:
        if not self._token:
            raise RuntimeError("JWT token is not set")

        url = f"{self.base_url}/users/me"
        resp = self._session.get(url, timeout=self._timeout)
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Get current user failed", resp.text)
        return resp.json()

    def update_me(
        self, 
        is_public_profile: Optional[bool] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        current_password: Optional[str] = None
    ) -> dict[str, Any]:
        if not self._token:
            raise RuntimeError("JWT token is not set")

        url = f"{self.base_url}/users/me"
        payload = {}
        if is_public_profile is not None:
            payload["is_public_profile"] = is_public_profile
        if username is not None:
            payload["username"] = username
        if email is not None:
            payload["email"] = email
        if password is not None:
            payload["password"] = password
        if current_password is not None:
            payload["current_password"] = current_password

        resp = self._session.patch(
            url, 
            json=payload, 
            timeout=self._timeout
        )
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Update profile failed", resp.text)
        return resp.json()

    def upload_avatar(self, file_path: str) -> dict[str, Any]:
        if not self._token:
            raise RuntimeError("JWT token is not set")
            
        url = f"{self.base_url}/users/me/avatar"
        
        with open(file_path, "rb") as f:
            filename = Path(file_path).name
            # MIME type guessing could be better, but simple is ok for now
            mime_type = "image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else "image/png"
            
            resp = self._session.post(
                url,
                files={"file": (filename, f, mime_type)},
                timeout=self._timeout
            )
            
        if resp.status_code != 200:
            raise APIError(resp.status_code, "Avatar upload failed", resp.text)
        return resp.json()

