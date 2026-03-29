import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ManagerAPIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.token: Optional[str] = None
        self.headers: Dict[str, str] = {}
        self.timeout = 5 # seconds

    def login(self, username: str, password: str) -> bool:
        url = f"{self.base_url}/auth/token"
        try:
            response = requests.post(url, data={"username": username, "password": password}, timeout=self.timeout)
            if response.status_code == 200:
                self.token = response.json().get("access_token")
                self.headers = {"Authorization": f"Bearer {self.token}"}
                return True
            return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/admin/stats"
        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_users(self) -> list:
        url = f"{self.base_url}/users/"
        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def delete_user(self, user_id: int):
        url = f"{self.base_url}/api/v1/admin/users/{user_id}"
        response = requests.delete(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()

    def admin_change_password(self, user_id: int, new_password: str):
        url = f"{self.base_url}/api/v1/admin/users/{user_id}/password"
        response = requests.post(url, data={"new_password": new_password}, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def create_user(self, username: str, email: Optional[str], password: Optional[str], role: str = "user"):
        url = f"{self.base_url}/users"
        data = {"username": username, "role": role}
        if email: data["email"] = email
        if password: data["password"] = password
        
        response = requests.post(url, data=data, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def save_backup_to_file(self, target_path: str):
        url = f"{self.base_url}/api/v1/admin/backup"
        with requests.post(url, headers=self.headers, timeout=self.timeout, stream=True) as r:
            r.raise_for_status()
            with open(target_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

    def reindex(self) -> str:
        url = f"{self.base_url}/api/v1/admin/reindex"
        response = requests.post(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json().get("message", "")

    def merge_tags(self, old_tag: str, new_tag: str) -> str:
        url = f"{self.base_url}/api/v1/admin/merge-tags"
        params = {"old_tag": old_tag, "new_tag": new_tag}
        response = requests.post(url, params=params, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json().get("message", "")

    def get_categories(self) -> list:
        url = f"{self.base_url}/categories/"
        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def create_category(self, name: str):
        url = f"{self.base_url}/categories/"
        response = requests.post(url, json={"name": name}, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_file_types(self) -> list:
        url = f"{self.base_url}/file_types/"
        response = requests.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def create_file_type(self, name: str):
        url = f"{self.base_url}/file_types/"
        response = requests.post(url, json={"name": name}, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_history(self, limit: int = 100) -> list:
        url = f"{self.base_url}/api/v1/admin/history"
        try:
            response = requests.get(url, headers=self.headers, params={"limit": limit}, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return []

    def auto_tag(self) -> str:
        """
        Trigger automatic tagging for all documents based on content.
        Returns status message.
        """
        url = f"{self.base_url}/api/v1/admin/auto-tag"
        response = requests.post(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json().get("message", "")

